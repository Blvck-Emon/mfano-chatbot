<?php
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';

$user = mb_require_login();
$pdo = mb_db();

$sessionFilter = trim($_GET['session'] ?? '');
$fallbackOnly = isset($_GET['fallback_only']);

$sql = "SELECT log_id, session_id, sender_type, message_text, intent_matched, was_fallback, timestamp
        FROM chat_logs WHERE 1=1";
$params = [];

if ($sessionFilter !== '') {
    $sql .= ' AND session_id = ?';
    $params[] = $sessionFilter;
}
if ($fallbackOnly) {
    $sql .= ' AND was_fallback = 1';
}
$sql .= ' ORDER BY timestamp DESC LIMIT 300';

$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$rows = $stmt->fetchAll();

mb_render_header('Chat Logs', $user);
?>

<form method="get" class="mb-filter-form">
    <input type="text" name="session" placeholder="Filter by session_id" value="<?= h($sessionFilter) ?>">
    <label class="mb-checkbox">
        <input type="checkbox" name="fallback_only" value="1" <?= $fallbackOnly ? 'checked' : '' ?>>
        Fallback replies only
    </label>
    <button type="submit">Filter</button>
</form>

<table class="mb-table">
    <thead><tr><th>Time</th><th>Session</th><th>Sender</th><th>Message</th><th>Intent</th><th>Fallback</th></tr></thead>
    <tbody>
    <?php foreach ($rows as $row): ?>
        <tr class="<?= $row['was_fallback'] ? 'mb-row-fallback' : '' ?>">
            <td><?= h($row['timestamp']) ?></td>
            <td><a href="?session=<?= h($row['session_id']) ?>"><?= h(substr($row['session_id'], 0, 8)) ?>…</a></td>
            <td><?= h(ucfirst($row['sender_type'])) ?></td>
            <td class="mb-truncate"><?= h($row['message_text']) ?></td>
            <td><?= h($row['intent_matched'] ?? '—') ?></td>
            <td><?= $row['was_fallback'] ? 'Yes' : 'No' ?></td>
        </tr>
    <?php endforeach; ?>
    <?php if (!$rows): ?>
        <tr><td colspan="6" class="mb-muted">No chat logs yet.</td></tr>
    <?php endif; ?>
    </tbody>
</table>

<?php mb_render_footer(); ?>
