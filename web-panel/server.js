import express from 'express';
import cors from 'cors';
import { Client } from 'ssh2';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 84;

app.use(cors());
app.use(express.json());
// Servir interfaz Web compilada (dist / static)
app.use(express.static(process.cwd()));

const DATA_DIR = path.join(process.cwd(), 'data');
const DB_FILE = path.join(DATA_DIR, 'maximus_db.json');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// Initial DB Structure
const initialDb = {
  users: [
    {
      id: 'usr_admin_owner',
      username: 'admin',
      email: 'admin@maximus.com',
      password: 'admin', // default password
      role: 'owner', // owner, subadmin, reseller
      name: 'Administrador Principal',
      credits: 9999,
      createdAt: new Date().toISOString(),
    }
  ],
  servers: [],
  clients: [],
  resellers: [],
};

// Load or Initialize DB
const getDb = () => {
  try {
    if (!fs.existsSync(DB_FILE)) {
      fs.writeFileSync(DB_FILE, JSON.stringify(initialDb, null, 2), 'utf-8');
      return initialDb;
    }
    const raw = fs.readFileSync(DB_FILE, 'utf-8');
    return JSON.parse(raw);
  } catch (e) {
    console.error('Error cargando DB:', e);
    return initialDb;
  }
};

const saveDb = (data) => {
  try {
    fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 2), 'utf-8');
  } catch (e) {
    console.error('Error guardando DB:', e);
  }
};

// Endpoint: Autenticación / Login
app.post('/api/auth/login', (req, res) => {
  const { username, password } = req.body;
  if (!username || !password) {
    return res.status(400).json({ error: 'Usuario y contraseña requeridos' });
  }

  const db = getDb();
  const cleanUser = username.trim().toLowerCase();

  // Search in System Admins / Owners
  let user = db.users.find(
    (u) => (u.username.toLowerCase() === cleanUser || u.email.toLowerCase() === cleanUser) && u.password === password
  );

  let userRole = user ? user.role : 'reseller';

  // If not found in users, search in Resellers list
  if (!user && db.resellers) {
    const resellerObj = db.resellers.find(
      (r) =>
        ((r.username && r.username.toLowerCase() === cleanUser) ||
          (r.email && r.email.toLowerCase() === cleanUser) ||
          r.name.toLowerCase() === cleanUser) &&
        (r.password ? r.password === password : password === '123456')
    );

    if (resellerObj) {
      user = {
        id: resellerObj.id,
        username: resellerObj.username || resellerObj.name.toLowerCase().replace(/\s+/g, '_'),
        email: resellerObj.email,
        name: resellerObj.name,
        role: 'reseller',
        credits: resellerObj.credits || 0,
        createdAt: resellerObj.joinedDate || new Date().toISOString(),
      };
      userRole = 'reseller';
    }
  }

  if (!user) {
    return res.status(401).json({ error: 'Credenciales inválidas. Verifica tu usuario y contraseña.' });
  }

  // Token de sesión simple
  const token = `token_${user.id}_${Date.now()}`;
  const { password: _, ...userWithoutPass } = user;

  res.json({
    token,
    user: userWithoutPass,
  });
});

// Endpoint: Sincronización global (GET)
app.get('/api/db/sync', (req, res) => {
  const db = getDb();
  // Quitar contraseñas de la lista de usuarios por seguridad
  const safeUsers = db.users.map(({ password, ...u }) => u);
  res.json({
    ...db,
    users: safeUsers,
  });
});

// Endpoint: Actualizar datos globales (POST)
app.post('/api/db/update', (req, res) => {
  const { servers, clients, resellers, users } = req.body;
  const db = getDb();

  if (servers !== undefined) db.servers = servers;
  if (clients !== undefined) db.clients = clients;
  if (resellers !== undefined) db.resellers = resellers;
  if (users !== undefined) {
    // Preservar contraseñas existentes si se envían usuarios sin contraseña
    db.users = users.map((u) => {
      const existing = db.users.find((ex) => ex.id === u.id);
      return {
        ...u,
        password: u.password || existing?.password || 'admin123',
      };
    });
  }

  saveDb(db);
  res.json({ status: 'SUCCESS', message: 'Datos guardados correctamente' });
});

// Ruta raíz: Estado del servidor backend
app.get('/', (req, res) => {
  res.send(`
    <html>
      <body style="font-family: sans-serif; background: #0f172a; color: #fff; padding: 40px; text-align: center;">
        <h1 style="color: #06b6d4;">🚀 Backend Master Maximus VPS (Puerto 3001)</h1>
        <p>Servidor API de instalación SSH, Persistencia DB y Sincronización Multi-nodo activo.</p>
        <p>Para ver el Panel Web React, entra a: <a href="http://localhost:3000" style="color: #38bdf8;">http://localhost:3000</a></p>
      </body>
    </html>
  `);
});

// Endpoint 1: Health check del backend web
app.get('/api/health', (req, res) => {
  res.json({ status: 'ONLINE', message: 'Backend Web Master de Maximus VPS' });
});

// Endpoint 2: Instalación SSH Real de Maximus VPS en Servidor Remoto
app.post('/api/vps/install', (req, res) => {
  const { ip, sshPort = 22, sshUser = 'root', sshPassword } = req.body;

  if (!ip || !sshPassword) {
    return res.status(400).json({ error: 'La IP y la Contraseña SSH son obligatorias.' });
  }

  // Set SSE response headers for real-time progress streaming
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const sendLog = (message, progress) => {
    res.write(`data: ${JSON.stringify({ message, progress })}\n\n`);
  };

  sendLog(`[1/6] Iniciando conexión SSH hacia ${sshUser}@${ip}:${sshPort}...`, 10);

  const conn = new Client();

  conn.on('ready', () => {
    sendLog(`[2/6] Autenticación SSH exitosa en ${ip}. Verificando sistema operativo...`, 25);

    // Command to install MAXIMUS Node via official repo
    const installCmd = `cd /root; export DEBIAN_FRONTEND=noninteractive; apt-get update -y >/dev/null 2>&1; apt-get install -y git curl python3 >/dev/null 2>&1; rm -rf /tmp/MaximusVpsMx; git clone https://github.com/JuandeMx/MAXIMUS.git /tmp/MaximusVpsMx && cd /tmp/MaximusVpsMx && chmod +x install.sh core/*.py core/*.sh && bash install.sh --slave`;

    sendLog(`[3/6] Descargando y ejecutando instalador MAXIMUS desde GitHub...`, 40);

    conn.exec(installCmd, (err, stream) => {
      if (err) {
        sendLog(`[ERROR SSH]: Falló la ejecución del comando: ${err.message}`, 100);
        conn.end();
        return res.end();
      }

      let pct = 40;

      const processChunk = (prefix, text) => {
        const lines = text.split('\n');
        for (const line of lines) {
          const cleanLine = line.replace(/\x1B\[[0-9;]*[mG]/g, '').trim();
          if (cleanLine) {
            pct = Math.min(pct + 2, 92);
            sendLog(`[${prefix}] ${cleanLine.substring(0, 160)}`, pct);
          }
        }
      };

      stream.on('close', (code, signal) => {
        if (code === 0) {
          sendLog(`[4/6] Configuración de paquetes, comandos (menu/MX) y UFW completada.`, 95);
          sendLog(`[5/6] Maximus Multi-Node API activa en puerto 6767.`, 98);
          sendLog(`[6/6] ¡Servidor VPS ${ip} instalado y emparejado con éxito!`, 100);
        } else {
          sendLog(`[ERROR CÓDIGO ${code}] La instalación SSH finalizó con código de salida ${code}. Revisa los logs anteriores.`, 100);
        }
        conn.end();
        res.end();
      }).on('data', (data) => {
        processChunk('STDOUT', data.toString());
      }).stderr.on('data', (data) => {
        processChunk('STDERR', data.toString());
      });
    });
  }).on('error', (err) => {
    sendLog(`[ERROR SSH CONEXIÓN]: No se pudo conectar por SSH a ${ip}: ${err.message}`, 100);
    res.end();
  }).connect({
    host: ip,
    port: Number(sshPort),
    username: sshUser,
    password: sshPassword,
    readyTimeout: 20000
  });
});

// Endpoint 3: Proxy para Sincronizar Clientes a Nodos VPS (Multi-nodo sync)
app.post('/api/vps/sync-client', async (req, res) => {
  const { vpsList, action, clientData } = req.body;

  if (!vpsList || !Array.isArray(vpsList) || vpsList.length === 0) {
    return res.status(400).json({ error: 'Debes proporcionar la lista de VPS a sincronizar.' });
  }

  const results = [];

  for (const node of vpsList) {
    try {
      const targetUrl = `http://${node.ip}:6767/api/v1/client/${action || 'create'}`;
      const response = await fetch(targetUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-KEY': node.token || 'maximus_secret_node_key_2026'
        },
        body: JSON.stringify(clientData)
      });
      const data = await response.json();
      results.push({ ip: node.ip, status: 'SUCCESS', data });
    } catch (err) {
      results.push({ ip: node.ip, status: 'FAILED', error: err.message });
    }
  }

  res.json({ success: true, results });
});

// Endpoint 4: Consultar métricas reales del VPS (CPU, RAM, Disco, Uptime, Usuarios en vivo)
app.get('/api/vps/metrics', async (req, res) => {
  const ip = req.query.ip;
  if (!ip) {
    return res.status(400).json({ error: 'IP de VPS requerida' });
  }

  try {
    const response = await fetch(`http://${ip}:6767/api/v1/health`, {
      headers: { 'X-API-KEY': 'maximus_secret_node_key_2026' },
      signal: AbortSignal.timeout(4000)
    });

    if (response.ok) {
      const data = await response.json();
      return res.json({
        status: 'online',
        cpuUsage: data.cpuUsage || 12,
        ramUsage: data.ramUsage || 28,
        ramTotalGb: data.ramTotalGb || 4,
        diskUsage: data.diskUsage || 35,
        diskTotalGb: data.diskTotalGb || 80,
        bytesSent: data.bytesSent || 0,
        bytesRecv: data.bytesRecv || 0,
        activeServices: data.activeServices || {},
        uptime: data.uptime || '1d 4h',
        usersRegistered: data.users_registered || 0
      });
    }
  } catch (e) {
    console.warn(`No se pudo obtener métricas en vivo de ${ip}:`, e.message);
  }

  res.json({
    status: 'offline',
    cpuUsage: 0,
    ramUsage: 0,
    ramTotalGb: 4,
    diskUsage: 0,
    diskTotalGb: 80,
    uptime: 'Offline'
  });
});

// Endpoint 5: Ejecutar Comandos SSH Reales en la VPS desde la Terminal Web
app.post('/api/vps/exec', (req, res) => {
  const { ip, sshPort = 22, sshUser = 'root', sshPassword, command } = req.body;

  if (!ip || !command) {
    return res.status(400).json({ error: 'IP y Comando requeridos.' });
  }

  const conn = new Client();

  conn.on('ready', () => {
    conn.exec(command, (err, stream) => {
      if (err) {
        conn.end();
        return res.status(500).json({ error: err.message });
      }

      let stdout = '';
      let stderr = '';

      stream.on('close', (code) => {
        conn.end();
        res.json({ code, stdout, stderr });
      }).on('data', (data) => {
        stdout += data.toString();
      }).stderr.on('data', (data) => {
        stderr += data.toString();
      });
    });
  }).on('error', (err) => {
    res.status(500).json({ error: `Fallo de conexión SSH a ${ip}: ${err.message}` });
  }).connect({
    host: ip,
    port: Number(sshPort),
    username: sshUser,
    password: sshPassword || 'root',
    readyTimeout: 10000
});

app.get('*', (req, res) => {
  res.sendFile(path.join(process.cwd(), 'index.html'));
});

app.listen(PORT, () => {
  console.log(`🚀 Servidor MAXIMUS PANEL escuchando en el puerto ${PORT} (http://localhost:${PORT})`);
});
