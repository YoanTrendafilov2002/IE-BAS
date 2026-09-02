import { json2satrec } from '../lib/satellite-core';
import { findLidarTargetEventsAsync, type GroundSite, type LidarTargetEvent } from '../lib/orbit';
import { validateEarthcareOmm, type OmmRecord } from '../lib/omm';

const legacyArrayPrototype = Array.prototype as unknown as { at?: (index: number) => unknown };
if (!legacyArrayPrototype.at) {
  Object.defineProperty(Array.prototype, 'at', {
    configurable: true,
    writable: true,
    value(this: unknown[], index: number) {
      const normalized = Math.trunc(index) || 0;
      const resolved = normalized < 0 ? this.length + normalized : normalized;
      return resolved < 0 || resolved >= this.length ? undefined : this[resolved];
    },
  });
}

const BUNDLED_OMM: OmmRecord = {
  OBJECT_NAME: 'EARTHCARE', OBJECT_ID: '2024-101A', EPOCH: '2026-08-31T21:21:54.340992Z',
  MEAN_MOTION: 15.57062303, ECCENTRICITY: 0.00015758, INCLINATION: 97.0604,
  RA_OF_ASC_NODE: 9.6615, ARG_OF_PERICENTER: 101.0817, MEAN_ANOMALY: 259.0616,
  EPHEMERIS_TYPE: 0, CLASSIFICATION_TYPE: 'U', NORAD_CAT_ID: 59908,
  ELEMENT_SET_NO: 999, REV_AT_EPOCH: 12834, BSTAR: 0.0001374668,
  MEAN_MOTION_DOT: 0.00009844, MEAN_MOTION_DDOT: 0,
};

const SNAPSHOT_START = Date.parse('2026-09-01T03:21:54.340Z');
const SNAPSHOT_END = Date.parse('2026-09-15T03:21:54.340Z');
const SNAPSHOT_TARGET: GroundSite = {
  name: 'Academician Emil Djakov Institute of Electronics, BAS, Sofia',
  lat: 42.65389,
  lon: 23.38722,
  heightKm: 0,
};
const SNAPSHOT_EVENTS: LidarTargetEvent[] = [
  {
    entry: new Date('2026-09-07T12:48:31.608Z'), closest: new Date('2026-09-07T12:48:43.703Z'), exit: new Date('2026-09-07T12:48:55.797Z'),
    minimumDistanceKm: 47.23960843131941, footprintLat: 42.565485304107405, footprintLon: 23.95182083240109,
    subpointLat: 42.3803102172201, subpointLon: 23.897565186537093, ongoing: false, numericalResolutionSeconds: 0.01,
  },
  {
    entry: new Date('2026-09-14T12:54:25.453Z'), closest: new Date('2026-09-14T12:54:35.458Z'), exit: new Date('2026-09-14T12:54:45.462Z'),
    minimumDistanceKm: 68.35921857555266, footprintLat: 42.78707848712536, footprintLon: 22.57029734170699,
    subpointLat: 42.60187919991576, subpointLon: 22.515726687811966, ongoing: false, numericalResolutionSeconds: 0.01,
  },
];

const byId = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const startInput = byId<HTMLInputElement>('period-start');
const endInput = byId<HTMLInputElement>('period-end');
const radiusInput = byId<HTMLInputElement>('radius');
const targetNameInput = byId<HTMLInputElement>('target-name');
const targetLatInput = byId<HTMLInputElement>('target-lat');
const targetLonInput = byId<HTMLInputElement>('target-lon');
const calculateButton = byId<HTMLButtonElement>('calculate');
const exportButton = byId<HTMLButtonElement>('export');
const ommFileInput = byId<HTMLInputElement>('omm-file');
const statusBox = byId<HTMLDivElement>('status');
const countValue = byId<HTMLElement>('event-count');
const firstValue = byId<HTMLElement>('first-entry');
const lastValue = byId<HTMLElement>('last-exit');
const closestValue = byId<HTMLElement>('closest-distance');
const tableBody = byId<HTMLTableSectionElement>('event-rows');
const orbitRows = byId<HTMLDListElement>('orbit-rows');
const runtimeBadge = byId<HTMLElement>('runtime-badge');

let activeOmm = BUNDLED_OMM;
let ommSource = 'Bundled CelesTrak OMM retrieved 2026-09-01';
let events: LidarTargetEvent[] = SNAPSHOT_EVENTS.slice();
let activePeriod: { startMs: number; endMs: number } | null = { startMs: SNAPSHOT_START, endMs: SNAPSHOT_END };
let activeTarget: GroundSite | null = SNAPSHOT_TARGET;
let activeRadiusKm = 100;
let controller: AbortController | null = null;

function utcInput(ms: number) { return new Date(ms).toISOString().slice(0, 16); }
function parseUtc(value: string) { return Date.parse(`${value}Z`); }
function formatDuration(event: LidarTargetEvent) { return ((event.exit.getTime() - event.entry.getTime()) / 1000).toFixed(2); }
function csvCell(value: unknown) { return `"${String(value).replace(/"/g, '""')}"`; }

function replaceChildrenCompat(parent: Element, ...nodes: Node[]) {
  while (parent.firstChild) parent.removeChild(parent.firstChild);
  nodes.forEach((node) => parent.appendChild(node));
}

function readFileText(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ''));
    reader.onerror = () => reject(reader.error ?? new Error('The local file could not be read.'));
    reader.readAsText(file);
  });
}

function initialiseSnapshotPeriod() {
  startInput.value = utcInput(SNAPSHOT_START);
  endInput.value = utcInput(SNAPSHOT_END);
}

function restoreEmbeddedSnapshot() {
  if (controller) controller.abort();
  activeOmm = BUNDLED_OMM;
  ommSource = 'Bundled CelesTrak OMM retrieved 2026-09-01';
  events = SNAPSHOT_EVENTS.slice();
  activePeriod = { startMs: SNAPSHOT_START, endMs: SNAPSHOT_END };
  activeTarget = SNAPSHOT_TARGET;
  activeRadiusKm = 100;
  targetNameInput.value = SNAPSHOT_TARGET.name;
  targetLatInput.value = String(SNAPSHOT_TARGET.lat);
  targetLonInput.value = String(SNAPSHOT_TARGET.lon);
  radiusInput.value = '100';
  initialiseSnapshotPeriod();
  renderOrbit();
  renderEvents();
}

function orbitRow(label: string, value: string) {
  const item = document.createElement('div');
  const term = document.createElement('dt');
  const detail = document.createElement('dd');
  term.textContent = label;
  detail.textContent = value;
  item.append(term, detail);
  return item;
}

function renderOrbit() {
  replaceChildrenCompat(orbitRows,
    orbitRow('Source', ommSource),
    orbitRow('Object', `${activeOmm.OBJECT_NAME} / ${activeOmm.OBJECT_ID}`),
    orbitRow('NORAD catalog ID', String(activeOmm.NORAD_CAT_ID)),
    orbitRow('OMM epoch UTC', activeOmm.EPOCH),
    orbitRow('Element set', String(activeOmm.ELEMENT_SET_NO)),
    orbitRow('Revolution at epoch', String(activeOmm.REV_AT_EPOCH)),
    orbitRow('Mean motion', `${activeOmm.MEAN_MOTION.toFixed(8)} rev/day`),
    orbitRow('Inclination', `${activeOmm.INCLINATION.toFixed(6)}°`),
  );
}

function setStatus(kind: 'info' | 'warning' | 'error' | 'success', heading: string, message: string) {
  statusBox.className = `status-box ${kind}`;
  replaceChildrenCompat(statusBox);
  const strong = document.createElement('strong');
  const span = document.createElement('span');
  strong.textContent = heading;
  span.textContent = message;
  statusBox.append(strong, span);
}

function setSummary() {
  countValue.textContent = String(events.length);
  firstValue.textContent = events[0]?.entry.toISOString() ?? '—';
  const lastEvent = events[events.length - 1];
  lastValue.textContent = lastEvent ? lastEvent.exit.toISOString() : '—';
  const closest = events.reduce<LidarTargetEvent | null>((best, event) => !best || event.minimumDistanceKm < best.minimumDistanceKm ? event : best, null);
  closestValue.textContent = closest ? `${closest.minimumDistanceKm.toFixed(6)} km` : '—';
}

function renderEvents() {
  replaceChildrenCompat(tableBody);
  if (!events.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 11;
    cell.className = 'empty';
    cell.textContent = activePeriod ? `No ATLID footprint comes within ${activeRadiusKm.toFixed(1)} km during the accepted interval.` : 'Calculate an interval to produce target-event rows.';
    row.append(cell);
    tableBody.append(row);
    setSummary();
    return;
  }
  events.forEach((event, index) => {
    const values = [
      index + 1,
      event.entry.toISOString(),
      event.closest.toISOString(),
      event.exit.toISOString(),
      formatDuration(event),
      event.minimumDistanceKm.toFixed(6),
      event.footprintLat.toFixed(7),
      event.footprintLon.toFixed(7),
      event.subpointLat.toFixed(7),
      event.subpointLon.toFixed(7),
      event.ongoing ? 'ACTIVE AT START' : 'COMPLETE',
    ];
    const row = document.createElement('tr');
    values.forEach((value) => {
      const cell = document.createElement('td');
      cell.textContent = String(value);
      row.append(cell);
    });
    tableBody.append(row);
  });
  setSummary();
}

function readTarget(): GroundSite | null {
  const lat = Number(targetLatInput.value);
  const lon = Number(targetLonInput.value);
  if (!Number.isFinite(lat) || lat < -90 || lat > 90 || !Number.isFinite(lon) || lon < -180 || lon > 180) return null;
  return { name: targetNameInput.value.trim() || 'Unnamed target', lat, lon, heightKm: 0 };
}

async function calculate(selfCheck = false) {
  const startMs = parseUtc(startInput.value);
  const endMs = parseUtc(endInput.value);
  const radiusKm = Number(radiusInput.value);
  const target = readTarget();
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) return setStatus('error', 'INPUT NOT APPLIED', 'Enter a valid UTC start and end.');
  const durationMs = endMs - startMs;
  if (durationMs < 60_000) return setStatus('error', 'INPUT NOT APPLIED', 'The end must be at least one minute after the start.');
  if (durationMs > 90 * 24 * 3_600_000) return setStatus('error', 'INPUT NOT APPLIED', 'The maximum calculation period is 90 days.');
  if (!target) return setStatus('error', 'INPUT NOT APPLIED', 'Target latitude must be −90…90° and longitude −180…180°.');
  if (!Number.isFinite(radiusKm) || radiusKm < 1 || radiusKm > 500) return setStatus('error', 'INPUT NOT APPLIED', 'Target radius must be 1…500 km.');

  if (controller) controller.abort();
  controller = typeof AbortController === 'function' ? new AbortController() : null;
  calculateButton.disabled = true;
  exportButton.disabled = true;
  const previousEvents = events;
  const previousPeriod = activePeriod;
  const previousTarget = activeTarget;
  const previousRadius = activeRadiusKm;
  activePeriod = { startMs, endMs };
  activeTarget = target;
  activeRadiusKm = radiusKm;
  runtimeBadge.textContent = 'OFFLINE · ENGINE RUNNING';
  setStatus('info', selfCheck ? 'STARTUP SELF-CHECK 0%' : 'CALCULATING 0%', 'Existing rows remain visible while the local WGS-72 SGP4 and ATLID footprint scan runs. No network connection is used.');
  try {
    const satrec = json2satrec(activeOmm);
    const calculatedEvents = await findLidarTargetEventsAsync(satrec, target, new Date(startMs), durationMs / 3_600_000, radiusKm, 250, controller ? controller.signal : undefined, (progress) => {
      setStatus('info', `${selfCheck ? 'STARTUP SELF-CHECK' : 'CALCULATING'} ${Math.round(progress * 100)}%`, 'Existing rows remain visible while coarse samples are processed in batches.');
    });
    events = calculatedEvents;
    renderEvents();
    runtimeBadge.textContent = 'OFFLINE · ENGINE READY';
    const maximumEpochDistanceHours = Math.max(Math.abs(startMs - Date.parse(activeOmm.EPOCH)), Math.abs(endMs - Date.parse(activeOmm.EPOCH))) / 3_600_000;
    if (maximumEpochDistanceHours > 120) {
      setStatus('warning', selfCheck ? 'SELF-CHECK PASSED · EXTRAPOLATION WARNING' : 'EXTRAPOLATION WARNING', `${events.length} event rows are visible. Maximum distance from the OMM epoch is ${maximumEpochDistanceHours.toFixed(2)} h; uncertainty is elevated.`);
    } else {
      setStatus('success', selfCheck ? 'STARTUP SELF-CHECK PASSED' : 'CALCULATION COMPLETE', `${events.length} events overlap the accepted interval. Maximum OMM epoch distance: ${maximumEpochDistanceHours.toFixed(2)} h.`);
    }
  } catch (error) {
    events = previousEvents;
    activePeriod = previousPeriod;
    activeTarget = previousTarget;
    activeRadiusKm = previousRadius;
    renderEvents();
    runtimeBadge.textContent = 'OFFLINE · SNAPSHOT DATA';
    setStatus('error', 'ENGINE CHECK FAILED · SNAPSHOT PRESERVED', `${error instanceof Error ? error.message : 'The local calculation could not be completed.'} The embedded validated event rows remain visible.`);
  } finally {
    calculateButton.disabled = false;
    exportButton.disabled = !events.length;
  }
}

function exportCsv() {
  if (!activePeriod || !activeTarget || !events.length) return;
  const headers = ['object_name','norad_catalog_id','omm_epoch_utc','omm_source','period_start_utc','period_end_utc','target_name','target_lat_deg','target_lon_deg','target_radius_km','atlid_off_nadir_aft_deg','radius_entry_utc','closest_approach_utc','radius_exit_utc','inside_radius_seconds','minimum_target_distance_km','footprint_lat_deg','footprint_lon_deg','subpoint_lat_deg','subpoint_lon_deg','numerical_resolution_s'];
  const rows = events.map((event) => [activeOmm.OBJECT_NAME,activeOmm.NORAD_CAT_ID,activeOmm.EPOCH,ommSource,new Date(activePeriod!.startMs).toISOString(),new Date(activePeriod!.endMs).toISOString(),activeTarget!.name,activeTarget!.lat,activeTarget!.lon,activeRadiusKm,3,event.entry.toISOString(),event.closest.toISOString(),event.exit.toISOString(),formatDuration(event),event.minimumDistanceKm.toFixed(6),event.footprintLat.toFixed(7),event.footprintLon.toFixed(7),event.subpointLat.toFixed(7),event.subpointLon.toFixed(7),event.numericalResolutionSeconds]);
  const csv = [headers, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n');
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  link.download = `earthcare-atlid-events-${new Date(activePeriod.startMs).toISOString().slice(0,10)}.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

async function loadOmm(file: File) {
  try {
    const parsed = JSON.parse(await readFileText(file)) as unknown;
    activeOmm = validateEarthcareOmm(Array.isArray(parsed) ? parsed[0] : parsed);
    ommSource = `Local file: ${file.name}`;
    events = [];
    activePeriod = null;
    renderOrbit();
    renderEvents();
    setStatus('success', 'OMM LOADED', `Validated EarthCARE OMM epoch ${activeOmm.EPOCH}. Recalculate the requested interval.`);
  } catch (error) {
    setStatus('error', 'OMM REJECTED', error instanceof Error ? error.message : 'The selected JSON file is not a valid EarthCARE OMM.');
  }
}

document.querySelectorAll<HTMLButtonElement>('[data-hours]').forEach((button) => button.addEventListener('click', () => {
  const hours = Number(button.dataset.hours);
  const startMs = Math.floor(Date.now() / 60_000) * 60_000;
  startInput.value = utcInput(startMs);
  endInput.value = utcInput(startMs + hours * 3_600_000);
  void calculate();
}));
byId<HTMLButtonElement>('snapshot-period').addEventListener('click', () => {
  restoreEmbeddedSnapshot();
  void calculate(true);
});
calculateButton.addEventListener('click', () => void calculate());
exportButton.addEventListener('click', exportCsv);
ommFileInput.addEventListener('change', () => { const file = ommFileInput.files?.[0]; if (file) void loadOmm(file); });

initialiseSnapshotPeriod();
renderOrbit();
renderEvents();
exportButton.disabled = false;
runtimeBadge.textContent = 'OFFLINE · ENGINE STARTING';
setStatus('info', 'EMBEDDED DATA READY', 'Two precomputed validation events are visible now. A local startup self-check is recalculating the same 14-day interval.');
setTimeout(() => void calculate(true), 0);
