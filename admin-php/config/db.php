<?php
/**
 * Shared PDO connection for the admin panel. Uses the same DB_* env
 * vars as the FastAPI service so both point at the one MySQL database.
 */

require_once __DIR__ . '/env.php';

function mb_db(): PDO
{
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }

    $host = env('DB_HOST', '127.0.0.1');
    $port = env('DB_PORT', '3306');
    $name = env('DB_NAME', 'mfano_bora_chatbot');
    $user = env('DB_USER', 'mfano_app');
    $pass = env('DB_PASSWORD', '');

    $dsn = "mysql:host={$host};port={$port};dbname={$name};charset=utf8mb4";

    try {
        $pdo = new PDO($dsn, $user, $pass, [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ]);
    } catch (PDOException $e) {
        http_response_code(500);
        die('Database connection failed. Check admin-php/config and .env settings.');
    }

    return $pdo;
}
