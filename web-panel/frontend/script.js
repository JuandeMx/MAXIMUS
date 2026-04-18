let resourceChart;

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    initChart();
    startPolling();
    switchTab('dashboard');
});

async function checkAuth() {
    // Si estamos en index.html, el backend ya valida la sesión. 
    // Si falla una API, nos redirigirá al login.
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    
    document.getElementById(`tab-${tabName}`).classList.add('active');
    event.currentTarget.classList.add('active');
    
    document.getElementById('pageTitle').innerText = tabName.charAt(0).toUpperCase() + tabName.slice(1);
    
    if (tabName === 'users') fetchUsers();
    if (tabName === 'services') fetchServices();
}

async function startPolling() {
    setInterval(updateStats, 3000);
    updateStats();
}

async function updateStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        
        document.getElementById('cpu-val').innerText = `${data.cpu}%`;
        document.getElementById('ram-val').innerText = `${data.ram.used} / ${data.ram.total} MB`;
        document.getElementById('disk-val').innerText = `${data.disk.percent}`;
        document.getElementById('online-val').innerText = data.online;
        document.getElementById('uptime-val').innerText = data.uptime;
        
        updateChart(data.cpu, (parseInt(data.ram.used) / parseInt(data.ram.total)) * 100);
    } catch (err) {
        console.error("Stats error", err);
    }
}

async function fetchUsers() {
    const list = document.getElementById('userListBody');
    list.innerHTML = '<tr><td colspan="5">Cargando usuarios...</td></tr>';
    
    try {
        const res = await fetch('/api/users/list');
        const users = await res.json();
        list.innerHTML = '';
        
        users.forEach(u => {
            const row = `<tr>
                <td style="font-weight:700">${u.username}</td>
                <td><span class="badge">${u.type}</span></td>
                <td>${u.expiry}</td>
                <td><span class="status-on">Active</span></td>
                <td>
                    <button class="btn-sm" onclick="deleteUser('${u.username}')"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>`;
            list.innerHTML += row;
        });
    } catch (err) {
        list.innerHTML = '<tr><td colspan="5">Error al cargar listado.</td></tr>';
    }
}

async function fetchServices() {
    const grid = document.getElementById('servicesGrid');
    grid.innerHTML = 'Cargando servicios...';
    
    try {
        const res = await fetch('/api/service/status');
        const services = await res.json();
        grid.innerHTML = '';
        
        services.forEach(s => {
            const card = `<div class="card service-card ${s.active ? 'active' : 'inactive'}">
                <div class="s-info">
                    <h4>${s.name}</h4>
                    <span class="s-status">${s.active ? 'ONLINE' : 'OFFLINE'}</span>
                </div>
                <div class="s-action">
                    <button onclick="toggleService('${s.name}')">
                        <i class="fa-solid ${s.active ? 'fa-rotate' : 'fa-play'}"></i>
                    </button>
                </div>
            </div>`;
            grid.innerHTML += card;
        });
    } catch (err) {
        grid.innerHTML = 'Error al cargar servicios.';
    }
}

function initChart() {
    const ctx = document.getElementById('resourceChart').getContext('2d');
    resourceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array(10).fill(''),
            datasets: [{
                label: 'CPU %',
                data: Array(10).fill(0),
                borderColor: '#22d3ee',
                tension: 0.4,
                fill: true,
                backgroundColor: 'rgba(34, 211, 238, 0.1)'
            }, {
                label: 'RAM %',
                data: Array(10).fill(0),
                borderColor: '#f59e0b',
                tension: 0.4,
                fill: false
            }]
        },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: true, max: 100 } }
        }
    });
}

function updateChart(cpu, ram) {
    if (!resourceChart) return;
    resourceChart.data.datasets[0].data.shift();
    resourceChart.data.datasets[0].data.push(cpu);
    resourceChart.data.datasets[1].data.shift();
    resourceChart.data.datasets[1].data.push(ram);
    resourceChart.update();
}

function openGen(type) {
    document.getElementById('genType').value = type;
    document.getElementById('genTitle').innerText = `Crear Cuenta ${type.toUpperCase()}`;
    document.getElementById('genModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('genModal').style.display = 'none';
}

async function logout() {
    await fetch('/api/logout');
    window.location.reload();
}
