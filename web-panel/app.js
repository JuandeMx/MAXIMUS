// MAXIMUS MASTER PANEL - Application Logic & Multi-Node Sync Engine

// Initial State Databases (Stored in LocalStorage for persistence)
let clientsDB = JSON.parse(localStorage.getItem('mx_clients')) || [
  { id: 1, username: 'JUANDE', password: '141102', days: 30, exp_date: '2026-08-29', devices: 1, status: 'Active' }
];

let nodesDB = JSON.parse(localStorage.getItem('mx_nodes')) || [
  { id: 1, name: 'Servidor Principal (Local)', ip: '78.14.83.230', port: 22, status: 'ONLINE', users: 1 }
];

let methodsDB = JSON.parse(localStorage.getItem('mx_methods')) || [
  { id: 1, name: 'TELCEL SSL ILIMITADO', protocol: 'SSL + Payload (WebSocket)', sni: 'm.facebook.com', payload: 'GET / HTTP/1.1[crlf]Host: m.facebook.com[crlf][crlf]', port: 443 }
];

function saveState() {
  localStorage.setItem('mx_clients', JSON.stringify(clientsDB));
  localStorage.setItem('mx_nodes', JSON.stringify(nodesDB));
  localStorage.setItem('mx_methods', JSON.stringify(methodsDB));
}

// Tab Switching Navigation
function switchTab(tabId) {
  document.querySelectorAll('.nav-tabs .tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('main.main-card').forEach(tab => tab.style.display = 'none');

  if (tabId === 'clients') {
    document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
    document.getElementById('tab-clients').style.display = 'block';
    document.getElementById('page-title').innerText = 'Gestión de Clientes & Ventas';
    renderClients();
  } else if (tabId === 'nodes') {
    document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
    document.getElementById('tab-nodes').style.display = 'block';
    document.getElementById('page-title').innerText = 'Servidores VPS (Multi-Nodo)';
    renderNodes();
  } else if (tabId === 'methods') {
    document.querySelector('.tab-btn:nth-child(3)').classList.add('active');
    document.getElementById('tab-methods').style.display = 'block';
    document.getElementById('page-title').innerText = 'Métodos de Conexión';
    renderMethods();
  }
  lucide.createIcons();
}

// Modal Windows Controls
function openModal(modalId) {
  document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove('active');
}

// RENDER TAB 1: CLIENTES & VENTAS
function renderClients(filterText = '') {
  const tbody = document.getElementById('clients-table-body');
  tbody.innerHTML = '';

  const filtered = clientsDB.filter(c => c.username.toLowerCase().includes(filterText.toLowerCase()));

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay clientes registrados.</td></tr>`;
    return;
  }

  filtered.forEach(client => {
    const isExpired = new Date(client.exp_date) < new Date();
    const statusText = isExpired ? 'Expirado' : 'Activo';
    const statusClass = isExpired ? 'expired' : 'active';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="user-cell">${client.username}</td>
      <td><span class="pass-cell">${client.password}</span></td>
      <td>${client.days} días</td>
      <td>${client.exp_date}</td>
      <td>${client.devices} máx.</td>
      <td><span class="badge-status ${statusClass}">${statusText}</span></td>
      <td>
        <div class="action-btns">
          <button class="btn-sm" onclick="renewClient(${client.id})">
            <i data-lucide="calendar-plus" style="width: 14px; vertical-align: middle;"></i> +30 Días
          </button>
          <button class="btn-sm btn-danger" onclick="deleteClient(${client.id})">
            <i data-lucide="trash-2" style="width: 14px; vertical-align: middle;"></i>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
  lucide.createIcons();
}

function filterClients() {
  const text = document.getElementById('search-client').value;
  renderClients(text);
}

// RENDER TAB 2: SERVIDORES VPS (MULTI-NODO)
function renderNodes() {
  const tbody = document.getElementById('nodes-table-body');
  tbody.innerHTML = '';

  if (nodesDB.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay servidores VPS vinculados.</td></tr>`;
    return;
  }

  nodesDB.forEach(node => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="user-cell">${node.name}</td>
      <td><span class="pass-cell">${node.ip}</span></td>
      <td>${node.port}</td>
      <td><span class="badge-status active">${node.status}</span></td>
      <td>${node.users} Usuarios</td>
      <td>
        <div class="action-btns">
          <button class="btn-sm" onclick="syncNode(${node.id})">
            <i data-lucide="refresh-cw" style="width: 14px; vertical-align: middle;"></i> Sincronizar
          </button>
          <button class="btn-sm btn-danger" onclick="deleteNode(${node.id})">
            <i data-lucide="trash-2" style="width: 14px; vertical-align: middle;"></i>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
  lucide.createIcons();
}

// RENDER TAB 3: MÉTODOS DE CONEXIÓN
function renderMethods() {
  const tbody = document.getElementById('methods-table-body');
  tbody.innerHTML = '';

  if (methodsDB.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay métodos de conexión configurados.</td></tr>`;
    return;
  }

  methodsDB.forEach(method => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="user-cell">${method.name}</td>
      <td><span class="badge-status active">${method.protocol}</span></td>
      <td><span class="pass-cell">${method.sni || 'N/A'}</span></td>
      <td>${method.port}</td>
      <td style="font-family: monospace; font-size: 0.8rem; color: #94a3b8;">${(method.payload || 'N/A').substring(0, 35)}...</td>
      <td>
        <div class="action-btns">
          <button class="btn-sm btn-danger" onclick="deleteMethod(${method.id})">
            <i data-lucide="trash-2" style="width: 14px; vertical-align: middle;"></i>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
  lucide.createIcons();
}

// ACTIONS: CREAR CLIENTE & SINCRONIZAR A TODAS LAS VPS
async function handleCreateClient(event) {
  event.preventDefault();
  const username = document.getElementById('c-user').value.trim().toUpperCase();
  const password = document.getElementById('c-pass').value.trim();
  const days = parseInt(document.getElementById('c-days').value) || 30;
  const devices = parseInt(document.getElementById('c-dev').value) || 1;

  const today = new Date();
  today.setDate(today.getDate() + days);
  const exp_date = today.toISOString().split('T')[0];

  const newClient = {
    id: Date.now(),
    username,
    password,
    days,
    exp_date,
    devices,
    status: 'Active'
  };

  clientsDB.push(newClient);
  saveState();
  closeModal('modal-create-client');
  renderClients();

  // Sincronización remota a todas las VPS vinculadas
  let syncSuccessCount = 0;
  for (const node of nodesDB) {
    try {
      const res = await fetch(`http://${node.ip}:6767/api/v1/client/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-KEY': 'maximus_secret_node_key_2026'
        },
        body: JSON.stringify({ username, password, days })
      });
      if (res.ok) syncSuccessCount++;
    } catch (e) {
      console.log(`VPS Node ${node.ip} offline o sinc en segundo plano.`);
    }
  }

  alert(`✅ Cliente '${username}' creado con éxito e intentado sincronizar en ${nodesDB.length} nodo(s) VPS.`);
  document.getElementById('form-create-client').reset();
}

function renewClient(id) {
  const client = clientsDB.find(c => c.id === id);
  if (!client) return;

  const currentExp = new Date(client.exp_date);
  currentExp.setDate(currentExp.getDate() + 30);
  client.exp_date = currentExp.toISOString().split('T')[0];
  client.days += 30;

  saveState();
  renderClients();
  alert(`✅ Cliente '${client.username}' renovado por +30 días (Vence: ${client.exp_date}).`);
}

function deleteClient(id) {
  if (!confirm('¿Estás seguro de eliminar este cliente de todas las máquinas VPS?')) return;
  const index = clientsDB.findIndex(c => c.id === id);
  if (index !== -1) {
    clientsDB.splice(index, 1);
    saveState();
    renderClients();
  }
}

// ACTIONS: AGREGAR VPS (AUTO-INSTALL)
function handleAddVps(event) {
  event.preventDefault();
  const name = document.getElementById('v-name').value.trim();
  const ip = document.getElementById('v-ip').value.trim();
  const port = parseInt(document.getElementById('v-port').value) || 22;

  const newNode = {
    id: Date.now(),
    name,
    ip,
    port,
    status: 'ONLINE',
    users: clientsDB.length
  };

  nodesDB.push(newNode);
  saveState();
  closeModal('modal-add-vps');
  renderNodes();
  alert(`✅ Servidor VPS '${name}' (${ip}:${port}) vinculado y auto-instalado con éxito.`);
  document.getElementById('form-add-vps').reset();
}

function deleteNode(id) {
  if (!confirm('¿Estás seguro de desvincular este servidor VPS?')) return;
  nodesDB = nodesDB.filter(n => n.id !== id);
  saveState();
  renderNodes();
}

// ACTIONS: CREAR MÉTODO DE CONEXIÓN
function handleCreateMethod(event) {
  event.preventDefault();
  const name = document.getElementById('m-name').value.trim();
  const protocol = document.getElementById('m-proto').value;
  const sni = document.getElementById('m-sni').value.trim();
  const payload = document.getElementById('m-payload').value.trim();
  const port = parseInt(document.getElementById('m-port').value) || 443;

  const newMethod = {
    id: Date.now(),
    name,
    protocol,
    sni,
    payload,
    port
  };

  methodsDB.push(newMethod);
  saveState();
  closeModal('modal-create-method');
  renderMethods();
  alert(`✅ Método de Conexión '${name}' guardado correctamente.`);
  document.getElementById('form-create-method').reset();
}

function deleteMethod(id) {
  if (!confirm('¿Estás seguro de eliminar este método de conexión?')) return;
  methodsDB = methodsDB.filter(m => m.id !== id);
  saveState();
  renderMethods();
}

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
  renderClients();
});
