<?php
/**
 * Tiny dependency-free .env loader (keeps this admin panel installable
 * on a shared host with no Composer access). Looks for a `.env` file
 * two levels up (project root) first, falling back to a local one in
 * this config/ folder so the panel can also be dropped in standalone.
 */

function mb_load_env(): array
{
    static $vars = null;
    if ($vars !== null) {
        return $vars;
    }

    $candidates = [
        __DIR__ . '/../../.env',
        __DIR__ . '/.env',
    ];

    $vars = [];
    foreach ($candidates as $path) {
        if (!is_file($path)) {
            continue;
        }
        foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
            $line = trim($line);
            if ($line === '' || str_starts_with($line, '#')) {
                continue;
            }
            [$key, $value] = array_pad(explode('=', $line, 2), 2, '');
            $vars[trim($key)] = trim($value);
        }
        break; // first file found wins
    }
    return $vars;
}

function env(string $key, ?string $default = null): ?string
{
    $vars = mb_load_env();
    return $vars[$key] ?? getenv($key) ?: $default;
}
