"use client";

import type { Map as MapLibreMap, MapLayerMouseEvent } from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { DisruptionAnalysis, RoadRisk } from "@/domain/disruption";

export function DisruptionMap({ data, selectedRoadId, onSelectRoad, onClearSelection }: { data: DisruptionAnalysis; selectedRoadId?: string; onSelectRoad: (road: RoadRisk) => void; onClearSelection: () => void }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);

  useEffect(() => {
    let disposed = false;
    void import("maplibre-gl").then((maplibregl) => {
      maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");
      if (!container.current || disposed) return;
      const map = new maplibregl.Map({
        container: container.current,
        center: [106.845, -6.185], zoom: 11.4,
        style: { version: 8, sources: {}, layers: [{ id: "background", type: "background", paint: { "background-color": "#e8efef" } }] },
        attributionControl: false,
      });
      mapRef.current = map;
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: "Pemutaran ulang historis Â· Jakarta" }));
      map.on("load", () => {
        if (data.historicalFloodGeometry) { map.addSource("flood", { type: "geojson", data: { type: "Feature", properties: {}, geometry: data.historicalFloodGeometry } }); map.addLayer({ id: "flood", type: "fill", source: "flood", paint: { "fill-color": "#ba1a1a", "fill-opacity": .11 } }); }
        map.addSource("roads-risk", { type: "geojson", data: { type: "FeatureCollection", features: data.roads.map((road) => ({ type: "Feature", id: road.segmentId, properties: { segmentId: road.segmentId, risk: road.riskLevel }, geometry: road.geometry })) } });
        map.addLayer({ id: "roads-risk", type: "line", source: "roads-risk", paint: { "line-color": ["match", ["get", "risk"], "high", "#ba1a1a", "critical", "#93000a", "medium", "#c45f00", "#00685f"], "line-width": ["case", ["==", ["get", "segmentId"], selectedRoadId ?? ""], 7, 4], "line-opacity": .85 } });
        for (const routeType of ["baseline", "recovery"] as const) {
          const routes = data.routes.filter((route) => route.type === routeType);
          if (routes.length === 0) continue;
          const id = `route-${routeType}`;
          map.addSource(id, {
            type: "geojson",
            data: {
              type: "FeatureCollection",
              features: routes.map((route) => ({
                type: "Feature" as const,
                properties: { id: route.id },
                geometry: route.geometry,
              })),
            },
          });
          map.addLayer({
            id,
            type: "line",
            source: id,
            paint: {
              "line-color": routeType === "baseline" ? "#ba1a1a" : "#00685f",
              "line-width": routeType === "baseline" ? 3 : 4,
              "line-opacity": routeType === "baseline" ? .55 : 1,
              ...(routeType === "baseline" ? { "line-dasharray": [2, 2] } : {}),
            },
          });
        }
        map.addSource("facilities", { type: "geojson", data: { type: "FeatureCollection", features: data.facilities.map((facility) => ({ type: "Feature", properties: { id: facility.id, name: facility.name, kind: facility.kind }, geometry: facility.location })) } });
        map.addLayer({ id: "facilities", type: "circle", source: "facilities", paint: { "circle-radius": ["match", ["get", "kind"], "factory", 9, "warehouse", 8, 6], "circle-color": ["match", ["get", "kind"], "supplier", "#565e74", "factory", "#00685f", "warehouse", "#4d5d73", "#ffffff"], "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
        map.addLayer({ id: "facility-labels", type: "symbol", source: "facilities", layout: { "text-field": ["get", "name"], "text-size": 10, "text-offset": [0, 1.5], "text-anchor": "top" }, paint: { "text-color": "#191c1d", "text-halo-color": "#ffffff", "text-halo-width": 1.5 } });
        map.on("click", "roads-risk", (event: MapLayerMouseEvent) => { const segmentId = event.features?.[0]?.properties?.segmentId as string | undefined; const road = data.roads.find((item) => item.segmentId === segmentId); if (road) onSelectRoad(road); });
        map.on("click", (event) => { if (map.queryRenderedFeatures(event.point, { layers: ["roads-risk"] }).length === 0) onClearSelection(); });
        map.on("mouseenter", "roads-risk", () => { map.getCanvas().style.cursor = "pointer"; }); map.on("mouseleave", "roads-risk", () => { map.getCanvas().style.cursor = ""; });
      });

      const resizeObserver = new ResizeObserver(() => {
        if (mapRef.current) mapRef.current.resize();
      });
      resizeObserver.observe(container.current);
      return () => { disposed = true; resizeObserver.disconnect(); mapRef.current?.remove(); mapRef.current = null; };
    });
    return () => { disposed = true; mapRef.current?.remove(); mapRef.current = null; };
  }, [data, onClearSelection, onSelectRoad, selectedRoadId]);

  return <div className="absolute inset-0"><div ref={container} className="h-full w-full" aria-label="Peta risiko gangguan banjir Jakarta" /></div>;
}
