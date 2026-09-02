export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.get('q')?.trim() ?? '';
  if (query.length < 3) return Response.json({ results: [] });
  try {
    const endpoint = new URL('https://nominatim.openstreetmap.org/search');
    endpoint.searchParams.set('format', 'jsonv2');
    endpoint.searchParams.set('limit', '6');
    endpoint.searchParams.set('q', query);
    const response = await fetch(endpoint, { headers: { 'User-Agent': 'EarthCARE-Orbit-Tracker/1.0', 'Accept-Language': 'en' } });
    if (!response.ok) return Response.json({ results: [], error: 'Geocoder unavailable' }, { status: 502 });
    const payload = await response.json() as Array<{ place_id: number; display_name: string; lat: string; lon: string; type: string }>;
    return Response.json({ results: payload.map((item) => ({ id: item.place_id, name: item.display_name, lat: Number(item.lat), lon: Number(item.lon), type: item.type })) }, { headers: { 'Cache-Control': 'public, max-age=300, s-maxage=86400' } });
  } catch {
    return Response.json({ results: [], error: 'Geocoder temporarily unavailable' }, { status: 503 });
  }
}
