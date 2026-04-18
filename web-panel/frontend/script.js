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
    // CPU
    const cpuVal = parseFloat(data.cpu?.load) || 0;
    document.getElementById('cpu-val').innerText = `${cpuVal.toFixed(1)}%`;
    document.getElementById('cpu-bar').style.width = `${Math.min(cpuVal, 100)}%`;
    document.getElementById('cpu-detail').innerText = `${data.cpu?.cores || '--'} cores · ${data.cpu?.model || '--'}`;

    // RAM
    const ramUsed = parseInt(data.ram?.used) || 0;
    const ramTotal = parseInt(data.ram?.total) || 1;
    const ramPerc = ((ramUsed / ramTotal) * 100).toFixed(1);
    document.getElementById('ram-val').innerText = `${ramPerc}%`;
    document.getElementById('ram-bar').style.width = `${ramPerc}%`;
    document.getElementById('ram-detail').innerText = `${ramUsed} / ${ramTotal} MB`;

    // Disk
    document.getElementById('disk-val').innerText = data.disk?.percent || '0%';
    const diskPerc = parseInt(data.disk?.percent) || 0;
    document.getElementById('disk-bar').style.width = `${diskPerc}%`;
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
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No hay usuarios registrados</td></tr>';
        return;
    }
    tbody.innerHTML = users.map(u => `<tr>
        <td><strong>${u.username}</strong></td>
        <td><span class="badge ${u.type === 'SSH/SSL' ? 'badge-ssh' : 'badge-hy'}">${u.type}</span></td>
        <td><code>${u.password}</code></td>
        <td>${u.expiry}</td>
        <td><span class="${u.status === 'Active' ? 'status-active' : 'status-expired'}">${u.status}</span></td>
        <td><button class="btn-delete" onclick="deleteUser('${u.username}')"><i class="fa-solid fa-trash-can"></i></button></td>
    </tr>`).join('');
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

    let content = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding:14px;background:rgba(255,255,255,0.03);border-radius:12px">
            <div>
                <div style="font-weight:600">${svc.desc}</div>
                <div style="font-size:0.8rem;color:var(--text-dim);margin-top:4px">Puerto actual: <strong style="color:var(--primary)">${svc.port}</strong></div>
            </div>
            ${statusBadge}
        </div>
    `;

    // Si NO está instalado y tiene instalador → mostrar formulario de instalación
    if (!svc.installed && svc.has_installer) {
        content += buildInstallForm(svc);
    }

    // Si YA está instalado → mostrar controles
    if (svc.installed) {
        content += `<div style="display:flex;flex-direction:column;gap:10px">`;

        // Cambiar Puerto
        if (['ssh', 'dropbear', 'stunnel4', 'badvpn', 'x-ui'].includes(svc.id)) {
            content += `
                <div style="display:flex;gap:8px;align-items:center">
                    <input type="number" id="svcNewPort" placeholder="Nuevo puerto..." value="${svc.port !== '--' ? svc.port : ''}" 
                        style="flex:1;padding:11px 14px;background:var(--bg-elevated);border:1px solid var(--border);border-radius:10px;color:white;font-size:0.88rem;outline:none">
                    <button onclick="svcConfigAction('${svc.id}','change-port')" class="btn-primary" style="width:auto;margin:0;padding:11px 18px;white-space:nowrap">
                        <i class="fa-solid fa-plug"></i> Cambiar Puerto
                    </button>
                </div>
            `;
        }

        // Botones de control
        content += `
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:6px">
                <button onclick="svcConfigAction('${svc.id}','restart')" class="btn-primary" style="margin:0;background:linear-gradient(135deg,var(--primary),#0891b2)">
                    <i class="fa-solid fa-rotate-right"></i> Reiniciar
                </button>
                <button onclick="svcConfigAction('${svc.id}','${svc.active ? 'stop' : 'start'}')" class="btn-primary" style="margin:0;background:${svc.active ? 'linear-gradient(135deg,var(--warning),#d97706)' : 'linear-gradient(135deg,var(--success),#059669)'}">
                    <i class="fa-solid ${svc.active ? 'fa-stop' : 'fa-play'}"></i> ${svc.active ? 'Detener' : 'Iniciar'}
                </button>
            </div>
        `;

        // Reinstalar y Desinstalar
        if (svc.has_installer) {
            content += `
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:4px">
                    <button onclick="svcConfigAction('${svc.id}','install')" class="btn-secondary" style="margin:0">
                        <i class="fa-solid fa-download"></i> Reinstalar
                    </button>
                    <button onclick="if(confirm('¿Desinstalar ${svc.name}?')) svcConfigAction('${svc.id}','uninstall')" class="btn-secondary" style="margin:0;border-color:rgba(239,68,68,0.3);color:var(--danger)">
                        <i class="fa-solid fa-trash-can"></i> Desinstalar
                    </button>
                </div>
            `;
        }

        content += `</div>`;
    }

    body.innerHTML = content;
    modal.classList.add('show');
}

function buildInstallForm(svc) {
    let form = '<div style="border-top:1px solid var(--border);padding-top:18px;margin-top:4px">';
    form += '<h4 style="margin-bottom:14px;font-size:0.95rem"><i class="fa-solid fa-download" style="color:var(--success);margin-right:8px"></i>Instalar ${svc.name}</h4>'.replace('${svc.name}', svc.name);

    // Stunnel: opciones de modo
    if (svc.id === 'stunnel4') {
        form += `
            <div class="field" style="margin-bottom:14px">
                <label>Modo de conexión SSL</label>
                <div style="display:flex;flex-direction:column;gap:8px;margin-top:8px">
                    <label style="display:flex;align-items:center;gap:10px;padding:12px;background:rgba(255,255,255,0.03);border-radius:10px;border:1px solid var(--border);cursor:pointer">
                        <input type="radio" name="stunMode" value="1" checked style="width:auto;margin:0">
                        <div>
                            <div style="font-weight:600;font-size:0.88rem;color:var(--text)">SSL Directo</div>
                            <div style="font-size:0.75rem;color:var(--text-dim)">SSL → SSH · Máxima velocidad, sin Payloads</div>
                        </div>
                    </label>
                    <label style="display:flex;align-items:center;gap:10px;padding:12px;background:rgba(255,255,255,0.03);border-radius:10px;border:1px solid var(--border);cursor:pointer">
                        <input type="radio" name="stunMode" value="2" style="width:auto;margin:0">
                        <div>
                            <div style="font-weight:600;font-size:0.88rem;color:var(--text)">SSL + Proxy</div>
                            <div style="font-size:0.75rem;color:var(--text-dim)">SSL → Proxy 80 → SSH · Para Payloads y apps HTTP</div>
                        </div>
                    </label>
                    <label style="display:flex;align-items:center;gap:10px;padding:12px;background:rgba(255,255,255,0.03);border-radius:10px;border:1px solid var(--border);cursor:pointer">
                        <input type="radio" name="stunMode" value="3" style="width:auto;margin:0">
                        <div>
                            <div style="font-weight:600;font-size:0.88rem;color:var(--text)">Híbrido Universal</div>
                            <div style="font-size:0.75rem;color:var(--text-dim)">Acepta TODO automáticamente (BETA)</div>
                        </div>
                    </label>
                </div>
            </div>
        `;
    }

    // Campo de puerto
    const defaultPorts = {
        'stunnel4': '443', 'dropbear': '44', 'badvpn': '7300', 'mx-proxy': '80',
        'ws-epro': '80', 'mx-slowdns': '53', 'udp-custom': '36712',
    };
    const defPort = defaultPorts[svc.id] || '';

    if (defPort) {
        form += `
            <div class="field" style="margin-bottom:16px">
                <label>Puerto de instalación</label>
                <div class="field-input">
                    <i class="fa-solid fa-plug"></i>
                    <input type="number" id="svcInstallPort" value="${defPort}" placeholder="Puerto...">
                </div>
            </div>
        `;
    }

    form += `
        <button onclick="executeInstall('${svc.id}')" class="btn-primary" style="background:linear-gradient(135deg,var(--success),#059669)">
            <i class="fa-solid fa-download"></i> INSTALAR ${svc.name.toUpperCase()}
        </button>
    `;
    form += '</div>';
    return form;
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
