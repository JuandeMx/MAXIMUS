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
    const diskPerc = parseInt(data.disk?.percent) || 0;
    document.getElementById('disk-val').innerText = `${diskPerc}%`;
    setRing('disk-ring', diskPerc);
    document.getElementById('disk-detail').innerText = `${data.disk?.used || '--'} / ${data.disk?.total || '--'}`;

    // Online
    document.getElementById('online-val').innerText = data.online || '0';
    document.getElementById('users-detail').innerText = `Total: ${data.total_users || 0} cuentas`;

    // Uptime
    document.getElementById('uptime-val').innerText = data.uptime || '--';

    // Network
    document.getElementById('net-rx').innerText = `${data.network?.rx || '0'} GB`;
    document.getElementById('net-tx').innerText = `${data.network?.tx || '0'} GB`;

    // System info
    document.getElementById('sys-hostname').innerText = data.system?.hostname || '--';
    document.getElementById('sys-kernel').innerText = data.system?.kernel || '--';
    document.getElementById('sys-loadavg').innerText = data.load_avg || '--';
    document.getElementById('server-ip').innerText = data.system?.ip || '--';
    document.getElementById('server-os').innerText = data.system?.os || '--';

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

        // Fila 3: Info específica por servicio
        if (svc.id === 'mx-slowdns') {
            content += `
                <div class="action-tile info" onclick="showServiceInfo('${svc.id}')" style="grid-column: span 2; border-color: rgba(139,92,246,0.3)">
                    <i class="fa-solid fa-key" style="color:#8b5cf6"></i>
                    <div class="action-label" style="color:#8b5cf6">VER LLAVE PÚBLICA</div>
                </div>
            `;
        } else if (svc.id === 'x-ui') {
            content += `
                <div class="action-tile info" onclick="showServiceInfo('${svc.id}')" style="grid-column: span 2; border-color: rgba(139,92,246,0.3)">
                    <i class="fa-solid fa-arrow-up-right-from-square" style="color:#8b5cf6"></i>
                    <div class="action-label" style="color:#8b5cf6">ABRIR PANEL WEB</div>
                </div>
            `;
        } else if (svc.id === 'stunnel4') {
            content += `
                <div class="action-tile info" onclick="showServiceInfo('${svc.id}')" style="grid-column: span 2; border-color: rgba(6,182,212,0.2)">
                    <i class="fa-solid fa-file-lines"></i>
                    <div class="action-label">VER CONFIGURACIÓN</div>
                </div>
            `;
        }

        // Fila Final: START/STOP
        content += `
            <div class="action-tile ${svc.active ? 'stop' : 'start'}" onclick="svcConfigAction('${svc.id}','${svc.active ? 'stop' : 'start'}')" style="grid-column: span 2; margin-top: 4px; border-color: ${svc.active ? 'var(--danger)' : 'var(--success)'}">
                <i class="fa-solid ${svc.active ? 'fa-stop' : 'fa-play'}"></i>
                <div class="action-label">${svc.active ? 'DETENER SERVICIO' : 'INICIAR SERVICIO'}</div>
            </div>
        `;
    }

    content += `</div>`;

    // Contenedor para Sub-Menús + Info (oculto por defecto)
    content += `<div id="svcSubMenu" class="svc-submenu-container" style="display:none; margin-top: 20px; border-top: 1px solid var(--border); padding-top: 20px;"></div>`;

    body.innerHTML = content;
    modal.classList.add('show');
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

async function svcConfigAction(id, action) {
    const portEl = document.getElementById('svcNewPort');
    const port = portEl ? portEl.value : '';

    closeSvcModal();

    const labels = {restart:'Reiniciando', stop:'Deteniendo', start:'Iniciando', install:'Reinstalando', uninstall:'Desinstalando', 'change-port':'Cambiando puerto de'};
    showToast(`⏳ ${labels[action] || action} ${id}...`);

    try {
        const res = await fetch('/api/service/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id, action, port })
        });
        const data = await res.json();
        if (data.success) {
            if (action === 'change-port') showToast(`✅ Puerto de ${id} cambiado a ${data.port}`);
            else if (action === 'uninstall') showToast(`🗑️ ${id} desinstalado`);
            else if (action === 'install') showToast(`✅ ${id} reinstalado`);
            else showToast(data.active ? `✅ ${id} ONLINE` : `⚠️ ${id} OFFLINE`);
        } else {
            showToast(`❌ ${data.error || 'Error'}`);
        }
        setTimeout(fetchServices, 1500);
    } catch (e) {
        showToast('❌ Error al gestionar servicio');
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

// ========== UTILS ==========
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
