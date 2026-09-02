<?php

$path = parse_url( $_SERVER['REQUEST_URI'], PHP_URL_PATH );
$file = __DIR__ . '/site' . $path;

$blocked = array(
	'/.htaccess',
	'/license.txt',
	'/readme.html',
	'/sh_version_checker.php',
);

if (
	in_array( strtolower( $path ), $blocked, true )
	|| preg_match( '#(?:^|/)(?:error_log|debug\.log)$#i', $path )
) {
	http_response_code( 404 );
	exit;
}

if ( '/' !== $path && is_file( $file ) ) {
	return false;
}

require __DIR__ . '/site/index.php';
