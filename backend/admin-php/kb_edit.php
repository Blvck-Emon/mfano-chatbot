<?php
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';

// Editors and superadmins may create/update KB entries; viewers cannot.
$user = mb_require_role(['editor', 'superadmin']);
$pdo = mb_db();

$id = isset($_GET['id']) ? (int) $_GET['id'] : null;
$entry = [
    'category_id'   => '',
    'question'      => $_GET['prefill'] ?? '',
    'content_chunk' => '',
    'keywords'      => '',
    'source_url'    => '',
    'status'        => 'active',
];

if ($id) {
    $stmt = $pdo->prepare('SELECT * FROM knowledge_base WHERE doc_id = ?');
    $stmt->execute([$id]);
    $found = $stmt->fetch();
    if ($found) {
        $entry = $found;
    }
}

$categories = $pdo->query('SELECT category_id, name FROM kb_categories ORDER BY name')->fetchAll();

mb_render_header($id ? 'Edit Knowledge Base Entry' : 'Add Knowledge Base Entry', $user);
?>

<form method="post" action="kb_save.php" class="mb-form">
    <?php if ($id): ?><input type="hidden" name="doc_id" value="<?= (int) $id ?>"><?php endif; ?>

    <label>Category
        <select name="category_id" required>
            <?php foreach ($categories as $c): ?>
                <option value="<?= (int) $c['category_id'] ?>" <?= $entry['category_id'] == $c['category_id'] ? 'selected' : '' ?>>
                    <?= h($c['name']) ?>
                </option>
            <?php endforeach; ?>
        </select>
    </label>

    <label>Question (optional for scraped chunks)
        <input type="text" name="question" maxlength="500" value="<?= h($entry['question']) ?>">
    </label>

    <label>Answer / Content
        <textarea name="content_chunk" rows="6" required><?= h($entry['content_chunk']) ?></textarea>
    </label>

    <label>Keywords / Metadata tags (comma separated)
        <input type="text" name="keywords" value="<?= h($entry['keywords']) ?>">
    </label>

    <label>Source URL
        <input type="url" name="source_url" value="<?= h($entry['source_url']) ?>">
    </label>

    <label>Status
        <select name="status">
            <option value="active" <?= $entry['status'] === 'active' ? 'selected' : '' ?>>Active</option>
            <option value="draft" <?= $entry['status'] === 'draft' ? 'selected' : '' ?>>Draft</option>
            <option value="archived" <?= $entry['status'] === 'archived' ? 'selected' : '' ?>>Archived</option>
        </select>
    </label>

    <div class="mb-form-actions">
        <button type="submit">Save</button>
        <a class="mb-btn mb-btn-secondary" href="knowledge_base.php">Cancel</a>
        <?php if ($id): ?>
            <button type="submit" form="delete-form" class="mb-btn mb-btn-danger" onclick="return confirm('Delete this entry?')">Delete</button>
        <?php endif; ?>
    </div>
</form>

<?php if ($id): ?>
<form id="delete-form" method="post" action="kb_save.php">
    <input type="hidden" name="doc_id" value="<?= (int) $id ?>">
    <input type="hidden" name="action" value="delete">
</form>
<?php endif; ?>

<?php mb_render_footer(); ?>
