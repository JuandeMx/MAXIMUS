// MAXIMUS MASTER PANEL - Application Logic & Real Multi-Node Sync Engine

const API_BASE = window.location.origin.includes('http') ? window.location.origin : 'http://127.0.0.1:8080';

// Initial State Databases
let clientsDB = JSON.parse(localStorage.getItem('mx_clients')) || [];
let nodesDB = JSON.parse(localStorage.getItem('mx_nodes')) || [
  { id: 1, name: 'Servidor Principal (Master)', ip: window.location.hostname || '187.209.14.58', port: 22, status: 'ONLINE', users: 1 }
];
let methodsDB = JSON.parse(localStorage.getItem('mx_methods')) || [
  { id: 1, name: 'TELCEL SSL ILIMITADO', protocol: 'SSL + Payload (WebSocket)', sni: 'm.facebook.com', payload: 'GET / HTTP/1.1[crlf]Host: m.facebook.com[crlf][crlf]', port: 443 }
];

function saveState() {
  localStorage.setItem('mx_clients', JSON.stringify(clientsDB));
  localStorage.setItem('mx_nodes', JSON.stringify(nodesDB));
  localStorage.setItem('mx_methods', JSON.stringify(methodsDB));
}

async function fetchRealState() {
  try {
    const resC = await fetch(`${API_BASE}/api/clients`);
    if (resC.ok) {
      const data = await resC.json();
      if (data.clients && data.clients.length > 0) {
        clientsDB = data.clients;
      }
    }
    const resN = await fetch(`${API_BASE}/api/nodes`);
    if (resN.ok) {
      const data = await resN.json();
      if (data.nodes && data.nodes.length > 0) {
        nodesDB = data.nodes;
      }
    }
    const resM = await fetch(`${API_BASE}/api/methods`);
    if (resM.ok) {
      const data = await resM.json();
      if (data.methods && data.methods.length > 0) {
        methodsDB = data.methods;
      }
    }
  } catch (e) {
    console.log("Servidor Backend Master offline o modo estático local.");
  }
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
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay clientes registrados en Linux.</td></tr>`;
    return;
  }

  filtered.forEach(client => {
    const isExpired = client.exp_date ? (new Date(client.exp_date) < new Date()) : false;
    const statusText = isExpired ? 'Expirado' : 'Activo';
    const statusClass = isExpired ? 'expired' : 'active';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="user-cell">${client.username}</td>
      <td><span class="pass-cell">${client.password || '••••••'}</span></td>
      <td>${client.days || 30} días</td>
      <td>${client.exp_date || 'N/A'}</td>
      <td>${client.devices || 1} máx.</td>
      <td><span class="badge-status ${statusClass}">${statusText}</span></td>
      <td>
        <div class="action-btns">
          <button class="btn-sm" onclick="renewClient('${client.username}')">
            <i data-lucide="calendar-plus" style="width: 14px; vertical-align: middle;"></i> +30 Días
          </button>
          <button class="btn-sm btn-danger" onclick="deleteClient('${client.username}')">
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
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay servidores VPS vinculados.</td></tr>`;
    return;
  }

  nodesDB.forEach(node => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="user-cell">${node.name}</td>
      <td><span class="pass-cell">${node.ip}</span></td>
      <td>${node.port}</td>
      <td><span class="badge-status active">${node.status}</span></td>
      <td>${clientsDB.length}</td>
      <td>
        <button class="btn-sm" onclick="openProtocols('${node.ip}', '${node.name}')" style="background: rgba(139,92,246,0.15); color: #a78bfa; border-color: rgba(139,92,246,0.3);">
          <i data-lucide="shield" style="width: 14px; vertical-align: middle;"></i> Gestionar
        </button>
      </td>
      <td>
        <div class="action-btns">
          <button class="btn-sm" onclick="syncNode(${node.id})">
            <i data-lucide="refresh-cw" style="width: 14px; vertical-align: middle;"></i> Sync
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

// PROTOCOLOS: Abrir modal y consultar estado real del nodo remoto
let _currentProtoNodeIp = '';

const PROTO_LABELS = {
  ssh: 'OpenSSH',
  dropbear: 'Dropbear',
  stunnel: 'Stunnel (SSL)',
  hysteria: 'Hysteria v2',
  v2ray: 'V2Ray / Xray',
  badvpn: 'BadVPN (UDP)',
  slowdns: 'SlowDNS'
};

async function openProtocols(ip, name) {
  _currentProtoNodeIp = ip;
  document.getElementById('proto-node-name').innerText = name;
  document.getElementById('proto-node-ip').innerText = `IP: ${ip} — Puerto API: 6767`;
  const container = document.getElementById('proto-list-container');
  container.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 1rem;">Consultando protocolos en el nodo remoto...</p>';
  openModal('modal-protocols');
  lucide.createIcons();

  try {
    const res = await fetch(`http://${ip}:6767/api/v1/protocols/status`, {
      headers: { 'X-API-KEY': 'maximus_secret_node_key_2026' }
    });
    const data = await res.json();
    renderProtocolRows(container, data.protocols, ip);
  } catch (e) {
    container.innerHTML = '<p style="color: #f87171; text-align: center; padding: 1rem;">⚠️ No se pudo conectar al nodo. Verifica que esté en línea y el puerto 6767 abierto.</p>';
  }
}

function renderProtocolRows(container, protocols, ip) {
  container.innerHTML = '';
  for (const [key, status] of Object.entries(protocols)) {
    const label = PROTO_LABELS[key] || key;
    const isOnline = status === 'ONLINE';
    const statusClass = isOnline ? 'online' : 'stopped';

    const row = document.createElement('div');
    row.className = 'proto-row';
    row.id = `proto-row-${key}`;
    row.innerHTML = `
      <div class="proto-info">
        <span class="proto-name">${label}</span>
        <span class="proto-status ${statusClass}" id="proto-badge-${key}">${status}</span>
      </div>
      <div class="proto-actions">
        <button class="btn-sm" onclick="controlProtocol('${ip}', '${key}', 'start')" style="color: #4ade80;">▶ Iniciar</button>
        <button class="btn-sm" onclick="controlProtocol('${ip}', '${key}', 'restart')" style="color: #38bdf8;">⟳ Reiniciar</button>
        <button class="btn-sm btn-danger" onclick="controlProtocol('${ip}', '${key}', 'stop')">■ Detener</button>
      </div>
    `;
    container.appendChild(row);
  }
  lucide.createIcons();
}

async function controlProtocol(ip, service, action) {
  const badge = document.getElementById(`proto-badge-${service}`);
  if (badge) {
    badge.innerText = '...';
    badge.className = 'proto-status';
  }

  try {
    const res = await fetch(`http://${ip}:6767/api/v1/protocols/control`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-KEY': 'maximus_secret_node_key_2026'
      },
      body: JSON.stringify({ service, action })
    });
    const data = await res.json();

    // Refrescar estado después de la acción
    await new Promise(r => setTimeout(r, 800));
    const statusRes = await fetch(`http://${ip}:6767/api/v1/protocols/status`, {
      headers: { 'X-API-KEY': 'maximus_secret_node_key_2026' }
    });
    const statusData = await statusRes.json();

    const newStatus = statusData.protocols[service] || 'STOPPED';
    if (badge) {
      badge.innerText = newStatus;
      badge.className = `proto-status ${newStatus === 'ONLINE' ? 'online' : 'stopped'}`;
    }
  } catch (e) {
    if (badge) {
      badge.innerText = 'ERROR';
      badge.className = 'proto-status stopped';
    }
  }
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

// ACTIONS: CREAR CLIENTE REAL EN LINUX OS & SINCRONIZAR
async function handleCreateClient(event) {
  event.preventDefault();
  const username = document.getElementById('c-user').value.trim().toUpperCase();
  const password = document.getElementById('c-pass').value.trim();
  const days = parseInt(document.getElementById('c-days').value) || 30;
  const devices = parseInt(document.getElementById('c-dev').value) || 1;

  closeModal('modal-create-client');

  try {
    const res = await fetch(`${API_BASE}/api/client/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, days })
    });
    const resData = await res.json();
    if (resData.success) {
      alert(`✅ Usuario REAL '${username}' creado exitosamente en Linux OS (Servidor Master y Nodos).`);
    } else {
      alert(`❌ Error al crear usuario: ${resData.error || 'Fallo desconocido'}`);
    }
  } catch (e) {
    // Si corre en archivo local
    const today = new Date();
    today.setDate(today.getDate() + days);
    clientsDB.push({
      id: Date.now(),
      username,
      password,
      days,
      exp_date: today.toISOString().split('T')[0],
      devices,
      status: 'Active'
    });
    saveState();
    alert(`⚠️ Servidor Backend Offline. Cliente '${username}' guardado en memoria estática.`);
  }

  await fetchRealState();
  renderClients();
  document.getElementById('form-create-client').reset();
}

async function deleteClient(username) {
  if (!confirm(`¿Estás seguro de eliminar al usuario REAL '${username}' de Linux OS y todas las VPS?`)) return;

  try {
    await fetch(`${API_BASE}/api/client/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
  } catch (e) {
    clientsDB = clientsDB.filter(c => c.username !== username);
    saveState();
  }

  await fetchRealState();
  renderClients();
}

async function renewClient(username) {
  try {
    const res = await fetch(`${API_BASE}/api/client/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password: "123", days: 30 })
    });
    alert(`✅ Cliente REAL '${username}' renovado por +30 días.`);
  } catch (e) {}

  await fetchRealState();
  renderClients();
}

// ACTIONS: AGREGAR VPS (AUTO-INSTALL SSH REAL)
async function handleAddVps(event) {
  event.preventDefault();
  const name = document.getElementById('v-name').value.trim();
  const ip = document.getElementById('v-ip').value.trim();
  const port = parseInt(document.getElementById('v-port').value) || 22;
  const user = document.getElementById('v-user').value.trim() || 'root';
  const password = document.getElementById('v-pass').value.trim();

  closeModal('modal-add-vps');
  openModal('modal-installing-vps');

  const titleEl = document.getElementById('install-vps-title');
  const barEl = document.getElementById('install-progress-bar');
  const termEl = document.getElementById('install-terminal-box');
  const footerEl = document.getElementById('install-modal-footer');

  termEl.innerHTML = '';
  barEl.style.width = '0%';
  footerEl.style.display = 'none';

  function appendLog(text, type = 'info') {
    const div = document.createElement('div');
    div.className = `terminal-line ${type}`;
    div.innerText = text;
    termEl.appendChild(div);
    termEl.scrollTop = termEl.scrollHeight;
  }

  appendLog(`[+] Enviando orden de instalación SSH REAL a ${user}@${ip}:${port}...`);
  titleEl.innerText = `Conectando al Backend Master para instalar en ${ip}...`;
  barEl.style.width = '5%';

  // Enviar la orden al Backend Master (que ejecuta SSH real)
  let installId = '';
  try {
    const res = await fetch(`${API_BASE}/api/vps/install`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, ip, port, user, password })
    });
    const data = await res.json();
    installId = data.install_id || '';
    appendLog(`[OK] Backend Master recibió la orden. ID: ${installId}`, 'success');
  } catch (e) {
    appendLog(`[ERROR] No se pudo contactar al Backend Master.`, 'error');
    titleEl.innerText = `Error de conexión con el Backend Master.`;
    footerEl.style.display = 'flex';
    return;
  }

  // Poll de progreso real cada 3 segundos
  let lastLogCount = 0;
  let pollAttempts = 0;
  const maxPollAttempts = 120; // 6 minutos máximo

  while (pollAttempts < maxPollAttempts) {
    await new Promise(r => setTimeout(r, 3000));
    pollAttempts++;

    try {
      const statusRes = await fetch(`${API_BASE}/api/vps/install/status?id=${installId}`);
      const status = await statusRes.json();

      // Mostrar nuevas líneas de log
      if (status.log && status.log.length > lastLogCount) {
        for (let i = lastLogCount; i < status.log.length; i++) {
          const line = status.log[i];
          const type = line.includes('[OK]') || line.includes('[SUCCESS]') ? 'success' :
                       line.includes('[ERROR]') ? 'error' :
                       line.includes('[WARN]') ? 'warning' : 'info';
          appendLog(line, type);
        }
        lastLogCount = status.log.length;
      }

      // Actualizar barra de progreso
      const pct = Math.min(Math.round((status.step / status.total_steps) * 100), 100);
      barEl.style.width = `${pct}%`;
      titleEl.innerText = status.status;

      if (status.done) {
        if (status.error) {
          appendLog(`[ERROR] La instalación falló. Verifica credenciales SSH y acceso al puerto.`, 'error');
        } else {
          barEl.style.width = '100%';
          appendLog(`[SUCCESS] ✅ ¡VPS '${name}' (${ip}) instalada y conectada correctamente!`, 'success');
        }
        break;
      }
    } catch (e) {
      // Silenciar errores de polling
    }
  }

  footerEl.style.display = 'flex';

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
  renderNodes();
  document.getElementById('form-add-vps').reset();
}

function deleteNode(id) {
  if (!confirm('¿Estás seguro de desvincular este servidor VPS?')) return;
  nodesDB = nodesDB.filter(n => n.id !== id);
  saveState();
  renderNodes();
}

// ACTIONS: CREAR MÉTODO DE CONEXIÓN
async function handleCreateMethod(event) {
  event.preventDefault();
  const name = document.getElementById('m-name').value.trim();
  const protocol = document.getElementById('m-proto').value;
  const sni = document.getElementById('m-sni').value.trim();
  const payload = document.getElementById('m-payload').value.trim();
  const port = parseInt(document.getElementById('m-port').value) || 443;

  try {
    await fetch(`${API_BASE}/api/method/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, protocol, sni, payload, port })
    });
  } catch (e) {}

  const newMethod = { id: Date.now(), name, protocol, sni, payload, port };
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

// Initialize Dashboard with Real State
document.addEventListener('DOMContentLoaded', async () => {
  await fetchRealState();
  renderClients();
});
