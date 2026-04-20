/* ==========================================
   MAXIMUS LIVE ENGINE v3.1
   Custom SSE Real-Time Monitor
   ========================================== */

let mainChart;
let history = { cpu: Array(30).fill(0), ram: Array(30).fill(0) };

document.addEventListener('DOMContentLoaded', () => {
    console.log("Maximus v3.1 Engine Starting...");
    initChart();
    startStream();
});

function startStream() {
    const dot = document.getElementById('stream-dot');
    const txt = document.getElementById('stream-text');

    const es = new EventSource('/api/stream');

    es.onmessage = (e) => {
        const data = JSON.parse(e.data);
        console.log("Data:", data);
        updateUI(data);
        
        dot.style.background = '#10b981';
        dot.style.boxShadow = '0 0 10px #10b981';
        txt.innerText = 'EN VIVO';
    };

    es.onerror = () => {
        dot.style.background = '#ef4444';
        dot.style.boxShadow = '0 0 10px #ef4444';
        txt.innerText = 'RECONECTANDO...';
    };
}

function updateUI(data) {
    if (!data) return;

    // CPU
    const cpu = data.cpu?.load || 0;
    document.getElementById('val-cpu').innerText = `${cpu}%`;
    document.getElementById('fill-cpu').style.width = `${cpu}%`;
    document.getElementById('val-cpu-detail').innerText = `${data.cpu?.cores || '--'} cores · ${data.cpu?.model || '--'}`;

    // RAM
    const ramPerc = data.ram?.percent || 0;
    document.getElementById('val-ram').innerText = `${ramPerc}%`;
    document.getElementById('fill-ram').style.width = `${ramPerc}%`;
    document.getElementById('val-ram-detail').innerText = `${data.ram?.used || 0} / ${data.ram?.total || 1} MB`;

    // DISK
    const diskPerc = data.disk?.percent || 0;
    document.getElementById('val-disk').innerText = `${diskPerc}%`;
    document.getElementById('fill-disk').style.width = `${diskPerc}%`;
    document.getElementById('val-disk-detail').innerText = `${data.disk?.used || '--'} / ${data.disk?.total || '--'}`;

    // ONLINE
    document.getElementById('val-online').innerText = data.online || '0';
    document.getElementById('val-users').innerText = data.total_users || '0';

    // NET
    document.getElementById('val-rx').innerText = `${data.net?.rx || 0} GB`;
    document.getElementById('val-tx').innerText = `${data.net?.tx || 0} GB`;

    // SYS
    document.getElementById('val-uptime').innerText = data.sys?.uptime || '--';
    document.getElementById('val-host').innerText = data.sys?.hostname || '--';
    document.getElementById('val-kernel').innerText = data.sys?.kernel || '--';
    document.getElementById('val-os').innerText = data.sys?.os || '--';
    document.getElementById('display-ip').innerText = data.sys?.ip || '0.0.0.0';

    // CHART
    history.cpu.push(cpu);
    history.cpu.shift();
    history.ram.push(parseFloat(ramPerc));
    history.ram.shift();
    
    if (mainChart) {
        mainChart.data.datasets[0].data = [...history.cpu];
        mainChart.data.datasets[1].data = [...history.ram];
        mainChart.update('none');
    }
}

function initChart() {
    const canvas = document.getElementById('mainChart');
    if (!canvas) return;

    try {
        const ctx = canvas.getContext('2d');
        
        const cpuGrad = ctx.createLinearGradient(0, 0, 0, 250);
        cpuGrad.addColorStop(0, 'rgba(6, 182, 212, 0.2)');
        cpuGrad.addColorStop(1, 'rgba(6, 182, 212, 0)');

        const ramGrad = ctx.createLinearGradient(0, 0, 0, 250);
        ramGrad.addColorStop(0, 'rgba(139, 92, 246, 0.15)');
        ramGrad.addColorStop(1, 'rgba(139, 92, 246, 0)');

        mainChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(30).fill(''),
                datasets: [
                    {
                        label: 'CPU',
                        data: [...history.cpu],
                        borderColor: '#06b6d4',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 0,
                        fill: true,
                        backgroundColor: cpuGrad
                    },
                    {
                        label: 'RAM',
                        data: [...history.ram],
                        borderColor: '#8b5cf6',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 0,
                        fill: true,
                        backgroundColor: ramGrad
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: { 
                        beginAtZero: true, 
                        max: 100, 
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#475569', font: { size: 10 } }
                    }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });
    } catch (e) {
        console.warn("Chart.js failed:", e);
    }
}

// ========== NAVIGATION ==========
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        if(link.classList.contains('disabled')) return;
        e.preventDefault();
        
        document.querySelectorAll('.nav-link').forEach(n => n.classList.remove('active'));
        link.classList.add('active');
        
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        const tab = link.dataset.tab;
        const targetPanel = document.getElementById(`tab-${tab}`);
        if(targetPanel) targetPanel.classList.add('active');
        
        const titles = {dashboard: 'Dashboard Principal', users: 'Gestión de Usuarios', services: 'Protocolos y Servicios', settings: 'Ajustes Visuales'};
        document.getElementById('pageTitle').innerText = titles[tab] || tab;
        
        if (tab === 'users') fetchUsers();
        if (tab === 'services') fetchServices();
    });
});

function showToast(msg) {
    const t = document.getElementById('toast');
    if(!t) return alert(msg);
    t.innerText = msg;
    t.className = "toast show";
    setTimeout(() => { t.className = t.className.replace("show", ""); }, 3000);
}

// ========== USERS ==========
let allUsers = [];

async function fetchUsers() {
    const tbody = document.getElementById('userListBody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">Cargando...</td></tr>';
    try {
        const res = await fetch('/api/users/list');
        allUsers = await res.json();
        renderUsers(allUsers);
    } catch(e) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color: #ef4444">Error de red</td></tr>'; }
}

function renderUsers(users) {
    const tbody = document.getElementById('userListBody');
    if(!users.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center">No hay usuarios</td></tr>'; return; }
    tbody.innerHTML = users.map(u => {
        let statusColor = u.status === 'Active' ? '#10b981' : '#ef4444';
        return `
        <tr>
            <td><strong>${u.username}</strong></td>
            <td><code>${u.password || '******'}</code></td>
            <td>${u.limit}</td>
            <td>${u.expiry}</td>
            <td style="color:${u.days_left > 3 ? '#10b981' : '#f59e0b'}">${u.days_left} d</td>
            <td style="color:${statusColor}">${u.status}</td>
            <td>
                <button class="btn-mini" onclick="renewUser('${u.username}')" title="Agregar días"><i class="fa-solid fa-calendar-plus"></i></button>
                <button class="btn-mini" onclick="editUser('${u.username}')" title="Modificar"><i class="fa-solid fa-pen"></i></button>
                <button class="btn-mini" onclick="deleteUser('${u.username}')" title="Eliminar"><i class="fa-solid fa-trash-can"></i></button>
            </td>
        </tr>
    `}).join('');
}

// User CRUD operations
window.openCreateUserModal = function() {
    document.getElementById('userModalTitle').innerText = "Crear Usuario";
    document.getElementById('editMode').value = "0";
    document.getElementById('uname').value = "";
    document.getElementById('uname').disabled = false;
    document.getElementById('upass').value = "";
    document.getElementById('udays').value = "30";
    document.getElementById('ulimit').value = "1";
    document.getElementById('daysField').style.display = "block";
    document.getElementById('userModal').classList.add('show');
}

window.editUser = function(username) {
    const user = allUsers.find(u => u.username === username);
    if(!user) return;
    document.getElementById('userModalTitle').innerText = "Editar Usuario: " + username;
    document.getElementById('editMode').value = "1";
    document.getElementById('uname').value = username;
    document.getElementById('uname').disabled = true;
    document.getElementById('upass').value = ""; // Leave blank to not change
    document.getElementById('ulimit').value = user.limit;
    document.getElementById('daysField').style.display = "none";
    document.getElementById('userModal').classList.add('show');
}

window.closeUserModal = function() {
    document.getElementById('userModal').classList.remove('show');
}

window.submitUserForm = async function() {
    const isEdit = document.getElementById('editMode').value === "1";
    const username = document.getElementById('uname').value;
    const password = document.getElementById('upass').value;
    const limit = document.getElementById('ulimit').value;
    
    if (isEdit) {
        let payload = { username, limit };
        if (password) payload.password = password;
        await executeUserAction('/api/users/edit', payload, "Usuario actualizado");
    } else {
        const days = document.getElementById('udays').value;
        if(!username || !password) return showToast("Llene usuario y contraseña");
        await executeUserAction('/api/users/create', {username, password, days, limit}, "Usuario creado");
    }
    closeUserModal();
}

window.deleteUser = async function(username) {
    if(confirm(`¿Eliminar al usuario ${username}?`)) await executeUserAction('/api/users/delete', {username}, "Usuario eliminado");
}
window.renewUser = function(username) {
    document.getElementById('renewUnameDisplay').innerText = username;
    document.getElementById('renewUnameStore').value = username;
    document.getElementById('renewDays').value = "30";
    document.getElementById('renewModal').classList.add('show');
}
window.closeRenewModal = function() {
    document.getElementById('renewModal').classList.remove('show');
}
window.submitRenewForm = async function() {
    const username = document.getElementById('renewUnameStore').value;
    const days = document.getElementById('renewDays').value;
    if(!days || days < 1) return showToast("Monto inválido de días");
    
    closeRenewModal();
    await executeUserAction('/api/users/renew', {username, days}, `Se sumaron ${days} días a ${username}`);
}
window.toggleLock = async function(username) {
    await executeUserAction('/api/users/toggle-lock', {username}, "Estado de bloqueo modificado");
}

async function executeUserAction(endpoint, payload, successMsg) {
    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(data.success) { showToast(successMsg); fetchUsers(); }
        else showToast("Error: " + data.error);
    } catch(e) { showToast("Error de red al conectar con el servidor API"); }
}

// ========== STUNNEL UI LOGIC ==========
let stunnelIsOnline = false;
let stunnelPort = 443;

// ========== PROXY 80 UI LOGIC ==========
let proxyIsOnline = false;
let proxyPort = 80;

async function fetchServices() {
    try {
        const res = await fetch('/api/service/status');
        const services = await res.json();
        const stnl = services.find(s => s.id === 'stunnel4');
        if(stnl) {
            stunnelIsOnline = stnl.active;
            stunnelPort = stnl.port;
            document.getElementById('stnlPort').innerText = stunnelPort;
            updateServiceUI('stunnel4', stnl, 'stnlStatusTxt', 'stunnelAccent', 'btnStnlToggle');
        }

        const prxy = services.find(s => s.id === 'mx-proxy');
        if(prxy) {
            proxyIsOnline = prxy.active;
            proxyPort = prxy.port;
            document.getElementById('proxyPortTxt').innerText = proxyPort;
            updateServiceUI('mx-proxy', prxy, 'proxyStatusTxt', 'proxyAccent', 'btnProxyToggle');
        }
    } catch(e) { console.error("Error cargando status de servicios", e); }
}

function updateServiceUI(id, data, labelId, accentId, btnId) {
    const label = document.getElementById(labelId);
    const accent = document.getElementById(accentId);
    const btnToggle = document.getElementById(btnId);
    if(!label || !accent || !btnToggle) return;

    if(!data.installed) {
        label.innerText = 'NO INSTALADO';
        label.className = 'proto-status-text';
        label.style.color = '#94a3b8';
        accent.style.background = '#64748b';
        btnToggle.style.pointerEvents = 'none';
        btnToggle.style.opacity = '0.5';
    } else if(data.active) {
        label.innerText = 'ONLINE';
        label.className = 'proto-status-text proto-status-online';
        accent.style.background = '#4ade80';
        btnToggle.style.pointerEvents = 'auto';
        btnToggle.style.opacity = '1';
    } else {
        label.innerText = 'OFFLINE';
        label.className = 'proto-status-text proto-status-offline';
        accent.style.background = '#a855f7';
        btnToggle.style.pointerEvents = 'auto';
        btnToggle.style.opacity = '1';
    }
}

window.switchViewStunnel = function(viewId) {
    const views = ['viewMain_stunnel', 'viewSettings_stunnel', 'viewInstall_stunnel', 'terminal_stunnel'];
    views.forEach(v => {
        const el = document.getElementById(v);
        if(el) el.classList.add('proto-hidden');
    });
    const target = document.getElementById(viewId);
    if(target) target.classList.remove('proto-hidden');
}

window.toggleStunnelService = async function() {
    const action = (!stunnelIsOnline) ? 'start' : 'restart';
    await window.svcAction('stunnel4', action);
    setTimeout(fetchServices, 1000);
}

window.promptStunnelPort = async function() {
    const newPort = prompt("Introduce el nuevo puerto para Stunnel4:", stunnelPort);
    if (newPort && !isNaN(newPort)) {
        showToast(`Cambiando puerto de Stunnel a: ${newPort}...`);
        try {
            const res = await fetch('/api/service/stunnel4/port', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({port: newPort})
            });
            const data = await res.json();
            if(data.success) {
                showToast("Puerto de Stunnel cambiado exitosamente.");
                setTimeout(fetchServices, 2000);
            } else {
                showToast("Error cambiando el puerto.");
            }
        } catch(e) { showToast("Error de conexión"); }
    }
}

window.switchViewProxy = function(viewId) {
    const views = ['viewMain_proxy', 'viewSettings_proxy'];
    views.forEach(v => {
        const el = document.getElementById(v);
        if(el) el.classList.add('proto-hidden');
    });
    const target = document.getElementById(viewId);
    if(target) target.classList.remove('proto-hidden');
}

window.toggleProxyService = async function() {
    const action = (!proxyIsOnline) ? 'start' : 'restart';
    await window.svcAction('mx-proxy', action);
    setTimeout(fetchServices, 1500);
}

window.promptProxyPort = async function() {
    const newPort = prompt("Introduce el nuevo puerto para el Proxy Python:", proxyPort);
    if (newPort && !isNaN(newPort)) {
        showToast(`Cambiando puerto del proxy a: ${newPort}...`);
        try {
            const res = await fetch('/api/service/proxy/port', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({port: newPort})
            });
            const data = await res.json();
            if(data.success) {
                showToast("Puerto del Proxy cambiado. Reiniciando...");
                setTimeout(fetchServices, 2000);
            } else {
                showToast("Error cambiando puerto del Proxy");
            }
        } catch(e) { showToast("Error de conexión"); }
    }
}

window.runStunnelInstall = async function(type) {
    if(type === 'uninstall') {
        if(!confirm("¿Seguro que deseas desinstalar Stunnel4? Se borrarán sus certificados.")) return;
        showStunnelTerminal("Desinstalando Stunnel4...", false);
        const res = await fetch('/api/service/stunnel4/uninstall', {method: 'POST'});
        showStunnelTerminal("Desinstalado con éxito.", false);
        setTimeout(() => { switchViewStunnel('viewMain_stunnel'); fetchServices(); }, 2000);
        return;
    }

    switchViewStunnel('terminal_stunnel');
    // Limpieza total para que solo se vea el mensaje solicitado
    document.getElementById('consoleOutput_stunnel').innerHTML = "";
    
    showStunnelTerminal(`Instalando, espere unos segundos por favor...`, false);
    
    try {
        const res = await fetch('/api/service/install/stunnel4/simple', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ type })
        });
        const data = await res.json();
        if(data.success) {
            showStunnelTerminal(`¡Instalación de ${type} completada con éxito!`, false);
        } else {
            showStunnelTerminal(`Error de instalación: ${data.error}`, false);
        }
    } catch(e) {
        showStunnelTerminal(`Error de red al conectar al servidor.`, false);
    }
    
    // Retorno automático tras 3 segundos
    setTimeout(() => { 
        switchViewStunnel('viewMain_stunnel'); 
        fetchServices(); 
    }, 3000);
}

function showStunnelTerminal(msg, append=false) {
    switchViewStunnel('terminal_stunnel');
    const output = document.getElementById('consoleOutput_stunnel');
    const timestamp = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
    const line = `<div style="margin-bottom:4px"><span style="opacity:0.5">[${timestamp}]</span> > ${msg}</div>`;
    
    if(append) output.innerHTML += line;
    else output.innerHTML = line;
    
    output.scrollTop = output.scrollHeight;
}

window.svcAction = async function(id, action) {
    showToast(`Ejecutando ${action} en ${id}...`);
    try {
        const res = await fetch('/api/service/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id, action})
        });
        const data = await res.json();
        if(data.success) { showToast("Acción completada con éxito"); fetchServices(); }
        else showToast("Error ejecutando acción: " + data.error);
    } catch(e) { showToast("Error de conexión"); }
}
