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
    devicePollTimer: null,
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
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.getAttribute('data-view') === viewId);
    });
    document.querySelectorAll('.view').forEach(view => {
        view.classList.toggle('active', view.id === `view-${viewId}`);
    });
    
    // Stop device polling if not in devices view
    if (viewId !== 'devices') stopDevicePolling();

    if (viewId === 'dashboard') renderDashboard();
    if (viewId === 'widget-mapper') renderWidgetMapper();
    if (viewId === 'channel-mapper') renderChannelMapper();
    if (viewId === 'settings') loadSettings();
    if (viewId === 'devices') refreshDevices();
    if (viewId === 'waveform') initWaveformViewer();
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
            if (!confirm('Are you sure you want to restart?')) return;
            try {
                await apiPost('/system/restart');
                location.reload();
            } catch (e) { addLog(`Restart failed: ${e.message}`, 'error'); }
        };
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
    
    const deviceRateSelect = document.getElementById('device-poll-rate');
    if (deviceRateSelect) {
        deviceRateSelect.onchange = () => {
            if (state.activeDeviceId) startDevicePolling(state.activeDeviceId);
        };
    }
}

function startPolling() {
    stopPolling();
    const intervalEl = document.getElementById('poll-interval');
    const ms = intervalEl ? parseInt(intervalEl.value) : 1000;
    state.pollTimer = setInterval(pollDashboard, ms);
}

function stopPolling() { if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; } }

function startDevicePolling(deviceId) {
    stopDevicePolling();
    state.activeDeviceId = deviceId;
    const rateEl = document.getElementById('device-poll-rate');
    const ms = rateEl ? parseInt(rateEl.value) : 1000;
    state.devicePollTimer = setInterval(() => {
        if (state.currentView === 'devices' && state.activeDeviceId) {
            updateDeviceSignalsList(state.activeDeviceId);
        }
    }, ms);
}

function stopDevicePolling() {
    if (state.devicePollTimer) {
        clearInterval(state.devicePollTimer);
        state.devicePollTimer = null;
    }
    state.activeDeviceId = null;
}

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
    if (state.uiConfig.widgets.length === 0) {
        grid.innerHTML = '<div class="empty-state"><p>No widgets. Add some in Widget Mapper.</p></div>';
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
    let content = `<div class="widget-header"><span class="widget-label">${widget.label}</span><span class="widget-channel">${widget.channel}</span><div class="widget-actions"><button class="btn-icon" onclick="editWidgetById('${widget.id}')"><i data-lucide="edit-2"></i></button></div></div>`;
    if (widget.type === 'gauge') content += `<div class="widget-content gauge-container"><div class="gauge-value" id="val-${widget.id}">--</div><div class="gauge-label">${widget.type}</div></div>`;
    else if (widget.type === 'bar') content += `<div class="widget-content bar-container"><div class="bar-bg"><div class="bar-fill" id="fill-${widget.id}" style="width: 0%"></div></div><div class="widget-value-sm" id="val-${widget.id}">--</div></div>`;
    else if (widget.type === 'waveform') content += `<div class="widget-content waveform-container"><svg viewBox="0 0 100 40" preserveAspectRatio="none"><polyline id="poly-${widget.id}" fill="none" stroke="var(--accent-primary)" stroke-width="1.5" points="0,20 100,20" /></svg><div class="widget-value-sm"><span id="val-${widget.id}">--</span></div></div>`;
    else if (widget.type === 'led') content += `<div class="widget-content led-container"><div class="led-bulb" id="led-${widget.id}"></div><div class="widget-value-sm" id="val-${widget.id}">OFF</div></div>`;
    else if (widget.type === 'button') content += `<div class="widget-content button-container"><button class="btn btn-primary btn-block" onclick="widgetWrite('${widget.channel}', 1)">Trigger</button></div>`;
    else if (widget.type === 'slider') {
        const ch = state.channels.find(c => c.channel_id === widget.channel);
        const min = ch ? ch.properties.min : 0;
        const max = ch ? ch.properties.max : 100;
        content += `<div class="widget-content slider-container"><input type="range" class="btn-block" onchange="widgetWrite('${widget.channel}', this.value)" min="${min}" max="${max}" value="${min}" id="slider-${widget.id}"><div class="widget-value-sm" id="val-${widget.id}">--</div></div>`;
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
    } else if (widget.type === 'gauge' || widget.type === 'numeric' || widget.type === 'slider') {
        valEl.innerText = Number(val).toFixed(2);
        if (widget.type === 'slider') { const slider = document.getElementById(`slider-${widget.id}`); if (slider) slider.value = val; }
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
    const min = ch ? ch.properties.min : 0, max = ch ? ch.properties.max : 100;
    const range = max - min || 1;
    waveformHistory[widget.id].push(40 - ((val - min) / range * 40));
    if (waveformHistory[widget.id].length > 50) waveformHistory[widget.id].shift();
    poly.setAttribute('points', waveformHistory[widget.id].map((v, i) => `${i * 2},${v}`).join(' '));
}

window.widgetWrite = async (id, val) => { try { await apiPut(`/channel/${id}?value=${val}`, {}); } catch (e) { addLog(`Write failed: ${e.message}`, 'error'); } };

async function refreshAllData() { await Promise.all([refreshChannels(), refreshUIConfig()]); renderDashboard(); }
async function refreshChannels() { try { state.channels = await apiGet('/channel'); } catch (e) { addLog('Channels fail', 'error'); } }
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
        row.innerHTML = `<td>${ch.channel_id}</td><td>${ch.device_id}</td><td>${ch.signal_id}</td><td>${ch.properties.unit}</td><td>${ch.properties.min}</td><td>${ch.properties.max}</td><td><input type="number" step="0.01" class="table-input" id="read-${ch.channel_id}" readonly></td><td><div class="flex-row" style="gap: 5px"><button class="btn btn-outline btn-sm" onclick="readSingleChannel('${ch.channel_id}')"><i data-lucide="refresh-cw"></i></button><button class="btn btn-outline btn-sm" onclick="editChannel('${ch.channel_id}')"><i data-lucide="edit"></i></button><button class="btn btn-outline btn-sm" onclick="removeChannel('${ch.channel_id}')"><i data-lucide="trash-2" style="color: var(--accent-danger)"></i></button></div></td>`;
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
    inputId.disabled = !!chan;
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
    if (btnRun) btnRun.onclick = async () => {
        try { await apiPost('/test/run', document.getElementById('test-content').value, 'text/plain'); addLog('Test started', 'info'); } catch (e) { addLog('Test fail', 'error'); }
    };
}

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
        if (state.waveform.history[id] && state.waveform.history[id].enabled && !state.waveform.paused) {
            state.waveform.history[id].data.push({t: Date.now(), v: val});
            if (state.waveform.history[id].data.length > 1000) state.waveform.history[id].data.shift();
        }
    };
}

async function refreshDevices() {
    try {
        state.devices = await apiGet('/device');
        const list = document.getElementById('device-explorer-list');
        if (!list) return;
        list.innerHTML = '';
        state.devices.forEach(dev => {
            const item = document.createElement('div');
            item.className = 'device-item';
            item.innerHTML = `<div class="flex-row" style="justify-content: space-between"><strong>${dev.id}</strong><span class="status-badge ${dev.is_connected ? 'online' : 'offline'}">${dev.is_connected ? 'Connected' : 'Offline'}</span></div><div style="font-size: 0.8rem; color: #94a3b8; margin-top: 5px">${dev.vendor} ${dev.model}</div>`;
            item.onclick = () => showDeviceSignals(dev.id);
            list.appendChild(item);
        });
    } catch (e) { addLog('Devices load fail', 'error'); }
}

async function showDeviceSignals(id) {
    const det = document.getElementById('device-explorer-detail');
    if (!det) return;
    det.innerHTML = '<div class="loading">Loading signals...</div>';
    startDevicePolling(id);
}

async function updateDeviceSignalsList(id) {
    const det = document.getElementById('device-explorer-detail');
    if (!det) return;
    try {
        const sigs = await apiGet(`/device/${id}/signal`);
        let h = `<div class="detail-header"><h3>Signals for ${id}</h3></div><table class="table"><thead><tr><th>ID</th><th>Name</th><th>Dir</th><th>Range</th><th>Display</th></tr></thead><tbody>`;
        sigs.forEach(s => { 
            h += `<tr><td><code class="badge badge-sm">${s.signal_id}</code></td><td>${s.name}</td><td>${s.direction}</td><td>${s.min}-${s.max} ${s.unit}</td><td><strong id="sig-val-${s.signal_id}">${Number(s.value).toFixed(2)}</strong></td></tr>`; 
        });
        det.innerHTML = h + '</tbody></table>';
    } catch (e) { det.innerHTML = `Error: ${e.message}`; stopDevicePolling(); }
}

function setupWaveformViewer() {
    const c = document.getElementById('waveform-canvas');
    if (!c) return;
    state.waveform.plotter = new WaveformPlotter(c);
    const btnP = document.getElementById('btn-waveform-pause');
    if (btnP) btnP.onclick = () => { state.waveform.paused = !state.waveform.paused; btnP.innerHTML = state.waveform.paused ? '<i data-lucide="play"></i> Resume' : '<i data-lucide="pause"></i> Pause'; lucide.createIcons(); };
    const btnC = document.getElementById('btn-waveform-clear');
    if (btnC) btnC.onclick = () => { Object.keys(state.waveform.history).forEach(id => state.waveform.history[id].data = []); state.waveform.plotter.resetView(); };
}

function initWaveformViewer() {
    refreshChannels().then(() => {
        const list = document.getElementById('waveform-channels-list');
        if (!list) return;
        list.innerHTML = '';
        state.channels.forEach(ch => {
            const color = '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');
            const item = document.createElement('div');
            item.className = 'waveform-channel-item';
            item.innerHTML = `<div class="waveform-channel-header"><input type="checkbox" onchange="toggleWaveformChannel('${ch.channel_id}', this.checked)"><strong>${ch.channel_id}</strong></div><div class="flex-row" style="gap: 5px"><input type="color" value="${color}" onchange="setWaveformColor('${ch.channel_id}', this.value)"><select class="table-input" onchange="setWaveformStyle('${ch.channel_id}', this.value)"><option value="solid">Solid</option><option value="dashed">Dashed</option><option value="dotted">Dotted</option></select></div>`;
            list.appendChild(item);
            if (!state.waveform.history[ch.channel_id]) state.waveform.history[ch.channel_id] = { data: [], color: color, style: 'solid', enabled: false };
        });
    });
}

window.toggleWaveformChannel = (id, e) => { if (state.waveform.history[id]) { state.waveform.history[id].enabled = e; if (e) subscribeToChannel(id); } };
window.setWaveformColor = (id, c) => { if (state.waveform.history[id]) state.waveform.history[id].color = c; };
window.setWaveformStyle = (id, s) => { if (state.waveform.history[id]) state.waveform.history[id].style = s; };

class WaveformPlotter {
    constructor(c) {
        this.canvas = c; this.ctx = c.getContext('2d');
        this.padding = { left: 60, right: 20, top: 20, bottom: 40 };
        this.zoom = {x:1,y:1}; this.offset = {x:0,y:0}; this.isPanning = false; this.lastMouse = {x:0,y:0};
        this.initEvents(); this.animate();
    }
    initEvents() {
        this.canvas.addEventListener('mousedown', e => { this.isPanning = true; this.lastMouse = {x:e.clientX,y:e.clientY}; });
        window.addEventListener('mousemove', e => { if (!this.isPanning) return; this.offset.x -= (e.clientX - this.lastMouse.x)/this.zoom.x; this.offset.y += (e.clientY - this.lastMouse.y)/this.zoom.y; this.lastMouse = {x:e.clientX,y:e.clientY}; });
        window.addEventListener('mouseup', () => this.isPanning = false);
        this.canvas.addEventListener('wheel', e => { if (state.currentView !== 'waveform') return; e.preventDefault(); const f = e.deltaY > 0 ? 0.9 : 1.1; this.zoom.x *= f; this.zoom.y *= f; }, { passive: false });
    }
    resetView() { this.zoom = {x:1,y:1}; this.offset = {x:0,y:0}; }
    animate() { this.draw(); requestAnimationFrame(() => this.animate()); }
    draw() {
        if (state.currentView !== 'waveform') return;
        const {width, height} = this.canvas;
        if (this.canvas.width !== this.canvas.clientWidth) { this.canvas.width = this.canvas.clientWidth; this.canvas.height = this.canvas.clientHeight; }
        const ctx = this.ctx; ctx.clearRect(0,0,width,height);
        const graphW = width - this.padding.left - this.padding.right, graphH = height - this.padding.top - this.padding.bottom;
        ctx.strokeStyle = '#4b5563'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(this.padding.left, this.padding.top); ctx.lineTo(this.padding.left, height - this.padding.bottom); ctx.lineTo(width - this.padding.right, height - this.padding.bottom); ctx.stroke();
        ctx.font = '10px monospace'; ctx.fillStyle = '#94a3b8'; ctx.textAlign = 'right';
        const now = Date.now(), timeWindow = 10000 / this.zoom.x;
        for (let i = 0; i <= 5; i++) { const y = height - this.padding.bottom - (i / 5) * graphH; ctx.fillText((i * 20).toFixed(0), this.padding.left - 10, y + 3); ctx.strokeStyle = 'rgba(75, 85, 99, 0.2)'; ctx.beginPath(); ctx.moveTo(this.padding.left, y); ctx.lineTo(width - this.padding.right, y); ctx.stroke(); }
        ctx.textAlign = 'center'; for (let i = 0; i <= 5; i++) { const x = this.padding.left + (i / 5) * graphW; const timeOffset = ((5 - i) / 5) * timeWindow; ctx.fillText((timeOffset / 1000).toFixed(1) + 's', x, height - this.padding.bottom + 20); ctx.beginPath(); ctx.moveTo(x, height - this.padding.bottom); ctx.lineTo(x, height - this.padding.bottom + 5); ctx.stroke(); }
        ctx.save(); ctx.beginPath(); ctx.rect(this.padding.left, this.padding.top, graphW, graphH); ctx.clip();
        const legend = document.getElementById('waveform-legend'); if (legend) legend.innerHTML = '';
        Object.keys(state.waveform.history).forEach(id => {
            const chan = state.waveform.history[id]; if (!chan.enabled || chan.data.length < 2) return;
            if (legend) { const li = document.createElement('div'); li.className = 'legend-item'; li.style.borderLeftColor = chan.color; li.innerHTML = `<span>${id}</span><strong>${chan.data[chan.data.length-1].v.toFixed(2)}</strong>`; legend.appendChild(li); }
            ctx.beginPath(); ctx.strokeStyle = chan.color; ctx.lineWidth = 2; if (chan.style === 'dashed') ctx.setLineDash([10,5]); else if (chan.style === 'dotted') ctx.setLineDash([2,2]); else ctx.setLineDash([]);
            const cfg = state.channels.find(c => c.channel_id === id); const min = cfg ? cfg.properties.min : 0, max = cfg ? cfg.properties.max : 100, range = max - min || 1;
            chan.data.forEach((p, i) => { const x = width - this.padding.right - ((now - p.t + (this.offset.x * 10)) / timeWindow) * graphW, y = height - this.padding.bottom - ((p.v - min + this.offset.y) / range) * graphH; if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); });
            ctx.stroke(); ctx.setLineDash([]);
        });
        ctx.restore();
    }
}

function addLog(m, t = 'info') {
    const d = document.getElementById('debug-window'), tl = document.getElementById('test-log'); if (!d) return;
    const e = document.createElement('div'); e.className = `log-entry ${t}`; e.innerHTML = `<span style="color: #4b5563">[${new Date().toLocaleTimeString()}]</span> ${m}`;
    d.appendChild(e.cloneNode(true)); if (tl && (m.startsWith('Step') || t === 'success' || t === 'error')) { tl.appendChild(e); tl.scrollTop = tl.scrollHeight; }
    const as = document.getElementById('chk-autoscroll'); if (as && as.checked) d.scrollTop = d.scrollHeight;
}

async function apiGet(p) { const r = await fetch(p); if (!r.ok) throw new Error(await r.text()); return r.json(); }
async function apiPut(p, b) { const r = await fetch(p, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }); if (!r.ok) throw new Error(await r.text()); return r.json(); }
async function apiPost(p, b = null, ct = 'application/json') { const o = { method: 'POST' }; if (b) { o.body = b; o.headers = { 'Content-Type': ct }; } const r = await fetch(p, o); if (!r.ok) throw new Error(await r.text()); return r.json(); }
async function readSingleChannel(id) { try { const d = await apiGet(`/channel/${id}`); const i = document.getElementById(`read-${id}`); if (i) i.value = Number(d.value).toFixed(2); } catch (e) { addLog(`Read fail: ${e.message}`, 'error'); } }
