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
    // ON DELETE CASCADE removes this answer's kb_questions; chat_logs.doc_id_matched is set to NULL.
    $stmt = $pdo->prepare('DELETE FROM knowledge_base WHERE doc_id = ?');
    $stmt->execute([$docId]);
    header('Location: knowledge_base.php?deleted=1');
    exit;
}

/** "One question per line" textarea -> clean, de-duplicated list (max 500 chars each). */
function mb_parse_questions(string $raw): array
{
    $seen = [];
    foreach (preg_split('/\R/u', $raw) ?: [] as $line) {
        $q = trim(preg_replace('/\s+/u', ' ', $line));
        if ($q === '') {
            continue;
        }
        $q = mb_substr($q, 0, 500);
        $seen[mb_strtolower($q)] = $q; // question_text is case-insensitive-unique in the DB
    }
    return array_values($seen);
}

$categoryId   = (int) ($_POST['category_id'] ?? 0);
$contentChunk = trim($_POST['content_chunk'] ?? '');
$keywords     = trim($_POST['keywords'] ?? '');
$sourceUrl    = trim($_POST['source_url'] ?? '');
$status       = in_array($_POST['status'] ?? '', ['active', 'draft', 'archived'], true)
                    ? $_POST['status'] : 'active';
$questions    = mb_parse_questions((string) ($_POST['questions'] ?? ''));

if ($contentChunk === '' || $categoryId <= 0) {
    http_response_code(422);
    die('Category and content are required.');
}

$pdo->beginTransaction();
try {
    if ($docId) {
        $stmt = $pdo->prepare(
            "UPDATE knowledge_base
             SET category_id = ?, content_chunk = ?, keywords = ?, source_url = ?, status = ?, source_type = 'manual'
             WHERE doc_id = ?"
        );
        $stmt->execute([$categoryId, $contentChunk, $keywords ?: null, $sourceUrl ?: null, $status, $docId]);
    } else {
        $stmt = $pdo->prepare(
            "INSERT INTO knowledge_base (category_id, content_chunk, keywords, source_url, status, source_type)
             VALUES (?, ?, ?, ?, ?, 'manual')"
        );
        $stmt->execute([$categoryId, $contentChunk, $keywords ?: null, $sourceUrl ?: null, $status]);
        $docId = (int) $pdo->lastInsertId();
    }

    // Replace this answer's training questions with the submitted list. A question
    // that already belongs to ANOTHER entry is never moved (one question = one answer,
    // and silently re-pointing trained data is dangerous): it is skipped and reported.
    $pdo->prepare('DELETE FROM kb_questions WHERE doc_id = ?')->execute([$docId]);
    $insertQ = $pdo->prepare('INSERT OR IGNORE INTO kb_questions (doc_id, question_text) VALUES (?, ?)');
    $skipped = [];
    foreach ($questions as $q) {
        $insertQ->execute([$docId, $q]);
        if ($insertQ->rowCount() === 0) {
            $skipped[] = $q;
        }
    }

    $pdo->commit();
} catch (Throwable $e) {
    if ($pdo->inTransaction()) {
        $pdo->rollBack();
    }
    http_response_code(500);
    die('Could not save the entry. Please try again.');
}

$redirect = 'kb_edit.php?id=' . $docId . '&saved=1';
foreach ($skipped as $q) {
    $redirect .= '&skipped[]=' . urlencode($q);
}
header('Location: ' . $redirect);
exit;
