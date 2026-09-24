<?php
/**
 * Shared PDO connection for the admin panel. Opens the same SQLite file as
 * the FastAPI service (DB_PATH env var; relative paths are resolved from the
 * project root, i.e. the folder that contains admin-php/ and data/).
 *
 * Requires the pdo_sqlite PHP extension, and SQLite built with FTS5 (the
 * knowledge_base triggers keep the FTS5 search indexes in sync on every
 * insert/update/delete made from this panel).
 */

require_once __DIR__ . '/env.php';

function mb_db_path(): string
{
    $raw = env('DB_PATH', 'data/mfano_bora_chatbot.db');
    $isAbsolute = preg_match('#^([A-Za-z]:[\\\\/]|/)#', $raw) === 1;
    return $isAbsolute ? $raw : dirname(__DIR__, 2) . '/' . $raw;
}

function mb_db(): PDO
{
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }

    $path = mb_db_path();
    if (!is_file($path)) {
        // PDO would silently create an empty database; fail clearly instead.
        http_response_code(500);
        die('SQLite database not found. Run: python database/init_db.py (see DB_PATH in .env).');
    }

    try {
        $pdo = new PDO('sqlite:' . $path, null, null, [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_TIMEOUT            => 5, // wait up to 5s if FastAPI is mid-write
        ]);
        $pdo->exec('PRAGMA foreign_keys = ON'); // off by default in SQLite; needed for CASCADE / SET NULL
        $pdo->exec('PRAGMA busy_timeout = 5000');
    } catch (PDOException $e) {
        http_response_code(500);
        die('Database connection failed. Check DB_PATH, file permissions and that pdo_sqlite is enabled.');
    }

    return $pdo;
}
