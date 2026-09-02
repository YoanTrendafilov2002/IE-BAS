export type OmmRecord = {
  OBJECT_NAME: string;
  OBJECT_ID: string;
  EPOCH: string;
  MEAN_MOTION: number;
  ECCENTRICITY: number;
  INCLINATION: number;
  RA_OF_ASC_NODE: number;
  ARG_OF_PERICENTER: number;
  MEAN_ANOMALY: number;
  EPHEMERIS_TYPE: 0;
  CLASSIFICATION_TYPE: 'U' | 'C';
  NORAD_CAT_ID: number;
  ELEMENT_SET_NO: number;
  REV_AT_EPOCH: number;
  BSTAR: number;
  MEAN_MOTION_DOT: number;
  MEAN_MOTION_DDOT: number;
};

export type OrbitDataPayload = {
  name: string;
  catalogId: number;
  omm: OmmRecord;
  source: string;
  sourceUrl: string;
  fetchedAt: string;
  epoch: string;
  ageHours: number;
  elementSetNo: number;
  revAtEpoch: number;
  usingFallback: boolean;
};

const numericFields: (keyof OmmRecord)[] = [
  'MEAN_MOTION', 'ECCENTRICITY', 'INCLINATION', 'RA_OF_ASC_NODE',
  'ARG_OF_PERICENTER', 'MEAN_ANOMALY', 'NORAD_CAT_ID', 'ELEMENT_SET_NO',
  'REV_AT_EPOCH', 'BSTAR', 'MEAN_MOTION_DOT', 'MEAN_MOTION_DDOT',
];

export function validateEarthcareOmm(value: unknown): OmmRecord {
  if (!value || typeof value !== 'object') throw new Error('OMM record is not an object');
  const raw = value as Record<string, unknown>;
  const normalized = { ...raw } as Record<string, unknown>;
  for (const field of numericFields) normalized[field] = Number(raw[field]);

  if (Number(normalized.NORAD_CAT_ID) !== 59908) throw new Error('Unexpected NORAD catalog identifier');
  if (typeof raw.OBJECT_NAME !== 'string' || raw.OBJECT_NAME.toUpperCase() !== 'EARTHCARE') throw new Error('Unexpected spacecraft name');
  if (typeof raw.OBJECT_ID !== 'string' || raw.OBJECT_ID !== '2024-101A') throw new Error('Unexpected international designator');
  if (Number(raw.EPHEMERIS_TYPE) !== 0) throw new Error('OMM is not an SGP4 general-perturbations element set');
  if (typeof raw.EPOCH !== 'string' || !Number.isFinite(Date.parse(`${raw.EPOCH}${raw.EPOCH.endsWith('Z') ? '' : 'Z'}`))) throw new Error('Invalid OMM epoch');
  for (const field of numericFields) {
    if (!Number.isFinite(Number(normalized[field]))) throw new Error(`Invalid OMM field: ${field}`);
  }
  if (Number(normalized.MEAN_MOTION) <= 0 || Number(normalized.ECCENTRICITY) < 0 || Number(normalized.ECCENTRICITY) >= 1) throw new Error('Non-physical mean elements');

  return {
    OBJECT_NAME: raw.OBJECT_NAME,
    OBJECT_ID: raw.OBJECT_ID,
    EPOCH: raw.EPOCH.endsWith('Z') ? raw.EPOCH : `${raw.EPOCH}Z`,
    MEAN_MOTION: Number(normalized.MEAN_MOTION),
    ECCENTRICITY: Number(normalized.ECCENTRICITY),
    INCLINATION: Number(normalized.INCLINATION),
    RA_OF_ASC_NODE: Number(normalized.RA_OF_ASC_NODE),
    ARG_OF_PERICENTER: Number(normalized.ARG_OF_PERICENTER),
    MEAN_ANOMALY: Number(normalized.MEAN_ANOMALY),
    EPHEMERIS_TYPE: 0,
    CLASSIFICATION_TYPE: raw.CLASSIFICATION_TYPE === 'C' ? 'C' : 'U',
    NORAD_CAT_ID: 59908,
    ELEMENT_SET_NO: Number(normalized.ELEMENT_SET_NO),
    REV_AT_EPOCH: Number(normalized.REV_AT_EPOCH),
    BSTAR: Number(normalized.BSTAR),
    MEAN_MOTION_DOT: Number(normalized.MEAN_MOTION_DOT),
    MEAN_MOTION_DDOT: Number(normalized.MEAN_MOTION_DDOT),
  };
}

export function epochAgeHours(epoch: string, now = Date.now()) {
  return (now - Date.parse(epoch)) / 3_600_000;
}
