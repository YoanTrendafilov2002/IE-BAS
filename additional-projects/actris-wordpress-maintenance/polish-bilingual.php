<?php

require __DIR__ . '/site/wp-load.php';

function actris_wrap_content( $post_id, $class_name ) {
	$content = get_post_field( 'post_content', $post_id );
	if ( false === strpos( $content, $class_name ) ) {
		wp_update_post(
			wp_slash(
				array(
					'ID'           => $post_id,
					'post_content' => '<div class="' . esc_attr( $class_name ) . '">' . $content . '</div>',
				)
			)
		);
	}
}

actris_wrap_content( 527, 'actris-resource-list' );
actris_wrap_content( 528, 'actris-resource-list' );

$home_bg = <<<'HTML'
<div class="actris-intro">
<p class="actris-kicker"><strong>ACTRIS-BG</strong></p>
<p class="actris-lead"><strong>Научноизследователска инфраструктура за наблюдение на атмосферните аерозоли, облаци и газови замърсители, интегрирана в рамките на паневропейската инфраструктура ACTRIS</strong></p>

<p><a href="https://www.actris.eu/" target="_blank" rel="noopener">ACTRIS</a> (Aerosol, Clouds, and Trace Gases Research Infrastructure) е водеща европейска научноизследователска инфраструктура, посветена на наблюденията и характеризирането на краткоживеещи компоненти на атмосферния въздух — аерозоли, облаци и газови замърсители — и техните взаимодействия. Като паневропейска разпределена изследователска инфраструктура, ACTRIS предоставя отворен достъп до висококачествени данни, модерна научна апаратура и специализирани услуги, подпомагащи авангардни изследвания в областта на атмосферата и климата.</p>

<p>ACTRIS-BG е българското звено на Европейския научноизследователски консорциум <a href="https://www.actris.eu/" target="_blank" rel="noopener">ACTRIS ERIC</a>.</p>

<p>ACTRIS-BG е обект от Националната пътна карта за научна инфраструктура 2017–2023 г. и от актуализираната Национална пътна карта за научна инфраструктура 2020–2027 г., подкрепен финансово от Министерството на образованието и науката с договори D01-151/2018, D01-269/2019, D01-407/2020, D01-299/2021, D01-185/2022, D01-350/2023, D01-365/2023, D01-131/2025 и D01-137/2025.</p>
</div>
HTML;

$contacts_bg = <<<'HTML'
<div class="actris-contacts">
<h2>Координатор</h2>
<p><strong>Институт за ядрени изследвания и ядрена енергетика към Българската академия на науките</strong></p>

<h3>Ръководител на ACTRIS-BG</h3>
<p>проф. д-р Димитър Тонев<br>
<a href="mailto:dimitar.tonev@inrne.bas.bg">dimitar.tonev@inrne.bas.bg</a><br>
бул. „Цариградско шосе“ 72<br>
1784 София, България</p>

<h3>Базова екологична обсерватория Мусала</h3>
<p>доц. д-р Христо Ангелов<br>
<a href="mailto:hangelov@inrne.bas.bg">hangelov@inrne.bas.bg</a><br>
Институт за ядрени изследвания и ядрена енергетика<br>
бул. „Цариградско шосе“ 72<br>
1784 София, България</p>

<h3>Национално контактно лице</h3>
<p>гл. ас. д-р Нина Николова<br>
<a href="mailto:nikol@inrne.bas.bg">nikol@inrne.bas.bg</a><br>
Базова екологична обсерватория Мусала<br>
Институт за ядрени изследвания и ядрена енергетика<br>
бул. „Цариградско шосе“ 72<br>
1784 София, България</p>

<h3>Лаборатория „Лазерна локация“</h3>
<p>доц. д-р Таня Драйшу<br>
<a href="mailto:tanjad@ie.bas.bg">tanjad@ie.bas.bg</a><br>
Институт по електроника<br>
бул. „Цариградско шосе“ 72<br>
1784 София, България</p>
</div>
HTML;

wp_update_post( wp_slash( array( 'ID' => 524, 'post_content' => $home_bg ) ) );
wp_update_post( wp_slash( array( 'ID' => 308, 'post_content' => $contacts_bg ) ) );

$widgets = get_option( 'widget_text', array() );
if ( isset( $widgets[4]['text'] ) ) {
	$widgets[4]['text'] = str_replace(
		'http://127.0.0.1:8099/privacy-policy/',
		get_permalink( 300 ),
		$widgets[4]['text']
	);
	update_option( 'widget_text', $widgets );
}

echo "Bilingual presentation polished.\n";
