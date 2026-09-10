<?php
/** Small shared helpers to keep pages terse and consistently escaped. */

function h(?string $value): string
{
    return htmlspecialchars($value ?? '', ENT_QUOTES, 'UTF-8');
}

function mb_render_header(string $title, ?array $user): void
{
    ?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= h($title) ?> · Mfano Bora Admin</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
<header class="mb-topbar">
    <div class="mb-brand">Mfano Bora <span>Chatbot Admin</span></div>
    <?php if ($user): ?>
    <nav class="mb-nav">
        <a href="index.php">Dashboard</a>
        <a href="knowledge_base.php">Knowledge Base</a>
        <a href="chat_logs.php">Chat Logs</a>
        <?php if ($user['role'] === 'superadmin'): ?>
        <a href="users.php">Admin Users</a>
        <?php endif; ?>
    </nav>
    <div class="mb-user">
        <?= h($user['username']) ?> (<?= h($user['role']) ?>)
        &middot; <a href="logout.php">Log out</a>
    </div>
    <?php endif; ?>
</header>
<main class="mb-container">
    <h1><?= h($title) ?></h1>
    <?php
}

function mb_render_footer(): void
{
    ?>
</main>
<footer class="mb-footer">Mfano Bora Africa &middot; Chatbot Information Management System</footer>
</body>
</html>
    <?php
}

function mb_flash(string $message, string $type = 'success'): void
{
    echo '<div class="mb-alert mb-alert-' . h($type) . '">' . h($message) . '</div>';
}
