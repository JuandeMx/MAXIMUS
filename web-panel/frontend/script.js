/* ==========================================
   MAXIMUS ELITE - Engine v2.0
   Real-time SSE + Full Feature Set
   ========================================== */

let resourceChart;
let eventSource;
let chartHistory = { cpu: Array(30).fill(0), ram: Array(30).fill(0) };
let allUsers = [];

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initChart();
    connectSSE();
    loadTab('dashboard');
});

// ========== NAVIGATION ==========
function initNavigation() {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tab = link.dataset.tab;
            loadTab(tab);
        });
    });
}

function loadTab(tabName) {
    // Update nav
    document.querySelectorAll('.nav-link').forEach(n => n.classList.remove('active'));
    const activeLink = document.querySelector(`.nav-link[data-tab="${tabName}"]`);
    if (activeLink) activeLink.classList.add('active');

    // Update panels
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(`tab-${tabName}`);
    if (panel) panel.classList.add('active');

    // Update title
    const titles = {
        dashboard: 'Dashboard',
        users: 'Gestión de Usuarios',
        services: 'Administrador de Protocolos',
        accounts: 'Gestión de Cuentas',
        connections: 'Conexiones Activas'
    };
    document.getElementById('pageTitle').innerText = titles[tabName] || tabName;

    // Load data for the tab
    if (tabName === 'users') fetchUsers();
    if (tabName === 'services') fetchServices();
    if (tabName === 'connections') fetchConnections();

    // Close sidebar on mobile
    document.getElementById('sidebar').classList.remove('open');
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// ========== SSE: REAL-TIME MONITORING ==========
function connectSSE() {
    eventSource = new EventSource('/api/stream');

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        } catch (e) {
            console.error('SSE parse error:', e);
        }
    };

    eventSource.onerror = () => {
        console.warn('SSE disconnected. Falling back to polling...');
        eventSource.close();
        // Fallback: polling cada 3s
        setInterval(async () => {
            try {
                const res = await fetch('/api/stats');
                if (res.status === 401) { window.location.href = '/login.html'; return; }
                const data = await res.json();
                updateDashboard(data);
            } catch (e) { console.error('Polling error:', e); }
        }, 3000);
    };
}

function updateDashboard(data) {
    // Helper para actualizar anillos SVG
    const setRing = (id, percent) => {
        const ring = document.getElementById(id);
        if (!ring) return;
        const radius = 20;
        const circum = 2 * Math.PI * radius;
        const offset = circum - (percent / 100) * circum;
        ring.style.strokeDashoffset = offset;
    };

    // CPU
    const cpuVal = parseFloat(data.cpu?.load) || 0;
    document.getElementById('cpu-val').innerText = `${cpuVal.toFixed(1)}%`;
    setRing('cpu-ring', Math.min(cpuVal, 100));
    document.getElementById('cpu-detail').innerText = `${data.cpu?.cores || '--'} cores · ${data.cpu?.model || '--'}`;

    // RAM
    const ramUsed = parseInt(data.ram?.used) || 0;
    const ramTotal = parseInt(data.ram?.total) || 1;
    const ramPerc = ((ramUsed / ramTotal) * 100).toFixed(1);
    document.getElementById('ram-val').innerText = `${ramPerc}%`;
    setRing('ram-ring', ramPerc);
    document.getElementById('ram-detail').innerText = `${ramUsed} / ${ramTotal} MB`;

    // Disk
    const dObj = data.disk || {};
    const diskPerc = parseInt(dObj.percent) || 0;
    document.getElementById('disk-val').innerText = `${diskPerc}%`;
    setRing('disk-ring', diskPerc);
    document.getElementById('disk-detail').innerText = `${dObj.used || '0'} / ${dObj.total || '0'}`;

    // Online
    document.getElementById('online-val').innerText = data.online || '0';
    document.getElementById('users-detail').innerText = `Total: ${data.total_users || 0} cuentas`;

    // Uptime
    document.getElementById('uptime-val').innerText = data.uptime || '--';

    // Network
    const nObj = data.network || {};
    document.getElementById('net-rx').innerText = `${nObj.rx || '0'} GB`;
    document.getElementById('net-tx').innerText = `${nObj.tx || '0'} GB`;

    // System info
    const sObj = data.system || {};
    document.getElementById('sys-hostname').innerText = sObj.hostname || '--';
    document.getElementById('sys-kernel').innerText = sObj.kernel || '--';
    document.getElementById('sys-loadavg').innerText = data.load_avg || '--';
    document.getElementById('server-ip').innerText = sObj.ip || '--';
    document.getElementById('server-os').innerText = sObj.os || '--';

    // Settings tab info (if elements exist)
    const sIP = document.getElementById('settings-ip');
    if (sIP) sIP.innerText = data.system?.ip || '--';
    const sOS = document.getElementById('settings-os');
    if (sOS) sOS.innerText = data.system?.os || '--';
    const sKer = document.getElementById('settings-kernel');
    if (sKer) sKer.innerText = data.system?.kernel || '--';
    const sUp = document.getElementById('settings-uptime');
    if (sUp) sUp.innerText = data.uptime || '--';

    // Chart
    chartHistory.cpu.push(cpuVal);
    chartHistory.cpu.shift();
    chartHistory.ram.push(parseFloat(ramPerc));
    chartHistory.ram.shift();
    updateChart();
}

// ========== CHART ==========
function initChart() {
    const ctx = document.getElementById('resourceChart').getContext('2d');

    const cpuGrad = ctx.createLinearGradient(0, 0, 0, 250);
    cpuGrad.addColorStop(0, 'rgba(6, 182, 212, 0.2)');
    cpuGrad.addColorStop(1, 'rgba(6, 182, 212, 0)');

    const ramGrad = ctx.createLinearGradient(0, 0, 0, 250);
    ramGrad.addColorStop(0, 'rgba(139, 92, 246, 0.15)');
    ramGrad.addColorStop(1, 'rgba(139, 92, 246, 0)');

    resourceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array(30).fill(''),
            datasets: [{
                label: 'CPU %',
                data: chartHistory.cpu,
                borderColor: '#06b6d4',
                backgroundColor: cpuGrad,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                tension: 0.4,
                fill: true
            }, {
                label: 'RAM %',
                data: chartHistory.ram,
                borderColor: '#8b5cf6',
                backgroundColor: ramGrad,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    labels: { color: '#64748b', usePointStyle: true, pointStyle: 'circle', font: { size: 11 } }
                }
            },
            scales: {
                x: { display: false },
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#475569', font: { size: 10 }, callback: v => v + '%' }
                }
            },
            interaction: { intersect: false, mode: 'index' }
        }
    });
}

function updateChart() {
    if (!resourceChart) return;
    resourceChart.data.datasets[0].data = [...chartHistory.cpu];
    resourceChart.data.datasets[1].data = [...chartHistory.ram];
    resourceChart.update('none'); // Sin animación para fluidez
}

// ========== USERS ==========
async function fetchUsers() {
    const tbody = document.getElementById('userListBody');
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i> Cargando...</td></tr>';

    try {
        const res = await fetch('/api/users/list');
        if (res.status === 401) { window.location.href = '/login.html'; return; }
        allUsers = await res.json();
        renderUsers(allUsers);
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Error al cargar usuarios</td></tr>';
    }
}

function renderUsers(users) {
    const tbody = document.getElementById('userListBody');
    if (!users.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No hay usuarios registrados</td></tr>';
        return;
    }
    tbody.innerHTML = users.map(u => {
        const statusClass = u.status === 'Active' ? 'status-active' : (u.status === 'Locked' ? 'status-locked' : 'status-expired');
        const daysColor = u.days_left <= 1 ? 'var(--danger)' : (u.days_left <= 3 ? '#f59e0b' : 'var(--success)');
        const lockIcon = u.status === 'Locked' ? 'fa-lock-open' : 'fa-lock';
        const lockTitle = u.status === 'Locked' ? 'Desbloquear' : 'Bloquear';
        return `<tr>
        <td><strong>${u.username}</strong></td>
        <td><span class="badge ${u.type === 'SSH/SSL' ? 'badge-ssh' : 'badge-hy'}">${u.type}</span></td>
        <td><code>${u.password}</code></td>
        <td>${u.expiry}</td>
        <td style="color:${daysColor};font-weight:700">${u.days_left}d</td>
        <td>${u.limit}</td>
        <td><span class="${statusClass}">${u.status}</span></td>
        <td class="user-actions">
            <button class="btn-mini btn-renew" onclick="renewUser('${u.username}')" title="Renovar"><i class="fa-solid fa-calendar-plus"></i></button>
            <button class="btn-mini btn-pass" onclick="changeUserPass('${u.username}')" title="Cambiar contraseña"><i class="fa-solid fa-key"></i></button>
            <button class="btn-mini btn-lock" onclick="toggleLockUser('${u.username}')" title="${lockTitle}"><i class="fa-solid ${lockIcon}"></i></button>
            <button class="btn-mini btn-del" onclick="deleteUser('${u.username}')" title="Eliminar"><i class="fa-solid fa-trash-can"></i></button>
        </td>
    </tr>`;
    }).join('');
}

function filterUsers() {
    const q = document.getElementById('userSearch').value.toLowerCase();
    const filtered = allUsers.filter(u => u.username.toLowerCase().includes(q));
    renderUsers(filtered);
}

async function deleteUser(username) {
    if (!confirm(`¿Eliminar al usuario "${username}"?`)) return;
    try {
        const res = await fetch('/api/users/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ username })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ Usuario ${username} eliminado`);
            fetchUsers();
        } else {
            showToast(`❌ Error: ${data.error}`);
        }
    } catch (e) {
        showToast('❌ Error de conexión');
    }
}

async function renewUser(username) {
    const days = prompt(`¿Cuántos días renovar para "${username}"?`, '30');
    if (!days || isNaN(days) || days < 1) return;
    try {
        const res = await fetch('/api/users/renew', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ username, days: parseInt(days) })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ ${username} renovado hasta ${data.new_expiry}`);
            fetchUsers();
        } else {
            showToast(`❌ ${data.error}`);
        }
    } catch (e) { showToast('❌ Error de conexión'); }
}

async function changeUserPass(username) {
    const newPass = prompt(`Nueva contraseña para "${username}":`);
    if (!newPass || newPass.trim().length < 1) return;
    try {
        const res = await fetch('/api/users/change-password', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ username, password: newPass.trim() })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ Contraseña de ${username} actualizada`);
            fetchUsers();
        } else {
            showToast(`❌ ${data.error}`);
        }
    } catch (e) { showToast('❌ Error de conexión'); }
}

async function toggleLockUser(username) {
    try {
        const res = await fetch('/api/users/toggle-lock', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ username })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.locked ? `🔒 ${username} bloqueado` : `🔓 ${username} desbloqueado`);
            fetchUsers();
        } else {
            showToast(`❌ ${data.error}`);
        }
    } catch (e) { showToast('❌ Error de conexión'); }
}

async function purgeExpired() {
    if (!confirm('¿Eliminar TODOS los usuarios vencidos del sistema?')) return;
    try {
        const res = await fetch('/api/users/purge-expired', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        const data = await res.json();
        if (data.success) {
            showToast(`🧹 ${data.count} usuarios vencidos eliminados`);
            fetchUsers();
        }
    } catch (e) { showToast('❌ Error de conexión'); }
}

async function saveCredentials() {
    const user = document.getElementById('settingsUser').value.trim();
    const pass = document.getElementById('settingsPass').value.trim();
    if (!user || !pass) { showToast('⚠️ Completa ambos campos'); return; }
    try {
        const res = await fetch('/api/settings/credentials', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ ${data.message}`);
            document.getElementById('settingsUser').value = '';
            document.getElementById('settingsPass').value = '';
        } else {
            showToast(`❌ ${data.error}`);
        }
    } catch (e) { showToast('❌ Error de conexión'); }
}


// ========== SERVICES ==========
async function fetchServices() {
    const grid = document.getElementById('servicesGrid');
    grid.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i> Cargando servicios...</div>';

    try {
        const res = await fetch('/api/service/status');
        if (res.status === 401) { window.location.href = '/login.html'; return; }
        const services = await res.json();
        grid.innerHTML = services.map(s => {
            const stateClass = !s.installed ? 'not-installed' : (s.active ? 'online' : 'offline');
            const statusLabel = !s.installed ? 'NO INSTALADO' : (s.active ? 'ONLINE' : 'OFFLINE');
            const statusClass = !s.installed ? 'off' : (s.active ? 'on' : 'off');

            return `
            <div class="service-card ${stateClass}" onclick='openSvcConfig(${JSON.stringify(s)})' style="cursor:pointer">
                <div class="svc-icon ${s.active ? 'on' : 'off'}">
                    <i class="fa-solid ${s.icon}"></i>
                </div>
                <div class="svc-info">
                    <div class="svc-name">${s.name}</div>
                    <div class="svc-desc">${s.desc}</div>
                    <div class="svc-port">Puerto: ${s.port}</div>
                </div>
                <div style="text-align:right">
                    <div class="svc-status ${statusClass}">${statusLabel}</div>
                    <div style="margin-top:8px;font-size:0.7rem;color:var(--text-dim)">
                        <i class="fa-solid fa-gear"></i> Configurar
                    </div>
                </div>
            </div>
        `}).join('');
    } catch (e) {
        grid.innerHTML = '<div class="empty-state">Error al cargar servicios</div>';
    }
}

async function serviceAction(id, action) {
    const labels = {restart:'Reiniciando', stop:'Deteniendo', start:'Iniciando', install:'Instalando', uninstall:'Desinstalando'};
    showToast(`⏳ ${labels[action] || action} ${id}...`);
    try {
        const res = await fetch('/api/service/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id, action })
        });
        const data = await res.json();
        if (data.success) {
            if (action === 'install') showToast(`✅ ${id} instalado correctamente`);
            else if (action === 'uninstall') showToast(`🗑️ ${id} desinstalado`);
            else showToast(data.active ? `✅ ${id} está ONLINE` : `⚠️ ${id} está OFFLINE`);
        } else {
            showToast(`❌ ${data.error || 'Error desconocido'}`);
        }
        setTimeout(fetchServices, 1000);
    } catch (e) {
        showToast('❌ Error al gestionar servicio');
    }
}

async function restartAllServices() {
    if (!confirm('¿Reiniciar TODOS los servicios de red?')) return;
    showToast('🔄 Reiniciando todos los servicios...');
    const services = ['ssh', 'dropbear', 'stunnel4', 'mx-proxy', 'badvpn', 'mx-slowdns', 'ws-epro'];
    for (const svc of services) {
        await fetch('/api/service/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id: svc, action: 'restart' })
        }).catch(() => {});
    }
    showToast('✅ Todos los servicios han sido reiniciados');
    setTimeout(fetchServices, 2000);
}

async function openXuiPanel() {
    try {
        const res = await fetch('/api/xui/info');
        const data = await res.json();
        if (data.installed && data.url) {
            window.open(data.url, '_blank');
        } else {
            showToast('⚠️ X-UI no está instalado. Instálalo desde Servicios.');
        }
    } catch (e) {
        showToast('❌ Error al consultar X-UI');
    }
}

// ========== SERVICE CONFIG MODAL ==========
function openSvcConfig(svc) {
    const modal = document.getElementById('svcModal');
    const title = document.getElementById('svcModalTitle');
    const body = document.getElementById('svcModalBody');

    title.innerHTML = `<i class="fa-solid ${svc.icon}"></i> ${svc.name}`;

    const statusBadge = !svc.installed
        ? '<span class="svc-status off" style="display:inline-block">NO INSTALADO</span>'
        : svc.active
            ? '<span class="svc-status on" style="display:inline-block">ONLINE</span>'
            : '<span class="svc-status off" style="display:inline-block">OFFLINE</span>';

    // Header del servicio
    let content = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding:16px;background:rgba(255,255,255,0.03);border-radius:14px;border:1px solid var(--border)">
            <div>
                <div style="font-weight:700;font-size:1.1rem;color:var(--text)">${svc.name}</div>
                <div style="font-size:0.8rem;color:var(--text-dim);margin-top:4px">${svc.desc}</div>
                <div style="font-size:0.85rem;color:var(--primary);margin-top:6px;font-weight:600"><i class="fa-solid fa-plug"></i> Puerto: ${svc.port}</div>
            </div>
            ${statusBadge}
        </div>
    `;

    content += `<div class="svc-actions-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:12px">`;

    if (!svc.installed) {
        content += `
            <div class="action-tile install" onclick="showSvcActionMenu('${svc.id}', 'install')" style="grid-column: span 2">
                <i class="fa-solid fa-download"></i>
                <div class="action-label">INSTALACIÓN INTELIGENTE</div>
            </div>
        `;
    } else {
        // Fila 1: Reiniciar + Puerto
        content += `
            <div class="action-tile restart" onclick="svcConfigAction('${svc.id}','restart')">
                <i class="fa-solid fa-arrows-rotate"></i>
                <div class="action-label">REINICIAR</div>
            </div>
            <div class="action-tile port" onclick="showSvcActionMenu('${svc.id}', 'port')">
                <i class="fa-solid fa-plug-circle-bolt"></i>
                <div class="action-label">PUERTO</div>
            </div>
        `;
        // Fila 2: Reinstalar + Desinstalar
        content += `
            <div class="action-tile reinstall" onclick="showSvcActionMenu('${svc.id}', 'install')">
                <i class="fa-solid fa-sync"></i>
                <div class="action-label">REINSTALAR</div>
            </div>
            <div class="action-tile uninstall" onclick="if(confirm('¿Desinstalar ${svc.name}?')) svcConfigAction('${svc.id}','uninstall')">
                <i class="fa-solid fa-trash-can"></i>
                <div class="action-label">DESINSTALAR</div>
            </div>
        `;

        // Fila 3: Acciones Específicas Quirúrgicas
    const specActions = {
        'ssh': { label: 'GESTIÓN SSH', icon: 'fa-terminal', color: '#06b6d4', cmd: 'ssh' },
        'mx-slowdns': { label: 'VER LLAVE PÚBLICA', icon: 'fa-key', color: '#8b5cf6', cmd: 'info' },
        'x-ui': { label: 'ABRIR PANEL XRAY', icon: 'fa-arrow-up-right-from-square', color: '#f59e0b', cmd: 'panel' },
        'stunnel4': { label: 'EDITOR SSL', icon: 'fa-file-code', color: '#10b981', cmd: 'edit' },
        'hysteria': { label: 'CERTIFICADOS', icon: 'fa-certificate', color: '#ef4444', cmd: 'cert' }
    };

    if (specActions[svc.id]) {
        const sa = specActions[svc.id];
        content += `
            <div class="action-tile info" onclick="handleSpecAction('${svc.id}','${sa.cmd}')" style="grid-column: span 2; border-color: ${sa.color}33">
                <i class="fa-solid ${sa.icon}" style="color:${sa.color}"></i>
                <div class="action-label" style="color:${sa.color}">${sa.label}</div>
            </div>
        `;
    }

    // Fila Final: START/STOP
    content += `
        <div class="action-tile ${svc.active ? 'stop' : 'start'}" onclick="svcConfigAction('${svc.id}','${svc.active ? 'stop' : 'start'}')" style="grid-column: span 2; margin-top: 8px; border: 2px solid ${svc.active ? '#ef4444' : '#10b981'}">
            <i class="fa-solid ${svc.active ? 'fa-stop' : 'fa-play'}"></i>
            <div class="action-label">${svc.active ? 'DETENER SERVICIO' : 'INICIAR SERVICIO'}</div>
        </div>
    `;

    content += `</div>`;
    content += `<div id="svcSubMenu" class="svc-submenu-container" style="display:none; margin-top: 24px; padding-top: 24px; border-top: 1px solid var(--border)"></div>`;

    body.innerHTML = content;
    modal.classList.add('show');
}

async function handleSpecAction(id, cmd) {
    if (id === 'mx-slowdns') showServiceInfo(id);
    else if (id === 'stunnel4') showStunnelEditor();
    else if (id === 'x-ui') openXuiPanel();
    else if (id === 'ssh') showSshMenu();
    else showToast('⚠️ Módulo avanzado en desarrollo');
}

// ========== STUBS PARA FUNCIONES AVANZADAS (Evita Bloqueos) ==========
function showSshMenu() {
    showToast('🚀 Abriendo Gestor SSH Avanzado...');
    const sub = document.getElementById('svcSubMenu');
    sub.innerHTML = `
        <div style="padding:20px; background:#1a1f2e; border-radius:18px; border:1px solid #33415555">
            <h3 style="color:white; font-size:1rem; font-weight:700; margin-bottom:12px">Gestión SSH</h3>
            <button class="btn-primary" onclick="serviceAction('ssh','restart')" style="width:100%; margin-bottom:10px">REINICIAR SSH</button>
            <button class="btn-primary" onclick="showToast('Módulo de Banner en Herramientas')" style="width:100%; background:var(--bg-elevated)">EDITAR BANNER</button>
        </div>
    `;
    sub.style.display = 'block';
}

function showStunnelEditor() {
    showToast('📝 Cargando editor de Stunnel...');
    showServiceInfo('stunnel4'); // Reutilizamos el visor por ahora
}

// ========== SERVICE INFO PANEL ==========
async function showServiceInfo(id) {
    const sub = document.getElementById('svcSubMenu');
    sub.innerHTML = '<div style="text-align:center;padding:20px"><i class="fa-solid fa-spinner fa-spin" style="color:var(--primary);font-size:1.5rem"></i></div>';
    sub.style.display = 'block';

    try {
        const res = await fetch(`/api/service/info/${id}`);
        const info = await res.json();

        if (id === 'mx-slowdns') {
            sub.innerHTML = `
                <div style="padding:20px; background:#1a1f2e; border-radius:18px; border:1px solid #33415555">
                    <h3 style="color:white; font-size:1rem; font-weight:700; margin-bottom:16px"><i class="fa-solid fa-tower-broadcast" style="color:#8b5cf6; margin-right:8px"></i>Información SlowDNS</h3>
                    <div style="margin-bottom:14px">
                        <label style="display:block; color:#94a3b8; font-size:0.7rem; font-weight:600; margin-bottom:6px; letter-spacing:1px">DOMINIO NS</label>
                        <div style="padding:12px; background:var(--bg-elevated); border:1px solid var(--border); border-radius:10px; color:var(--primary); font-weight:600; font-family:monospace; font-size:0.9rem">${info.ns_domain || 'No configurado'}</div>
                    </div>
                    <div style="margin-bottom:14px">
                        <label style="display:block; color:#94a3b8; font-size:0.7rem; font-weight:600; margin-bottom:6px; letter-spacing:1px">LLAVE PÚBLICA (CLIENTE)</label>
                        <div id="slowdnsKey" style="padding:12px; background:var(--bg-elevated); border:1px solid var(--border); border-radius:10px; color:#10b981; font-family:monospace; font-size:0.75rem; word-break:break-all; max-height:80px; overflow-y:auto">${info.public_key || 'No generada'}</div>
                    </div>
                    <button class="btn-primary" onclick="navigator.clipboard.writeText(document.getElementById('slowdnsKey').innerText);showToast('📋 Llave copiada')" style="margin:0; width:100%; background:linear-gradient(135deg,#8b5cf6,#7c3aed)">
                        <i class="fa-solid fa-copy"></i> COPIAR LLAVE
                    </button>
                </div>
            `;
        } else if (id === 'x-ui') {
            sub.innerHTML = `
                <div style="padding:20px; background:#1a1f2e; border-radius:18px; border:1px solid #33415555">
                    <h3 style="color:white; font-size:1rem; font-weight:700; margin-bottom:16px"><i class="fa-solid fa-table-columns" style="color:#8b5cf6; margin-right:8px"></i>Acceso X-UI</h3>
                    <div style="margin-bottom:14px">
                        <label style="display:block; color:#94a3b8; font-size:0.7rem; font-weight:600; margin-bottom:6px; letter-spacing:1px">URL DE ACCESO</label>
                        <a href="${info.url}" target="_blank" style="display:block; padding:12px; background:var(--bg-elevated); border:1px solid var(--border); border-radius:10px; color:var(--primary); font-weight:600; font-family:monospace; text-decoration:none">${info.url || '--'}</a>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px">
                        <div>
                            <label style="display:block; color:#94a3b8; font-size:0.65rem; margin-bottom:4px">CERT PATH</label>
                            <div style="padding:8px; background:var(--bg-elevated); border-radius:8px; font-size:0.7rem; color:#64748b; font-family:monospace">${info.cert_path}</div>
                        </div>
                        <div>
                            <label style="display:block; color:#94a3b8; font-size:0.65rem; margin-bottom:4px">KEY PATH</label>
                            <div style="padding:8px; background:var(--bg-elevated); border-radius:8px; font-size:0.7rem; color:#64748b; font-family:monospace">${info.key_path}</div>
                        </div>
                    </div>
                    <button class="btn-primary" onclick="window.open('${info.url}','_blank')" style="margin:0; width:100%; background:linear-gradient(135deg,#8b5cf6,#7c3aed)">
                        <i class="fa-solid fa-arrow-up-right-from-square"></i> ABRIR PANEL
                    </button>
                </div>
            `;
        } else if (id === 'stunnel4') {
            sub.innerHTML = `
                <div style="padding:20px; background:#1a1f2e; border-radius:18px; border:1px solid #33415555">
                    <h3 style="color:white; font-size:1rem; font-weight:700; margin-bottom:16px"><i class="fa-solid fa-lock" style="color:var(--primary); margin-right:8px"></i>Configuración Stunnel</h3>
                    <pre style="padding:12px; background:var(--bg-elevated); border:1px solid var(--border); border-radius:10px; color:#94a3b8; font-size:0.75rem; max-height:200px; overflow-y:auto; white-space:pre-wrap">${info.config_preview || 'Sin configuración'}</pre>
                </div>
            `;
        }

        sub.scrollIntoView({ behavior: 'smooth' });
    } catch (e) {
        sub.innerHTML = '<div style="color:var(--danger);text-align:center;padding:20px">Error al cargar información</div>';
    }
}


function showSvcActionMenu(id, action) {
    const sub = document.getElementById('svcSubMenu');
    sub.innerHTML = '';
    sub.style.display = 'block';

    if (action === 'install') {
        if (id === 'stunnel4') {
            const methods = [
                { id: '1', name: 'Instalar Directo', desc: 'Conexión estándar sin intermediarios', icon: 'fa-terminal' },
                { id: '2', name: 'Instalar con Proxy', desc: 'Enrutamiento a través de un servidor Proxy', icon: 'fa-network-wired' },
                { id: '3', name: 'Modo Compatibilidad', desc: 'Funciones experimentales y ajustes (Híbrido)', icon: 'fa-flask' }
            ];

            let html = `
                <div style="padding:16px; background:#1a1f2e; border-radius:18px; border:1px solid #33415555; display:flex; justify-content:space-between; align-items:center; margin-bottom:20px">
                    <div>
                        <h3 style="color:white; font-size:1rem; font-weight:700">Seleccionar Método</h3>
                        <p style="color:#94a3b8; font-size:0.75rem">Elige el tipo de conexión deseada</p>
                    </div>
                    <span style="background:rgba(6,182,212,0.1); color:var(--primary); font-size:0.65rem; font-weight:700; padding:4px 10px; border-radius:6px">ESPERANDO</span>
                </div>
                <div id="methodList">
                    ${methods.map(m => `
                        <div class="method-card" data-mode="${m.id}" onclick="selectInstallMethod(this)">
                            <div class="method-icon"><i class="fa-solid ${m.icon}"></i></div>
                            <div class="method-info">
                                <span class="method-name">${m.name}</span>
                                <span class="method-desc">${m.desc}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <button id="btnStartInstall" class="btn-start-install" disabled onclick="handleAdvancedInstallExec('${id}')">
                    COMENZAR INSTALACIÓN
                </button>
            `;
            sub.innerHTML = html;
        } else {
            // Puerto automático para otros servicios (Dropbear, Proxy, etc)
            const defaultPorts = {dropbear:'44', badvpn:'7300', 'mx-proxy':'80', 'ws-epro':'80', 'hysteria':'443', 'x-ui':'8080'};
            const p = defaultPorts[id] || '80';
            sub.innerHTML = `
                <div style="padding:16px; background:#1a1f2e; border-radius:18px; border:1px solid #33415555; margin-bottom:20px">
                    <h3 style="color:white; font-size:1rem; font-weight:700; margin-bottom:14px">Configurar Instalación</h3>
                    <div class="field" style="margin-bottom:16px">
                        <label style="display:block; color:#94a3b8; font-size:0.75rem; margin-bottom:8px">PUERTO DE ESCUCHA:</label>
                        <input type="number" id="subPort" value="${p}" style="width:100%; padding:12px; background:var(--bg-elevated); border:1px solid var(--border); border-radius:10px; color:white; font-size:0.9rem; outline:none">
                    </div>
                    <button class="btn-primary" onclick="executeAdvancedInstall('${id}','',document.getElementById('subPort').value)" style="margin:0; width:100%">
                        <i class="fa-solid fa-download"></i> INICIAR INSTALACIÓN
                    </button>
                </div>
            `;
        }
    } else if (action === 'port') {
        sub.innerHTML = `
            <h4 style="margin-bottom:14px; font-size:0.9rem; color:var(--text-muted)">NUEVO PUERTO:</h4>
            <input type="number" id="subPort" placeholder="Ej: 444" style="width:100%; padding:12px; background:var(--bg-elevated); border:1px solid var(--border); border-radius:10px; color:white; margin-bottom:12px">
            <button class="btn-primary" onclick="svcConfigAction('${id}','change-port',document.getElementById('subPort').value)">GUARDAR CAMBIOS</button>
        `;
    }

    sub.scrollIntoView({ behavior: 'smooth' });
}

let selectedInstallMode = null;

function selectInstallMethod(el) {
    document.querySelectorAll('.method-card').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    selectedInstallMode = el.dataset.mode;
    
    const btn = document.getElementById('btnStartInstall');
    btn.disabled = false;
    btn.classList.add('ready');
}

async function handleAdvancedInstallExec(id) {
    if (!selectedInstallMode) return;
    executeAdvancedInstall(id, selectedInstallMode, '443');
}

async function executeAdvancedInstall(id, mode, port) {
    closeSvcModal();
    showToast(`⏳ Ejecutando acción en ${id}...`);
    try {
        const res = await fetch('/api/service/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id, action: 'install', port, mode })
        });
        const data = await res.json();
        if (data.success) showToast(`✅ Operación enviada para ${id}`);
        else showToast(`❌ Error: ${data.error}`);
        setTimeout(fetchServices, 2000);
    } catch (e) {
        showToast('❌ Error de conexión');
    }
}

async function svcConfigAction(id, action, portValue = null) {
    const portEl = document.getElementById('svcNewPort');
    const port = portValue || (portEl ? portEl.value : '');

    closeSvcModal();
    const labels = {restart:'Reiniciando', stop:'Deteniendo', start:'Iniciando', uninstall:'Desinstalando', 'change-port':'Cambiando puerto de'};
    showToast(`⏳ ${labels[action] || action} ${id}...`);

    try {
        const res = await fetch('/api/service/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id, action, port })
        });
        const data = await res.json();
        if (data.success) {
            if (action === 'change-port') showToast(`✅ Puerto cambiado a ${data.port}`);
            else showToast(data.active ? `✅ ${id} está ONLINE` : `⚠️ ${id} procesado`);
        } else showToast(`❌ Error: ${data.error}`);
        setTimeout(fetchServices, 2000);
    } catch (e) {
        showToast('❌ Error al gestionar servicio');
    }
}

async function executeInstall(id) {
    const portEl = document.getElementById('svcInstallPort');
    const port = portEl ? portEl.value : '';
    const modeEl = document.querySelector('input[name="stunMode"]:checked');
    const mode = modeEl ? modeEl.value : '';

    closeSvcModal();
    showToast(`⏳ Instalando ${id}...`);

    try {
        const res = await fetch('/api/service/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id, action: 'install', port, mode })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ ${id} instalado correctamente`);
        } else {
            showToast(`❌ ${data.error || 'Error'}`);
        }
        setTimeout(fetchServices, 2000);
    } catch (e) {
        showToast('❌ Error de conexión');
    }
}

// svcConfigAction ya está definida más abajo o arriba, nos aseguramos que solo haya UNA versión operativa que maneje puertos.
async function svcConfigAction(id, action, portValue = null) {
    const portEl = document.getElementById('subPort');
    const port = portValue || (portEl ? portEl.value : '');

    closeSvcModal();
    const labels = {restart:'Reiniciando', stop:'Deteniendo', start:'Iniciando', install:'Instalando', uninstall:'Desinstalando', 'change-port':'Copiando puerto'};
    showToast(`⏳ ${labels[action] || action} ${id}...`);

    try {
        const res = await fetch('/api/service/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id, action, port })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ Operación sobre ${id} completada`);
        } else {
            showToast(`❌ ${data.error || 'Error'}`);
        }
        setTimeout(fetchServices, 1500);
    } catch (e) {
        showToast('❌ Error al conectar con el servidor');
    }
}

function closeSvcModal() {
    document.getElementById('svcModal').classList.remove('show');
}

// ========== CONNECTIONS ==========
async function fetchConnections() {
    const tbody = document.getElementById('connListBody');
    tbody.innerHTML = '<tr><td colspan="5" class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i> Cargando...</td></tr>';

    try {
        const res = await fetch('/api/connections');
        const conns = await res.json();
        if (!conns.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No hay conexiones activas</td></tr>';
            return;
        }
        tbody.innerHTML = conns.map(c => `<tr>
            <td><span class="badge badge-ssh">${c.proto}</span></td>
            <td><code>${c.local}</code></td>
            <td><code>${c.remote}</code></td>
            <td><span class="status-active">${c.state}</span></td>
            <td>${c.process}</td>
        </tr>`).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Error al cargar conexiones</td></tr>';
    }
}

// ========== GENERATOR ==========
function openGen(type) {
    document.getElementById('genType').value = type;
    document.getElementById('genTitle').innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Crear Cuenta ${type.toUpperCase()}`;
    document.getElementById('genUser').value = '';
    document.getElementById('genPass').value = '';
    document.getElementById('genDays').value = 3;
    document.getElementById('genModal').classList.add('show');
}

function closeModal() {
    document.getElementById('genModal').classList.remove('show');
}

function closeResultModal() {
    document.getElementById('resultModal').classList.remove('show');
}

async function handleCreate(e) {
    e.preventDefault();
    const type = document.getElementById('genType').value;
    const username = document.getElementById('genUser').value.trim();
    const password = document.getElementById('genPass').value.trim();
    const days = parseInt(document.getElementById('genDays').value) || 3;

    const btn = document.getElementById('genSubmitBtn');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creando...';
    btn.disabled = true;

    try {
        const endpoint = type === 'hysteria' ? '/api/create/hysteria' : '/api/create/ssh';
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ username, password, days })
        });
        const data = await res.json();

        if (data.success) {
            closeModal();
            let resultText = `🎉 Cuenta ${type.toUpperCase()} Creada\n\n`;
            resultText += `👤 Usuario: ${data.username}\n`;
            resultText += `🔑 Contraseña: ${data.password}\n`;
            resultText += `📅 Vencimiento: ${data.expiry}\n`;
            resultText += `🌐 Server: ${data.server_ip || '--'}\n`;
            if (data.link) resultText += `\n🔗 Link:\n${data.link}`;

            document.getElementById('resultData').innerText = resultText;
            document.getElementById('resultModal').classList.add('show');
            showToast('✅ Cuenta creada con éxito');
        } else {
            showToast(`❌ ${data.error}`);
        }
    } catch (e) {
        showToast('❌ Error de conexión');
    }

    btn.innerHTML = '<span class="btn-label">GENERAR CUENTA</span><i class="fa-solid fa-arrow-right"></i>';
    btn.disabled = false;
}

function copyResult() {
    const text = document.getElementById('resultData').innerText;
    navigator.clipboard.writeText(text).then(() => {
        showToast('📋 Datos copiados al portapapeles');
    });
}

// ========== HERRAMIENTAS DE SISTEMA (Réplica 1:1 del menu_sistema MX) ==========

function showConsole(title, html) {
    const con = document.getElementById('toolConsole');
    const body = document.getElementById('toolConsoleBody');
    con.style.display = 'block';
    body.innerHTML = `<div style="font-weight:700;color:var(--primary);margin-bottom:12px;font-size:0.9rem"><i class="fa-solid fa-terminal" style="margin-right:6px"></i>${title}</div>${html}`;
    con.scrollIntoView({ behavior: 'smooth' });
}

function logLine(text, type = 'info') {
    const colors = { info: '#94a3b8', success: 'var(--success)', error: 'var(--danger)', warn: '#f59e0b' };
    return `<div style="font-family:monospace;font-size:0.8rem;padding:4px 0;color:${colors[type] || colors.info}">${text}</div>`;
}

async function toolOptimize() {
    showConsole('Optimizar VPS', logLine('⏳ Ejecutando optimización del sistema...', 'warn'));
    try {
        const res = await fetch('/api/tools/optimize', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            let html = data.log.map(l => logLine(`✅ ${l}`, 'success')).join('');
            showConsole('Optimizar VPS — Completado', html);
            showToast('✅ VPS Optimizado');
        } else {
            showConsole('Error', logLine(`❌ ${data.error}`, 'error'));
        }
    } catch (e) { showConsole('Error', logLine('❌ Error de conexión con el backend', 'error')); }
}

async function toolBanner() {
    showConsole('Editor de Banner', logLine('⏳ Cargando banner actual de /etc/issue.net...', 'warn'));
    try {
        const res = await fetch('/api/tools/banner');
        const data = await res.json();
        showConsole('Editor de Banner — /etc/issue.net', `
            <textarea id="bannerEditor" style="width:100%;height:200px;background:var(--bg-elevated);border:1px solid var(--border);border-radius:10px;color:var(--text);font-family:monospace;font-size:0.8rem;padding:12px;resize:vertical">${data.banner || ''}</textarea>
            <button class="btn-primary" onclick="saveBanner()" style="margin-top:12px;width:100%"><i class="fa-solid fa-floppy-disk"></i> GUARDAR BANNER</button>
        `);
    } catch (e) { showConsole('Error', logLine('❌ Error de conexión', 'error')); }
}

async function saveBanner() {
    const content = document.getElementById('bannerEditor').value;
    try {
        const res = await fetch('/api/tools/banner', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ content })
        });
        const data = await res.json();
        if (data.success) showToast('✅ Banner guardado en /etc/issue.net');
        else showToast(`❌ ${data.error}`);
    } catch (e) { showToast('❌ Error de conexión'); }
}

async function toolBackup() {
    showConsole('Respaldar Cuentas', logLine('⏳ Generando /root/users_backup.tar ...', 'warn'));
    try {
        const res = await fetch('/api/tools/backup', { method: 'POST' });
        const data = await res.json();
        let html = '';
        if (data.success) {
            html += logLine(`✅ Backup generado: ${data.path}`, 'success');
            html += logLine(`📦 Tamaño: ${data.size}`, 'info');
            if (data.log) data.log.forEach(l => { html += logLine(`  ${l}`, 'info'); });
        } else {
            html += logLine(`❌ Error: ${data.error}`, 'error');
        }
        showConsole('Backup', html);
        if (data.success) showToast(`✅ Backup guardado: ${data.size}`);
    } catch (e) { showConsole('Error', logLine('❌ Error de conexión', 'error')); }
}

async function toolTraffic() {
    showConsole('Monitor de Tráfico', logLine('⏳ Consultando /proc/net/dev y netstat...', 'warn'));
    try {
        const res = await fetch('/api/tools/traffic');
        const data = await res.json();
        let html = '';
        html += logLine(`📡 Interfaz: ${data.interface}`, 'info');
        html += logLine(`⬇️ Descarga: ${data.rx_gb} GB (${data.rx_bytes.toLocaleString()} bytes)`, 'success');
        html += logLine(`⬆️ Subida: ${data.tx_gb} GB (${data.tx_bytes.toLocaleString()} bytes)`, 'success');
        if (data.top_ips && data.top_ips.length > 0) {
            html += '<div style="margin-top:16px;font-weight:700;color:var(--text);font-size:0.85rem">Top IPs Conectadas:</div>';
            html += '<table style="width:100%;margin-top:8px"><thead><tr><th style="text-align:left;color:#94a3b8;font-size:0.7rem">IP</th><th style="text-align:right;color:#94a3b8;font-size:0.7rem">Conexiones</th></tr></thead><tbody>';
            data.top_ips.forEach(ip => {
                html += `<tr><td style="font-family:monospace;font-size:0.8rem">${ip.ip}</td><td style="text-align:right;font-weight:700;color:var(--primary)">${ip.connections}</td></tr>`;
            });
            html += '</tbody></table>';
        } else {
            html += logLine('ℹ️ No hay conexiones activas', 'info');
        }
        showConsole('Monitor de Tráfico', html);
    } catch (e) { showConsole('Error', logLine('❌ Error de conexión', 'error')); }
}

async function toolFirewall() {
    showConsole('Firewall UFW', logLine('⏳ Consultando estado de UFW...', 'warn'));
    try {
        const res = await fetch('/api/tools/firewall');
        const fw = await res.json();
        let html = '';
        html += logLine(`Estado: ${fw.active ? '🟢 ACTIVO' : '🔴 INACTIVO'}`, fw.active ? 'success' : 'error');
        if (fw.rules && fw.rules.length > 0) {
            html += '<div style="margin-top:12px;font-weight:700;color:var(--text);font-size:0.85rem">Reglas activas:</div>';
            fw.rules.forEach(r => { html += logLine(`  ${r}`, 'info'); });
        }
        html += `
        <div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap">
            <button class="btn-primary" onclick="fwAction('${fw.active ? 'disable' : 'enable'}')" style="flex:1;min-width:120px;background:${fw.active ? 'var(--danger)' : 'var(--success)'}">
                <i class="fa-solid ${fw.active ? 'fa-power-off' : 'fa-shield-halved'}"></i> ${fw.active ? 'DESACTIVAR' : 'ACTIVAR'}
            </button>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px;align-items:center">
            <input type="number" id="fwPort" placeholder="Puerto" style="flex:1;padding:10px;background:var(--bg-elevated);border:1px solid var(--border);border-radius:8px;color:white;font-size:0.85rem">
            <select id="fwProto" style="padding:10px;background:var(--bg-elevated);border:1px solid var(--border);border-radius:8px;color:white;font-size:0.85rem">
                <option value="tcp">TCP</option>
                <option value="udp">UDP</option>
            </select>
            <button class="btn-primary" onclick="fwAction('allow')" style="padding:10px 16px"><i class="fa-solid fa-plus"></i> Abrir</button>
            <button class="btn-primary" onclick="fwAction('delete')" style="padding:10px 16px;background:var(--danger)"><i class="fa-solid fa-minus"></i> Cerrar</button>
        </div>`;
        showConsole('Firewall UFW', html);
    } catch (e) { showConsole('Error', logLine('❌ Error de conexión', 'error')); }
}

async function fwAction(action) {
    const port = document.getElementById('fwPort')?.value || '';
    const proto = document.getElementById('fwProto')?.value || 'tcp';
    try {
        const res = await fetch('/api/tools/firewall', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ action, port, proto })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ Firewall: ${action} ejecutado`);
            toolFirewall(); // Refrescar
        } else {
            showToast(`❌ ${data.error}`);
        }
    } catch (e) { showToast('❌ Error de conexión'); }
}

async function toolCloudflare() {
    showConsole('Cloudflare DDNS', logLine('⏳ Cargando configuración sincronizada...', 'warn'));
    try {
        const res = await fetch('/api/tools/cloudflare');
        const cf = await res.json();
        let html = `
            <div style="margin-bottom:12px">${logLine(`Sincronización Cron: ${cf.active ? '🟢 ACTIVA' : '🔴 INACTIVA'}`, cf.active ? 'success' : 'error')}</div>
            <div style="margin-bottom:12px">
                <label style="color:#94a3b8;font-size:0.7rem;font-weight:600">DOMINIO / RECORD</label>
                <input type="text" id="cfRecord" value="${cf.record}" placeholder="vpn.dominio.com" style="width:100%;padding:10px;background:var(--bg-elevated);border:1px solid var(--border);border-radius:10px;color:white;font-family:monospace;font-size:0.8rem">
            </div>
            <div style="display:flex;gap:8px">
                <button class="btn-primary" onclick="cfAction('enable')" style="flex:1;background:var(--success)"><i class="fa-solid fa-play"></i> ACTIVAR</button>
                <button class="btn-primary" onclick="cfAction('disable')" style="flex:1;background:var(--danger)"><i class="fa-solid fa-stop"></i> PARAR</button>
            </div>
            <div style="margin-top:12px;font-size:0.7rem;color:var(--text-dim)">* Use 'Configurar' para editar Token y ZoneID.</div>
        `;
        showConsole('Cloudflare DDNS Sync', html);
    } catch (e) { showConsole('Error', logLine('❌ Error de conexión Cloudflare', 'error')); }
}

async function cfAction(action) {
    const body = { action };
    if (action === 'save') {
        body.token = document.getElementById('cfToken').value.trim();
        body.zone_id = document.getElementById('cfZone').value.trim();
        body.record = document.getElementById('cfRecord').value.trim();
    }
    try {
        const res = await fetch('/api/tools/cloudflare', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ Cloudflare: ${action} ejecutado`);
            if (action !== 'save') toolCloudflare();
        } else {
            showToast(`❌ ${data.error}`);
        }
    } catch (e) { showToast('❌ Error de conexión'); }
}


async function logout() {
    await fetch('/api/logout');
    if (eventSource) eventSource.close();
    window.location.href = '/login.html';
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3500);
}
