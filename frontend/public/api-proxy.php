<?php
declare(strict_types=1);

$UPSTREAM = 'https://mana-meeples-boardgame-list.onrender.com';
$ALLOWED_METHODS = ['GET', 'POST', 'PUT', 'DELETE'];

// Enable error reporting for debugging
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Add CORS headers
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization, X-Admin-Token');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if (!in_array($method, $ALLOWED_METHODS, true)) {
    http_response_code(405);
    header('Allow: ' . implode(', ', $ALLOWED_METHODS));
    header('Content-Type: application/json');
    echo json_encode(['error' => 'method_not_allowed']);
    exit;
}

$path = $_GET['path'] ?? '';
if ($path === '' || $path[0] !== '/') {
    http_response_code(400);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'invalid_path', 'received_path' => $path]);
    exit;
}

// FIXED: Forward all query parameters except 'path'
$queryParams = $_GET;
unset($queryParams['path']); // Remove the 'path' parameter

$queryString = '';
if (!empty($queryParams)) {
    $queryString = '?' . http_build_query($queryParams);
}

$target = $UPSTREAM . $path . $queryString;

// Log the request for debugging
error_log("API Proxy Request: " . $method . " " . $target);

// Prepare cURL
$ch = curl_init();
curl_setopt_array($ch, [
    CURLOPT_URL            => $target,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HEADER         => true,
    CURLOPT_CUSTOMREQUEST  => $method,
    CURLOPT_FOLLOWLOCATION => true,
    CURLOPT_TIMEOUT        => 30, // Increased timeout
    CURLOPT_CONNECTTIMEOUT => 15, // Increased connection timeout
    CURLOPT_SSL_VERIFYPEER => true,
]);

// Forward headers
$incoming = function_exists('getallheaders') ? getallheaders() : [];
$whitelist = ['Accept', 'Content-Type', 'Authorization', 'X-Admin-Token'];
$outHeaders = ['User-Agent: ManaMeeplesProxy/1.0'];
foreach ($whitelist as $h) {
    if (isset($incoming[$h])) {
        $outHeaders[] = $h . ': ' . $incoming[$h];
    }
}
curl_setopt($ch, CURLOPT_HTTPHEADER, $outHeaders);

// Forward body for POST requests
if (in_array($method, ['POST', 'PUT', 'PATCH'], true)) {
    $body = file_get_contents('php://input');
    curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
}

// Execute request
$response = curl_exec($ch);
if ($response === false) {
    $err = curl_error($ch);
    curl_close($ch);
    error_log("cURL Error: " . $err);
    http_response_code(502);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'upstream_error', 'detail' => $err, 'target' => $target]);
    exit;
}

$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$headerSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
$headersRaw = substr($response, 0, $headerSize);
$respBody = substr($response, $headerSize);
curl_close($ch);

// Log response for debugging
error_log("API Proxy Response: " . $httpCode . " for " . $target);

// Forward response headers
$contentType = 'application/json';
foreach (explode("\r\n", $headersRaw) as $line) {
    if (stripos($line, 'Content-Type:') === 0) {
        $contentType = trim(substr($line, 13));
    }
    if (stripos($line, 'Cache-Control:') === 0) {
        header($line);
    }
}

http_response_code($httpCode);
header('Content-Type: ' . $contentType);
header('X-Proxy-Target: ' . $target);

echo $respBody;
?>