<?php
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';

$user = mb_require_login();
$pdo = mb_db();

$search = trim($_GET['q'] ?? '');
$categoryId = $_GET['category'] ?? '';

$categories = $pdo->query('SELECT category_id, name FROM kb_categories ORDER BY name')->fetchAll();

// One row per ANSWER; its training questions are summarised (first question + count).
$sql = "SELECT kb.doc_id, kb.content_chunk, kb.source_type, kb.status, kb.last_updated,
               cat.name AS category,
               (SELECT COUNT(*) FROM kb_questions q WHERE q.doc_id = kb.doc_id) AS question_count,
               (SELECT q.question_text FROM kb_questions q WHERE q.doc_id = kb.doc_id
                 ORDER BY q.question_id LIMIT 1) AS first_question
        FROM knowledge_base kb
        LEFT JOIN kb_categories cat ON cat.category_id = kb.category_id
        WHERE 1=1";
$params = [];

if ($search !== '') {
    $sql .= ' AND (kb.content_chunk LIKE ? OR kb.keywords LIKE ?
                   OR EXISTS (SELECT 1 FROM kb_questions q WHERE q.doc_id = kb.doc_id AND q.question_text LIKE ?))';
    $like = "%{$search}%";
    array_push($params, $like, $like, $like);
}
if ($categoryId !== '') {
    $sql .= ' AND kb.category_id = ?';
    $params[] = (int) $categoryId;
}
$sql .= ' ORDER BY kb.last_updated DESC, kb.doc_id DESC LIMIT 200';

$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$rows = $stmt->fetchAll();

mb_render_header('Knowledge Base', $user);
?>

<div class="mb-toolbar">
    <form method="get" class="mb-filter-form">
        <input type="text" name="q" placeholder="Search question / content..." value="<?= h($search) ?>">
        <select name="category">
            <option value="">All categories</option>
            <?php foreach ($categories as $c): ?>
                <option value="<?= (int) $c['category_id'] ?>" <?= $categoryId == $c['category_id'] ? 'selected' : '' ?>>
                    <?= h($c['name']) ?>
                </option>
            <?php endforeach; ?>
        </select>
        <button type="submit">Filter</button>
    </form>
    <a class="mb-btn" href="kb_edit.php">+ Add Entry</a>
</div>

<table class="mb-table">
    <thead>
    <tr><th>Category</th><th>Sample question</th><th>Answer</th><th>Source</th><th>Status</th><th>Updated</th><th></th></tr>
    </thead>
    <tbody>
    <?php foreach ($rows as $row): ?>
        <?php $qCount = (int) $row['question_count']; ?>
        <tr>
            <td><?= h($row['category'] ?? 'Uncategorized') ?></td>
            <td>
                <?= h($row['first_question'] ?: '(no training questions)') ?>
                <?php if ($qCount > 1): ?><span class="mb-muted">(+<?= $qCount - 1 ?> more)</span><?php endif; ?>
            </td>
            <td class="mb-truncate"><?= h(mb_strimwidth($row['content_chunk'], 0, 140, '…')) ?></td>
            <td><span class="mb-tag mb-tag-<?= h($row['source_type']) ?>"><?= h($row['source_type']) ?></span></td>
            <td><span class="mb-status mb-status-<?= h($row['status']) ?>"><?= h($row['status']) ?></span></td>
            <td><?= h($row['last_updated']) ?> UTC</td>
            <td><a href="kb_edit.php?id=<?= (int) $row['doc_id'] ?>">Edit</a></td>
        </tr>
    <?php endforeach; ?>
    <?php if (!$rows): ?>
        <tr><td colspan="7" class="mb-muted">No knowledge base entries found. Load the CSV via csv-loader or add one manually.</td></tr>
    <?php endif; ?>
    </tbody>
</table>

<?php mb_render_footer(); ?>
