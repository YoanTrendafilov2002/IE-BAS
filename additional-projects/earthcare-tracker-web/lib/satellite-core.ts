// satellite.js 7 exports an optional WebAssembly bundle from its package root.
// Vinext's browser-worker build does not support the top-level await used by
// that optional bundle, so the tracker imports only the JavaScript SGP4 modules.
export { json2satrec, twoline2satrec } from '../node_modules/satellite.js/dist/io.js';
export { gstime, propagate } from '../node_modules/satellite.js/dist/propagation.js';
export {
  degreesLat,
  degreesLong,
  degreesToRadians,
  ecfToLookAngles,
  eciToEcf,
  eciToGeodetic,
  radiansToDegrees,
} from '../node_modules/satellite.js/dist/transforms.js';
export type { SatRec } from '../node_modules/satellite.js/dist/propagation/SatRec.js';
