import { epochAgeHours, validateEarthcareOmm, type OmmRecord } from '@/lib/omm';

const SOURCE_URL = 'https://celestrak.org/NORAD/elements/gp.php?CATNR=59908&FORMAT=JSON';
const FALLBACK: OmmRecord = {
  OBJECT_NAME: 'EARTHCARE', OBJECT_ID: '2024-101A', EPOCH: '2026-08-26T02:32:36.501792Z',
  MEAN_MOTION: 15.57128415, ECCENTRICITY: 0.00015528, INCLINATION: 97.059,
  RA_OF_ASC_NODE: 3.9361, ARG_OF_PERICENTER: 100.0223, MEAN_ANOMALY: 260.1209,
  EPHEMERIS_TYPE: 0, CLASSIFICATION_TYPE: 'U', NORAD_CAT_ID: 59908,
  ELEMENT_SET_NO: 999, REV_AT_EPOCH: 12744, BSTAR: 0.00014465799,
  MEAN_MOTION_DOT: 0.0001039, MEAN_MOTION_DDOT: 0,
};

export async function GET() {
  let omm = FALLBACK;
  let source = 'Bundled last-known OMM';
  let usingFallback = true;
  try {
    const response = await fetch(SOURCE_URL, { headers: { 'User-Agent': 'EarthCARE-Orbit-Tracker/2.0' } });
    if (!response.ok) throw new Error(`CelesTrak returned ${response.status}`);
    const payload = await response.json() as unknown;
    if (!Array.isArray(payload) || payload.length !== 1) throw new Error('Expected one EarthCARE OMM record');
    omm = validateEarthcareOmm(payload[0]);
    source = 'CelesTrak current GP / CCSDS OMM';
    usingFallback = false;
  } catch { /* The timestamped fallback is disclosed and automatically becomes stale. */ }

  const fetchedAt = new Date().toISOString();
  return Response.json({
    name: omm.OBJECT_NAME,
    catalogId: omm.NORAD_CAT_ID,
    omm,
    source,
    sourceUrl: SOURCE_URL,
    fetchedAt,
    epoch: omm.EPOCH,
    ageHours: epochAgeHours(omm.EPOCH),
    elementSetNo: omm.ELEMENT_SET_NO,
    revAtEpoch: omm.REV_AT_EPOCH,
    usingFallback,
  }, {
    headers: { 'Cache-Control': usingFallback ? 'no-store' : 'public, max-age=300, s-maxage=900, stale-while-revalidate=3600' },
  });
}
