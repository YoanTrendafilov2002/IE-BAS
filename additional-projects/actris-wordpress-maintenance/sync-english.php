<?php

require __DIR__ . '/site/wp-load.php';

if ( ! function_exists( 'pll_set_post_language' ) ) {
	throw new RuntimeException( 'Polylang is not active.' );
}

function actris_upsert_english_page( $english_id, $bulgarian_id, $title, $slug, $content, $parent = 0 ) {
	$source = get_post( $bulgarian_id );
	if ( ! $english_id && function_exists( 'pll_get_post' ) ) {
		$english_id = (int) pll_get_post( $bulgarian_id, 'en' );
	}

	$data   = array(
		'post_type'    => 'page',
		'post_status'  => 'publish',
		'post_title'   => $title,
		'post_name'    => $slug,
		'post_content' => $content,
		'post_excerpt' => '',
		'post_parent'  => $parent,
		'menu_order'   => $source ? $source->menu_order : 0,
	);

	if ( $english_id ) {
		delete_post_meta( $english_id, '_wp_page_template' );
		$data['ID'] = $english_id;
		$result     = wp_update_post( wp_slash( $data ), true );
	} else {
		$result = wp_insert_post( wp_slash( $data ), true );
	}

	if ( is_wp_error( $result ) ) {
		throw new RuntimeException( $result->get_error_message() );
	}

	$template = get_page_template_slug( $bulgarian_id );
	if ( $template ) {
		update_post_meta( $result, '_wp_page_template', $template );
	} else {
		delete_post_meta( $result, '_wp_page_template' );
	}

	pll_set_post_language( $bulgarian_id, 'bg' );
	pll_set_post_language( $result, 'en' );
	pll_save_post_translations(
		array(
			'bg' => $bulgarian_id,
			'en' => $result,
		)
	);

	return (int) $result;
}

$home = <<<'HTML'
<div class="actris-intro">
<p class="actris-kicker"><strong>ACTRIS-BG</strong></p>
<p class="actris-lead"><strong>Research Infrastructure for the Observation of Atmospheric Aerosols, Clouds and Trace Gases, integrated within the pan-European ACTRIS infrastructure</strong></p>

<p><a href="https://www.actris.eu/" target="_blank" rel="noopener">ACTRIS</a> (Aerosol, Clouds and Trace Gases Research Infrastructure) is a leading European research infrastructure dedicated to observing and characterising short-lived atmospheric components — aerosols, clouds and trace gases — and their interactions. As a distributed pan-European research infrastructure, ACTRIS provides open access to high-quality data, advanced scientific instruments and specialised services that support cutting-edge atmospheric and climate research.</p>

<p>ACTRIS-BG is the Bulgarian national node of the European Research Infrastructure Consortium <a href="https://www.actris.eu/" target="_blank" rel="noopener">ACTRIS ERIC</a>.</p>

<p>ACTRIS-BG is included in Bulgaria's National Roadmap for Research Infrastructure 2017–2023 and its updated 2020–2027 edition. It is financially supported by the Ministry of Education and Science under contracts D01-151/2018, D01-269/2019, D01-407/2020, D01-299/2021, D01-185/2022, D01-350/2023, D01-365/2023, D01-131/2025 and D01-137/2025.</p>
</div>
HTML;

$about = <<<'HTML'
<p>Atmospheric processes are increasingly central to societal and environmental challenges including air quality, health, sustainability and climate change. ACTRIS-BG — the Research Infrastructure for the Observation of Atmospheric Aerosols, Clouds and Trace Gases, integrated within the pan-European ACTRIS infrastructure — is included in Bulgaria's National Roadmap for Research Infrastructure 2017–2023 and the updated <a href="https://naukamon.eu//wp-content/uploads/2020/12/RoadMap_BG2020-2027_sm.pdf" target="_blank" rel="noopener">2020–2027 Roadmap</a>.</p>

<p>The ACTRIS-BG partners are the <a href="https://www.inrne.bas.bg/" target="_blank" rel="noopener">Institute for Nuclear Research and Nuclear Energy (INRNE)</a> and the <a href="https://ie-bas.org/" target="_blank" rel="noopener">Institute of Electronics (IE)</a> at the Bulgarian Academy of Sciences. The two institutes have signed a cooperation agreement establishing the Bulgarian ACTRIS-BG consortium.</p>

<p>Both institutes have participated in <a href="https://www.actris.eu/" target="_blank" rel="noopener">ACTRIS</a> since its establishment in 2011. ACTRIS joined the ESFRI Roadmap in 2016 and received Landmark status in the 2021 update. On 25 April 2023, the European Commission announced the establishment of ACTRIS ERIC, with Bulgaria among its founding member countries.</p>
HTML;

$stations = <<<'HTML'
<div class="actris-stations-map">
<img class="aligncenter size-large wp-image-619" src="http://127.0.0.1:8099/wp-content/uploads/2026/05/Bulgaria-locator-template.svg_-1024x668.png" alt="ACTRIS-BG observational stations in Bulgaria" width="1024" height="668" />
</div>
HTML;

$data = <<<'HTML'
<p>ACTRIS data are freely available to everyone.</p>

<p><a href="https://dc.actris.nilu.no/" target="_blank" rel="noopener">The ACTRIS Data Portal</a> provides tools to search, analyse and download atmospheric composition data from multiple archives. The datasets originate from the ACTRIS infrastructure network and other relevant networks, providing open access to atmospheric observations.</p>

<p>Atmospheric data measured at Mount Moussala by the Basic Environmental Observatory of the Institute for Nuclear Research and Nuclear Energy are available on the <a href="http://beo-db.inrne.bas.bg/moussala/mainnew.php?action=atmosphere" target="_blank" rel="noopener">BEO Moussala data page</a>.</p>

<p>Data from the lidar systems operated by the Institute of Electronics are available on the <a href="http://www.ie-bas.org/Departments/LidarData/Quicklooks.htm" target="_blank" rel="noopener">Laser Radars Laboratory page</a>.</p>
HTML;

$documents = <<<'HTML'
<div class="actris-data-page">
<p><a href="https://www.actris.eu/" target="_blank" rel="noopener">ACTRIS ERIC</a> provides open access to high-quality data, advanced research instrumentation and a broad range of specialised services. These resources support cutting-edge atmospheric and climate research and the development of sustainable responses to environmental challenges such as climate change, poor air quality and long-range pollutant transport.</p>

<p><a href="https://dc.actris.nilu.no/" target="_blank" rel="noopener">The ACTRIS Data Portal</a> enables users to search, analyse and download atmospheric composition data from multiple archives. The datasets originate from ACTRIS infrastructure activities and other relevant networks.</p>

<p>The complete ACTRIS data policy is available here:</p>

<p><a href="https://www.actris.eu/topical-centre/data-centre/data-policy" target="_blank" rel="noopener">ACTRIS Data Policy</a></p>
</div>
HTML;

$beo_data = <<<'HTML'
<div class="actris-resource-list">
<h2>Real-time aerosol data</h2>
<ul>
<li><a href="https://gml.noaa.gov/aero/net/stations.html" target="_blank" rel="noopener">NOAA Global Monitoring Laboratory aerosol network, Boulder, USA</a></li>
<li><a href="https://dc.actris.nilu.no/" target="_blank" rel="noopener">ACTRIS Data Centre for aerosol measurements</a></li>
</ul>

<h2>Continuous cosmic-ray observations since 2008</h2>
<ul>
<li><a href="https://crd.yerphi.am/Moussala_SEVAN_Data" target="_blank" rel="noopener">SEVAN — Space Environmental Viewing and Analysis Network, A. I. Alikhanyan National Laboratory, Armenia</a></li>
</ul>

<h2>Continuous observations of persistent organic pollutants since 2009</h2>
<ul>
<li>MONET-EU — European Persistent Organic Pollutants Network</li>
<li><a href="https://www.genasis.cz/index-en.php" target="_blank" rel="noopener">RECETOX Centre at Masaryk University</a></li>
</ul>
</div>
HTML;

$sofia_data = <<<'HTML'
<p>The Sofia (IE-BAS) station performs continuous remote and in-situ monitoring of the atmosphere above Sofia. It provides openly accessible information on air quality and on transported aerosol layers of different origins.</p>

<p>Continuous photometric and ceilometer measurements are transmitted in real time to:</p>
<ul>
<li><a href="https://aeronet.gsfc.nasa.gov/" target="_blank" rel="noopener">AERONET — the programme established by NASA and PHOTONS, France</a></li>
<li><a href="https://e-profile.eu/" target="_blank" rel="noopener">E-PROFILE — a programme of the European Meteorological Services Network, EUMETNET</a></li>
</ul>

<p>Regular lidar measurements are submitted to the European aerosol lidar network:</p>
<ul>
<li><a href="https://earlinet.eu/" target="_blank" rel="noopener">EARLINET — European Aerosol Research Lidar Network</a></li>
</ul>

<p>These datasets are also freely available through the <a href="https://dc.actris.nilu.no/" target="_blank" rel="noopener">ACTRIS ERIC Data Portal</a>.</p>

<p>The station also operates automatic meteorological instruments and an aerosol spectrometer for fine particulate matter. Meteorological parameters and PM1, PM2.5, PM4 and PM10 mass concentrations are measured every minute. Hourly PM2.5 and PM10 values are published in real time by the <a href="https://ie-bas.org/" target="_blank" rel="noopener">Institute of Electronics</a>. Current meteorological data are available at <a href="https://meter.ac/gs/meteo/M21/history.html" target="_blank" rel="noopener">meter.ac</a>.</p>
HTML;

$contacts = <<<'HTML'
<div class="actris-contacts">
<h2>Coordinator</h2>
<p><strong>Institute for Nuclear Research and Nuclear Energy, Bulgarian Academy of Sciences</strong></p>

<h3>Head of ACTRIS-BG</h3>
<p>Prof. Dr. Dimitar Tonev<br>
<a href="mailto:dimitar.tonev@inrne.bas.bg">dimitar.tonev@inrne.bas.bg</a><br>
72 Tsarigradsko Shose Blvd.<br>
1784 Sofia, Bulgaria</p>

<h3>Basic Environmental Observatory Moussala</h3>
<p>Assoc. Prof. Dr. Christo Angelov<br>
<a href="mailto:hangelov@inrne.bas.bg">hangelov@inrne.bas.bg</a><br>
Institute for Nuclear Research and Nuclear Energy<br>
72 Tsarigradsko Shose Blvd.<br>
1784 Sofia, Bulgaria</p>

<h3>National Contact Person</h3>
<p>Assist. Prof. Dr. Nina Nikolova<br>
<a href="mailto:nikol@inrne.bas.bg">nikol@inrne.bas.bg</a><br>
Basic Environmental Observatory Moussala<br>
Institute for Nuclear Research and Nuclear Energy<br>
72 Tsarigradsko Shose Blvd.<br>
1784 Sofia, Bulgaria</p>

<h3>Laser Radars Laboratory</h3>
<p>Assoc. Prof. Dr. Tanja Dreischuh<br>
<a href="mailto:tanjad@ie.bas.bg">tanjad@ie.bas.bg</a><br>
Institute of Electronics<br>
72 Tsarigradsko Shose Blvd.<br>
1784 Sofia, Bulgaria</p>
</div>
HTML;

$publication_content = get_post_field( 'post_content', 156 );
$publication_content = str_replace(
	array(
		'Дни на отворените врати',
		'С цел популяризирането на изследователската дейност на БЕО Мусала в последните три години през лятото бяха проведени Дни на отворени врати в рамките на кампанията "БАН представя своите институти".',
		'В тези дни имаше свободен достъп на желаещите да се запознаят с работата на екологичната обсерватория.',
		'БЕО Мусала - отворени врати 2018 г.',
		'Дни на отворени врати 2018',
		'Публикации на БЕО Мусала - Институт за ядрени изследвания и ядрена енергетика - БАН',
		'Публикации на Лаборатория "Лазерна локация" - Институт по електроника - БАН',
		' – постер',
	),
	array(
		'Open Days',
		'To present the research carried out at BEO Moussala, Open Days were organised during the summer as part of the Bulgarian Academy of Sciences campaign “BAS Presents Its Institutes”.',
		'Visitors were given open access and an opportunity to learn about the work of the environmental observatory.',
		'BEO Moussala Open Day 2018',
		'Open Day 2018',
		'Publications of BEO Moussala — Institute for Nuclear Research and Nuclear Energy — BAS',
		'Publications of the Laser Radars Laboratory — Institute of Electronics — BAS',
		' — poster',
	),
	$publication_content
);

$beo_publications = str_replace(
	'Публикации на БЕО Мусала – Институт за ядрени изследвания и ядрена енергетика – БАН',
	'Publications of BEO Moussala — Institute for Nuclear Research and Nuclear Energy — BAS',
	get_post_field( 'post_content', 582 )
);

$sofia_publications = str_replace(
	'Публикации - Лаборатория Лазерна Локация – Институт по Електроника – БАН',
	'Publications — Laser Radars Laboratory — Institute of Electronics — BAS',
	get_post_field( 'post_content', 584 )
);

$ids = array();
$ids['home']         = actris_upsert_english_page( 0, 524, 'Home', 'home-en', $home );
$ids['about']        = actris_upsert_english_page( 77, 614, 'About Us', 'about-us', $about );
$ids['stations']     = actris_upsert_english_page( 0, 607, 'Observational Stations', 'observational-stations', $stations );
$ids['data']         = actris_upsert_english_page( 336, 153, 'Data and Services', 'data-and-services', $data );
$ids['documents']    = actris_upsert_english_page( 0, 526, 'Documents', 'documents', $documents, $ids['data'] );
$ids['beo_data']     = actris_upsert_english_page( 0, 527, 'BEO Moussala', 'beo-moussala-data', $beo_data, $ids['data'] );
$ids['sofia_data']   = actris_upsert_english_page( 0, 528, 'Sofia (IE-BAS) Station', 'sofia-ie-bas-data', $sofia_data, $ids['data'] );
$ids['publications'] = actris_upsert_english_page( 330, 156, 'Publications', 'publications', $publication_content );
$ids['beo_pubs']     = actris_upsert_english_page( 0, 582, 'BEO Moussala', 'beo-moussala-publications', $beo_publications, $ids['publications'] );
$ids['sofia_pubs']   = actris_upsert_english_page( 0, 584, 'Sofia (IE-BAS)', 'sofia-ie-bas-publications', $sofia_publications, $ids['publications'] );
$ids['contacts']     = actris_upsert_english_page( 316, 308, 'Contacts', 'contacts', $contacts );

wp_update_post( array( 'ID' => 93, 'post_parent' => $ids['stations'] ) );
wp_update_post( array( 'ID' => 104, 'post_parent' => $ids['stations'] ) );

$news_category = term_exists( 'News and Events', 'category' );
if ( ! $news_category ) {
	$news_category = wp_insert_term( 'News and Events', 'category', array( 'slug' => 'news-and-events' ) );
}
$news_category_id = is_array( $news_category ) ? (int) $news_category['term_id'] : (int) $news_category;
pll_set_term_language( 1, 'bg' );
pll_set_term_language( $news_category_id, 'en' );
pll_save_term_translations( array( 'bg' => 1, 'en' => $news_category_id ) );

$news_content = <<<'HTML'
<p>ACTRIS-BG is included in the updated <a href="https://mon.bg/upload/25680/RoadMap_BG2020-2027_sm.pdf" target="_blank" rel="noopener">National Roadmap for Research Infrastructure 2020–2027</a>. Institutional support from the Ministry of Education and Science and its commitment to financial assistance continue.</p>
HTML;
$news_id = wp_insert_post(
	wp_slash(
		array(
			'post_type'     => 'post',
			'post_status'   => 'publish',
			'post_title'    => 'Institutional Support for ACTRIS-BG Continues',
			'post_name'     => 'institutional-support-for-actris-bg-continues',
			'post_content'  => $news_content,
			'post_date'     => get_post_field( 'post_date', 456 ),
			'post_date_gmt' => get_post_field( 'post_date_gmt', 456 ),
		)
	),
	true
);
if ( ! is_wp_error( $news_id ) ) {
	pll_set_post_language( 456, 'bg' );
	pll_set_post_language( $news_id, 'en' );
	pll_save_post_translations( array( 'bg' => 456, 'en' => $news_id ) );
	wp_set_post_categories( $news_id, array( $news_category_id ) );
}

$menu_id = 11;
foreach ( wp_get_nav_menu_items( $menu_id ) as $item ) {
	if ( 43 !== (int) $item->ID ) {
		wp_delete_post( $item->ID, true );
	}
}

function actris_menu_page( $menu_id, $page_id, $title, $parent = 0 ) {
	return wp_update_nav_menu_item(
		$menu_id,
		0,
		array(
			'menu-item-object-id' => $page_id,
			'menu-item-object'    => 'page',
			'menu-item-type'      => 'post_type',
			'menu-item-title'     => $title,
			'menu-item-parent-id' => $parent,
			'menu-item-status'    => 'publish',
		)
	);
}

$menu_home     = actris_menu_page( $menu_id, $ids['home'], 'Home' );
$menu_about    = actris_menu_page( $menu_id, $ids['about'], 'About Us' );
$menu_stations = actris_menu_page( $menu_id, $ids['stations'], 'Observational Stations' );
actris_menu_page( $menu_id, 93, 'BEO Moussala', $menu_stations );
actris_menu_page( $menu_id, 104, 'Sofia (IE-BAS) Station', $menu_stations );
$menu_data = actris_menu_page( $menu_id, $ids['data'], 'Data and Services' );
actris_menu_page( $menu_id, $ids['documents'], 'Documents', $menu_data );
actris_menu_page( $menu_id, $ids['beo_data'], 'BEO Moussala', $menu_data );
actris_menu_page( $menu_id, $ids['sofia_data'], 'Sofia (IE-BAS) Station', $menu_data );
$menu_publications = actris_menu_page( $menu_id, $ids['publications'], 'Publications' );
actris_menu_page( $menu_id, $ids['beo_pubs'], 'BEO Moussala', $menu_publications );
actris_menu_page( $menu_id, $ids['sofia_pubs'], 'Sofia (IE-BAS)', $menu_publications );

wp_update_nav_menu_item(
	$menu_id,
	0,
	array(
		'menu-item-object-id' => $news_category_id,
		'menu-item-object'    => 'category',
		'menu-item-type'      => 'taxonomy',
		'menu-item-title'     => 'News and Events',
		'menu-item-status'    => 'publish',
	)
);
actris_menu_page( $menu_id, $ids['contacts'], 'Contacts' );

if ( get_post( 43 ) ) {
	wp_update_post( array( 'ID' => 43, 'menu_order' => 99 ) );
}

echo wp_json_encode( $ids, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
