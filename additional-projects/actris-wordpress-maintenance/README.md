# ACTRIS Working Copy

This directory contains an isolated copy of the WordPress site from:

`C:\xampp 7.4\htdocs\actris`

## Contents

- `site/`: copied WordPress files
- `database.sql`: database snapshot taken on June 9, 2026
- `router.php`: router for PHP's local development server

## Isolation

The copied `wp-config.php` uses the separate `actris_work` database.
The source files and original `actrisbg_actris` database are not used by this copy.

The working copy URL is:

`http://127.0.0.1:8099`

## Copy-only changes

- The copied site uses the `actris_work` database.
- `siteurl` and `home` point to the local development URL.
- The site runs locally on the bundled PHP 8.2.31 runtime.
- Elementor and My WP Translate were removed from the working site.
- Active plugins and Sydney were updated from official WordPress packages.
- Unused plugins, themes, old logs, and replaced components are preserved in
  `component-backups/2026-06-09/`, outside the web root.
- WordPress tables use InnoDB and old URLs were migrated to the local URL.
- Automatic updates are enabled for the active plugins and theme.

The original files and database remain unchanged. Pre-fix SQL snapshots are
stored as `database-pre-fix.sql` and `database-working-pre-fix.sql`.

## Start

From this directory:

```powershell
& '.\runtime\php-8.2\php.exe' -S 127.0.0.1:8099 -t site router.php
```

Apache is not required for the working copy, but XAMPP MySQL must be running.
