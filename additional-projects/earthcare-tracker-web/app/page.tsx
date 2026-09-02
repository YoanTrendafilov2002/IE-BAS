'use client';

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { json2satrec, type SatRec } from '@/lib/satellite-core';
import { findLidarTargetEventsAsync, lidarFootprintAt, positionAt, surfaceDistanceKm, type GroundSite, type LidarTargetEvent } from '@/lib/orbit';
import { epochAgeHours, type OrbitDataPayload } from '@/lib/omm';

type GeocodeResult = { id: number; name: string; lat: number; lon: number; type: string };
type CalculationState = 'idle' | 'calculating' | 'complete' | 'error';

const MAX_PERIOD_DAYS = 90;

const defaultSite: GroundSite = {
  name: 'Academician Emil Djakov Institute of Electronics, BAS, Sofia',
  lat: 42.65389,
  lon: 23.38722,
  heightKm: 0.55,
};

function utcTime(date?: Date) { return date ? date.toISOString().slice(11, 19) : '--:--:--'; }
function dayLabel(date?: Date) { return date ? date.toISOString().slice(0, 10) : '---'; }
function eventDuration(event: LidarTargetEvent) { return ((event.exit.getTime() - event.entry.getTime()) / 1_000).toFixed(2); }
function csvCell(value: string | number | boolean) { return `"${String(value).replaceAll('"', '""')}"`; }
function utcInputValue(ms: number) { return new Date(ms).toISOString().slice(0, 16); }
function parseUtcInput(value: string) { return Date.parse(`${value}Z`); }
function periodLabel(hours: number) {
  if (hours >= 24 && Number.isInteger(hours / 24)) return `${hours / 24} d`;
  return `${hours.toFixed(hours < 1 ? 2 : 1).replace(/\.0$/, '')} h`;
}
async function fetchOrbitData() {
  const response = await fetch('/api/earthcare', { cache: 'no-store' });
  if (!response.ok) throw new Error(`Orbit service returned ${response.status}`);
  return response.json() as Promise<OrbitDataPayload>;
}

export default function Home() {
  const [nowMs, setNowMs] = useState(0);
  const [orbitData, setOrbitData] = useState<OrbitDataPayload | null>(null);
  const [orbitError, setOrbitError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [site, setSite] = useState<GroundSite>(defaultSite);
  const [targetRadiusKm, setTargetRadiusKm] = useState(100);
  const [query, setQuery] = useState('Institute of Electronics BAS, Sofia, Bulgaria');
  const [results, setResults] = useState<GeocodeResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchMessage, setSearchMessage] = useState('');
  const [periodStartText, setPeriodStartText] = useState('');
  const [periodEndText, setPeriodEndText] = useState('');
  const [predictionPeriod, setPredictionPeriod] = useState<{ startMs: number; endMs: number } | null>(null);
  const [periodMessage, setPeriodMessage] = useState('');
  const [periodError, setPeriodError] = useState('');
  const [targetEvents, setTargetEvents] = useState<LidarTargetEvent[]>([]);
  const [calculationState, setCalculationState] = useState<CalculationState>('idle');
  const [calculationProgress, setCalculationProgress] = useState(0);
  const [calculationError, setCalculationError] = useState('');

  useEffect(() => {
    const initialTick = window.requestAnimationFrame(() => {
      const initialMs = Math.floor(Date.now() / 60_000) * 60_000;
      setNowMs(initialMs);
      setPeriodStartText(utcInputValue(initialMs));
      setPeriodEndText(utcInputValue(initialMs + 72 * 3_600_000));
      setPredictionPeriod({ startMs: initialMs, endMs: initialMs + 72 * 3_600_000 });
    });
    const timer = window.setInterval(() => setNowMs(Date.now()), 1_000);
    return () => { window.cancelAnimationFrame(initialTick); window.clearInterval(timer); };
  }, []);

  async function refreshOrbitData() {
    setRefreshing(true);
    setOrbitError('');
    try {
      setOrbitData(await fetchOrbitData());
    } catch {
      setOrbitError('No validated orbital element set is available. Predictions are suspended.');
      setOrbitData(null);
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    fetchOrbitData().then((data) => { if (!cancelled) setOrbitData(data); }).catch(() => {
      if (!cancelled) setOrbitError('No validated orbital element set is available. Predictions are suspended.');
    });
    return () => { cancelled = true; };
  }, []);

  const satrec = useMemo<SatRec | null>(() => orbitData ? json2satrec(orbitData.omm) : null, [orbitData]);
  const position = useMemo(() => satrec && nowMs ? positionAt(satrec, new Date(nowMs)) : null, [satrec, nowMs]);
  const currentFootprint = useMemo(() => satrec && nowMs ? lidarFootprintAt(satrec, new Date(nowMs)) : null, [satrec, nowMs]);
  const currentTargetDistance = currentFootprint ? surfaceDistanceKm(currentFootprint.lat, currentFootprint.lon, site.lat, site.lon) : null;
  const elementAge = orbitData ? (nowMs ? epochAgeHours(orbitData.epoch, nowMs) : orbitData.ageHours) : null;
  const freshness = !orbitData ? 'unavailable' : elementAge !== null && (elementAge < -1 || elementAge > 120) ? 'stale' : orbitData.usingFallback ? 'fallback' : elementAge !== null && elementAge <= 48 ? 'current' : 'aging';
  const modelAvailable = Boolean(satrec);
  const periodHours = predictionPeriod ? (predictionPeriod.endMs - predictionPeriod.startMs) / 3_600_000 : 0;
  const periodEpochDistanceHours = orbitData && predictionPeriod ? Math.max(
    Math.abs(predictionPeriod.startMs - Date.parse(orbitData.epoch)),
    Math.abs(predictionPeriod.endMs - Date.parse(orbitData.epoch)),
  ) / 3_600_000 : null;
  const periodExtrapolated = periodEpochDistanceHours !== null && periodEpochDistanceHours > 120;

  useEffect(() => {
    if (!satrec || !predictionPeriod) {
      queueMicrotask(() => {
        setTargetEvents([]);
        setCalculationState('idle');
      });
      return;
    }

    let active = true;
    const controller = new AbortController();
    queueMicrotask(() => {
      if (!active) return;
      setCalculationState('calculating');
      setCalculationProgress(0);
      setCalculationError('');
    });
    void findLidarTargetEventsAsync(
      satrec,
      site,
      new Date(predictionPeriod.startMs),
      periodHours,
      targetRadiusKm,
      250,
      controller.signal,
      (progress) => {
        if (active) setCalculationProgress(progress);
      },
    ).then((events) => {
      if (!active) return;
      setTargetEvents(events);
      setCalculationProgress(1);
      setCalculationState('complete');
    }).catch(() => {
      if (!active) return;
      setTargetEvents([]);
      setCalculationError('The ATLID calculation could not be completed.');
      setCalculationState('error');
    });
    return () => {
      active = false;
      controller.abort();
    };
  }, [satrec, site, predictionPeriod, periodHours, targetRadiusKm]);

  const closestEvent = targetEvents.reduce<LidarTargetEvent | null>((best, event) => !best || event.minimumDistanceKm < best.minimumDistanceKm ? event : best, null);

  function setQuickPeriod(hours: number) {
    const startMs = Math.floor(Date.now() / 60_000) * 60_000;
    const endMs = startMs + hours * 3_600_000;
    setPeriodStartText(utcInputValue(startMs));
    setPeriodEndText(utcInputValue(endMs));
    setPredictionPeriod({ startMs, endMs });
    setPeriodError('');
    setPeriodMessage(`Calculated the next ${periodLabel(hours)} from the current UTC minute.`);
  }

  function calculatePeriod(event: FormEvent) {
    event.preventDefault();
    const startMs = parseUtcInput(periodStartText);
    const endMs = parseUtcInput(periodEndText);
    if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) {
      setPeriodError('Enter a valid UTC start and end.');
      return;
    }
    const durationMs = endMs - startMs;
    if (durationMs < 60_000) {
      setPeriodError('The end must be at least one minute after the start.');
      return;
    }
    if (durationMs > MAX_PERIOD_DAYS * 24 * 3_600_000) {
      setPeriodError(`The maximum calculation period is ${MAX_PERIOD_DAYS} days.`);
      return;
    }
    setPeriodError('');
    setPredictionPeriod({ startMs, endMs });
    setPeriodMessage('Period accepted. Every listed ATLID target event overlaps this UTC window.');
  }

  function exportTargetEvents() {
    if (!orbitData || !predictionPeriod || !targetEvents.length) return;
    const headers = ['object_name', 'norad_catalog_id', 'omm_epoch_utc', 'element_age_hours_at_export', 'source', 'period_start_utc', 'period_end_utc', 'period_duration_hours', 'maximum_period_epoch_distance_hours', 'period_exceeds_120h_epoch_window', 'target_name', 'target_lat_deg', 'target_lon_deg', 'target_radius_km', 'atlid_off_nadir_aft_deg', 'radius_entry_utc', 'closest_approach_utc', 'radius_exit_utc', 'inside_radius_seconds', 'minimum_target_distance_km', 'footprint_lat_at_closest_deg', 'footprint_lon_at_closest_deg', 'satellite_subpoint_lat_deg', 'satellite_subpoint_lon_deg', 'event_numerical_resolution_s'];
    const rows = targetEvents.map((event) => [orbitData.name, orbitData.catalogId, orbitData.epoch, elementAge?.toFixed(3) ?? '', orbitData.source, new Date(predictionPeriod.startMs).toISOString(), new Date(predictionPeriod.endMs).toISOString(), periodHours.toFixed(6), periodEpochDistanceHours?.toFixed(3) ?? '', periodExtrapolated, site.name, site.lat.toFixed(7), site.lon.toFixed(7), targetRadiusKm.toFixed(3), 3, event.entry.toISOString(), event.closest.toISOString(), event.exit.toISOString(), eventDuration(event), event.minimumDistanceKm.toFixed(6), event.footprintLat.toFixed(7), event.footprintLon.toFixed(7), event.subpointLat.toFixed(7), event.subpointLon.toFixed(7), event.numericalResolutionSeconds]);
    const csv = [headers, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `earthcare-atlid-target-events-${dayLabel(new Date(predictionPeriod.startMs))}-to-${dayLabel(new Date(predictionPeriod.endMs))}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function searchInstitute(event: FormEvent) {
    event.preventDefault();
    if (query.trim().length < 3) return;
    setSearching(true);
    setSearchMessage('');
    setResults([]);
    try {
      const response = await fetch(`/api/geocode?q=${encodeURIComponent(query)}`);
      const payload = await response.json() as { results?: GeocodeResult[] };
      const found = payload.results ?? [];
      setResults(found);
      setSearchMessage(found.length ? `${found.length} locations found.` : 'No exact match. Include the institute, city, and country.');
    } catch {
      setSearchMessage('Location search is temporarily unavailable.');
    } finally {
      setSearching(false);
    }
  }

  function selectLocation(result: GeocodeResult) {
    setSite({ name: result.name, lat: result.lat, lon: result.lon, heightKm: 0 });
    setResults([]);
    setSearchMessage('Lidar target updated. The active period has been recalculated.');
  }

  return (
    <main className="console-shell">
      <header className="console-header">
        <div><span className="product-code">EC / ATLID</span><strong>EarthCARE lidar target data</strong></div>
        <span className={`status ${freshness}`}>{freshness.toUpperCase()} OMM</span>
        <time>{nowMs ? new Date(nowMs).toISOString() : 'Synchronising UTC…'}</time>
      </header>

      <div className="console-body">
        <section className="intro">
          <div>
            <p>EARTHCARE × INSTITUTE OF ELECTRONICS, BULGARIAN ACADEMY OF SCIENCES</p>
            <h1>ATLID target prediction data</h1>
            <span>Validated CCSDS OMM → WGS-72 SGP4 → 3° aft beam → WGS-84 surface intercept → target distance in kilometres.</span>
          </div>
          <div className="primary-actions">
            <button onClick={() => void refreshOrbitData()} disabled={refreshing}>{refreshing ? 'REFRESHING…' : 'REFRESH OMM'}</button>
            <button className="primary" onClick={exportTargetEvents} disabled={calculationState !== 'complete' || !targetEvents.length}>EXPORT {targetEvents.length || ''} CSV ROWS</button>
          </div>
        </section>

        <div className={`data-gate ${freshness}`}>
          <b>DATA GATE</b>
          <span>{orbitData ? `${modelAvailable ? freshness === 'stale' ? 'CAUTION' : 'OPEN' : 'CLOSED'} · ${orbitData.source} · fetched ${orbitData.fetchedAt} · epoch age ${elementAge?.toFixed(2)} h` : orbitError || 'Acquiring a validated EarthCARE OMM record.'}</span>
          <small>Validated OMM data remains calculable at any epoch distance; values beyond ±120 h are shown with an extrapolation warning and elevated uncertainty. Modelled ATLID geometry only.</small>
        </div>

        <section className="data-grid two-column">
          <article className="data-panel">
            <div className="panel-title"><h2>Orbit record</h2><span>CCSDS OMM</span></div>
            <dl className="key-values">
              <div><dt>Object</dt><dd>{orbitData ? `${orbitData.omm.OBJECT_NAME} / ${orbitData.omm.OBJECT_ID}` : '—'}</dd></div>
              <div><dt>NORAD catalog ID</dt><dd>{orbitData?.catalogId ?? '—'}</dd></div>
              <div><dt>Epoch UTC</dt><dd>{orbitData?.epoch ?? '—'}</dd></div>
              <div><dt>Element set</dt><dd>{orbitData?.elementSetNo ?? '—'}</dd></div>
              <div><dt>Revolution at epoch</dt><dd>{orbitData?.revAtEpoch ?? '—'}</dd></div>
              <div><dt>Mean motion</dt><dd>{orbitData ? `${orbitData.omm.MEAN_MOTION.toFixed(8)} rev/day` : '—'}</dd></div>
              <div><dt>Inclination</dt><dd>{orbitData ? `${orbitData.omm.INCLINATION.toFixed(6)}°` : '—'}</dd></div>
              <div><dt>Eccentricity</dt><dd>{orbitData?.omm.ECCENTRICITY ?? '—'}</dd></div>
              <div><dt>RAAN</dt><dd>{orbitData ? `${orbitData.omm.RA_OF_ASC_NODE.toFixed(6)}°` : '—'}</dd></div>
              <div><dt>Argument of perigee</dt><dd>{orbitData ? `${orbitData.omm.ARG_OF_PERICENTER.toFixed(6)}°` : '—'}</dd></div>
              <div><dt>Mean anomaly</dt><dd>{orbitData ? `${orbitData.omm.MEAN_ANOMALY.toFixed(6)}°` : '—'}</dd></div>
              <div><dt>B*</dt><dd>{orbitData?.omm.BSTAR ?? '—'}</dd></div>
            </dl>
            {orbitData && <a className="source-link" href={orbitData.sourceUrl} target="_blank" rel="noreferrer">OPEN SOURCE RECORD ↗</a>}
          </article>

          <article className="data-panel">
            <div className="panel-title"><h2>Current ATLID geometry</h2><span>{nowMs ? utcTime(new Date(nowMs)) : '—'} UTC</span></div>
            <dl className="key-values">
              <div><dt>Satellite latitude</dt><dd>{position ? `${position.lat.toFixed(6)}°` : '—'}</dd></div>
              <div><dt>Satellite longitude</dt><dd>{position ? `${position.lon.toFixed(6)}°` : '—'}</dd></div>
              <div><dt>Satellite altitude</dt><dd>{position ? `${position.alt.toFixed(3)} km` : '—'}</dd></div>
              <div><dt>Inertial speed</dt><dd>{position ? `${position.velocity.toFixed(6)} km/s` : '—'}</dd></div>
              <div><dt>ATLID footprint latitude</dt><dd>{currentFootprint ? `${currentFootprint.lat.toFixed(6)}°` : '—'}</dd></div>
              <div><dt>ATLID footprint longitude</dt><dd>{currentFootprint ? `${currentFootprint.lon.toFixed(6)}°` : '—'}</dd></div>
              <div><dt>Aft offset from subpoint</dt><dd>{currentFootprint ? `${currentFootprint.aftOffsetKm.toFixed(3)} km` : '—'}</dd></div>
              <div><dt>Distance to target</dt><dd>{currentTargetDistance !== null ? `${currentTargetDistance.toFixed(3)} km` : '—'}</dd></div>
              <div><dt>Inside target radius</dt><dd>{currentTargetDistance !== null ? (currentTargetDistance <= targetRadiusKm ? 'YES' : 'NO') : '—'}</dd></div>
              <div><dt>Beam pointing</dt><dd>3.000° aft of nadir</dd></div>
              <div><dt>Surface ellipsoid</dt><dd>WGS-84</dd></div>
              <div><dt>Event refinement</dt><dd>≤0.01 s</dd></div>
            </dl>
          </article>
        </section>

        <section className="data-panel observer-panel">
          <div className="panel-title"><h2>Lidar target configuration</h2><span>Geodetic point + radius</span></div>
          <div className="observer-data">
            <div className="observer-current"><b>{site.name}</b><span>Target latitude {site.lat.toFixed(7)}° · longitude {site.lon.toFixed(7)}°</span></div>
            <form className="search-form" onSubmit={searchInstitute}><label htmlFor="station-search">TARGET SEARCH</label><div><input id="station-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Institute, city, country" /><button disabled={searching}>{searching ? 'SEARCHING…' : 'SEARCH'}</button></div><small>{searchMessage || 'The selected location is treated as the centre of a circular surface target.'}</small></form>
            <div className="radius-control"><label htmlFor="target-radius">TARGET RADIUS (KM)</label><input id="target-radius" type="number" min="1" max="500" step="0.1" value={targetRadiusKm} onChange={(event) => setTargetRadiusKm(Math.min(500, Math.max(1, Number(event.target.value) || 1)))} /><div><button type="button" onClick={() => setTargetRadiusKm(1)}>1 KM</button><button type="button" onClick={() => setTargetRadiusKm(10)}>10 KM</button><button type="button" onClick={() => setTargetRadiusKm(50)}>50 KM</button><button type="button" onClick={() => setTargetRadiusKm(100)}>100 KM</button></div><small>An event exists when the modelled ATLID surface footprint is within this radius. Default 100 km represents a broad regional atmospheric target.</small></div>
          </div>
          {results.length > 0 && <div className="search-results">{results.map((result) => <button key={result.id} onClick={() => selectLocation(result)}><span>{result.name}</span><b>{result.lat.toFixed(6)}, {result.lon.toFixed(6)}</b></button>)}</div>}
        </section>

        <section className="data-panel period-panel">
          <div className="panel-title"><h2>Prediction interval</h2><span>UTC · 1 min to {MAX_PERIOD_DAYS} d</span></div>
          <form className="period-form" onSubmit={calculatePeriod}>
            <label htmlFor="period-start">START UTC<input id="period-start" type="datetime-local" step="60" value={periodStartText} onChange={(event) => setPeriodStartText(event.target.value)} required /></label>
            <label htmlFor="period-end">END UTC<input id="period-end" type="datetime-local" step="60" value={periodEndText} onChange={(event) => setPeriodEndText(event.target.value)} required /></label>
            <button type="submit" className="primary">CALCULATE</button>
            <div className="quick-periods"><button type="button" onClick={() => setQuickPeriod(24)}>NEXT 24 H</button><button type="button" onClick={() => setQuickPeriod(72)}>NEXT 72 H</button><button type="button" onClick={() => setQuickPeriod(168)}>NEXT 7 D</button><button type="button" onClick={() => setQuickPeriod(720)}>NEXT 30 D</button><button type="button" onClick={() => setQuickPeriod(1440)}>NEXT 60 D</button></div>
          </form>
          <div className={`period-readout ${periodError ? 'error' : periodExtrapolated ? 'warning' : ''}`}>
            <b>{periodError ? 'INPUT NOT APPLIED' : periodExtrapolated ? 'EXTRAPOLATION WARNING' : 'ACTIVE INTERVAL'}</b>
            <span>{predictionPeriod ? `${new Date(predictionPeriod.startMs).toISOString()} → ${new Date(predictionPeriod.endMs).toISOString()}` : 'Initialising…'}</span>
            <small>{periodError ? `${periodError} Results below still use the accepted interval shown above.` : periodExtrapolated ? `Duration ${periodLabel(periodHours)} · maximum distance from OMM epoch is ${periodEpochDistanceHours?.toFixed(2)} h. Results remain visible but uncertainty is elevated.` : periodMessage || `Duration ${periodLabel(periodHours)} · maximum distance from epoch ${periodEpochDistanceHours?.toFixed(2) ?? '—'} h.`}</small>
          </div>
        </section>

        <section className="summary-row" aria-label="Prediction summary">
          <div><span>TARGET EVENT COUNT</span><strong>{calculationState === 'calculating' ? 'CALCULATING' : modelAvailable && predictionPeriod ? targetEvents.length : '—'}</strong></div>
          <div><span>FIRST RADIUS ENTRY</span><strong>{targetEvents[0] ? targetEvents[0].entry.toISOString() : '—'}</strong></div>
          <div><span>LAST RADIUS EXIT</span><strong>{targetEvents.at(-1) ? targetEvents.at(-1)?.exit.toISOString() : '—'}</strong></div>
          <div><span>CLOSEST DISTANCE</span><strong>{closestEvent ? `${closestEvent.minimumDistanceKm.toFixed(3)} km` : '—'}</strong></div>
        </section>

        <section className="data-panel results-panel">
          <div className="panel-title"><h2>ATLID target events</h2><span>{calculationState === 'calculating' ? 'calculating in responsive batches…' : `${targetEvents.length} rows · distance ≤ ${targetRadiusKm.toFixed(1)} km`}</span></div>
          <div className="table-scroll">
            <table>
              <thead><tr><th>#</th><th>Radius entry UTC</th><th>Closest UTC</th><th>Radius exit UTC</th><th>Inside radius s</th><th>Min distance km</th><th>Footprint lat °</th><th>Footprint lon °</th><th>Subpoint lat °</th><th>Subpoint lon °</th><th>Boundary state</th></tr></thead>
              <tbody>
                {targetEvents.map((event, index) => <tr key={event.closest.toISOString()}><td>{index + 1}</td><td>{event.entry.toISOString()}</td><td>{event.closest.toISOString()}</td><td>{event.exit.toISOString()}</td><td>{eventDuration(event)}</td><td>{event.minimumDistanceKm.toFixed(6)}</td><td>{event.footprintLat.toFixed(7)}</td><td>{event.footprintLon.toFixed(7)}</td><td>{event.subpointLat.toFixed(7)}</td><td>{event.subpointLon.toFixed(7)}</td><td>{event.ongoing ? 'ACTIVE AT START' : 'COMPLETE'}</td></tr>)}
                {!targetEvents.length && <tr><td colSpan={11} className="empty-row">{calculationState === 'calculating' ? `Calculating ${periodLabel(periodHours)} of ATLID footprint data: ${Math.round(calculationProgress * 100)}% complete…` : calculationState === 'error' ? calculationError : modelAvailable && predictionPeriod ? `No ATLID footprint comes within ${targetRadiusKm.toFixed(1)} km of the target during this ${periodLabel(periodHours)} interval.` : 'Prediction data unavailable until a validated EarthCARE OMM is loaded.'}</td></tr>}
              </tbody>
            </table>
          </div>
        </section>

        <footer><span>EARTHCARE ATLID TARGET PREDICTION · NORAD 59908</span><span>Target: {site.lat.toFixed(5)}°, {site.lon.toFixed(5)}° · Radius: {targetRadiusKm.toFixed(1)} km · Beam: 3° aft · Solver: 20 s / ≤0.01 s</span></footer>
      </div>
    </main>
  );
}
