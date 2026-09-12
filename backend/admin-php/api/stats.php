<?php
/**
 * GET admin-php/api/stats.php?days=7
 * Session-authenticated JSON endpoint used by index.php's optional
 * auto-refresh (or any internal tool) without hitting FastAPI directly.
 */

require_once __DIR__ . '/../includes/auth.php';

header('Content-Type: application/json');
mb_require_login();

$pdo = mb_db();
$days = isset($_GET['days']) ? max(1, min(90, (int) $_GET['days'])) : 7;

$stmt = $pdo->prepare(
    "SELECT COUNT(DISTINCT session_id) AS conversations,
            COUNT(*) AS messages,
            SUM(CASE WHEN was_fallback = 1 THEN 1 ELSE 0 END) AS fallbacks
     FROM chat_logs
     WHERE sender_type = 'bot' AND timestamp >= (NOW() - INTERVAL ? DAY)"
);
$stmt->execute([$days]);
$row = $stmt->fetch() ?: ['conversations' => 0, 'messages' => 0, 'fallbacks' => 0];

$messages = (int) $row['messages'];
$fallbacks = (int) $row['fallbacks'];

echo json_encode([
    'date_range_days' => $days,
    'conversations'   => (int) $row['conversations'],
    'messages'        => $messages,
    'fallback_rate'   => $messages ? round(($fallbacks / $messages) * 100, 2) : 0,
    'resolution_rate' => $messages ? round(100 - (($fallbacks / $messages) * 100), 2) : 0,
]);
