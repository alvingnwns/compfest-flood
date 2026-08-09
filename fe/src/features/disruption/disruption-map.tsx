"use client";

import type { Map as MapLibreMap, MapLayerMouseEvent } from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { DisruptionAnalysis, RoadRisk } from "@/domain/disruption";

export function DisruptionMap({ data, selectedRoadId, onSelectRoad }: { data: DisruptionAnalysis; selectedRoadId?: string; onSelectRoad: (road: RoadRisk) => void }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);

  useEffect(() => {
    let disposed = false;
    void import("maplibre-gl").then((maplibregl) => {
      if (!container.current || disposed) return;
      const map = new maplibregl.Map({
        container: container.current,
        center: [106.845, -6.185], zoom: 11.4,
        style: { version: 8, sources: {}, layers: [{ id: "background", type: "background", paint: { "background-color": "#e8efef" } }] },
        attributionControl: false,
      });
      mapRef.current = map;
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: "Historical replay Â· Jakarta" }));
      map.on("load", () => {
        const grid = { type: "FeatureCollection" as const, features: Array.from({ length: 8 }, (_, i) => ({ type: "Feature" as const, properties: {}, geometry: { type: "LineString" as const, coordinates: [[106.74 + i * .03, -6.12], [106.77 + i * .025, -6.27]] } })) };
        map.addSource("context-roads", { type: "geojson", data: grid });
        map.addLayer({ id: "context-roads", type: "line", source: "context-roads", paint: { "line-color": "#aebbb8", "line-width": 1 } });
        if (data.historicalFloodGeometry) { map.addSource("flood", { type: "geojson", data: { type: "Feature", properties: {}, geometry: data.historicalFloodGeometry } }); map.addLayer({ id: "flood", type: "fill", source: "flood", paint: { "fill-color": "#ba1a1a", "fill-opacity": .11 } }); }
        map.addSource("roads-risk", { type: "geojson", data: { type: "FeatureCollection", features: data.roads.map((road) => ({ type: "Feature", id: road.segmentId, properties: { segmentId: road.segmentId, risk: road.riskLevel }, geometry: road.geometry })) } });
        map.addLayer({ id: "roads-risk", type: "line", source: "roads-risk", paint: { "line-color": ["match", ["get", "risk"], "high", "#ba1a1a", "critical", "#93000a", "medium", "#c45f00", "#00685f"], "line-width": ["case", ["==", ["get", "segmentId"], selectedRoadId ?? ""], 7, 4], "line-opacity": .85 } });
        for (const route of data.routes) { const id = `route-${route.type}`; map.addSource(id, { type: "geojson", data: { type: "Feature", properties: {}, geometry: route.geometry } }); map.addLayer({ id, type: "line", source: id, paint: { "line-color": route.type === "baseline" ? "#ba1a1a" : "#00685f", "line-width": route.type === "baseline" ? 3 : 4, "line-opacity": route.type === "baseline" ? .55 : 1, ...(route.type === "baseline" ? { "line-dasharray": [2, 2] } : {}) } }); }
        map.addSource("facilities", { type: "geojson", data: { type: "FeatureCollection", features: data.facilities.map((facility) => ({ type: "Feature", properties: { id: facility.id, name: facility.name, kind: facility.kind }, geometry: facility.location })) } });
        map.addLayer({ id: "facilities", type: "circle", source: "facilities", paint: { "circle-radius": ["match", ["get", "kind"], "factory", 9, "warehouse", 8, 6], "circle-color": ["match", ["get", "kind"], "supplier", "#565e74", "factory", "#00685f", "warehouse", "#4d5d73", "#ffffff"], "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
        map.addLayer({ id: "facility-labels", type: "symbol", source: "facilities", layout: { "text-field": ["get", "name"], "text-size": 10, "text-offset": [0, 1.5], "text-anchor": "top" }, paint: { "text-color": "#191c1d", "text-halo-color": "#ffffff", "text-halo-width": 1.5 } });
        map.on("click", "roads-risk", (event: MapLayerMouseEvent) => { const segmentId = event.features?.[0]?.properties?.segmentId as string | undefined; const road = data.roads.find((item) => item.segmentId === segmentId); if (road) onSelectRoad(road); });
        map.on("mouseenter", "roads-risk", () => { map.getCanvas().style.cursor = "pointer"; }); map.on("mouseleave", "roads-risk", () => { map.getCanvas().style.cursor = ""; });
      });
    });
    return () => { disposed = true; mapRef.current?.remove(); mapRef.current = null; };
  }, [data, onSelectRoad, selectedRoadId]);

  return <div ref={container} className="absolute inset-0" aria-label="Jakarta flood disruption risk map" />;
}
