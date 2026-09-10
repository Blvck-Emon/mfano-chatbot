<?php
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';

$user = mb_require_role(['editor', 'superadmin']);

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: knowledge_base.php');
    exit;
}

$pdo = mb_db();
$docId = isset($_POST['doc_id']) ? (int) $_POST['doc_id'] : null;
$action = $_POST['action'] ?? 'save';

if ($action === 'delete' && $docId) {
    $stmt = $pdo->prepare('DELETE FROM knowledge_base WHERE doc_id = ?');
    $stmt->execute([$docId]);
    header('Location: knowledge_base.php?deleted=1');
    exit;
}

$categoryId   = (int) ($_POST['category_id'] ?? 0);
$question     = trim($_POST['question'] ?? '');
$contentChunk = trim($_POST['content_chunk'] ?? '');
$keywords     = trim($_POST['keywords'] ?? '');
$sourceUrl    = trim($_POST['source_url'] ?? '');
$status       = in_array($_POST['status'] ?? '', ['active', 'draft', 'archived'], true)
                    ? $_POST['status'] : 'active';

if ($contentChunk === '' || $categoryId <= 0) {
    http_response_code(422);
    die('Category and content are required.');
}

if ($docId) {
    $stmt = $pdo->prepare(
        'UPDATE knowledge_base
         SET category_id = ?, question = ?, content_chunk = ?, keywords = ?, source_url = ?, status = ?, source_type = "manual"
         WHERE doc_id = ?'
    );
    $stmt->execute([$categoryId, $question ?: null, $contentChunk, $keywords ?: null, $sourceUrl ?: null, $status, $docId]);
} else {
    $stmt = $pdo->prepare(
        'INSERT INTO knowledge_base (category_id, question, content_chunk, keywords, source_url, status, source_type)
         VALUES (?, ?, ?, ?, ?, ?, "manual")'
    );
    $stmt->execute([$categoryId, $question ?: null, $contentChunk, $keywords ?: null, $sourceUrl ?: null, $status]);
    $docId = (int) $pdo->lastInsertId();
}

header('Location: kb_edit.php?id=' . $docId . '&saved=1');
exit;
