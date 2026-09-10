<?php
/**
 * Session-based authentication + Role-Based Access Control (RBAC).
 * Task 15 (Information Security & Privacy): passwords are bcrypt
 * hashed, sessions are HttpOnly/SameSite, and every mutating action
 * requires the 'editor' or 'superadmin' role.
 */

require_once __DIR__ . '/../config/env.php';
require_once __DIR__ . '/../config/db.php';

function mb_start_session(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }
    session_name(env('ADMIN_SESSION_NAME', 'mfano_admin_sess'));
    session_set_cookie_params([
        'lifetime' => (int) env('ADMIN_SESSION_LIFETIME', '3600'),
        'path'     => '/',
        'httponly' => true,
        'samesite' => 'Lax',
        'secure'   => (($_SERVER['HTTPS'] ?? '') === 'on'),
    ]);
    session_start();
}

function mb_current_user(): ?array
{
    mb_start_session();
    return $_SESSION['admin_user'] ?? null;
}

/** Call at the top of every protected page. Redirects to login if needed. */
function mb_require_login(): array
{
    $user = mb_current_user();
    if (!$user) {
        header('Location: login.php');
        exit;
    }
    return $user;
}

/** Call after mb_require_login() on pages that mutate data. */
function mb_require_role(array $allowedRoles): array
{
    $user = mb_require_login();
    if (!in_array($user['role'], $allowedRoles, true)) {
        http_response_code(403);
        die('You do not have permission to access this page.');
    }
    return $user;
}

function mb_attempt_login(string $username, string $password): bool
{
    $pdo = mb_db();
    $stmt = $pdo->prepare(
        'SELECT user_id, username, password_hash, role, is_active FROM admin_users WHERE username = ?'
    );
    $stmt->execute([$username]);
    $row = $stmt->fetch();

    if (!$row || !$row['is_active'] || !password_verify($password, $row['password_hash'])) {
        return false;
    }

    mb_start_session();
    session_regenerate_id(true);
    $_SESSION['admin_user'] = [
        'user_id'  => $row['user_id'],
        'username' => $row['username'],
        'role'     => $row['role'],
    ];

    $update = $pdo->prepare('UPDATE admin_users SET last_login_at = NOW() WHERE user_id = ?');
    $update->execute([$row['user_id']]);

    return true;
}

function mb_logout(): void
{
    mb_start_session();
    $_SESSION = [];
    session_destroy();
}
