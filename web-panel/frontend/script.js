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

            let actionBtns = '';
            if (!s.installed && s.has_installer) {
                actionBtns = `<button class="svc-btn install" title="Instalar" onclick="serviceAction('${s.id}','install')"><i class="fa-solid fa-download"></i></button>`;
            } else if (s.installed) {
                actionBtns = `
                    <button class="svc-btn" title="Reiniciar" onclick="serviceAction('${s.id}','restart')"><i class="fa-solid fa-rotate-right"></i></button>
                    <button class="svc-btn" title="${s.active ? 'Detener' : 'Iniciar'}" onclick="serviceAction('${s.id}','${s.active ? 'stop' : 'start'}')"><i class="fa-solid ${s.active ? 'fa-stop' : 'fa-play'}"></i></button>
                    ${s.has_installer ? `<button class="svc-btn danger" title="Desinstalar" onclick="if(confirm('¿Desinstalar ${s.name}?')) serviceAction('${s.id}','uninstall')"><i class="fa-solid fa-trash-can"></i></button>` : ''}
                `;
            }

            return `
            <div class="service-card ${stateClass}">
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
                    <div class="svc-actions" style="margin-top:8px">
                        ${actionBtns}
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
