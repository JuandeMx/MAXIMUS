<?php
// API RELAY PROXY FOR HOSTINGER (HTTPS -> MASTER BACKEND HTTP:8080)
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Headers: Content-Type");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS, DELETE");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

$path = isset($_GET['endpoint']) ? $_GET['endpoint'] : '';
$master_url = "http://187.127.17.250:8080" . $path;

if (!empty($_SERVER['QUERY_STRING'])) {
    $qs = $_SERVER['QUERY_STRING'];
    $qs_clean = preg_replace('/^endpoint=[^&]*&?/', '', $qs);
    if (!empty($qs_clean)) {
        $master_url .= "?" . $qs_clean;
    }
}

$ch = curl_init($master_url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 300);
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $_SERVER['REQUEST_METHOD']);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $post_data = file_get_contents('php://input');
    curl_setopt($ch, CURLOPT_POSTFIELDS, $post_data);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
}

$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

http_response_code($http_code ? $http_code : 200);
header('Content-Type: application/json');
echo $response;
?>
