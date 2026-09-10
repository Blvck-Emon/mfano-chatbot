<?php
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';

$user = mb_require_login();
$pdo = mb_db();

// KPIs computed directly against MySQL (mirrors FastAPI's
// /api/v1/admin/dashboard-stats so the panel works even if the
// Python service is temporarily down).
$days = 7;

$stmt = $pdo->prepare(
    "SELECT COUNT(DISTINCT session_id) AS conversations,
            COUNT(*) AS messages,
            SUM(CASE WHEN was_fallback = 1 THEN 1 ELSE 0 END) AS fallbacks
     FROM chat_logs
     WHERE sender_type = 'bot' AND timestamp >= (NOW() - INTERVAL ? DAY)"
);
$stmt->execute([$days]);
$stats = $stmt->fetch() ?: ['conversations' => 0, 'messages' => 0, 'fallbacks' => 0];

$messages = (int) ($stats['messages'] ?? 0);
$fallbacks = (int) ($stats['fallbacks'] ?? 0);
$fallbackRate = $messages ? round(($fallbacks / $messages) * 100, 1) : 0.0;
$resolutionRate = $messages ? round(100 - $fallbackRate, 1) : 0.0;

$gapStmt = $pdo->query(
    "SELECT unanswered_query, frequency FROM kb_gap_log
     WHERE status != 'resolved' ORDER BY frequency DESC, flagged_at DESC LIMIT 8"
);
$gaps = $gapStmt->fetchAll();

$kbCountStmt = $pdo->query("SELECT COUNT(*) AS c FROM knowledge_base WHERE status = 'active'");
$kbCount = (int) $kbCountStmt->fetch()['c'];

mb_render_header('Dashboard', $user);
?>

<section class="mb-kpi-grid">
    <div class="mb-kpi-card">
        <span class="mb-kpi-value"><?= (int) ($stats['conversations'] ?? 0) ?></span>
        <span class="mb-kpi-label">Conversations (last <?= $days ?> days)</span>
    </div>
    <div class="mb-kpi-card">
        <span class="mb-kpi-value"><?= $messages ?></span>
        <span class="mb-kpi-label">Bot Replies (last <?= $days ?> days)</span>
    </div>
    <div class="mb-kpi-card">
        <span class="mb-kpi-value"><?= $fallbackRate ?>%</span>
        <span class="mb-kpi-label">Fallback Rate</span>
    </div>
    <div class="mb-kpi-card">
        <span class="mb-kpi-value"><?= $resolutionRate ?>%</span>
        <span class="mb-kpi-label">Resolution Rate</span>
    </div>
    <div class="mb-kpi-card">
        <span class="mb-kpi-value"><?= $kbCount ?></span>
        <span class="mb-kpi-label">Active KB Entries</span>
    </div>
</section>

<section class="mb-panel">
    <h2>Top Unanswered Questions (Information Gap Analysis)</h2>
    <p class="mb-muted">Questions the chatbot fell back on most often. Add matching knowledge-base entries to close these gaps.</p>
    <?php if (!$gaps): ?>
        <p class="mb-muted">No open gaps recorded yet.</p>
    <?php else: ?>
    <table class="mb-table">
        <thead><tr><th>Question</th><th>Times Asked</th><th></th></tr></thead>
        <tbody>
        <?php foreach ($gaps as $gap): ?>
            <tr>
                <td><?= h($gap['unanswered_query']) ?></td>
                <td><?= (int) $gap['frequency'] ?></td>
                <td><a href="kb_edit.php?prefill=<?= urlencode($gap['unanswered_query']) ?>">Add to KB &rarr;</a></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php endif; ?>
</section>

<?php mb_render_footer(); ?>
