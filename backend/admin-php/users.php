<?php
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/functions.php';

$user = mb_require_role(['superadmin']);
$pdo = mb_db();

$error = '';
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $formAction = $_POST['form_action'] ?? '';

    if ($formAction === 'create') {
        $username = trim($_POST['username'] ?? '');
        $email    = trim($_POST['email'] ?? '');
        $password = $_POST['password'] ?? '';
        $role     = in_array($_POST['role'] ?? '', ['superadmin', 'editor', 'viewer'], true)
                        ? $_POST['role'] : 'viewer';

        if ($username === '' || $email === '' || strlen($password) < 8) {
            $error = 'Username, email and a password (8+ chars) are required.';
        } else {
            try {
                $stmt = $pdo->prepare(
                    'INSERT INTO admin_users (username, email, password_hash, role) VALUES (?, ?, ?, ?)'
                );
                $stmt->execute([$username, $email, password_hash($password, PASSWORD_BCRYPT), $role]);
                $success = "User '{$username}' created.";
            } catch (PDOException $e) {
                $error = 'Could not create user (username/email may already exist).';
            }
        }
    } elseif ($formAction === 'deactivate') {
        $targetId = (int) ($_POST['user_id'] ?? 0);
        if ($targetId && $targetId !== (int) $user['user_id']) {
            $stmt = $pdo->prepare('UPDATE admin_users SET is_active = 0 WHERE user_id = ?');
            $stmt->execute([$targetId]);
            $success = 'User deactivated.';
        }
    }
}

$users = $pdo->query('SELECT user_id, username, email, role, is_active, last_login_at FROM admin_users ORDER BY username')->fetchAll();

mb_render_header('Admin Users', $user);
if ($error) mb_flash($error, 'error');
if ($success) mb_flash($success, 'success');
?>

<section class="mb-panel">
    <h2>Existing Users</h2>
    <table class="mb-table">
        <thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Active</th><th>Last Login</th><th></th></tr></thead>
        <tbody>
        <?php foreach ($users as $u): ?>
            <tr>
                <td><?= h($u['username']) ?></td>
                <td><?= h($u['email']) ?></td>
                <td><?= h($u['role']) ?></td>
                <td><?= $u['is_active'] ? 'Yes' : 'No' ?></td>
                <td><?= h($u['last_login_at'] ?? 'Never') ?></td>
                <td>
                    <?php if ($u['is_active'] && $u['user_id'] != $user['user_id']): ?>
                    <form method="post" style="display:inline">
                        <input type="hidden" name="form_action" value="deactivate">
                        <input type="hidden" name="user_id" value="<?= (int) $u['user_id'] ?>">
                        <button type="submit" onclick="return confirm('Deactivate this user?')">Deactivate</button>
                    </form>
                    <?php endif; ?>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</section>

<section class="mb-panel">
    <h2>Add User</h2>
    <form method="post" class="mb-form">
        <input type="hidden" name="form_action" value="create">
        <label>Username <input type="text" name="username" required></label>
        <label>Email <input type="email" name="email" required></label>
        <label>Password <input type="password" name="password" minlength="8" required></label>
        <label>Role
            <select name="role">
                <option value="viewer">Viewer (read-only)</option>
                <option value="editor">Editor (manage KB)</option>
                <option value="superadmin">Superadmin (full access)</option>
            </select>
        </label>
        <button type="submit">Create User</button>
    </form>
</section>

<?php mb_render_footer(); ?>
