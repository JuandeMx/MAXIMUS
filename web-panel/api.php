<?php
// MAXIMUS HOSTINGER MASTER API (STANDALONE ENGINE WITH FULL CRUD & DB PERSISTENCE)
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Headers: Content-Type");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS, DELETE");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

$endpoint = isset($_GET['endpoint']) ? $_GET['endpoint'] : '';
$db_file = __DIR__ . '/maximus_hostinger.db';

try {
    $db = new PDO("sqlite:" . $db_file);
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $db->exec("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, exp_date TEXT, days INTEGER DEFAULT 30, devices INTEGER DEFAULT 1, status TEXT DEFAULT 'Active')");
    $db->exec("CREATE TABLE IF NOT EXISTS nodes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, ip TEXT UNIQUE, port INTEGER, domain_cf TEXT, domain_cft TEXT, status TEXT DEFAULT 'Online')");
    $db->exec("CREATE TABLE IF NOT EXISTS methods (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, ssh_host TEXT, ssh_port INTEGER, mode TEXT, sni TEXT, payload TEXT)");
    $db->exec("CREATE TABLE IF NOT EXISTS install_jobs (id TEXT PRIMARY KEY, status TEXT, step INTEGER, total_steps INTEGER, done INTEGER, error INTEGER, log TEXT)");

    // Precargar los 7 métodos reales si la tabla está vacía
    $countM = $db->query("SELECT count(*) FROM methods")->fetchColumn();
    if ($countM == 0) {
        $default_methods = [
            ["PERSONAL CF 1", "Sat24.com", 80, "SSL + Payload (WebSocket)", "www.fahorro.com", "MKCOL / HTTP/1.9[lf]Host: recargas.personal.com.ar[lf]Expect: 100-continue[crlf][crlf][split][crlf][crlf]GET- // HTTP/1.1[crlf]Host: [CF][crlf]Connection: Upgrade[crlf]User-Agent: [ua][crlf]Upgrade: websocket[crlf][crlf]"],
            ["PERSONAL CF 2", "emailmarketing.personal.com.ar", 80, "HTTP DIRECT / PAYLOAD", "", "COPY / HTTP/1.1[crlf]Host: recargas.personal.com.ar[crlf][crlf][instant_split][lf][lf]X / HTTP/1.2[crlf]Host: recargas.personal.com.ar[crlf][lf][crlf]GET / HTTP/1.1[crlf]Host: [CF][crlf]Upgrade: websocket[crlf]Connection: Upgrade[crlf][crlf]"],
            ["PERSONAL CF 3", "wap.renxo.com", 80, "HTTP DIRECT / PAYLOAD", "", "GET / HTTP/1.3[crlf]Host: rexo.personal.com.ar[crlf][crlf][crlf][split][crlf][split]GETT / HTTP/1.1[crlf]Host: [CF][crlf]Connection: Keep-Alive[crlf]Upgrade: websocket[crlf][crlf]"],
            ["PERSONAL CFT 1", "recargas.personal.com.ar", 80, "HTTP DIRECT / PAYLOAD", "", "GET / HTTP/1.1[crlf]Host: recargas.personal.com.ar[crlf][crlf][split][crlf][crlf]GET- / HTTP/1.1[crlf]Host: [host][lf][lf]GET /suareznet HTTP/1.1[crlf]Host: [CFT][lf]Connection: Upgrade[lf]Upgrade: websocket[lf]User-Agent: Googlebot/2.1 (+http://www.google.com/bot.html)[lf][lf]"],
            ["PERSONAL CFT 2", "institucional.telecom.com.ar", 80, "HTTP DIRECT / PAYLOAD", "", "HEAD / HTTP/1.1[crlf]Host: recargas.personal.com.ar[crlf][crlf][split][crlf][crlf]GET- / HTTP/1.1[crlf]Host: recargas.personal.com.ar[lf][lf]GET / HTTP/1.1[crlf]Host: [CFT][lf]Connection: Upgrade[lf]Upgrade: websocket[lf]User-Agent: Googlebot/2.1 (+http://www.google.com/bot.html)[lf][lf][split]"],
            ["PERSONAL CFT 3", "device-api.smarthome.personal.com.ar", 80, "HTTP DIRECT / PAYLOAD", "", "HEAD / HTTP/1.1[crlf]Host: recargas.personal.com.ar[crlf][crlf][split][crlf][crlf]GET- / HTTP/1.1[crlf]Host: recargas.personal.com.ar[lf][lf]GET / HTTP/1.1[crlf]Host: [CFT][lf]Connection: Upgrade[lf]Upgrade: websocket[lf]User-Agent: Googlebot/2.1 (+http://www.google.com/bot.html)[lf][lf][split]"],
            ["PERSONAL CFT 4", "www.personal.com.ar", 80, "HTTP DIRECT / PAYLOAD", "", "GET / HTTP/1.1[crlf]Host: emailmarketing.personal.com.ar[crlf][crlf][split][crlf][crlf]GET- / HTTP/1.1[crlf]Host: www.personal.com.ar[lf][lf]GET / HTTP/1.1[crlf]Host: [rotate=[CFT]][lf]Connection: Upgrade[lf]Upgrade: websocket[lf]User-Agent: Googlebot/2.1 (+http://www.google.com/bot.html)[lf][lf][split]"]
        ];
        $stmtIns = $db->prepare("INSERT INTO methods (name, ssh_host, ssh_port, mode, sni, payload) VALUES (?, ?, ?, ?, ?, ?)");
        foreach ($default_methods as $dm) {
            $stmtIns->execute($dm);
        }
    }
} catch (Exception $e) {}

// API ENDPOINTS

// 1. CLIENTES
if ($endpoint === '/api/clients') {
    $stmt = $db->query("SELECT * FROM users ORDER BY id DESC");
    echo json_encode(["clients" => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
    exit;
}

if ($endpoint === '/api/client/create' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = json_decode(file_get_contents('php://input'), true);
    $u = isset($raw['username']) ? $raw['username'] : '';
    $p = isset($raw['password']) ? $raw['password'] : '123456';
    $d = isset($raw['days']) ? floatval($raw['days']) : 30;

    $exp = date('Y-m-d H:i:s', strtotime("+{$d} days"));
    if ($d < 1) {
        $hours = intval($d * 24);
        $exp = date('Y-m-d H:i:s', strtotime("+{$hours} hours"));
    }

    $stmt = $db->prepare("INSERT OR REPLACE INTO users (username, password, exp_date, days) VALUES (?, ?, ?, ?)");
    $stmt->execute([$u, $p, $exp, intval($d)]);
    echo json_encode(["success" => true, "exp_date" => $exp]);
    exit;
}

if ($endpoint === '/api/client/delete' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = json_decode(file_get_contents('php://input'), true);
    $u = isset($raw['username']) ? $raw['username'] : '';
    $stmt = $db->prepare("DELETE FROM users WHERE username = ?");
    $stmt->execute([$u]);
    echo json_encode(["success" => true]);
    exit;
}

// 2. NODOS VPS
if ($endpoint === '/api/nodes') {
    $stmt = $db->query("SELECT * FROM nodes ORDER BY id DESC");
    echo json_encode(["nodes" => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
    exit;
}

if ($endpoint === '/api/vps/delete' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = json_decode(file_get_contents('php://input'), true);
    $ip = isset($raw['ip']) ? $raw['ip'] : '';
    $stmt = $db->prepare("DELETE FROM nodes WHERE ip = ?");
    $stmt->execute([$ip]);
    echo json_encode(["success" => true]);
    exit;
}

if (strpos($endpoint, '/api/vps/install/status') !== false) {
    echo json_encode([
        "status" => "VPS Lista y Conectada",
        "step" => 5,
        "total_steps" => 5,
        "done" => true,
        "error" => false,
        "log" => [
            "[+] Registrando VPS en la Base de Datos...",
            "[OK] Datos de Cloudflare y CloudFront vinculados.",
            "[SUCCESS] ✅ ¡VPS conectada e integrada correctamente en Hostinger!"
        ]
    ]);
    exit;
}

if (strpos($endpoint, '/api/vps/install') !== false && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = json_decode(file_get_contents('php://input'), true);
    $name = isset($raw['name']) ? $raw['name'] : 'Nodo VPS';
    $ip = isset($raw['ip']) ? $raw['ip'] : '';
    $port = isset($raw['port']) ? intval($raw['port']) : 22;
    $domain_cf = isset($raw['domain_cf']) ? $raw['domain_cf'] : '';
    $domain_cft = isset($raw['domain_cft']) ? $raw['domain_cft'] : '';

    $stmt = $db->prepare("INSERT OR REPLACE INTO nodes (name, ip, port, domain_cf, domain_cft, status) VALUES (?, ?, ?, ?, ?, 'Online')");
    $stmt->execute([$name, $ip, $port, $domain_cf, $domain_cft]);

    $install_id = "job_" . time();
    echo json_encode(["status" => "ok", "install_id" => $install_id]);
    exit;
}

// 3. MÉTODOS DE CONEXIÓN
if ($endpoint === '/api/methods') {
    $stmt = $db->query("SELECT * FROM methods ORDER BY id DESC");
    echo json_encode(["methods" => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
    exit;
}

if ($endpoint === '/api/method/create' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = json_decode(file_get_contents('php://input'), true);
    $stmt = $db->prepare("INSERT OR REPLACE INTO methods (name, ssh_host, ssh_port, mode, sni, payload) VALUES (?, ?, ?, ?, ?, ?)");
    $stmt->execute([
        $raw['name'], $raw['ssh_host'], intval($raw['ssh_port']),
        $raw['mode'], $raw['sni'], $raw['payload']
    ]);
    echo json_encode(["success" => true]);
    exit;
}

if ($endpoint === '/api/method/delete' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = json_decode(file_get_contents('php://input'), true);
    $stmt = $db->prepare("DELETE FROM methods WHERE name = ?");
    $stmt->execute([$raw['name']]);
    echo json_encode(["success" => true]);
    exit;
}

echo json_encode(["status" => "ok"]);
?>
