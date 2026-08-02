// Si la web corre en Hosting externo HTTPS (ej: vpsmx.store), usar api.php como puente proxy HTTPS
const API_BASE = (window.location.origin.includes('vpsmx.store') || !window.location.origin.includes(':8080')) 
  ? `${window.location.origin}/api.php?endpoint=` 
  : window.location.origin;

// Initial State Databases (Direct Real Backend Sync)
let clientsDB = [];
let nodesDB = [];
let methodsDB = [];

// Limpiar la caché antigua del navegador
localStorage.removeItem('mx_methods');
localStorage.removeItem('mx_nodes');

function saveState() {
  // No caching local state to prevent stale data
}

async function fetchRealState() {
  try {
    const resC = await fetch(`${API_BASE}/api/clients`);
    if (resC.ok) {
      const data = await resC.json();
      if (data.clients) {
        clientsDB = data.clients;
      }
    }
    const resN = await fetch(`${API_BASE}/api/nodes`);
    if (resN.ok) {
      const data = await resN.json();
      if (data.nodes) {
        nodesDB = data.nodes;
      }
    }
    const resM = await fetch(`${API_BASE}/api/methods`);
    if (resM.ok) {
      const data = await resM.json();
      if (data.methods) {
        methodsDB = data.methods;
      }
    }
  } catch (e) {
    console.log("Servidor Backend Master offline.");
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

    let durationLabel = `${client.days || 30} días`;
    if (client.exp_date && client.exp_date.includes(' ')) {
      const remainingMs = new Date(client.exp_date) - new Date();
      if (remainingMs > 0 && remainingMs < 86400000) {
        const hoursLeft = Math.ceil(remainingMs / (1000 * 60 * 60));
        durationLabel = `⏳ ${hoursLeft} Horas`;
      }
    }

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="user-cell">
        <span style="color: #ffffff; font-weight: 700;">${client.username}</span>
      </td>
      <td>${durationLabel}</td>
      <td><span class="badge-status ${statusClass}">${statusText}</span></td>
      <td>
        <div class="action-btns">
          <button class="btn-sm" onclick="showUserDetailsModal('${client.username}', '${client.password || '123'}', '${client.exp_date || 'N/A'}', ${client.username.startsWith('DEMO')})" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);">
            <i data-lucide="eye" style="width: 14px; vertical-align: middle;"></i> Ver
          </button>
          <button class="btn-sm" onclick="renewClient('${client.username}')">
            <i data-lucide="calendar-plus" style="width: 14px; vertical-align: middle;"></i> +30d
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
    const cfDom = node.domain_cf || 'N/A';
    const cftDom = node.domain_cft || 'N/A';
    tr.innerHTML = `
      <td class="user-cell">${node.name}</td>
      <td><span class="pass-cell">${node.ip}:${node.port}</span></td>
      <td><span class="pass-cell" style="color: #60a5fa;">CF: ${cfDom}</span><br><span class="pass-cell" style="color: #f472b6;">CFT: ${cftDom}</span></td>
      <td><span class="badge-status active">${node.status}</span></td>
      <td>${clientsDB.length}</td>
      <td>
        <button class="btn-sm" onclick="openProtocols('${node.ip}', '${node.name}')" style="background: rgba(139,92,246,0.15); color: #a78bfa; border-color: rgba(139,92,246,0.3);">
          <i data-lucide="shield" style="width: 14px; vertical-align: middle;"></i> Gestionar
        </button>
      </td>
      <td>
        <div class="action-btns">
          <button class="btn-sm" onclick="openEditVpsModal('${node.ip}', '${node.name}', '${node.port}', '${node.domain_cf || ''}', '${node.domain_cft || ''}')" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.3);">
            <i data-lucide="edit" style="width: 14px; vertical-align: middle;"></i> Editar
          </button>
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

function openEditVpsModal(ip, name, port, domain_cf, domain_cft) {
  document.getElementById('ve-original-ip').value = ip;
  document.getElementById('ve-ip').value = ip;
  document.getElementById('ve-name').value = name;
  document.getElementById('ve-port').value = port;
  document.getElementById('ve-domain-cf').value = domain_cf;
  document.getElementById('ve-domain-cft').value = domain_cft;
  openModal('modal-edit-vps');
}

async function handleSaveEditVps(e) {
  e.preventDefault();
  const original_ip = document.getElementById('ve-original-ip').value;
  const ip = document.getElementById('ve-ip').value.trim();
  const name = document.getElementById('ve-name').value.trim();
  const port = document.getElementById('ve-port').value;
  const domain_cf = document.getElementById('ve-domain-cf').value.trim();
  const domain_cft = document.getElementById('ve-domain-cft').value.trim();

  try {
    const res = await fetch(`${API_BASE}/api/vps/edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ original_ip, ip, name, port, domain_cf, domain_cft })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alert(`✅ Servidor VPS '${name}' (${ip}) actualizado correctamente.`);
      closeModal('modal-edit-vps');
      await fetchRealState();
      renderNodes();
      renderMethods();
    } else {
      alert(`❌ Error actualizando VPS: ${data.error || 'Error desconocido'}`);
    }
  } catch (err) {
    alert(`❌ Error de conexión con el servidor maestro.`);
  }
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
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay métodos de conexión configurados.</td></tr>`;
    return;
  }

  methodsDB.forEach(method => {
    const tr = document.createElement('tr');
    const safeName = method.name.replace(/[^a-zA-Z0-9_\-]/g, '_');
    const downloadUrl = `${API_BASE}/downloads/${safeName}.mx`;

    tr.innerHTML = `
      <td class="user-cell">${method.name}</td>
      <td><span class="pass-cell">${method.ssh_host || '127.0.0.1'}:${method.ssh_port || 22}</span></td>
      <td><span class="badge-status active">${method.protocol || 'SSL'}</span></td>
      <td><span class="pass-cell">${method.sni || 'N/A'}</span></td>
      <td style="font-family: monospace; font-size: 0.8rem; color: #94a3b8;">${(method.payload || 'N/A').substring(0, 35)}...</td>
      <td>
        <a href="${downloadUrl}" download="${safeName}.mx" class="btn-sm" style="background: rgba(16,185,129,0.15); color: #4ade80; border-color: rgba(16,185,129,0.3); text-decoration: none; display: inline-block; text-align: center; font-size: 0.75rem;">
          <i data-lucide="download" style="width: 13px; vertical-align: middle;"></i> .MX
        </a>
      </td>
      <td>
        <div class="action-btns">
          <button class="btn-sm" onclick="openEditMethodModal('${method.name}')" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.3);">
            <i data-lucide="edit" style="width: 14px; vertical-align: middle;"></i> Editar
          </button>
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

function showUserDetailsModal(username, password, expDate, isDemo = false) {
  const textEl = document.getElementById('user-info-text');
  const typeTitle = isDemo ? "🔥 DEMO DE PRUEBA MAXIMUS (2 HORAS) 🔥" : "✅ CLIENTE REGISTRADO - MAXIMUS VIP ✅";
  
  const formattedText = 
`${typeTitle}
━━━━━━━━━━━━━━━━━━━━━━
👤 Usuario: ${username}
🔑 Contraseña: ${password}
📅 Vencimiento: ${expDate}
━━━━━━━━━━━━━━━━━━━━━━
⚡ ¡Conéctate usando nuestra App Oficial MAXIMUS!`;

  if (textEl) textEl.value = formattedText;
  openModal('modal-user-created');
}

function copyUserDetails() {
  const textEl = document.getElementById('user-info-text');
  if (textEl) {
    const textToCopy = textEl.value;
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(textToCopy);
    } else {
      textEl.select();
      textEl.setSelectionRange(0, 99999);
      document.execCommand('copy');
    }
    const btn = document.getElementById('btn-copy-user-details');
    if (btn) {
      const origText = btn.innerHTML;
      btn.innerHTML = '✅ ¡Copiado!';
      setTimeout(() => { btn.innerHTML = origText; }, 2000);
    }
  }
}

// ACTIONS: CREAR CLIENTE REAL EN LINUX OS & SINCRONIZAR
async function handleCreateClient(event) {
  event.preventDefault();
  const username = document.getElementById('c-user').value.trim().toUpperCase();
  const password = document.getElementById('c-pass').value.trim();
  const val = parseFloat(document.getElementById('c-days').value) || 1;
  const unit = document.getElementById('c-unit') ? document.getElementById('c-unit').value : 'days';
  const days = unit === 'hours' ? (val / 24.0) : val;
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
      showUserDetailsModal(username, password, resData.exp_date || 'En 30 Días', false);
    } else {
      alert(`❌ Error al crear usuario: ${resData.error || 'Fallo desconocido'}`);
    }
  } catch (e) {
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
    showUserDetailsModal(username, password, today.toISOString().split('T')[0], false);
  }

  await fetchRealState();
  renderClients();
  document.getElementById('form-create-client').reset();
}

// Botón de creación rápida de usuarios Demo por horas (ej: 2 Horas)
async function createQuickDemo() {
  const randomNum = Math.floor(1000 + Math.random() * 9000);
  const username = `DEMO${randomNum}`;
  const password = `${Math.floor(100 + Math.random() * 900)}`;
  const days = 2 / 24.0; // 2 Horas

  try {
    const res = await fetch(`${API_BASE}/api/client/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, days })
    });
    const data = await res.json();
    if (data.success) {
      showUserDetailsModal(username, password, data.exp_date, true);
    } else {
      alert(`❌ Error creando demo: ${data.error || 'Error desconocido'}`);
    }
  } catch (e) {
    alert(`❌ Error de conexión con el Maestro.`);
  }

  await fetchRealState();
  renderClients();
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
  const domain_cf = document.getElementById('v-domain-cf') ? document.getElementById('v-domain-cf').value.trim() : '';
  const domain_cft = document.getElementById('v-domain-cft') ? document.getElementById('v-domain-cft').value.trim() : '';

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
      body: JSON.stringify({ name, ip, port, user, password, domain_cf, domain_cft })
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

  await fetchRealState();
  renderNodes();
  document.getElementById('form-add-vps').reset();
}

async function syncNode(id) {
  const node = nodesDB.find(n => n.id === id);
  if (!node) return;

  // Si es el servidor local, no requiere sync de red remota (o se puede sincronizar de igual manera)
  if (node.ip === '127.0.0.1') {
    alert('El servidor local ya se encuentra sincronizado.');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/vps/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip: node.ip })
    });
    const data = await res.json();
    if (data.success) {
      alert(`✅ Sincronización exitosa: ${data.message}`);
    } else {
      alert(`❌ Error al sincronizar: ${data.error || 'Fallo desconocido'}`);
    }
  } catch (e) {
    alert(`❌ No se pudo conectar al servidor maestro para la sincronización.`);
  }
}

async function syncAllNodes() {
  try {
    const res = await fetch(`${API_BASE}/api/vps/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip: 'all' })
    });
    const data = await res.json();
    if (data.success) {
      alert(`✅ Sincronización Masiva Exitosa: ${data.message}`);
    } else {
      alert(`❌ Error en la sincronización: ${data.error || 'Fallo desconocido'}`);
    }
  } catch (e) {
    alert(`❌ No se pudo conectar al servidor maestro para la sincronización masiva.`);
  }
}

async function deleteNode(id) {
  if (!confirm('¿Estás seguro de desvincular este servidor VPS?')) return;
  const node = nodesDB.find(n => n.id === id);
  if (node) {
    try {
      await fetch(`${API_BASE}/api/vps/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip: node.ip })
      });
    } catch (e) {}
  }
  nodesDB = nodesDB.filter(n => n.id !== id);
  saveState();
  await fetchRealState();
  renderNodes();
}

function openCreateMethodModal() {
  document.getElementById('modal-method-title').innerText = 'Crear Nuevo Método de Conexión';
  document.getElementById('m-original-name').value = '';
  document.getElementById('form-create-method').reset();
  openModal('modal-create-method');
}

function openEditMethodModal(methodName) {
  const method = methodsDB.find(m => m.name === methodName);
  if (!method) return;

  document.getElementById('modal-method-title').innerText = `Editar Método: ${method.name}`;
  document.getElementById('m-original-name').value = method.name;
  document.getElementById('m-name').value = method.name;
  document.getElementById('m-ssh-host').value = method.ssh_host || '';
  document.getElementById('m-ssh-port').value = method.ssh_port || 80;
  document.getElementById('m-proto').value = method.protocol || 'SSL + Payload (WebSocket)';
  document.getElementById('m-sni').value = method.sni || '';
  document.getElementById('m-payload').value = method.payload || '';

  openModal('modal-create-method');
}

// ACTIONS: CREAR O EDITAR MÉTODO DE CONEXIÓN
async function handleSaveMethod(event) {
  event.preventDefault();
  const original_name = document.getElementById('m-original-name').value.trim();
  const name = document.getElementById('m-name').value.trim();
  const ssh_host = document.getElementById('m-ssh-host').value.trim();
  const ssh_port = parseInt(document.getElementById('m-ssh-port').value) || 80;
  const protocol = document.getElementById('m-proto').value;
  const sni = document.getElementById('m-sni').value.trim();
  const payload = document.getElementById('m-payload').value.trim();

  // Si estábamos editando, eliminar el antiguo primero si cambió de nombre
  if (original_name && original_name !== name) {
    try {
      await fetch(`${API_BASE}/api/method/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: original_name })
      });
    } catch (e) {}
  }

  try {
    await fetch(`${API_BASE}/api/method/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, ssh_host, ssh_port, protocol, sni, payload })
    });
  } catch (e) {}

  await fetchRealState();
  closeModal('modal-create-method');
  renderMethods();
  alert(`✅ Método de Conexión '${name}' guardado correctamente.`);
  document.getElementById('form-create-method').reset();
}

async function deleteMethod(id) {
  if (!confirm('¿Estás seguro de eliminar este método de conexión?')) return;
  const method = methodsDB.find(m => m.id === id);
  if (method) {
    try {
      await fetch(`${API_BASE}/api/method/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: method.name })
      });
    } catch (e) {}
  }
  methodsDB = methodsDB.filter(m => m.id !== id);
  saveState();
  await fetchRealState();
  renderMethods();
}

// Initialize Dashboard with Real State
document.addEventListener('DOMContentLoaded', async () => {
  await fetchRealState();
  renderClients();
});
