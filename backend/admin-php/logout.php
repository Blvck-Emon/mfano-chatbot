<?php
require_once __DIR__ . '/includes/auth.php';
mb_logout();
header('Location: login.php');
exit;
