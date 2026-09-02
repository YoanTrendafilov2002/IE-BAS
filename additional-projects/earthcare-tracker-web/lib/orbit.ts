import {
  degreesLat,
  degreesLong,
  degreesToRadians,
  ecfToLookAngles,
  eciToEcf,
  eciToGeodetic,
  gstime,
  propagate,
  radiansToDegrees,
  type SatRec,
} from './satellite-core.ts';

export type GroundSite = { name: string; lat: number; lon: number; heightKm?: number };
export type OrbitPoint = { lat: number; lon: number; alt: number; velocity: number };
export type Look = { elevation: number; azimuth: number; range: number };
export type LidarFootprint = {
  lat: number;
  lon: number;
  subpointLat: number;
  subpointLon: number;
  aftOffsetKm: number;
};
export type LidarTargetEvent = {
  entry: Date;
  closest: Date;
  exit: Date;
  minimumDistanceKm: number;
  footprintLat: number;
  footprintLon: number;
  subpointLat: number;
  subpointLon: number;
  ongoing: boolean;
  numericalResolutionSeconds: number;
};
export type Pass = {
  rise: Date;
  peak: Date;
  set: Date;
  maxElevation: number;
  riseAzimuth: number;
  peakAzimuth: number;
  setAzimuth: number;
  peakRange: number;
  ongoing: boolean;
  numericalResolutionSeconds: number;
};

export function positionAt(satrec: SatRec, date: Date): OrbitPoint | null {
  const result = propagate(satrec, date, { communityDecayCheckEnabled: true });
  if (!result?.position || !result.velocity) return null;
  const gmst = gstime(date);
  const geodetic = eciToGeodetic(result.position, gmst);
  return {
    lat: degreesLat(geodetic.latitude),
    lon: degreesLong(geodetic.longitude),
    alt: geodetic.height,
    velocity: Math.hypot(result.velocity.x, result.velocity.y, result.velocity.z),
  };
}

export function lookAnglesAt(satrec: SatRec, site: GroundSite, date: Date): Look | null {
  const result = propagate(satrec, date, { communityDecayCheckEnabled: true });
  if (!result?.position) return null;
  const satelliteEcf = eciToEcf(result.position, gstime(date));
  const look = ecfToLookAngles({
    latitude: degreesToRadians(site.lat),
    longitude: degreesToRadians(site.lon),
    height: site.heightKm ?? 0,
  }, satelliteEcf);
  return {
    elevation: radiansToDegrees(look.elevation),
    azimuth: radiansToDegrees(look.azimuth),
    range: look.rangeSat,
  };
}

type Vector = { x: number; y: number; z: number };

const WGS84_A_KM = 6378.137;
const WGS84_B_KM = WGS84_A_KM * (1 - 1 / 298.257223563);
const MEAN_EARTH_RADIUS_KM = 6371.0088;

function subtract(a: Vector, b: Vector): Vector {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

function scale(vector: Vector, factor: number): Vector {
  return { x: vector.x * factor, y: vector.y * factor, z: vector.z * factor };
}

function dot(a: Vector, b: Vector) {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

function normalize(vector: Vector): Vector | null {
  const magnitude = Math.hypot(vector.x, vector.y, vector.z);
  return magnitude > 0 ? scale(vector, 1 / magnitude) : null;
}

function surfaceIntersection(origin: Vector, direction: Vector): Vector | null {
  const a2 = WGS84_A_KM * WGS84_A_KM;
  const b2 = WGS84_B_KM * WGS84_B_KM;
  const qa = (direction.x ** 2 + direction.y ** 2) / a2 + direction.z ** 2 / b2;
  const qb = 2 * ((origin.x * direction.x + origin.y * direction.y) / a2 + origin.z * direction.z / b2);
  const qc = (origin.x ** 2 + origin.y ** 2) / a2 + origin.z ** 2 / b2 - 1;
  const discriminant = qb * qb - 4 * qa * qc;
  if (discriminant < 0) return null;
  const roots = [(-qb - Math.sqrt(discriminant)) / (2 * qa), (-qb + Math.sqrt(discriminant)) / (2 * qa)]
    .filter((root) => root > 0)
    .sort((left, right) => left - right);
  return roots.length ? {
    x: origin.x + roots[0] * direction.x,
    y: origin.y + roots[0] * direction.y,
    z: origin.z + roots[0] * direction.z,
  } : null;
}

export function surfaceDistanceKm(latA: number, lonA: number, latB: number, lonB: number) {
  const phiA = degreesToRadians(latA);
  const phiB = degreesToRadians(latB);
  const deltaPhi = phiB - phiA;
  const deltaLambda = degreesToRadians(lonB - lonA);
  const haversine = Math.sin(deltaPhi / 2) ** 2
    + Math.cos(phiA) * Math.cos(phiB) * Math.sin(deltaLambda / 2) ** 2;
  return 2 * MEAN_EARTH_RADIUS_KM * Math.asin(Math.min(1, Math.sqrt(haversine)));
}

export function lidarFootprintAt(satrec: SatRec, date: Date, aftAngleDegrees = 3): LidarFootprint | null {
  const result = propagate(satrec, date, { communityDecayCheckEnabled: true });
  const beforeDate = new Date(date.getTime() - 500);
  const afterDate = new Date(date.getTime() + 500);
  const before = propagate(satrec, beforeDate, { communityDecayCheckEnabled: true });
  const after = propagate(satrec, afterDate, { communityDecayCheckEnabled: true });
  if (!result?.position || !before?.position || !after?.position) return null;

  const satelliteEcf = eciToEcf(result.position, gstime(date));
  const beforeEcf = eciToEcf(before.position, gstime(beforeDate));
  const afterEcf = eciToEcf(after.position, gstime(afterDate));
  const subpoint = eciToGeodetic(result.position, gstime(date));
  const subpointLat = degreesLat(subpoint.latitude);
  const subpointLon = degreesLong(subpoint.longitude);
  const latitude = degreesToRadians(subpointLat);
  const longitude = degreesToRadians(subpointLon);
  const up = {
    x: Math.cos(latitude) * Math.cos(longitude),
    y: Math.cos(latitude) * Math.sin(longitude),
    z: Math.sin(latitude),
  };
  const earthFixedMotion = subtract(afterEcf, beforeEcf);
  const tangentMotion = subtract(earthFixedMotion, scale(up, dot(earthFixedMotion, up)));
  const forward = normalize(tangentMotion);
  if (!forward) return null;
  const angle = degreesToRadians(aftAngleDegrees);
  const direction = normalize({
    x: -Math.cos(angle) * up.x - Math.sin(angle) * forward.x,
    y: -Math.cos(angle) * up.y - Math.sin(angle) * forward.y,
    z: -Math.cos(angle) * up.z - Math.sin(angle) * forward.z,
  });
  if (!direction) return null;
  const intercept = surfaceIntersection(satelliteEcf, direction);
  if (!intercept) return null;
  const footprint = eciToGeodetic(intercept, 0);
  const lat = degreesLat(footprint.latitude);
  const lon = degreesLong(footprint.longitude);
  return {
    lat,
    lon,
    subpointLat,
    subpointLon,
    aftOffsetKm: surfaceDistanceKm(subpointLat, subpointLon, lat, lon),
  };
}

export function lidarTargetDistanceAt(satrec: SatRec, target: GroundSite, date: Date) {
  const footprint = lidarFootprintAt(satrec, date);
  return footprint ? surfaceDistanceKm(footprint.lat, footprint.lon, target.lat, target.lon) : null;
}

function refineTargetMinimum(satrec: SatRec, target: GroundSite, lowerMs: number, upperMs: number) {
  let lower = lowerMs;
  let upper = upperMs;
  for (let iteration = 0; iteration < 48 && upper - lower > 10; iteration += 1) {
    const left = lower + (upper - lower) / 3;
    const right = upper - (upper - lower) / 3;
    const leftDistance = lidarTargetDistanceAt(satrec, target, new Date(left)) ?? Number.POSITIVE_INFINITY;
    const rightDistance = lidarTargetDistanceAt(satrec, target, new Date(right)) ?? Number.POSITIVE_INFINITY;
    if (leftDistance > rightDistance) lower = left; else upper = right;
  }
  const closest = new Date((lower + upper) / 2);
  return { closest, distance: lidarTargetDistanceAt(satrec, target, closest) ?? Number.POSITIVE_INFINITY };
}

function refineTargetCrossing(satrec: SatRec, target: GroundSite, radiusKm: number, lowerMs: number, upperMs: number) {
  let lower = lowerMs;
  let upper = upperMs;
  let lowerValue = (lidarTargetDistanceAt(satrec, target, new Date(lower)) ?? Number.POSITIVE_INFINITY) - radiusKm;
  for (let iteration = 0; iteration < 32 && upper - lower > 10; iteration += 1) {
    const middle = (lower + upper) / 2;
    const middleValue = (lidarTargetDistanceAt(satrec, target, new Date(middle)) ?? Number.POSITIVE_INFINITY) - radiusKm;
    if ((lowerValue <= 0) === (middleValue <= 0)) {
      lower = middle;
      lowerValue = middleValue;
    } else {
      upper = middle;
    }
  }
  return new Date((lower + upper) / 2);
}

export function findLidarTargetEvents(satrec: SatRec, target: GroundSite, start: Date, hours = 72, radiusKm = 5, limit = 250): LidarTargetEvent[] {
  const events: LidarTargetEvent[] = [];
  const stepMs = 20_000;
  const requestedStart = start.getTime();
  const requestedEnd = requestedStart + hours * 3_600_000;
  const scanStart = requestedStart - 30 * 60_000;
  const scanEnd = requestedEnd + 30 * 60_000;
  const distanceAt = (time: number) => lidarTargetDistanceAt(satrec, target, new Date(time)) ?? Number.POSITIVE_INFINITY;
  let left = { time: scanStart, distance: distanceAt(scanStart) };
  let middle = { time: scanStart + stepMs, distance: distanceAt(scanStart + stepMs) };

  for (let time = scanStart + 2 * stepMs; time <= scanEnd && events.length < limit; time += stepMs) {
    const right = { time, distance: distanceAt(time) };
    if (middle.distance <= left.distance && middle.distance <= right.distance) {
      const refined = refineTargetMinimum(satrec, target, left.time, right.time);
      const lastEvent = events[events.length - 1];
      const duplicate = lastEvent && Math.abs(lastEvent.closest.getTime() - refined.closest.getTime()) < 30 * 60_000;
      if (!duplicate && refined.distance <= radiusKm) {
        let entryOutside = refined.closest.getTime();
        while (entryOutside > scanStart && distanceAt(entryOutside) <= radiusKm) entryOutside -= stepMs;
        let exitOutside = refined.closest.getTime();
        while (exitOutside < scanEnd && distanceAt(exitOutside) <= radiusKm) exitOutside += stepMs;
        const entry = refineTargetCrossing(satrec, target, radiusKm, entryOutside, Math.min(entryOutside + stepMs, refined.closest.getTime()));
        const exit = refineTargetCrossing(satrec, target, radiusKm, Math.max(exitOutside - stepMs, refined.closest.getTime()), exitOutside);
        const footprint = lidarFootprintAt(satrec, refined.closest);
        if (footprint && exit.getTime() > requestedStart && entry.getTime() < requestedEnd) {
          events.push({
            entry,
            closest: refined.closest,
            exit,
            minimumDistanceKm: refined.distance,
            footprintLat: footprint.lat,
            footprintLon: footprint.lon,
            subpointLat: footprint.subpointLat,
            subpointLon: footprint.subpointLon,
            ongoing: entry.getTime() < requestedStart,
            numericalResolutionSeconds: 0.01,
          });
        }
      }
    }
    left = middle;
    middle = right;
  }
  return events;
}

function yieldToPage() {
  return new Promise<void>((resolve) => setTimeout(resolve, 0));
}

export async function findLidarTargetEventsAsync(
  satrec: SatRec,
  target: GroundSite,
  start: Date,
  hours = 72,
  radiusKm = 5,
  limit = 250,
  signal?: AbortSignal,
  onProgress?: (progress: number) => void,
): Promise<LidarTargetEvent[]> {
  const events: LidarTargetEvent[] = [];
  const stepMs = 20_000;
  const requestedStart = start.getTime();
  const requestedEnd = requestedStart + hours * 3_600_000;
  const scanStart = requestedStart - 30 * 60_000;
  const scanEnd = requestedEnd + 30 * 60_000;
  const distanceAt = (time: number) => lidarTargetDistanceAt(satrec, target, new Date(time)) ?? Number.POSITIVE_INFINITY;
  let left = { time: scanStart, distance: distanceAt(scanStart) };
  let middle = { time: scanStart + stepMs, distance: distanceAt(scanStart + stepMs) };
  let iteration = 0;

  for (let time = scanStart + 2 * stepMs; time <= scanEnd && events.length < limit; time += stepMs) {
    if (signal?.aborted) return [];
    const right = { time, distance: distanceAt(time) };
    if (middle.distance <= left.distance && middle.distance <= right.distance) {
      const refined = refineTargetMinimum(satrec, target, left.time, right.time);
      const lastEvent = events[events.length - 1];
      const duplicate = lastEvent && Math.abs(lastEvent.closest.getTime() - refined.closest.getTime()) < 30 * 60_000;
      if (!duplicate && refined.distance <= radiusKm) {
        let entryOutside = refined.closest.getTime();
        while (entryOutside > scanStart && distanceAt(entryOutside) <= radiusKm) entryOutside -= stepMs;
        let exitOutside = refined.closest.getTime();
        while (exitOutside < scanEnd && distanceAt(exitOutside) <= radiusKm) exitOutside += stepMs;
        const entry = refineTargetCrossing(satrec, target, radiusKm, entryOutside, Math.min(entryOutside + stepMs, refined.closest.getTime()));
        const exit = refineTargetCrossing(satrec, target, radiusKm, Math.max(exitOutside - stepMs, refined.closest.getTime()), exitOutside);
        const footprint = lidarFootprintAt(satrec, refined.closest);
        if (footprint && exit.getTime() > requestedStart && entry.getTime() < requestedEnd) {
          events.push({
            entry,
            closest: refined.closest,
            exit,
            minimumDistanceKm: refined.distance,
            footprintLat: footprint.lat,
            footprintLon: footprint.lon,
            subpointLat: footprint.subpointLat,
            subpointLon: footprint.subpointLon,
            ongoing: entry.getTime() < requestedStart,
            numericalResolutionSeconds: 0.01,
          });
        }
      }
    }
    left = middle;
    middle = right;
    iteration += 1;
    if (iteration % 200 === 0) {
      onProgress?.(Math.min(1, (time - scanStart) / (scanEnd - scanStart)));
      await yieldToPage();
    }
  }
  onProgress?.(1);
  return events;
}

export function groundTrack(satrec: SatRec, center: Date, minutes = 104) {
  const points: [number, number][] = [];
  const start = center.getTime() - (minutes / 2) * 60_000;
  for (let seconds = 0; seconds <= minutes * 60; seconds += 45) {
    const position = positionAt(satrec, new Date(start + seconds * 1_000));
    if (position) points.push([position.lon, position.lat]);
  }
  const segments: [number, number][][] = [[]];
  for (const point of points) {
    const segment = segments[segments.length - 1];
    const previous = segment[segment.length - 1];
    if (previous && Math.abs(point[0] - previous[0]) > 180) segments.push([]);
    segments[segments.length - 1].push(point);
  }
  return segments.filter((segment) => segment.length > 1);
}

function refineCrossing(satrec: SatRec, site: GroundSite, lowerMs: number, upperMs: number, threshold: number, rising: boolean) {
  let lower = lowerMs;
  let upper = upperMs;
  for (let iteration = 0; iteration < 24 && upper - lower > 100; iteration += 1) {
    const middle = (lower + upper) / 2;
    const elevation = lookAnglesAt(satrec, site, new Date(middle))?.elevation ?? -90;
    if ((rising && elevation >= threshold) || (!rising && elevation < threshold)) upper = middle;
    else lower = middle;
  }
  return new Date((lower + upper) / 2);
}

function refinePeak(satrec: SatRec, site: GroundSite, riseMs: number, setMs: number) {
  let lower = riseMs;
  let upper = setMs;
  for (let iteration = 0; iteration < 32 && upper - lower > 100; iteration += 1) {
    const left = lower + (upper - lower) / 3;
    const right = upper - (upper - lower) / 3;
    const leftElevation = lookAnglesAt(satrec, site, new Date(left))?.elevation ?? -90;
    const rightElevation = lookAnglesAt(satrec, site, new Date(right))?.elevation ?? -90;
    if (leftElevation < rightElevation) lower = left; else upper = right;
  }
  const peak = new Date((lower + upper) / 2);
  return { peak, look: lookAnglesAt(satrec, site, peak) };
}

export function findPasses(satrec: SatRec, site: GroundSite, start: Date, hours = 72, minimumElevation = 5, limit = 12): Pass[] {
  const passes: Pass[] = [];
  const stepMs = 20_000;
  const requestedStart = start.getTime();
  const requestedEnd = requestedStart + hours * 3_600_000;
  const scanStart = requestedStart - 30 * 60_000;
  const scanEnd = requestedEnd + 30 * 60_000;
  let previous = { time: scanStart, elevation: lookAnglesAt(satrec, site, new Date(scanStart))?.elevation ?? -90 };
  let activeRise: Date | null = null;

  for (let time = scanStart + stepMs; time <= scanEnd && passes.length < limit; time += stepMs) {
    const look = lookAnglesAt(satrec, site, new Date(time));
    if (!look) continue;
    const current = { time, elevation: look.elevation };
    if (!activeRise && previous.elevation < minimumElevation && current.elevation >= minimumElevation) {
      activeRise = refineCrossing(satrec, site, previous.time, current.time, minimumElevation, true);
    }
    if (activeRise && previous.elevation >= minimumElevation && current.elevation < minimumElevation) {
      const set = refineCrossing(satrec, site, previous.time, current.time, minimumElevation, false);
      const { peak, look: peakLook } = refinePeak(satrec, site, activeRise.getTime(), set.getTime());
      const riseLook = lookAnglesAt(satrec, site, activeRise);
      const setLook = lookAnglesAt(satrec, site, set);
      if (set.getTime() > requestedStart && activeRise.getTime() < requestedEnd && riseLook && peakLook && setLook) {
        passes.push({
          rise: activeRise,
          peak,
          set,
          maxElevation: peakLook.elevation,
          riseAzimuth: riseLook.azimuth,
          peakAzimuth: peakLook.azimuth,
          setAzimuth: setLook.azimuth,
          peakRange: peakLook.range,
          ongoing: activeRise.getTime() < requestedStart,
          numericalResolutionSeconds: 0.1,
        });
      }
      activeRise = null;
    }
    previous = current;
  }
  return passes;
}

export function compass(degrees: number) {
  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  return directions[Math.round(((degrees % 360) + 360) % 360 / 45) % 8];
}
