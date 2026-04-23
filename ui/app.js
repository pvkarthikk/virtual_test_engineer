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
    sse: {
        logs: null,
        channels: {} // channelId -> EventSource
    },
    waveform: {
        activeChannels: new Set(),
        paused: false,
        history: {}, // channelId -> { data: [{t, v}], color, style, enabled }
        plotter: null
    }
};

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    setupNavigation();
    setupSystemControls();
    setupTestEditor();
    setupSettings();
    setupWidgetMapper();
    setupChannelMapper();
    setupWaveformViewer();
    setupPolling();
    setupSSE();
    
    // Initial data load
    refreshAllData();
});

function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.onclick = () => {
            const viewId = item.getAttribute('data-view');
            switchView(viewId);
        };
    });
}

function switchView(viewId) {
    state.currentView = viewId;
    
    // Update Sidebar
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.getAttribute('data-view') === viewId);
    });
    
    // Update Content
    document.querySelectorAll('.view').forEach(view => {
        view.classList.toggle('active', view.id === `view-${viewId}`);
    });
    
    // View-specific logic
    if (viewId === 'dashboard') renderDashboard();
    if (viewId === 'widget-mapper') renderWidgetMapper();
    if (viewId === 'channel-mapper') renderChannelMapper();
    if (viewId === 'settings') loadSettings();
    if (viewId === 'devices') refreshDevices();
    if (viewId === 'waveform') initWaveformViewer();
}

// --- SYSTEM CONTROLS ---
function setupSystemControls() {
    const btnConnect = document.getElementById('btn-connect');
    const btnDisconnect = document.getElementById('btn-disconnect');
    const btnRestart = document.getElementById('btn-restart');

    if (btnConnect) {
        btnConnect.onclick = async () => {
            updateStatusIndicator('connecting', 'Connecting...');
            try {
                await apiPost('/system/connect');
                state.status = 'online';
                updateStatusIndicator('online', 'Connected');
                btnConnect.classList.add('hidden');
                btnDisconnect.classList.remove('hidden');
                addLog('System connected successfully', 'success');
                startPolling();
            } catch (e) {
                state.status = 'offline';
                updateStatusIndicator('offline', 'Disconnected');
                addLog(`Connection failed: ${e.message}`, 'error');
            }
        };
    }

    if (btnDisconnect) {
        btnDisconnect.onclick = async () => {
            try {
                await apiPost('/system/disconnect');
                state.status = 'offline';
                updateStatusIndicator('offline', 'Disconnected');
                btnConnect.classList.remove('hidden');
                btnDisconnect.classList.add('hidden');
                addLog('System disconnected', 'info');
                stopPolling();
            } catch (e) {
                addLog(`Disconnection failed: ${e.message}`, 'error');
            }
        };
    }

    if (btnRestart) {
        btnRestart.onclick = async () => {
            if (!confirm('Are you sure you want to restart the system? This will disconnect all devices.')) return;
            try {
                await apiPost('/system/restart');
                addLog('System restart initiated', 'info');
                location.reload();
            } catch (e) {
                addLog(`Restart failed: ${e.message}`, 'error');
            }
        };
    }
}

function updateStatusIndicator(status, text) {
    const indicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.status-text');
    if (!indicator || !statusText) return;
    indicator.className = `status-indicator ${status}`;
    statusText.innerText = text;
}

// --- POLLING ---
function setupPolling() {
    const intervalSelect = document.getElementById('poll-interval');
    if (intervalSelect) {
        intervalSelect.onchange = () => {
            if (state.status === 'online') startPolling();
        };
    }
}

function startPolling() {
    stopPolling();
    const intervalEl = document.getElementById('poll-interval');
    const ms = intervalEl ? parseInt(intervalEl.value) : 1000;
    addLog(`Starting channel polling at ${ms}ms`, 'info');
    state.pollTimer = setInterval(pollDashboard, ms);
}

function stopPolling() {
    if (state.pollTimer) {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
    }
}

async function pollDashboard() {
    if (state.status !== 'online') return;
    
    const channelIds = [...new Set(state.uiConfig.widgets.map(w => w.channel))];
    if (channelIds.length === 0) return;

    try {
        await Promise.all(channelIds.map(async (id) => {
            try {
                await apiGet(`/channel/${id}`);
            } catch (e) {
                if (e.message.includes('503')) {
                    console.warn(`Channel ${id} unavailable (503)`);
                }
            }
        }));
    } catch (e) {
        console.error('Polling error', e);
    }
}

// --- DASHBOARD ---
function renderDashboard() {
    const grid = document.getElementById('dashboard-grid');
    if (!grid) return;
    grid.innerHTML = '';
    
    if (state.uiConfig.widgets.length === 0) {
        grid.innerHTML = '<div class="empty-state"><p>No widgets configured. Go to Widget Mapper to add some.</p></div>';
        return;
    }

    state.uiConfig.widgets.forEach(widget => {
        const card = createWidgetCard(widget);
        grid.appendChild(card);
        subscribeToChannel(widget.channel);
    });
}

function createWidgetCard(widget) {
    const card = document.createElement('div');
    card.className = 'widget-card';
    card.id = `widget-${widget.id}`;
    
    let content = `
        <div class="widget-header">
            <span class="widget-label">${widget.label}</span>
            <span class="widget-channel">${widget.channel}</span>
            <div class="widget-actions">
                <button class="btn-icon" onclick="editWidgetById('${widget.id}')"><i data-lucide="edit-2"></i></button>
            </div>
        </div>
    `;

    if (widget.type === 'gauge') {
        content += `
            <div class="widget-content gauge-container">
                <div class="gauge-value" id="val-${widget.id}">--</div>
                <div class="gauge-label">${widget.type}</div>
            </div>
        `;
    } else if (widget.type === 'bar') {
        content += `
            <div class="widget-content bar-container">
                <div class="bar-bg">
                    <div class="bar-fill" id="fill-${widget.id}" style="width: 0%"></div>
                </div>
                <div class="widget-value-sm" id="val-${widget.id}">--</div>
            </div>
        `;
    } else if (widget.type === 'waveform') {
        content += `
            <div class="widget-content waveform-container">
                <svg viewBox="0 0 100 40" preserveAspectRatio="none">
                    <polyline id="poly-${widget.id}" fill="none" stroke="var(--accent-primary)" stroke-width="1.5" points="0,20 100,20" />
                </svg>
                <div class="widget-value-sm">
                    <span id="val-${widget.id}">--</span>
                </div>
            </div>
        `;
    } else if (widget.type === 'led') {
        content += `
            <div class="widget-content led-container">
                <div class="led-bulb" id="led-${widget.id}"></div>
                <div class="widget-value-sm" id="val-${widget.id}">OFF</div>
            </div>
        `;
    } else if (widget.type === 'button') {
        content += `
            <div class="widget-content button-container">
                <button class="btn btn-primary btn-block" onclick="widgetWrite('${widget.channel}', 1)">Trigger</button>
            </div>
        `;
    } else if (widget.type === 'slider') {
        const ch = state.channels.find(c => c.channel_id === widget.channel);
        const min = ch ? ch.properties.min : 0;
        const max = ch ? ch.properties.max : 100;
        content += `
            <div class="widget-content slider-container">
                <input type="range" class="btn-block" onchange="widgetWrite('${widget.channel}', this.value)" 
                    min="${min}" max="${max}" value="${min}" id="slider-${widget.id}">
                <div class="widget-value-sm" id="val-${widget.id}">--</div>
            </div>
        `;
    } else {
        content += `
            <div class="widget-content numeric-container">
                <div class="widget-value" id="val-${widget.id}">--</div>
            </div>
        `;
    }

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
    } else if (widget.type === 'gauge' || widget.type === 'numeric' || widget.type === 'slider') {
        valEl.innerText = val.toFixed(2);
        if (widget.type === 'slider') {
            const slider = document.getElementById(`slider-${widget.id}`);
            if (slider) slider.value = val;
        }
    } else if (widget.type === 'bar') {
        const fill = document.getElementById(`fill-${widget.id}`);
        if (fill) {
            const ch = state.channels.find(c => c.channel_id === widget.channel);
            const min = ch ? ch.properties.min : 0;
            const max = ch ? ch.properties.max : 100;
            const percent = Math.min(Math.max(((val - min) / (max - min)) * 100, 0), 100);
            fill.style.width = `${percent}%`;
        }
        valEl.innerText = val.toFixed(2);
    } else if (widget.type === 'waveform') {
        const poly = document.getElementById(`poly-${widget.id}`);
        if (poly) updateWaveform(poly, val, widget);
        valEl.innerText = val.toFixed(2);
    } else {
        valEl.innerText = val.toFixed(2);
    }
}

const waveformHistory = {};
function updateWaveform(poly, val, widget) {
    if (!waveformHistory[widget.id]) waveformHistory[widget.id] = new Array(50).fill(20);
    const ch = state.channels.find(c => c.channel_id === widget.channel);
    const min = ch ? ch.properties.min : 0;
    const max = ch ? ch.properties.max : 100;
    const range = max - min || 1;
    const scaled = 40 - ((val - min) / range * 40);
    waveformHistory[widget.id].push(scaled);
    if (waveformHistory[widget.id].length > 50) waveformHistory[widget.id].shift();
    const points = waveformHistory[widget.id].map((v, i) => `${i * 2},${v}`).join(' ');
    poly.setAttribute('points', points);
}

window.widgetWrite = async (channelId, value) => {
    try {
        await apiPut(`/channel/${channelId}?value=${value}`, {});
        addLog(`Widget write ${channelId}: ${value}`, 'info');
    } catch (e) {
        addLog(`Widget write failed: ${e.message}`, 'error');
    }
};

// --- DATA LOADING ---
async function refreshAllData() {
    await Promise.all([
        refreshChannels(),
        refreshUIConfig()
    ]);
    renderDashboard();
}

async function refreshChannels() {
    try {
        state.channels = await apiGet('/channel');
    } catch (e) {
        addLog(`Failed to load channels: ${e.message}`, 'error');
    }
}

async function refreshUIConfig() {
    try {
        state.uiConfig = await apiGet('/ui/config');
    } catch (e) {
        addLog(`Failed to load UI config: ${e.message}`, 'error');
    }
}

// --- WIDGET MAPPER ---
function setupWidgetMapper() {
    const btnAdd = document.getElementById('btn-add-widget');
    if (btnAdd) {
        btnAdd.onclick = () => {
            state.editingWidgetIndex = null;
            openWidgetModal();
        };
    }
}

function renderWidgetMapper() {
    const tableBody = document.getElementById('widget-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '';
    
    state.uiConfig.widgets.forEach((widget, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${widget.label}</strong></td>
            <td><code>${widget.type}</code></td>
            <td><code>${widget.channel}</code></td>
            <td>
                <div class="flex-row" style="gap: 10px">
                    <button class="btn btn-outline btn-sm" onclick="editWidget(${index})">
                        <i data-lucide="edit"></i> Edit
                    </button>
                    <button class="btn btn-outline btn-sm" onclick="removeWidget(${index})">
                        <i data-lucide="trash-2" style="color: #ef4444"></i>
                    </button>
                </div>
            </td>
        `;
        tableBody.appendChild(row);
    });
    lucide.createIcons();
}

window.editWidget = (index) => {
    state.editingWidgetIndex = index;
    const widget = state.uiConfig.widgets[index];
    openWidgetModal(widget);
};

window.editWidgetById = (id) => {
    const index = state.uiConfig.widgets.findIndex(w => w.id === id);
    if (index !== -1) {
        switchView('widget-mapper');
        editWidget(index);
    }
};

window.removeWidget = (index) => {
    state.uiConfig.widgets.splice(index, 1);
    renderWidgetMapper();
};

function openWidgetModal(widget = null) {
    const modal = document.getElementById('modal-widget');
    const title = document.getElementById('widget-modal-title');
    const inputLabel = document.getElementById('widget-label');
    const selectChannel = document.getElementById('widget-channel');
    const selectType = document.getElementById('widget-type');

    title.innerText = widget ? 'Edit Widget' : 'Add Widget';
    inputLabel.value = widget ? widget.label : '';
    
    selectChannel.innerHTML = '';
    state.channels.forEach(ch => {
        const opt = document.createElement('option');
        opt.value = ch.channel_id;
        opt.text = ch.channel_id;
        if (widget && widget.channel === ch.channel_id) opt.selected = true;
        selectChannel.appendChild(opt);
    });

    if (widget) selectType.value = widget.type;
    modal.classList.add('active');

    document.getElementById('btn-widget-cancel').onclick = () => modal.classList.remove('active');
    document.getElementById('btn-widget-save').onclick = () => {
        const newWidget = {
            id: widget ? widget.id : `w${Date.now()}`,
            label: inputLabel.value,
            channel: selectChannel.value,
            type: selectType.value,
            position: { row: 0, col: 0 }
        };

        if (state.editingWidgetIndex !== null) {
            state.uiConfig.widgets[state.editingWidgetIndex] = newWidget;
        } else {
            state.uiConfig.widgets.push(newWidget);
        }

        modal.classList.remove('active');
        renderWidgetMapper();
    };
}

const btnSaveWidgets = document.getElementById('btn-save-widgets');
if (btnSaveWidgets) {
    btnSaveWidgets.onclick = async () => {
        try {
            await apiPut('/ui/config', state.uiConfig);
            addLog('Widget configuration saved', 'success');
            if (state.status === 'online') startPolling();
        } catch (e) {
            addLog(`Save failed: ${e.message}`, 'error');
        }
    };
}

// --- CHANNEL MAPPER ---
function setupChannelMapper() {
    const btnAdd = document.getElementById('btn-add-channel');
    if (btnAdd) {
        btnAdd.onclick = () => {
            state.editingChannelId = null;
            openChannelModal();
        };
    }
}

async function renderChannelMapper() {
    await refreshChannels();
    const table = document.getElementById('channel-mapping-table');
    if (!table) return;
    table.innerHTML = '';
    
    state.channels.forEach(ch => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${ch.channel_id}</td>
            <td>${ch.device_id}</td>
            <td>${ch.signal_id}</td>
            <td>${ch.properties.unit}</td>
            <td>${ch.properties.min}</td>
            <td>${ch.properties.max}</td>
            <td>
                <input type="number" step="0.01" class="table-input" id="read-${ch.channel_id}" readonly>
            </td>
            <td>
                <div class="flex-row" style="gap: 5px">
                    <button class="btn btn-outline btn-sm" onclick="readSingleChannel('${ch.channel_id}')" title="Read Once">
                        <i data-lucide="refresh-cw"></i>
                    </button>
                    <button class="btn btn-outline btn-sm" onclick="editChannel('${ch.channel_id}')" title="Edit">
                        <i data-lucide="edit"></i>
                    </button>
                    <button class="btn btn-outline btn-sm" onclick="removeChannel('${ch.channel_id}')" title="Delete">
                        <i data-lucide="trash-2" style="color: var(--accent-danger)"></i>
                    </button>
                </div>
            </td>
        `;
        table.appendChild(row);
    });
    lucide.createIcons();
}

window.editChannel = (id) => {
    state.editingChannelId = id;
    const chan = state.channels.find(c => c.channel_id === id);
    openChannelModal(chan);
};

window.removeChannel = async (id) => {
    if (!confirm(`Are you sure you want to remove channel ${id}?`)) return;
    const newChannels = state.channels.filter(c => c.channel_id !== id);
    try {
        await apiPut('/system/config/channels', newChannels);
        addLog(`Channel ${id} removed`, 'success');
        renderChannelMapper();
    } catch (e) {
        addLog(`Failed to remove channel: ${e.message}`, 'error');
    }
};

async function openChannelModal(chan = null) {
    const modal = document.getElementById('modal-channel');
    const title = document.getElementById('channel-modal-title');
    const inputId = document.getElementById('chan-id');
    const selectDevice = document.getElementById('chan-device');
    const selectSignal = document.getElementById('chan-signal');
    const inputUnit = document.getElementById('chan-unit');
    const inputScale = document.getElementById('chan-scale');
    const inputMin = document.getElementById('chan-min');
    const inputMax = document.getElementById('chan-max');

    title.innerText = chan ? 'Edit Channel' : 'Add Channel';
    inputId.value = chan ? chan.channel_id : '';
    inputId.disabled = !!chan;
    inputUnit.value = chan ? chan.properties.unit : '';
    inputScale.value = chan ? chan.properties.scale_factor : 1;
    inputMin.value = chan ? chan.properties.min : 0;
    inputMax.value = chan ? chan.properties.max : 100;

    try {
        state.devices = await apiGet('/device');
        selectDevice.innerHTML = '<option value="">Select Device...</option>';
        state.devices.forEach(dev => {
            const opt = document.createElement('option');
            opt.value = dev.id;
            opt.text = dev.id;
            if (chan && chan.device_id === dev.id) opt.selected = true;
            selectDevice.appendChild(opt);
        });
        if (chan) await onChannelDeviceChange(chan.signal_id);
    } catch (e) {
        addLog('Failed to load devices', 'error');
    }

    modal.classList.add('active');

    document.getElementById('btn-chan-cancel').onclick = () => modal.classList.remove('active');
    document.getElementById('btn-chan-save').onclick = async () => {
        const newChan = {
            channel_id: inputId.value,
            device_id: selectDevice.value,
            signal_id: selectSignal.value,
            properties: {
                unit: inputUnit.value,
                scale_factor: parseFloat(inputScale.value),
                min: parseFloat(inputMin.value),
                max: parseFloat(inputMax.value),
                resolution: 0.1, // Required by backend
                offset: 0,
                value: 0
            }
        };

        let newChannels;
        if (state.editingChannelId) {
            newChannels = state.channels.map(c => c.channel_id === state.editingChannelId ? newChan : c);
        } else {
            newChannels = [...state.channels, newChan];
        }

        try {
            await apiPut('/system/config/channels', newChannels);
            addLog(`Channel ${newChan.channel_id} saved`, 'success');
            modal.classList.remove('active');
            renderChannelMapper();
        } catch (e) {
            addLog(`Failed to save channel: ${e.message}`, 'error');
        }
    };
}

window.onChannelDeviceChange = async (selectedSignalId = null) => {
    const deviceId = document.getElementById('chan-device').value;
    const selectSignal = document.getElementById('chan-signal');
    if (!deviceId) return;
    try {
        const signals = await apiGet(`/device/${deviceId}/signal`);
        selectSignal.innerHTML = '';
        signals.forEach(sig => {
            const opt = document.createElement('option');
            opt.value = sig.signal_id;
            opt.text = `${sig.name} (${sig.signal_id})`;
            if (selectedSignalId === sig.signal_id) opt.selected = true;
            selectSignal.appendChild(opt);
        });
    } catch (e) {
        addLog('Failed to load signals', 'error');
    }
};

// --- SETTINGS ---
function setupSettings() {
    const btnSave = document.getElementById('btn-save-settings');
    if (btnSave) {
        btnSave.onclick = async () => {
            const config = {
                device_directory: document.getElementById('setting-dev-dir').value,
                server: {
                    host: document.getElementById('setting-host').value,
                    port: parseInt(document.getElementById('setting-port').value)
                }
            };
            try {
                await apiPut('/system/config', config);
                addLog('Settings saved. Restart system to apply.', 'success');
            } catch (e) {
                addLog(`Failed to save settings: ${e.message}`, 'error');
            }
        };
    }
}

async function loadSettings() {
    try {
        const config = await apiGet('/system/config');
        const devDir = document.getElementById('setting-dev-dir');
        const host = document.getElementById('setting-host');
        const port = document.getElementById('setting-port');
        if (devDir) devDir.value = config.device_directory;
        if (host) host.value = config.server.host;
        if (port) port.value = config.server.port;
    } catch (e) {
        addLog(`Failed to load settings: ${e.message}`, 'error');
    }
}

// --- TEST EDITOR ---
function setupTestEditor() {
    const btnRun = document.getElementById('btn-run-test');
    if (btnRun) {
        btnRun.onclick = async () => {
            const content = document.getElementById('test-content').value;
            try {
                await apiPost('/test/run', content, 'text/plain');
                addLog('Test sequence started', 'info');
            } catch (e) {
                addLog(`Test failed: ${e.message}`, 'error');
            }
        };
    }
}

// --- SSE ---
function setupSSE() {
    const source = new EventSource('/system/logs/stream');
    source.onmessage = (event) => {
        addLog(event.data, 'info');
    };
    state.sse.logs = source;
}

function subscribeToChannel(channelId) {
    if (state.sse.channels[channelId]) return;
    const source = new EventSource(`/channel/${channelId}/stream`);
    state.sse.channels[channelId] = source;
    source.onmessage = (event) => {
        const update = JSON.parse(event.data);
        const val = Number(update.value);
        state.uiConfig.widgets.forEach(widget => {
            if (widget.channel === channelId) {
                updateWidgetValue(widget, val);
            }
        });
        if (state.waveform.history[channelId] && state.waveform.history[channelId].enabled && !state.waveform.paused) {
            state.waveform.history[channelId].data.push({t: Date.now(), v: val});
            if (state.waveform.history[channelId].data.length > 1000) state.waveform.history[channelId].data.shift();
        }
    };
}

// --- DEVICES ---
async function refreshDevices() {
    try {
        state.devices = await apiGet('/device');
        const list = document.getElementById('device-explorer-list');
        if (!list) return;
        list.innerHTML = '';
        state.devices.forEach(dev => {
            const item = document.createElement('div');
            item.className = 'device-item';
            item.innerHTML = `
                <div class="flex-row" style="justify-content: space-between">
                    <strong>${dev.id}</strong>
                    <span class="status-badge ${dev.is_connected ? 'online' : 'offline'}">
                        ${dev.is_connected ? 'Connected' : 'Offline'}
                    </span>
                </div>
                <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 5px">
                    ${dev.vendor} ${dev.model} (v${dev.firmware_version})
                </div>
            `;
            item.onclick = () => showDeviceSignals(dev.id);
            list.appendChild(item);
        });
    } catch (e) {
        addLog(`Failed to load devices: ${e.message}`, 'error');
    }
}

async function showDeviceSignals(deviceId) {
    const detail = document.getElementById('device-explorer-detail');
    if (!detail) return;
    detail.innerHTML = '<div class="loading">Loading signals...</div>';
    try {
        const signals = await apiGet(`/device/${deviceId}/signal`);
        let html = `<div class="detail-header"><h3>Signals for ${deviceId}</h3></div><table class="table"><thead><tr><th>ID</th><th>Name</th><th>Type</th><th>Dir</th><th>Range</th><th>Value</th><th>Description</th></tr></thead><tbody>`;
        signals.forEach(sig => {
            html += `<tr><td><code class="badge badge-sm">${sig.signal_id}</code></td><td>${sig.name}</td><td>${sig.type}</td><td>${sig.direction}</td><td>${sig.min} - ${sig.max} ${sig.unit}</td><td><strong>${sig.value}</strong></td><td style="font-size: 0.8rem; color: #94a3b8">${sig.description}</td></tr>`;
        });
        html += '</tbody></table>';
        detail.innerHTML = html;
    } catch (e) {
        detail.innerHTML = `<div class="error">Error: ${e.message}</div>`;
    }
}

// --- WAVEFORM VIEWER ---
function setupWaveformViewer() {
    const canvas = document.getElementById('waveform-canvas');
    if (!canvas) return;
    state.waveform.plotter = new WaveformPlotter(canvas);
    const btnPause = document.getElementById('btn-waveform-pause');
    if (btnPause) {
        btnPause.onclick = () => {
            state.waveform.paused = !state.waveform.paused;
            btnPause.innerHTML = state.waveform.paused ? '<i data-lucide="play"></i> Resume' : '<i data-lucide="pause"></i> Pause';
            lucide.createIcons();
        };
    }
    const btnClear = document.getElementById('btn-waveform-clear');
    if (btnClear) {
        btnClear.onclick = () => {
            Object.keys(state.waveform.history).forEach(id => state.waveform.history[id].data = []);
            state.waveform.plotter.resetView();
        };
    }
}

function initWaveformViewer() {
    refreshChannels().then(() => {
        const list = document.getElementById('waveform-channels-list');
        if (!list) return;
        list.innerHTML = '';
        state.channels.forEach(ch => {
            const item = document.createElement('div');
            item.className = 'waveform-channel-item';
            const color = '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');
            item.innerHTML = `<div class="waveform-channel-header"><input type="checkbox" onchange="toggleWaveformChannel('${ch.channel_id}', this.checked)"><strong>${ch.channel_id}</strong></div><div class="flex-row" style="gap: 5px"><input type="color" value="${color}" onchange="setWaveformColor('${ch.channel_id}', this.value)"><select class="table-input" style="padding: 2px" onchange="setWaveformStyle('${ch.channel_id}', this.value)"><option value="solid">Solid</option><option value="dashed">Dashed</option><option value="dotted">Dotted</option></select></div>`;
            list.appendChild(item);
            if (!state.waveform.history[ch.channel_id]) {
                state.waveform.history[ch.channel_id] = { data: [], color: color, style: 'solid', enabled: false };
            }
        });
    });
}

window.toggleWaveformChannel = (id, enabled) => {
    if (state.waveform.history[id]) {
        state.waveform.history[id].enabled = enabled;
        if (enabled) subscribeToChannel(id);
    }
};

window.setWaveformColor = (id, color) => { if (state.waveform.history[id]) state.waveform.history[id].color = color; };
window.setWaveformStyle = (id, style) => { if (state.waveform.history[id]) state.waveform.history[id].style = style; };

class WaveformPlotter {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.zoom = { x: 1, y: 1 };
        this.offset = { x: 0, y: 0 };
        this.isPanning = false;
        this.lastMouse = { x: 0, y: 0 };
        this.initEvents();
        this.animate();
    }
    initEvents() {
        this.canvas.addEventListener('mousedown', e => { this.isPanning = true; this.lastMouse = { x: e.clientX, y: e.clientY }; });
        window.addEventListener('mousemove', e => {
            if (!this.isPanning) return;
            const dx = (e.clientX - this.lastMouse.x) / this.zoom.x;
            const dy = (e.clientY - this.lastMouse.y) / this.zoom.y;
            this.offset.x -= dx; this.offset.y += dy;
            this.lastMouse = { x: e.clientX, y: e.clientY };
        });
        window.addEventListener('mouseup', () => this.isPanning = false);
        this.canvas.addEventListener('wheel', e => {
            if (state.currentView !== 'waveform') return;
            e.preventDefault();
            const factor = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoom.x *= factor; this.zoom.y *= factor;
        }, { passive: false });
    }
    resetView() { this.zoom = { x: 1, y: 1 }; this.offset = { x: 0, y: 0 }; }
    animate() { this.draw(); requestAnimationFrame(() => this.animate()); }
    draw() {
        if (state.currentView !== 'waveform') return;
        const { width, height } = this.canvas;
        if (this.canvas.width !== this.canvas.clientWidth || this.canvas.height !== this.canvas.clientHeight) {
            this.canvas.width = this.canvas.clientWidth; this.canvas.height = this.canvas.clientHeight;
        }
        const ctx = this.ctx;
        ctx.clearRect(0, 0, width, height);
        ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 1;
        for (let i = 0; i < width; i += 50) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, height); ctx.stroke(); }
        for (let i = 0; i < height; i += 50) { ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(width, i); ctx.stroke(); }
        const now = Date.now();
        const timeWindow = 10000 / this.zoom.x;
        const legend = document.getElementById('waveform-legend');
        if (legend) legend.innerHTML = '';
        Object.keys(state.waveform.history).forEach(id => {
            const chan = state.waveform.history[id];
            if (!chan.enabled || chan.data.length < 2) return;
            if (legend) {
                const lastData = chan.data[chan.data.length - 1];
                const lastVal = lastData ? lastData.v : 0;
                const legItem = document.createElement('div');
                legItem.className = 'legend-item'; legItem.style.borderLeftColor = chan.color;
                legItem.innerHTML = `<span>${id}</span><strong>${lastVal.toFixed(2)}</strong>`;
                legend.appendChild(legItem);
            }
            ctx.beginPath(); ctx.strokeStyle = chan.color; ctx.lineWidth = 2;
            if (chan.style === 'dashed') ctx.setLineDash([10, 5]); else if (chan.style === 'dotted') ctx.setLineDash([2, 2]); else ctx.setLineDash([]);
            const chCfg = state.channels.find(c => c.channel_id === id);
            const min = chCfg ? chCfg.properties.min : 0;
            const max = chCfg ? chCfg.properties.max : 100;
            const range = max - min || 1;
            chan.data.forEach((p, i) => {
                const x = width - ((now - p.t + (this.offset.x * 10)) / timeWindow) * width;
                const y = height - ((p.v - min + this.offset.y) / range) * height;
                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            });
            ctx.stroke(); ctx.setLineDash([]);
        });
    }
}

// --- UTILS ---
function addLog(message, type = 'info') {
    const debugWindow = document.getElementById('debug-window');
    const testLog = document.getElementById('test-log');
    if (!debugWindow) return;
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `<span style="color: #4b5563">[${timestamp}]</span> ${message}`;
    debugWindow.appendChild(entry.cloneNode(true));
    if (testLog && (message.startsWith('Step') || type === 'success' || type === 'error')) {
        testLog.appendChild(entry);
        testLog.scrollTop = testLog.scrollHeight;
    }
    const autoScroll = document.getElementById('chk-autoscroll');
    if (autoScroll && autoScroll.checked) debugWindow.scrollTop = debugWindow.scrollHeight;
}

async function apiGet(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

async function apiPut(path, body) {
    const res = await fetch(path, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

async function apiPost(path, body = null, contentType = 'application/json') {
    const options = { method: 'POST' };
    if (body) {
        options.body = body;
        options.headers = { 'Content-Type': contentType };
    }
    const res = await fetch(path, options);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

async function readSingleChannel(id) {
    try {
        const data = await apiGet(`/channel/${id}`);
        const readInput = document.getElementById(`read-${id}`);
        if (readInput) readInput.value = Number(data.value).toFixed(2);
    } catch (e) {
        addLog(`Read failed: ${e.message}`, 'error');
    }
}
