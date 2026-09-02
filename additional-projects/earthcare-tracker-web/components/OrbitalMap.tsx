'use client';

import { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import type { GeoJSONSource, Map as MapLibreMap } from 'maplibre-gl';
import type { GroundSite, OrbitPoint } from '@/lib/orbit';

type Props = { position: OrbitPoint | null; track: [number, number][][]; site: GroundSite };

const emptyCollection = { type: 'FeatureCollection' as const, features: [] };

export default function OrbitalMap({ position, track, site }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const readyRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      center: [12, 22],
      zoom: 1.45,
      minZoom: 1,
      maxZoom: 12,
      attributionControl: { compact: true },
      style: {
        version: 8,
        sources: {
          osm: { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: '© OpenStreetMap contributors' },
        },
        layers: [
          { id: 'osm', type: 'raster', source: 'osm', paint: { 'raster-saturation': -0.82, 'raster-contrast': 0.28, 'raster-brightness-min': 0.13, 'raster-brightness-max': 0.66, 'raster-hue-rotate': 155 } },
        ],
      },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
    map.on('load', () => {
      map.addSource('orbit-track', { type: 'geojson', data: emptyCollection });
      map.addLayer({ id: 'orbit-track-glow', type: 'line', source: 'orbit-track', paint: { 'line-color': '#d8ff62', 'line-width': 5, 'line-opacity': .18 } });
      map.addLayer({ id: 'orbit-track-line', type: 'line', source: 'orbit-track', paint: { 'line-color': '#d8ff62', 'line-width': 1.8, 'line-dasharray': [3, 3] } });
      map.addSource('markers', { type: 'geojson', data: emptyCollection });
      map.addLayer({ id: 'marker-rings', type: 'circle', source: 'markers', paint: { 'circle-radius': ['match', ['get', 'kind'], 'satellite', 8, 11], 'circle-color': 'transparent', 'circle-stroke-width': 2, 'circle-stroke-color': ['match', ['get', 'kind'], 'satellite', '#d8ff62', '#ff8d6b'] } });
      map.addLayer({ id: 'marker-dots', type: 'circle', source: 'markers', paint: { 'circle-radius': ['match', ['get', 'kind'], 'satellite', 4, 5], 'circle-color': ['match', ['get', 'kind'], 'satellite', '#d8ff62', '#ff8d6b'] } });
      readyRef.current = true;
    });
    mapRef.current = map;
    return () => { readyRef.current = false; map.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const update = () => {
      if (!readyRef.current) return;
      const trackData = {
        type: 'FeatureCollection' as const,
        features: track.map((coordinates, index) => ({ type: 'Feature' as const, id: index, properties: {}, geometry: { type: 'LineString' as const, coordinates } })),
      };
      const markerData = {
        type: 'FeatureCollection' as const,
        features: [
          ...(position ? [{ type: 'Feature' as const, properties: { kind: 'satellite' }, geometry: { type: 'Point' as const, coordinates: [position.lon, position.lat] } }] : []),
          { type: 'Feature' as const, properties: { kind: 'site' }, geometry: { type: 'Point' as const, coordinates: [site.lon, site.lat] } },
        ],
      };
      (map.getSource('orbit-track') as GeoJSONSource | undefined)?.setData(trackData);
      (map.getSource('markers') as GeoJSONSource | undefined)?.setData(markerData);
    };
    if (readyRef.current) update(); else map.once('idle', update);
  }, [position, site, track]);

  return <div className="real-map" ref={containerRef} aria-label="Interactive OpenStreetMap showing EarthCARE and the selected institute" />;
}
