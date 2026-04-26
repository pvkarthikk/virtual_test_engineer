/**
 * SDTB Dashboard Application Logic
 */

// Global State
const state = {
    currentView: 'dashboard',
    status: 'offline',
    channels: [],
    devices: [],
    systemConfig: {},
    uiConfig: { layout: 'dashboard', widgets: [] },
    tempWidgets: [],
    editingWidgetIndex: null,
    editingChannelId: null,
    pollTimer: null,
    activeDeviceId: null,
    sse: {
        logs: null,
        channels: {} // channelId -> EventSource
    },
    waveform: {
        activeChannels: new Set(),
        paused: false,
        history: {}, // channelId -> { data: [{t, v}], color, style, enabled }
        plotter: null
    },
    testSteps: [{ cmd: 'WRITE', channel: '', value: '', assert: false }],
    logFilters: { system: true, devices: {}, showDebug: false },
    isBackendAlive: true,
    heartbeatTimer: null,
    layout: null,
    quickWave: { active: false, plotter: null, data: [[], []], channelId: null, paused: false }
};

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    initLayout(); // Initialize GoldenLayout first
    setupNavigation();
    setupSystemControls();
    setupTestEditor();
    setupSettings();
    setupWidgetMapper();
    setupChannelMapper();
    setupWaveformViewer();
    setupTheme(); // Initialize theme toggle
    setupPolling();
    setupSSE();
    setupHeartbeat();
    refreshAllData();
});

const viewTitles = {
    'dashboard': 'Dashboard',
    'devices': 'Device Explorer',
    'channel-mapper': 'Channel Mapper',
    'widget-mapper': 'Widget Mapper',
    'waveform': 'Waveform Viewer',
    'test-editor': 'Test Editor',
    'debug': 'System Logs',
    'settings': 'Settings'
};

function initLayout() {
    const container = document.getElementById('layout-container');
    if (!container) return;
    
    const defaultLayout = {
        settings: {
            showPopoutIcon: false,
            showMaximiseIcon: true,
            showCloseIcon: true
        },
        content: [{
            type: 'row',
            content: [
                {
                    type: 'column',
                    width: 75,
                    content: [
                        { type: 'component', componentName: 'dashboard', title: 'Dashboard' },
                        { type: 'component', componentName: 'debug', title: 'System Logs', height: 30 }
                    ]
                },
                {
                    type: 'component',
                    componentName: 'devices',
                    title: 'Devices',
                    width: 25
                }
            ]
        }]
    };

    let savedLayout = localStorage.getItem('sdtb-layout-v1');
    let config = savedLayout ? JSON.parse(savedLayout) : defaultLayout;

    state.layout = new GoldenLayout(config, $(container));

    Object.keys(viewTitles).forEach(viewId => {
        state.layout.registerComponent(viewId, function(container, componentState) {
            const el = document.getElementById(`view-${viewId}`);
            if (el) {
                container.getElement().append($(el));
                el.style.display = 'flex';
                lucide.createIcons(el);
            }
            container.on('show', () => {
                state.currentView = viewId;
                document.querySelectorAll('.nav-item').forEach(item => {
                    item.classList.toggle('active', item.getAttribute('data-view') === viewId);
                });
                
                // Use a slightly longer timeout to ensure GL has rendered the container
                setTimeout(() => {
                    refreshViewContent(viewId);
                    lucide.createIcons(container.getElement()[0]);
                }, 100);
            });
            container.on('resize', () => {
                if (viewId === 'waveform' && state.waveform.plotter) {
                    const c = document.getElementById('waveform-chart-container');
                    if (c && c.clientWidth > 0) {
                        state.waveform.plotter.setSize({
                            width: c.clientWidth,
                            height: Math.max(50, c.clientHeight)
                        });
                    }
                }
            });
        });
    });

    state.layout.on('stateChanged', () => {
        if (state.layout.isInitialised) {
            const config = state.layout.toConfig();
            localStorage.setItem('sdtb-layout-v1', JSON.stringify(config));
            
            // Trigger a resize for any visible waveform plotter
            const c = document.getElementById('waveform-chart-container');
            if (c && c.clientWidth > 0 && state.waveform.plotter) {
                state.waveform.plotter.setSize({
                    width: c.clientWidth,
                    height: Math.max(50, c.clientHeight)
                });
            }
        }
    });

    state.layout.init();
    $(window).resize(() => { if(state.layout) state.layout.updateSize(); });
}

function refreshViewContent(viewId) {
    if (viewId === 'dashboard') renderDashboard();
    if (viewId === 'widget-mapper') renderWidgetMapper();
    if (viewId === 'channel-mapper') renderChannelMapper();
    if (viewId === 'settings') loadSettings();
    if (viewId === 'devices') refreshDevices();
    if (viewId === 'waveform') initWaveformViewer();
    if (viewId === 'test-editor') renderTestTable();
}

function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.onclick = () => {
            const viewId = item.getAttribute('data-view');
            switchView(viewId);
        };
    });
}

function setupTheme() {
    const btn = document.getElementById('btn-theme-toggle');
    const container = document.getElementById('theme-icon-container');
    if (!btn || !container) return;
    
    // Load preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.documentElement.classList.add('light-theme');
        container.innerHTML = '<i data-lucide="sun"></i>';
        lucide.createIcons();
    }

    btn.onclick = () => {
        const isLight = document.documentElement.classList.toggle('light-theme');
        localStorage.setItem('theme', isLight ? 'light' : 'dark');
        container.innerHTML = `<i data-lucide="${isLight ? 'sun' : 'moon'}"></i>`;
        lucide.createIcons();
        
        // Notify layout engine to resize if needed
        if (state.layout) state.layout.updateSize();
        
        addLog(`Switched to ${isLight ? 'Day' : 'Night'} mode`, 'info');
    };
}

window.resetLayout = () => {
    if (confirm('Are you sure you want to reset the entire workspace layout? All custom panel positions will be lost.')) {
        localStorage.removeItem('sdtb-layout-v1');
        location.reload();
    }
};

function switchView(viewId) {
    if (!state.layout || !state.layout.isInitialised) return;

    state.currentView = viewId;
    
    // Update sidebar active state
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.getAttribute('data-view') === viewId);
    });
    
    // Search for existing component in v1.5.9
    const items = state.layout.root.getItemsByFilter(item => item.config.componentName === viewId);
    if (items.length > 0) {
        // Focus the existing tab
        const item = items[0];
        if (item.parent && item.parent.isStack) {
            item.parent.setActiveContentItem(item);
        }
    } else {
        // Add to the first stack found
        const stacks = state.layout.root.getItemsByType('stack');
        if (stacks.length > 0) {
            stacks[0].addChild({
                type: 'component',
                componentName: viewId,
                title: viewTitles[viewId] || viewId
            });
        } else {
            state.layout.root.addChild({
                type: 'component',
                componentName: viewId,
                title: viewTitles[viewId] || viewId
            });
        }
    }
    
    refreshViewContent(viewId);
}

function setupSystemControls() {
    const btnConnect = document.getElementById('btn-connect');
    const btnDisconnect = document.getElementById('btn-disconnect');
    const btnRestart = document.getElementById('btn-restart');
    if (btnConnect) {
        btnConnect.onclick = async () => {
            updateStatusIndicator('connecting', 'Connecting...');
            try {
                await apiPost('/system/connect');
                syncStatus(true);
                addLog('System connected successfully', 'success');
            } catch (e) {
                syncStatus(false);
                addLog(`Connection failed: ${e.message}`, 'error');
            }
        };
    }
    if (btnDisconnect) {
        btnDisconnect.onclick = async () => {
            try {
                await apiPost('/system/disconnect');
                syncStatus(false);
                addLog('System disconnected', 'info');
            } catch (e) { addLog(`Disconnection failed: ${e.message}`, 'error'); }
        };
    }
    if (btnRestart) {
        btnRestart.onclick = async () => {
            if (!confirm('Are you sure you want to restart?')) return;
            try {
                await apiPost('/system/restart');
                location.reload();
            } catch (e) { addLog(`Restart failed: ${e.message}`, 'error'); }
        };
    }
}

function syncStatus(isConnected) {
    state.status = isConnected ? 'online' : 'offline';
    updateStatusIndicator(state.status, isConnected ? 'Connected' : 'Disconnected');

    const btnConnect = document.getElementById('btn-connect');
    const btnDisconnect = document.getElementById('btn-disconnect');

    if (isConnected) {
        if (btnConnect) btnConnect.classList.add('hidden');
        if (btnDisconnect) btnDisconnect.classList.remove('hidden');
        document.getElementById('dashboard-grid')?.classList.remove('system-offline');
        startPolling();
    } else {
        if (btnConnect) btnConnect.classList.remove('hidden');
        if (btnDisconnect) btnDisconnect.classList.add('hidden');
        document.getElementById('dashboard-grid')?.classList.add('system-offline');
        stopPolling();
    }

    // Refresh UI based on state
    if (state.currentView === 'dashboard') {
        renderDashboard();
    } else if (state.currentView === 'devices') {
        refreshDevices();
        if (state.activeDeviceId) updateDeviceSignalsList(state.activeDeviceId);
    }
}

function updateStatusIndicator(status, text) {
    const indicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.status-text');
    if (indicator) indicator.className = `status-indicator ${status}`;
    if (statusText) statusText.innerText = text;
}

function setupPolling() {
    const intervalSelect = document.getElementById('poll-interval');
    if (intervalSelect) intervalSelect.onchange = () => { if (state.status === 'online') startPolling(); };
}

function setupHeartbeat() {
    if (state.heartbeatTimer) clearInterval(state.heartbeatTimer);
    state.heartbeatTimer = setInterval(checkBackendHealth, 10000);
}

async function checkBackendHealth() {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000);
        const response = await fetch('/system', { signal: controller.signal });
        clearTimeout(timeoutId);

        if (response.ok) {
            if (!state.isBackendAlive) {
                state.isBackendAlive = true;
                document.getElementById('backend-lost-banner').classList.add('hidden');
                addLog('Backend connection restored', 'success');
            }
        } else {
            throw new Error('Response not OK');
        }
    } catch (e) {
        if (state.isBackendAlive) {
            state.isBackendAlive = false;
            document.getElementById('backend-lost-banner').classList.remove('hidden');
            addLog('Backend connection lost', 'error');
            // stop all polling
            stopPolling();
        }
    }
}

function startPolling() {
    stopPolling();
    const intervalEl = document.getElementById('poll-interval');
    const ms = intervalEl ? parseInt(intervalEl.value) : 250;
    state.pollTimer = setInterval(pollDashboard, ms);
}

function stopPolling() { if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; } }

async function pollDashboard() {
    if (state.status !== 'online') return;
    const channelIds = [...new Set(state.uiConfig.widgets.map(w => w.channel))];
    if (channelIds.length === 0) return;
    try {
        await Promise.all(channelIds.map(async (id) => {
            try { await apiGet(`/channel/${id}`); } catch (e) { if (e.message.includes('503')) console.warn(`503 on ${id}`); }
        }));
    } catch (e) { console.error('Poll error', e); }
}

function renderDashboard() {
    const grid = document.getElementById('dashboard-grid');
    if (!grid) return;
    grid.innerHTML = '';

    if (state.status !== 'online') {
        grid.innerHTML = `
            <div class="empty-state" style="grid-row: 1; grid-column: 1 / -1; height: 300px; display: flex; flex-direction: column; justify-content: center; align-items: center; background: rgba(0,0,0,0.2); border-radius: 12px; border: 2px dashed var(--border-color);">
                <i data-lucide="shield-off" style="width: 48px; height: 48px; color: var(--text-muted); margin-bottom: 15px;"></i>
                <h2 style="color: var(--text-main); margin-bottom: 8px;">System Disconnected</h2>
                <p style="color: var(--text-muted);">Please click the <strong>Connect</strong> button in the toolbar to start hardware monitoring.</p>
            </div>`;
        lucide.createIcons();
        return;
    }

    if (state.uiConfig.widgets.length === 0) {
        grid.innerHTML = '<div class="empty-state"><p>No widgets configured. Add some in Widget Mapper.</p></div>';
        return;
    }
    state.uiConfig.widgets.forEach(widget => {
        grid.appendChild(createWidgetCard(widget));
        subscribeToChannel(widget.channel);
    });
}

function createWidgetCard(widget) {
    const card = document.createElement('div');
    card.className = 'widget-card';
    card.id = `widget-${widget.id}`;
    let content = `<div class="widget-header"><span class="widget-label">${widget.label}</span><div class="widget-actions"><button class="btn-icon" onclick="editWidgetById('${widget.id}')"><i data-lucide="edit-2"></i></button></div></div>`;
    if (widget.type === 'gauge') content += `<div class="widget-content gauge-container"><div class="gauge-value" id="val-${widget.id}">--</div><div class="gauge-label">${widget.type}</div></div>`;
    else if (widget.type === 'bar') content += `<div class="widget-content bar-container"><div class="bar-bg"><div class="bar-fill" id="fill-${widget.id}" style="width: 0%"></div></div><div class="widget-value-sm" id="val-${widget.id}">--</div></div>`;
    else if (widget.type === 'waveform') content += `<div class="widget-content waveform-container" style="cursor: pointer;" onclick="openQuickWaveform('${widget.channel}')" title="Click for detail view"><svg viewBox="0 0 100 40" preserveAspectRatio="none"><polyline id="poly-${widget.id}" fill="none" stroke="var(--accent-primary)" stroke-width="1.5" points="0,20 100,20" /></svg><div class="widget-value-sm"><span id="val-${widget.id}">--</span></div></div>`;
    else if (widget.type === 'led') content += `<div class="widget-content led-container"><div class="led-bulb" id="led-${widget.id}"></div><div class="widget-value-sm" id="val-${widget.id}">OFF</div></div>`;
    else if (widget.type === 'toggle') {
        content += `<div class="widget-content toggle-container">
            <label class="switch">
                <input type="checkbox" id="toggle-${widget.id}" onchange="widgetWrite('${widget.channel}', this.checked ? 1 : 0)">
                <span class="slider"></span>
            </label>
            <div class="widget-value-sm" id="val-${widget.id}">OFF</div>
        </div>`;
    }
    else if (widget.type === 'button') content += `<div class="widget-content button-container"><button class="btn btn-primary btn-block" onmousedown="this.innerText='Pressed'; widgetWrite('${widget.channel}', 1)" onmouseup="this.innerText='Released'; widgetWrite('${widget.channel}', 0)" onmouseleave="this.innerText='Released'; widgetWrite('${widget.channel}', 0)" ontouchstart="event.preventDefault(); this.innerText='Pressed'; widgetWrite('${widget.channel}', 1)" ontouchend="this.innerText='Released'; widgetWrite('${widget.channel}', 0)">Released</button></div>`;
    else if (widget.type === 'slider') {
        const ch = state.channels.find(c => c.channel_id === widget.channel);
        const min = ch ? ch.properties.min : 0, max = ch ? ch.properties.max : 100;
        const currentVal = ch ? ch.properties.value : min;
        content += `<div class="widget-content slider-container">
            <input type="range" class="widget-slider" 
                oninput="document.getElementById('val-${widget.id}').innerText = Number(this.value).toFixed(2); widgetWrite('${widget.channel}', this.value)" 
                min="${min}" max="${max}" value="${currentVal}" id="slider-${widget.id}">
            <div class="widget-value-sm" id="val-${widget.id}">${Number(currentVal).toFixed(2)}</div>
        </div>`;
    } else content += `<div class="widget-content numeric-container"><div class="widget-value" id="val-${widget.id}">--</div></div>`;
    card.innerHTML = content;
    lucide.createIcons();
    return card;
}

function updateWidgetValue(widget, val) {
    const valEl = document.getElementById(`val-${widget.id}`);
    if (!valEl) return;
    if (widget.type === 'led') {
        const bulb = document.getElementById(`led-${widget.id}`);
        const isActive = val > 0.5;
        if (bulb) bulb.classList.toggle('active', isActive);
        valEl.innerText = isActive ? 'ON' : 'OFF';
    } else if (widget.type === 'toggle') {
        const toggle = document.getElementById(`toggle-${widget.id}`);
        const isActive = val > 0.5;
        if (toggle) toggle.checked = isActive;
        valEl.innerText = isActive ? 'ON' : 'OFF';
    } else if (widget.type === 'gauge' || widget.type === 'numeric' || widget.type === 'slider') {
        valEl.innerText = Number(val).toFixed(2);
        if (widget.type === 'slider') { 
            const slider = document.getElementById(`slider-${widget.id}`); 
            if (slider && document.activeElement !== slider) slider.value = val; 
        }
    } else if (widget.type === 'bar') {
        const fill = document.getElementById(`fill-${widget.id}`);
        if (fill) {
            const ch = state.channels.find(c => c.channel_id === widget.channel);
            const min = ch ? ch.properties.min : 0, max = ch ? ch.properties.max : 100;
            fill.style.width = `${Math.min(Math.max(((val - min) / (max - min)) * 100, 0), 100)}%`;
        }
        valEl.innerText = Number(val).toFixed(2);
    } else if (widget.type === 'waveform') {
        const poly = document.getElementById(`poly-${widget.id}`);
        if (poly) updateWaveform(poly, val, widget);
        valEl.innerText = Number(val).toFixed(2);
    } else valEl.innerText = Number(val).toFixed(2);
}

const waveformHistory = {};
function updateWaveform(poly, val, widget) {
    if (!waveformHistory[widget.id]) waveformHistory[widget.id] = new Array(50).fill(20);
    const ch = state.channels.find(c => c.channel_id === widget.channel);
    const min = ch ? ch.properties.min : 0, max = ch ? ch.properties.max : 100, range = max - min || 1;
    waveformHistory[widget.id].push(40 - ((val - min) / range * 40));
    console.log(waveformHistory[widget.id]);
    if (waveformHistory[widget.id].length > 50) waveformHistory[widget.id].shift();
    poly.setAttribute('points', waveformHistory[widget.id].map((v, i) => `${i * 2},${v}`).join(' '));
}

window.widgetWrite = async (id, val) => { try { await apiPut(`/channel/${id}?value=${val}`, {}); } catch (e) { addLog(`Write failed: ${e.message}`, 'error'); } };

async function refreshAllData() {
    console.log('[SDTB] refreshAllData: starting...');
    await Promise.all([refreshChannels(), refreshUIConfig()]);
    try {
        console.log('[SDTB] Checking /system status...');
        const status = await apiGet('/system');
        console.log('[SDTB] System status:', status);
        syncStatus(status.is_connected === true);
    } catch (e) { console.error('[SDTB] Status check failed:', e); addLog('Status check fail: ' + e.message, 'error'); }
    renderDashboard();
    console.log('[SDTB] refreshAllData: complete');
}

async function refreshChannels() {
    try {
        state.channels = await apiGet('/channel');
        if (state.currentView === 'test-editor') renderTestTable();
    } catch (e) { addLog('Channels fail', 'error'); }
}
async function refreshUIConfig() { try { state.uiConfig = await apiGet('/ui/config'); } catch (e) { addLog('UI fail', 'error'); } }

function setupWidgetMapper() {
    const btnAdd = document.getElementById('btn-add-widget');
    if (btnAdd) btnAdd.onclick = () => { state.editingWidgetIndex = null; openWidgetModal(); };
}

function renderWidgetMapper() {
    const tableBody = document.getElementById('widget-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '';
    state.uiConfig.widgets.forEach((widget, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `<td><strong>${widget.label}</strong></td><td><code>${widget.type}</code></td><td><code>${widget.channel}</code></td><td><div class="flex-row" style="gap: 10px"><button class="btn btn-outline btn-sm" onclick="editWidget(${index})"><i data-lucide="edit"></i> Edit</button><button class="btn btn-outline btn-sm" onclick="removeWidget(${index})"><i data-lucide="trash-2" style="color: #ef4444"></i></button></div></td>`;
        tableBody.appendChild(row);
    });
    lucide.createIcons();
}

window.editWidget = (i) => { state.editingWidgetIndex = i; openWidgetModal(state.uiConfig.widgets[i]); };
window.editWidgetById = (id) => { const i = state.uiConfig.widgets.findIndex(w => w.id === id); if (i !== -1) { switchView('widget-mapper'); editWidget(i); } };
window.removeWidget = (i) => { state.uiConfig.widgets.splice(i, 1); renderWidgetMapper(); };

function openWidgetModal(w = null) {
    const modal = document.getElementById('modal-widget');
    const inputLabel = document.getElementById('widget-label'), selectChannel = document.getElementById('widget-channel'), selectType = document.getElementById('widget-type');
    inputLabel.value = w ? w.label : '';
    selectChannel.innerHTML = '';
    state.channels.forEach(ch => { const opt = document.createElement('option'); opt.value = ch.channel_id; opt.text = ch.channel_id; if (w && w.channel === ch.channel_id) opt.selected = true; selectChannel.appendChild(opt); });
    if (w) selectType.value = w.type;
    modal.classList.add('active');
    document.getElementById('btn-widget-cancel').onclick = () => modal.classList.remove('active');
    document.getElementById('btn-widget-save').onclick = () => {
        const newW = { id: w ? w.id : `w${Date.now()}`, label: inputLabel.value, channel: selectChannel.value, type: selectType.value, position: { row: 0, col: 0 } };
        if (state.editingWidgetIndex !== null) state.uiConfig.widgets[state.editingWidgetIndex] = newW;
        else state.uiConfig.widgets.push(newW);
        modal.classList.remove('active');
        renderWidgetMapper();
    };
}

const btnSaveWidgets = document.getElementById('btn-save-widgets');
if (btnSaveWidgets) btnSaveWidgets.onclick = async () => { try { await apiPut('/ui/config', state.uiConfig); addLog('Saved UI', 'success'); if (state.status === 'online') startPolling(); } catch (e) { addLog('Save UI fail', 'error'); } };

function setupChannelMapper() {
    const btnAdd = document.getElementById('btn-add-channel');
    if (btnAdd) btnAdd.onclick = () => { state.editingChannelId = null; openChannelModal(); };
}

async function renderChannelMapper() {
    await refreshChannels();
    const table = document.getElementById('channel-mapping-table');
    if (!table) return;
    table.innerHTML = '';
    state.channels.forEach(ch => {
        const row = document.createElement('tr');
        row.innerHTML = `<td>${ch.channel_id}</td><td>${ch.device_id}</td><td>${ch.signal_id}</td><td>${ch.properties.unit}</td><td>${ch.properties.min}</td><td>${ch.properties.max}</td><td><input type="number" step="any" class="table-input" id="read-${ch.channel_id}"></td><td><div class="flex-row" style="gap: 5px"><button class="btn btn-outline btn-sm" onclick="writeSingleChannel('${ch.channel_id}')" title="Write"><i data-lucide="edit-3"></i></button><button class="btn btn-outline btn-sm" onclick="readSingleChannel('${ch.channel_id}')" title="Read"><i data-lucide="refresh-cw"></i></button><button class="btn btn-outline btn-sm" onclick="editChannel('${ch.channel_id}')" title="Edit Mapping"><i data-lucide="edit"></i></button><button class="btn btn-outline btn-sm" onclick="removeChannel('${ch.channel_id}')" title="Delete"><i data-lucide="trash-2" style="color: var(--accent-danger)"></i></button></div></td>`;
        table.appendChild(row);
    });
    lucide.createIcons();
}

window.editChannel = (id) => { state.editingChannelId = id; openChannelModal(state.channels.find(c => c.channel_id === id)); };
window.removeChannel = async (id) => {
    if (!confirm(`Remove ${id}?`)) return;
    try { await apiPut('/system/config/channels', state.channels.filter(c => c.channel_id !== id)); renderChannelMapper(); } catch (e) { addLog('Remove fail', 'error'); }
};

async function openChannelModal(chan = null) {
    const modal = document.getElementById('modal-channel');
    const inputId = document.getElementById('chan-id'), selectDevice = document.getElementById('chan-device'), selectSignal = document.getElementById('chan-signal');
    const inputUnit = document.getElementById('chan-unit'), inputScale = document.getElementById('chan-scale'), inputMin = document.getElementById('chan-min'), inputMax = document.getElementById('chan-max');
    inputId.value = chan ? chan.channel_id : '';
    // Allow renaming Channel ID
    inputId.disabled = false;
    inputUnit.value = chan ? chan.properties.unit : '';
    inputScale.value = chan ? chan.properties.resolution : 1;
    inputMin.value = chan ? chan.properties.min : 0;
    inputMax.value = chan ? chan.properties.max : 100;
    try {
        state.devices = await apiGet('/device');
        selectDevice.innerHTML = '<option value="">Select Device...</option>';
        state.devices.forEach(dev => { const opt = document.createElement('option'); opt.value = dev.id; opt.text = dev.id; if (chan && chan.device_id === dev.id) opt.selected = true; selectDevice.appendChild(opt); });
        if (chan) await onChannelDeviceChange(chan.signal_id);
    } catch (e) { addLog('Devices load fail', 'error'); }
    modal.classList.add('active');
    document.getElementById('btn-chan-cancel').onclick = () => modal.classList.remove('active');
    document.getElementById('btn-chan-save').onclick = async () => {
        const newChan = {
            channel_id: inputId.value, device_id: selectDevice.value, signal_id: selectSignal.value,
            properties: { unit: inputUnit.value, resolution: parseFloat(inputScale.value), min: parseFloat(inputMin.value), max: parseFloat(inputMax.value), offset: 0, value: 0 }
        };
        let body = state.editingChannelId ? state.channels.map(c => c.channel_id === state.editingChannelId ? newChan : c) : [...state.channels, newChan];
        try { await apiPut('/system/config/channels', body); modal.classList.remove('active'); renderChannelMapper(); } catch (e) { addLog('Save Channel fail', 'error'); }
    };
}

window.onChannelDeviceChange = async (selId = null) => {
    const devId = document.getElementById('chan-device').value, selectSignal = document.getElementById('chan-signal');
    if (!devId) return;
    try {
        const signals = await apiGet(`/device/${devId}/signal`);
        selectSignal.innerHTML = '';
        signals.forEach(sig => { const opt = document.createElement('option'); opt.value = sig.signal_id; opt.text = `${sig.name} (${sig.signal_id})`; if (selId === sig.signal_id) opt.selected = true; selectSignal.appendChild(opt); });
    } catch (e) { addLog('Signals load fail', 'error'); }
};

function setupSettings() {
    const btnSave = document.getElementById('btn-save-settings');
    if (btnSave) btnSave.onclick = async () => {
        const cfg = { device_directory: document.getElementById('setting-dev-dir').value, server: { host: document.getElementById('setting-host').value, port: parseInt(document.getElementById('setting-port').value) } };
        try { await apiPut('/system/config', cfg); addLog('Settings saved', 'success'); } catch (e) { addLog('Settings fail', 'error'); }
    };
}

async function loadSettings() {
    try {
        const cfg = await apiGet('/system/config');
        document.getElementById('setting-dev-dir').value = cfg.device_directory;
        document.getElementById('setting-host').value = cfg.server.host;
        document.getElementById('setting-port').value = cfg.server.port;
    } catch (e) { addLog('Settings load fail', 'error'); }
}

function setupTestEditor() {
    const btnRun = document.getElementById('btn-run-test');
    const btnAdd = document.getElementById('btn-add-test-step');

    if (btnAdd) btnAdd.onclick = () => {
        state.testSteps.push({ cmd: 'WRITE', channel: '', value: '', assert: false });
        renderTestTable();
    };

    if (btnRun) btnRun.onclick = async () => {
        const log = document.getElementById('test-log');
        if (log) log.innerHTML = '';
        addLog('Starting Test Sequence...', 'info');

        for (let i = 0; i < state.testSteps.length; i++) {
            const step = state.testSteps[i];
            const stepNum = i + 1;
            try {
                if (step.cmd === 'WRITE') {
                    addLog(`Step ${stepNum}: Writing ${step.value} to ${step.channel}`, 'info');
                    await apiPut(`/channel/${step.channel}?value=${step.value}`, {});
                    addLog(`Step ${stepNum}: Success`, 'success');
                } else if (step.cmd === 'READ') {
                    addLog(`Step ${stepNum}: Reading ${step.channel}`, 'info');
                    const res = await apiGet(`/channel/${step.channel}`);
                    addLog(`Step ${stepNum}: Value = ${res.value}`, 'success');
                    if (step.assert) {
                        if (parseFloat(res.value) === parseFloat(step.value)) {
                            addLog(`Step ${stepNum}: Assert PASSED (${res.value} == ${step.value})`, 'success');
                        } else {
                            addLog(`Step ${stepNum}: Assert FAILED (${res.value} != ${step.value})`, 'error');
                        }
                    }
                }
            } catch (e) {
                addLog(`Step ${stepNum}: Failed - ${e.message}`, 'error');
                break;
            }
        }
        addLog('Test Sequence Complete', 'info');
    };
    renderTestTable();
}

function renderTestTable() {
    const tbody = document.getElementById('test-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    state.testSteps.forEach((step, index) => {
        const row = document.createElement('tr');
        const cmdHtml = `<select class="table-input" onchange="state.testSteps[${index}].cmd = this.value; renderTestTable();"><option value="WRITE" ${step.cmd === 'WRITE' ? 'selected' : ''}>WRITE</option><option value="READ" ${step.cmd === 'READ' ? 'selected' : ''}>READ</option></select>`;

        // Populate channels from state.channels
        let channelOptions = '<option value="">Select...</option>';
        state.channels.forEach(ch => {
            channelOptions += `<option value="${ch.channel_id}" ${step.channel === ch.channel_id ? 'selected' : ''}>${ch.channel_id}</option>`;
        });
        const chanHtml = `<select class="table-input" onchange="state.testSteps[${index}].channel = this.value">${channelOptions}</select>`;

        const valHtml = `<input type="number" class="table-input" value="${step.value}" onchange="state.testSteps[${index}].value = this.value" placeholder="Value">`;
        const assertHtml = step.cmd === 'READ' ? `<input type="checkbox" ${step.assert ? 'checked' : ''} onchange="state.testSteps[${index}].assert = this.checked">` : `<input type="checkbox" disabled>`;
        const actionsHtml = `<button class="btn-icon" onclick="removeTestStep(${index})"><i data-lucide="trash-2" style="color: #ef4444"></i></button>`;
        row.innerHTML = `<td>${cmdHtml}</td><td>${chanHtml}</td><td>${valHtml}</td><td>${assertHtml}</td><td><div class="flex-row">${actionsHtml}</div></td>`;
        tbody.appendChild(row);
    });
    lucide.createIcons();
}

window.removeTestStep = (index) => {
    state.testSteps.splice(index, 1);
    renderTestTable();
};

function setupSSE() {
    const s = new EventSource('/system/logs/stream');
    s.onmessage = (e) => addLog(e.data, 'info');
    state.sse.logs = s;
}

function subscribeToChannel(id) {
    if (state.sse.channels[id]) return;
    const s = new EventSource(`/channel/${id}/stream`);
    state.sse.channels[id] = s;
    s.onmessage = (e) => {
        const val = Number(JSON.parse(e.data).value);
        state.uiConfig.widgets.forEach(w => { if (w.channel === id) updateWidgetValue(w, val); });

        // Update waveform chart data
        if (state.waveform.history[id] && state.waveform.history[id].enabled && !state.waveform.paused) {
            state.waveform.history[id].data.push({ t: Date.now(), v: val });
            if (state.waveform.history[id].data.length > 1000) state.waveform.history[id].data.shift();
        }

        // Update quick waveform
        if (state.quickWave.active && state.quickWave.plotter && state.quickWave.channelId === id && !state.quickWave.paused) {
            const now = Date.now() / 1000;
            state.quickWave.data[0].push(now);
            state.quickWave.data[1].push(val);
            if (state.quickWave.data[0].length > 500) {
                state.quickWave.data[0].shift();
                state.quickWave.data[1].shift();
            }
            state.quickWave.plotter.setData(state.quickWave.data);
        }

        // Update live value in waveform config bar
        const waveValEl = document.getElementById(`wave-val-${id}`);
        if (waveValEl) waveValEl.innerText = val.toFixed(2);
    };
}

function subscribeToDeviceSignal(devId, sigId) {
    const id = `dev:${devId}:${sigId}`;
    if (state.sse.channels[id]) return;
    const s = new EventSource(`/device/${devId}/signal/${sigId}/stream`);
    state.sse.channels[id] = s;
    s.onmessage = (e) => {
        const data = JSON.parse(e.data);
        const val = Number(data.value);
        if (state.waveform.history[id] && state.waveform.history[id].enabled && !state.waveform.paused) {
            state.waveform.history[id].data.push({ t: Date.now(), v: val });
            if (state.waveform.history[id].data.length > 1000) state.waveform.history[id].data.shift();
        }
        const waveValEl = document.getElementById(`wave-val-${id}`);
        if (waveValEl) waveValEl.innerText = val.toFixed(2);
    };
}

async function refreshDevices() {
    try {
        state.devices = await apiGet('/device');
        const tabs = document.getElementById('device-tabs');

        state.devices.forEach(dev => {
            if (state.logFilters.devices[dev.id] === undefined) {
                state.logFilters.devices[dev.id] = false;
            }
        });
        if (window.updateLogFiltersUI) window.updateLogFiltersUI();

        if (!tabs) return;
        tabs.innerHTML = '';
        state.devices.forEach(dev => {
            const isOnline = dev.status === 'online' || dev.status === 'connected';
            const tab = document.createElement('div');
            tab.className = `tab-item ${state.activeDeviceId === dev.id ? 'active' : ''}`;
            tab.innerHTML = `
                <i data-lucide="${isOnline ? 'cpu' : 'zap-off'}" class="${isOnline ? 'text-success' : 'text-muted'}"></i>
                <span style="flex: 1">${dev.id}</span>
                <div class="flex-row" style="gap: 5px">
                    <button class="btn-icon" onclick="event.stopPropagation(); restartDevice('${dev.id}')" title="Restart Device">
                        <i data-lucide="refresh-cw"></i>
                    </button>
                    <div class="status-led ${isOnline ? 'online' : 'offline'}" title="${dev.status}"></div>
                </div>
            `;
            tab.onclick = () => {
                showDeviceSignals(dev.id);
                document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
            };
            tabs.appendChild(tab);
        });
        lucide.createIcons();
        if (state.activeDeviceId) updateDeviceSignalsList(state.activeDeviceId);
    } catch (e) { addLog('Devices load fail', 'error'); }
}

async function showDeviceSignals(id) {
    const det = document.getElementById('device-explorer-detail');
    if (!det) return;
    det.innerHTML = '<div class="loading">Loading signals...</div>';
    state.activeDeviceId = id;
    updateDeviceSignalsList(id);
}

window.toggleDevice = async (id, enabled) => {
    try {
        await apiPost(`/device/${id}/toggle?enabled=${enabled}`);
        addLog(`Device ${id} ${enabled ? 'enabled' : 'disabled'}`, 'info');
        refreshDevices();
    } catch (e) {
        addLog(`Toggle fail: ${e.message}`, 'error');
        refreshDevices();
    }
};

window.restartDevice = async (id) => {
    try {
        await apiPost(`/device/${id}/restart`);
        addLog(`Device ${id} restart initiated`, 'info');
        refreshDevices();
    } catch (e) {
        addLog(`Restart fail: ${e.message}`, 'error');
    }
};

window.closeModal = (id) => {
    const m = document.getElementById(id);
    if (m) m.classList.remove('active');
};

window.readDeviceSignal = async (deviceId, signalId) => {
    try {
        const data = await apiGet(`/device/${deviceId}/signal/${signalId}`);
        const input = document.getElementById(`sig-input-${signalId}`);
        if (input) input.value = Number(data.value).toFixed(2);
        addLog(`Read ${signalId} from ${deviceId}: ${data.value}`, 'success');
    } catch (e) {
        addLog(`Read failed for ${signalId}: ${e.message}`, 'error');
    }
};

window.writeDeviceSignal = async (deviceId, signalId) => {
    try {
        const input = document.getElementById(`sig-input-${signalId}`);
        if (!input) return;
        const val = parseFloat(input.value);
        await apiPut(`/device/${deviceId}/signal/${signalId}?value=${val}`);
        addLog(`Wrote ${val} to ${signalId} on ${deviceId}`, 'success');
    } catch (e) {
        addLog(`Write failed for ${signalId}: ${e.message}`, 'error');
    }
};

async function updateDeviceSignalsList(id) {
    const det = document.getElementById('device-explorer-detail');
    if (!det) return;
    try {
        const sigs = await apiGet(`/device/${id}/signal`);
        const dev = state.devices.find(d => d.id === id);
        const isOnline = dev ? (dev.status === 'online' || dev.status === 'connected') : false;
        let h = `
            <div class="device-toolbar">
                <div class="flex-row" style="gap: 15px">
                    <div class="device-info-pills">
                        <span class="badge badge-outline">${dev.vendor}</span>
                        <span class="badge badge-outline">${dev.model}</span>
                        <span class="badge badge-outline">v${dev.firmware_version || '1.0'}</span>
                    </div>
                </div>
                <div class="flex-row" style="gap: 10px">
                    <button class="btn btn-outline btn-sm" onclick="restartDevice('${dev.id}')" title="Restart Device" style="padding: 2px 8px; font-size: 0.75rem; color: var(--accent-warning); border-color: var(--accent-warning); display: flex; align-items: center; gap: 4px;">
                        <i data-lucide="refresh-cw" style="width: 12px; height: 12px"></i> Restart
                    </button>
                    <span style="font-size: 0.85rem; color: var(--text-muted); margin-left: 10px">Device Enable:</span>
                    <label class="switch-sm" title="${dev.enabled ? 'Disable' : 'Enable'} Device">
                        <input type="checkbox" ${dev.enabled ? 'checked' : ''} onchange="toggleDevice('${dev.id}', this.checked)">
                        <span class="slider-sm"></span>
                    </label>
                </div>
            </div>
            <div class="detail-header"><h3>Signals for ${id} <span class="status-badge-sm ${isOnline ? 'online' : 'offline'}" style="font-size: 0.7rem; padding: 2px 6px">${isOnline ? 'Online' : 'Offline'}</span></h3></div>
            <table class="table table-compact"><thead><tr><th>ID</th><th>Name</th><th>Dir</th><th>Min</th><th>Max</th><th>Unit</th><th>Value</th><th>Actions</th></tr></thead><tbody>`;
        sigs.forEach(s => {
            const val = Number(s.value).toFixed(2);
            h += `<tr>
                <td><code class="badge badge-sm">${s.signal_id}</code></td>
                <td><div style="font-weight:600">${s.name}</div><div style="font-size:0.7rem; opacity:0.6">${s.description || ''}</div></td>
                <td><span class="badge badge-outline" style="font-size:0.65rem">${s.direction}</span></td>
                <td>${s.min}</td>
                <td>${s.max}</td>
                <td><span class="text-muted" style="font-size:0.75rem">${s.unit}</span></td>
                <td><input type="number" step="any" class="table-input" id="sig-input-${s.signal_id}" value="${val}"></td>
                <td>
                    <div class="flex-row" style="gap: 4px">
                        <button class="btn btn-outline btn-sm" onclick="writeDeviceSignal('${id}', '${s.signal_id}')" title="Write">
                            <i data-lucide="edit-3" style="width:12px; height:12px"></i>
                        </button>
                        <button class="btn btn-outline btn-sm" onclick="readDeviceSignal('${id}', '${s.signal_id}')" title="Read">
                            <i data-lucide="refresh-cw" style="width:12px; height:12px"></i>
                        </button>
                    </div>
                </td>
            </tr>`;
        });
        det.innerHTML = h + '</tbody></table>';
        lucide.createIcons();
    } catch (e) { det.innerHTML = `Error: ${e.message}`; }
}

let waveformChart = null;
let uplotSeriesIds = [];
const uplotGlobal = { x: [], y: {} };

window.openPlotModal = async () => {
    // Fill channels
    const chSelect = document.getElementById('plot-channel');
    if (chSelect) {
        chSelect.innerHTML = state.channels.map(c => `<option value="${c.channel_id}">${c.channel_id} (${c.properties.unit})</option>`).join('');
    }

    // Fill devices
    const devSelect = document.getElementById('plot-device');
    if (devSelect) {
        devSelect.innerHTML = state.devices.map(d => `<option value="${d.id}">${d.id}</option>`).join('');
    }

    updatePlotSignalOptions();
    document.getElementById('modal-plot').classList.add('active');
};

window.updatePlotSignalOptions = () => {
    const type = document.getElementById('plot-type').value;
    document.getElementById('plot-channel-group').classList.toggle('hidden', type !== 'channel');
    document.getElementById('plot-device-group').classList.toggle('hidden', type !== 'device');
    document.getElementById('plot-signal-group').classList.toggle('hidden', type !== 'device');
    if (type === 'device') updatePlotDeviceSignals();
};

window.updatePlotDeviceSignals = async () => {
    const devId = document.getElementById('plot-device').value;
    const sigSelect = document.getElementById('plot-signal');
    if (!devId || !sigSelect) return;
    try {
        const sigs = await apiGet(`/device/${devId}/signal`);
        sigSelect.innerHTML = sigs.map(s => `<option value="${s.signal_id}">${s.signal_id} (${s.name})</option>`).join('');
    } catch (e) { console.error(e); }
};

window.addPlot = () => {
    const type = document.getElementById('plot-type').value;
    let id, label;
    if (type === 'channel') {
        id = document.getElementById('plot-channel').value;
        label = id;
    } else {
        const devId = document.getElementById('plot-device').value;
        const sigId = document.getElementById('plot-signal').value;
        id = `dev:${devId}:${sigId}`;
        label = `${devId}.${sigId}`;
    }

    if (state.waveform.history[id]) {
        alert('Signal already being plotted');
        return;
    }

    state.waveform.history[id] = {
        label: label,
        data: [],
        color: document.getElementById('plot-color').value,
        style: document.getElementById('plot-style').value,
        enabled: true,
        type: type
    };

    if (type === 'channel') {
        subscribeToChannel(id);
    } else {
        const parts = id.split(':');
        subscribeToDeviceSignal(parts[1], parts[2]);
    }

    closeModal('modal-plot');
    renderWaveformChannelsList();
    rebuildWaveformChart();
};

window.removePlot = (id) => {
    if (state.sse.channels[id]) {
        state.sse.channels[id].close();
        delete state.sse.channels[id];
    }
    delete state.waveform.history[id];
    delete uplotGlobal.y[id];
    renderWaveformChannelsList();
    rebuildWaveformChart();
};

function renderWaveformChannelsList() {
    const list = document.getElementById('waveform-channels-list');
    if (!list) return;
    list.innerHTML = '';
    Object.keys(state.waveform.history).forEach(id => {
        const plot = state.waveform.history[id];
        const item = document.createElement('div');
        item.className = 'channel-item';
        item.style.cssText = `background: rgba(0,0,0,0.2); border-radius: 8px; border-left: 4px solid ${plot.color}; border-right: 1px solid var(--border-color); border-top: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color);`;
        item.innerHTML = `
            <div class="flex-row" style="justify-content: space-between; padding: 8px 12px;">
                <div class="flex-row" style="gap: 10px;">
                    <span style="font-weight: 500">${plot.label}</span>
                    <span id="wave-val-${id}" style="font-family: monospace; color: var(--accent-primary)">--</span>
                </div>
                <button class="btn-icon" onclick="removePlot('${id}')">
                    <i data-lucide="trash-2" style="width: 14px; height: 14px; color: var(--accent-danger)"></i>
                </button>
            </div>
        `;
        list.appendChild(item);
    });
    lucide.createIcons();
}

function rebuildWaveformChart() {
    const c = document.getElementById('waveform-chart-container');
    if (!c) return;
    c.innerHTML = '';
    if (waveformChart) waveformChart.destroy();

    uplotSeriesIds = Object.keys(state.waveform.history).filter(id => state.waveform.history[id].enabled);
    if (uplotSeriesIds.length === 0) return;

    const series = [{ label: "Time", value: (u, v) => v ? new Date(v * 1000).toLocaleTimeString() : "--" }];
    uplotSeriesIds.forEach(id => {
        const chan = state.waveform.history[id];
        series.push({
            label: id,
            stroke: chan.color,
            width: 2,
            paths: uPlot.paths.stepped({ align: 1 }),
            dash: chan.style === 'dashed' ? [10, 5] : chan.style === 'dotted' ? [2, 2] : []
        });
    });

    const opts = {
        title: "Live Waveform",
        id: "chart1",
        class: "my-chart",
        width: c.clientWidth,
        height: c.clientHeight,
        series: series,
        axes: [
            { grid: { stroke: "rgba(255, 255, 255, 0.1)", width: 1 }, stroke: "#94a3b8" },
            { grid: { stroke: "rgba(255, 255, 255, 0.1)", width: 1 }, stroke: "#94a3b8" }
        ],
        cursor: { drag: { x: true, y: true, uni: 50 } }
    };

    const data = [uplotGlobal.x];
    uplotSeriesIds.forEach(id => {
        data.push(uplotGlobal.y[id] || new Array(uplotGlobal.x.length).fill(null));
    });

    waveformChart = new uPlot(opts, data, c);
    state.waveform.plotter = waveformChart;
}

function setupWaveformViewer() {
    const btnP = document.getElementById('btn-waveform-pause');
    if (btnP) btnP.onclick = () => {
        state.waveform.paused = !state.waveform.paused;
        btnP.innerHTML = state.waveform.paused ? '<i data-lucide="play"></i> Resume' : '<i data-lucide="pause"></i> Pause';
        lucide.createIcons();
    };
    const btnC = document.getElementById('btn-waveform-clear');
    if (btnC) btnC.onclick = () => {
        uplotGlobal.x = [];
        uplotGlobal.y = {};
        Object.keys(state.waveform.history).forEach(id => state.waveform.history[id].data = []);
        rebuildWaveformChart();
    };

    function updateWaveformFrame() {
        if (state.currentView !== 'waveform') {
            requestAnimationFrame(updateWaveformFrame);
            return;
        }

        if (!state.waveform.paused && uplotSeriesIds.length > 0) {
            const now = Date.now() / 1000;
            uplotGlobal.x.push(now);

            Object.keys(state.waveform.history).forEach(id => {
                if (!uplotGlobal.y[id]) uplotGlobal.y[id] = new Array(uplotGlobal.x.length - 1).fill(null);
                const chan = state.waveform.history[id];
                const latest = chan.data.length > 0 ? chan.data[chan.data.length - 1].v : null;
                uplotGlobal.y[id].push(latest);
            });

            if (uplotGlobal.x.length > 1000) {
                uplotGlobal.x.shift();
                Object.values(uplotGlobal.y).forEach(arr => arr.shift());
            }

            if (waveformChart) {
                const data = [uplotGlobal.x];
                uplotSeriesIds.forEach(id => data.push(uplotGlobal.y[id]));
                waveformChart.setData(data);
            }
        }
        requestAnimationFrame(updateWaveformFrame);
    }

    // Only start the loop once
    if (!window._waveformLoopStarted) {
        window._waveformLoopStarted = true;
        requestAnimationFrame(updateWaveformFrame);
    }
    rebuildWaveformChart();
}

function toggleWaveformSidebar() {
    const explorer = document.getElementById('waveform-explorer');
    const icon = document.getElementById('waveform-toggle-icon');
    if (!explorer || !icon) return;

    const isCollapsed = explorer.classList.toggle('collapsed');
    
    // Update icon
    icon.setAttribute('data-lucide', isCollapsed ? 'chevron-right' : 'chevron-left');
    lucide.createIcons();

    // Trigger chart resize after transition
    setTimeout(() => {
        if (state.waveform.plotter) {
            state.waveform.plotter.setSize({
                width: document.getElementById('waveform-chart-container').clientWidth,
                height: document.getElementById('waveform-chart-container').clientHeight
            });
        }
    }, 310);
}

function initWaveformViewer() {
    renderWaveformChannelsList();
    rebuildWaveformChart();
}

window.toggleWaveformChannel = (id, e) => { if (state.waveform.history[id]) { state.waveform.history[id].enabled = e; if (e) subscribeToChannel(id); rebuildWaveformChart(); } };
window.setWaveformColor = (id, c) => { if (state.waveform.history[id]) { state.waveform.history[id].color = c; rebuildWaveformChart(); } };
window.setWaveformStyle = (id, s) => { if (state.waveform.history[id]) { state.waveform.history[id].style = s; rebuildWaveformChart(); } };

function addLog(m, t = 'info') {
    const d = document.getElementById('debug-window'), tl = document.getElementById('test-log'); if (!d) return;

    let displayMsg = m;
    let logLevel = 'INFO';

    // Parse level if present: "LEVEL | Module: Message"
    if (m.includes(' | ')) {
        const parts = m.split(' | ');
        logLevel = parts[0];
        displayMsg = parts.slice(1).join(' | ');
    }

    const e = document.createElement('div');
    e.className = `log-entry ${t} level-${logLevel.toLowerCase()}`;
    e.innerHTML = `<span style="color: #4b5563">[${new Date().toLocaleTimeString()}]</span> ${displayMsg}`;
    e.setAttribute('data-level', logLevel);

    let source = 'system';
    if (m.includes('device_')) source = 'device_unknown';

    state.devices.forEach(dev => {
        if (m.includes(dev.id) || (dev.plugin && m.includes(dev.plugin)) || (dev.vendor && m.toLowerCase().includes(dev.vendor.toLowerCase()))) {
            source = dev.id;
        }
    });
    if (source === 'device_unknown' && state.devices.length === 1) source = state.devices[0].id;

    e.setAttribute('data-source', source);

    let isVisible = true;
    if (source === 'system' && !state.logFilters.system) isVisible = false;
    if (source !== 'system') {
        const devChecked = source === 'device_unknown' ? Object.values(state.logFilters.devices).some(v => v) : state.logFilters.devices[source];
        if (!devChecked) isVisible = false;
    }

    // Debug level filter
    if (logLevel === 'DEBUG' && !state.logFilters.showDebug) isVisible = false;

    if (!isVisible) e.style.display = 'none';

    d.appendChild(e.cloneNode(true));
    if (tl && (m.startsWith('Step') || t === 'success' || t === 'error')) { tl.appendChild(e); tl.scrollTop = tl.scrollHeight; }
    const as = document.getElementById('chk-autoscroll'); if (as && as.checked) d.scrollTop = d.scrollHeight;
}

window.updateLogFiltersUI = () => {
    const container = document.getElementById('device-log-filters');
    if (!container) return;
    let html = '';
    state.devices.forEach(dev => {
        const isChecked = state.logFilters.devices[dev.id] ? 'checked' : '';
        html += `<label style="font-size: 0.8rem; display: flex; align-items: center; gap: 5px; cursor: pointer;"><input type="checkbox" class="filter-device" value="${dev.id}" ${isChecked} onchange="state.logFilters.devices['${dev.id}'] = this.checked; updateLogVisibility()"> ${dev.id}</label>`;
    });
    container.innerHTML = html;
};

window.updateLogFilters = () => {
    const sysFilter = document.getElementById('filter-system');
    if (sysFilter) state.logFilters.system = sysFilter.checked;

    const debugFilter = document.getElementById('filter-debug');
    if (debugFilter) state.logFilters.showDebug = debugFilter.checked;

    updateLogVisibility();
};

window.updateLogVisibility = () => {
    const logs = document.querySelectorAll('.log-entry');
    logs.forEach(log => {
        if (!log.hasAttribute('data-source')) return;
        const source = log.getAttribute('data-source');
        let isVisible = true;
        if (source === 'system' && !state.logFilters.system) isVisible = false;
        if (source !== 'system') {
            const devChecked = source === 'device_unknown' ? Object.values(state.logFilters.devices).some(v => v) : state.logFilters.devices[source];
            if (!devChecked) isVisible = false;
        }

        // Debug level filter
        const level = log.getAttribute('data-level');
        if (level === 'DEBUG' && !state.logFilters.showDebug) isVisible = false;

        log.style.display = isVisible ? 'block' : 'none';
    });
    const d = document.getElementById('debug-window');
    const as = document.getElementById('chk-autoscroll');
    if (as && as.checked && d) d.scrollTop = d.scrollHeight;
};

async function apiGet(p) {
    if (!state.isBackendAlive && p !== '/system') return { error: 'Backend offline' };
    const r = await fetch(p);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}
async function apiPut(p, b) {
    if (!state.isBackendAlive) return { error: 'Backend offline' };
    const r = await fetch(p, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}
async function apiPost(p, b = null, ct = 'application/json') {
    if (!state.isBackendAlive) return { error: 'Backend offline' };
    const o = { method: 'POST' };
    if (b) { o.body = b; o.headers = { 'Content-Type': ct }; }
    const r = await fetch(p, o);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}
async function readSingleChannel(id) { try { const d = await apiGet(`/channel/${id}`); const i = document.getElementById(`read-${id}`); if (i) i.value = Number(d.value).toFixed(2); } catch (e) { addLog(`Read fail: ${e.message}`, 'error'); } }
async function writeSingleChannel(id) {
    try {
        const i = document.getElementById(`read-${id}`);
        if (!i) return;
        const val = parseFloat(i.value);
        await apiPut(`/channel/${id}?value=${val}`, {});
        addLog(`Wrote ${val} to channel ${id}`, 'success');
    } catch (e) {
        addLog(`Write fail: ${e.message}`, 'error');
    }
}

window.openQuickWaveform = (id) => {
    const modal = document.getElementById('modal-quick-waveform');
    const container = document.getElementById('quick-wave-container');
    const chanIdSpan = document.getElementById('quick-wave-channel-id');
    if (!modal || !container) return;

    state.quickWave.channelId = id;
    state.quickWave.data = [[], []];
    state.quickWave.active = true;
    state.quickWave.paused = false;
    
    const btnPause = document.getElementById('btn-quick-pause');
    if (btnPause) {
        btnPause.innerHTML = '<i data-lucide="pause"></i> Pause';
        lucide.createIcons(btnPause);
    }

    if (chanIdSpan) chanIdSpan.innerText = id;

    container.innerHTML = '';
    const opts = {
        title: "",
        width: container.clientWidth || 760,
        height: container.clientHeight || 400,
        series: [
            {},
            { stroke: "#3b82f6", width: 2, label: id }
        ],
        axes: [
            { stroke: "#94a3b8", grid: { stroke: "rgba(255,255,255,0.05)" } },
            { stroke: "#94a3b8", grid: { stroke: "rgba(255,255,255,0.05)" } }
        ],
        cursor: { drag: { x: true, y: true } }
    };

    state.quickWave.plotter = new uPlot(opts, state.quickWave.data, container);
    modal.classList.add('active');
};

window.closeQuickWaveform = () => {
    state.quickWave.active = false;
    if (state.quickWave.plotter) {
        state.quickWave.plotter.destroy();
        state.quickWave.plotter = null;
    }
    closeModal('modal-quick-waveform');
};

window.toggleQuickWavePause = () => {
    state.quickWave.paused = !state.quickWave.paused;
    const btn = document.getElementById('btn-quick-pause');
    if (btn) {
        btn.innerHTML = state.quickWave.paused ? '<i data-lucide="play"></i> Resume' : '<i data-lucide="pause"></i> Pause';
        lucide.createIcons(btn);
    }
    addLog(`Quick Waveform ${state.quickWave.paused ? 'Paused' : 'Resumed'}`, 'info');
};

window.clearQuickWave = () => {
    state.quickWave.data = [[], []];
    if (state.quickWave.plotter) {
        state.quickWave.plotter.setData(state.quickWave.data);
    }
    addLog('Quick Waveform Cleared', 'info');
};
