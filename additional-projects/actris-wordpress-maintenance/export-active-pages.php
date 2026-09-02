<?php

require __DIR__ . '/site/wp-load.php';

$ids = array( 524, 614, 607, 153, 526, 527, 528, 156, 582, 584, 308 );

foreach ( $ids as $id ) {
	$page = get_post( $id );

	echo "\n===== {$id}: {$page->post_title} =====\n";
	echo $page->post_content . "\n";
}
