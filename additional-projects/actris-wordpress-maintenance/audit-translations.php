<?php

require __DIR__ . '/site/wp-load.php';

$pages = get_posts(
	array(
		'post_type'   => 'page',
		'post_status' => 'publish',
		'numberposts' => -1,
		'orderby'     => 'ID',
		'order'       => 'ASC',
		'suppress_filters' => true,
	)
);

foreach ( $pages as $page ) {
	$language     = function_exists( 'pll_get_post_language' ) ? pll_get_post_language( $page->ID, 'slug' ) : '';
	$translations = function_exists( 'pll_get_post_translations' ) ? pll_get_post_translations( $page->ID ) : array();

	echo wp_json_encode(
		array(
			'id'           => $page->ID,
			'language'     => $language,
			'title'        => $page->post_title,
			'slug'         => $page->post_name,
			'template'     => get_page_template_slug( $page->ID ),
			'parent'       => $page->post_parent,
			'content_size' => strlen( $page->post_content ),
			'headings'     => preg_match_all( '/<h[1-6]\b/i', $page->post_content ),
			'images'       => preg_match_all( '/<img\b/i', $page->post_content ),
			'links'        => preg_match_all( '/<a\b/i', $page->post_content ),
			'translations' => $translations,
		),
		JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE
	) . PHP_EOL;
}
