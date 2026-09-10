<?php
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';

mb_start_session();
if (mb_current_user()) {
    header('Location: index.php');
    exit;
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';

    if ($username === '' || $password === '') {
        $error = 'Please enter both username and password.';
    } elseif (mb_attempt_login($username, $password)) {
        header('Location: index.php');
        exit;
    } else {
        $error = 'Invalid credentials.';
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login · Mfano Bora Admin</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body class="mb-login-body">
<div class="mb-login-box">
    <h1>Mfano Bora <span>Chatbot Admin</span></h1>
    <?php if ($error): ?><div class="mb-alert mb-alert-error"><?= h($error) ?></div><?php endif; ?>
    <form method="post" autocomplete="off">
        <label>Username
            <input type="text" name="username" required autofocus>
        </label>
        <label>Password
            <input type="password" name="password" required>
        </label>
        <button type="submit">Log in</button>
    </form>
</div>
</body>
</html>
