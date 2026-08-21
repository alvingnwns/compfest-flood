"use client";

import type { Map as MapLibreMap, MapLayerMouseEvent, Popup as MapLibrePopup } from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { DisruptionAnalysis, RoadRisk } from "@/domain/disruption";
import { publicEnv } from "@/config/public-env";
import {
  BASELINE_ROUTE_LABEL,
  CANDIDATE_ROUTE_COLOR,
  CANDIDATE_ROUTE_DASHARRAY,
  RISK_AWARE_CANDIDATE_LABEL,
} from "./route-semantics";

const ROAD_CONTEXT_URL = `${publicEnv.NEXT_PUBLIC_API_BASE_URL}/api/map/road-context`;

const RISK_COLORS: Record<string, string> = {
  critical: "#93000a",
  high: "#ba1a1a",
  medium: "#c45f00",
  low: "#00685f",
};

export function DisruptionMap({
  data,
  selectedRoadId,
  selectedCoords,
  onSelectRoad,
  onClearSelection,
  popupContent,
  showChrome = true,
  onMapReady,
}: {
  data: DisruptionAnalysis;
  selectedRoadId?: string;
  selectedCoords?: [number, number];
  onSelectRoad: (road: RoadRisk, coords: [number, number]) => void;
  onClearSelection: () => void;
  popupContent?: React.ReactNode;
  showChrome?: boolean;
  onMapReady?: (map: MapLibreMap) => void;
}) {
  const dynamic = data.roads.some((road) => road.dynamicRoadRiskScore !== undefined);
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const popupRef = useRef<MapLibrePopup | null>(null);
  const popupPortalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let disposed = false;
    void import("maplibre-gl").then((maplibregl) => {
      maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");
      if (!container.current || disposed) return;

      const map = new maplibregl.Map({
        container: container.current,
        center: [106.845, -6.185],
        zoom: 11.4,
        style: {
          version: 8,
          sources: {},
          layers: [{ id: "background", type: "background", paint: { "background-color": "#e8efef" } }],
        },
        attributionControl: false,
      });
      mapRef.current = map;
      onMapReady?.(map);

      // Automatically fit initial camera view to the exact geographic extent of the rendered road network
      const bounds = new maplibregl.LngLatBounds();
      data.roads.forEach((road) => {
        if (road.geometry.type === "LineString") {
          road.geometry.coordinates.forEach((coord) => bounds.extend(coord as [number, number]));
        } else if (road.geometry.type === "MultiLineString") {
          road.geometry.coordinates.forEach((line) =>
            line.forEach((coord) => bounds.extend(coord as [number, number]))
          );
        }
      });
      if (!bounds.isEmpty()) {
        map.fitBounds(bounds, { padding: 36, maxZoom: 13.2, duration: 0 });
      }

      map.addControl(
        new maplibregl.AttributionControl({
          compact: true,
          customAttribution: dynamic
            ? "Data jalan © OpenStreetMap contributors · Simulasi kondisi Jakarta"
            : "Data jalan © OpenStreetMap contributors · Pemutaran ulang historis Jakarta",
        })
      );

      map.on("load", () => {
        // ── Layer 1: Surrounding OSM road context ──
        map.addSource("road-context", {
          type: "geojson",
          data: ROAD_CONTEXT_URL,
        });
        map.addLayer({
          id: "road-context",
          type: "line",
          source: "road-context",
          paint: {
            "line-color": "#b0b8b5",
            "line-width": 1,
            "line-opacity": 0.35,
          },
        });

        // ── Layer 2: Flood scenario area ──
        if (!dynamic && data.historicalFloodGeometry) {
          map.addSource("flood", {
            type: "geojson",
            data: { type: "Feature", properties: {}, geometry: data.historicalFloodGeometry },
          });
          map.addLayer({
            id: "flood",
            type: "fill",
            source: "flood",
            paint: { "fill-color": "#ba1a1a", "fill-opacity": 0.11 },
          });
          map.addLayer({
            id: "flood-outline",
            type: "line",
            source: "flood",
            paint: { "line-color": "#ba1a1a", "line-width": 1.5, "line-opacity": 0.3, "line-dasharray": [4, 3] },
          });
        }

        // ── Layer 3: ARUNA analyzed road segments with ML risk colors ──
        map.addSource("roads-risk", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: data.roads.map((road) => ({
              type: "Feature" as const,
              id: road.segmentId,
              properties: {
                segmentId: road.segmentId,
                risk: road.riskLevel,
                roadName: road.roadName,
                highwayClass: road.highwayClass ?? "",
                osmWayIds: road.osmWayIds.join(", "),
                riskScore: road.dynamicRoadRiskScore ?? road.riskProbability,
              },
              geometry: road.geometry,
            })),
          },
        });
        map.addLayer({
          id: "roads-risk",
          type: "line",
          source: "roads-risk",
          paint: {
            "line-color": ["match", ["get", "risk"], "high", "#ba1a1a", "critical", "#93000a", "medium", "#c45f00", "#00685f"],
            "line-width": ["case", ["==", ["get", "segmentId"], selectedRoadId ?? ""], 7, 3.5],
            "line-opacity": 0.9,
          },
        });

        // ── Layer 4: Baseline route ──
        // ── Layer 5: Recovery route ──
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
              "line-color": routeType === "baseline" ? "#ba1a1a" : CANDIDATE_ROUTE_COLOR,
              "line-width": routeType === "baseline" ? 3 : 4,
              "line-opacity": routeType === "baseline" ? 0.6 : 0.85,
              "line-dasharray": routeType === "baseline" ? [2, 2] : CANDIDATE_ROUTE_DASHARRAY,
            },
          });
        }

        // ── Layer 6: Facilities ──
        map.addSource("facilities", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: data.facilities.map((facility) => ({
              type: "Feature" as const,
              properties: { id: facility.id, name: facility.name, kind: facility.kind },
              geometry: facility.location,
            })),
          },
        });
        map.addLayer({
          id: "facilities",
          type: "circle",
          source: "facilities",
          paint: {
            "circle-radius": ["match", ["get", "kind"], "factory", 9, "warehouse", 8, 6],
            "circle-color": ["match", ["get", "kind"], "supplier", "#565e74", "factory", "#00685f", "warehouse", "#4d5d73", "#ffffff"],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 2.5,
          },
        });
        map.addLayer({
          id: "facility-labels",
          type: "symbol",
          source: "facilities",
          layout: { "text-field": ["get", "name"], "text-size": 10, "text-offset": [0, 1.5], "text-anchor": "top" },
          paint: { "text-color": "#191c1d", "text-halo-color": "#ffffff", "text-halo-width": 1.5 },
        });

        // ── Interactions ──
        map.on("click", "roads-risk", (event: MapLayerMouseEvent) => {
          const segmentId = event.features?.[0]?.properties?.segmentId as string | undefined;
          const road = data.roads.find((item) => item.segmentId === segmentId);
          if (road && event.lngLat) {
            onSelectRoad(road, [event.lngLat.lng, event.lngLat.lat]);
          }
        });
        map.on("click", (event) => {
          if (map.queryRenderedFeatures(event.point, { layers: ["roads-risk"] }).length === 0) {
            onClearSelection();
          }
        });
        map.on("mouseenter", "roads-risk", () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", "roads-risk", () => { map.getCanvas().style.cursor = ""; });
      });

      const resizeObserver = new ResizeObserver(() => {
        if (mapRef.current) mapRef.current.resize();
      });
      resizeObserver.observe(container.current);
      return () => {
        disposed = true;
        resizeObserver.disconnect();
        mapRef.current?.remove();
        mapRef.current = null;
      };
    });
    return () => {
      disposed = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, onClearSelection, onSelectRoad]);

  // Dynamically update highlight stroke width when selection changes without re-creating the map
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const updateHighlight = () => {
      if (map.getLayer("roads-risk")) {
        map.setPaintProperty("roads-risk", "line-width", [
          "case",
          ["==", ["get", "segmentId"], selectedRoadId ?? ""],
          7,
          3.5,
        ]);
      }
    };

    if (map.isStyleLoaded()) {
      updateHighlight();
    } else {
      map.once("styledata", updateHighlight);
    }
  }, [selectedRoadId]);

  // Dynamically manage MapLibre Popup anchored at selectedCoords with directional pointer arrow
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedRoadId || !selectedCoords || !popupPortalRef.current) {
      if (popupRef.current) {
        popupRef.current.remove();
        popupRef.current = null;
      }
      return;
    }

    void import("maplibre-gl").then((maplibregl) => {
      if (!mapRef.current) return;
      if (popupRef.current) {
        popupRef.current.remove();
      }

      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        anchor: "bottom",
        offset: 14,
        className: "custom-road-popup",
      })
        .setLngLat(selectedCoords)
        .setDOMContent(popupPortalRef.current as HTMLElement)
        .addTo(mapRef.current);

      popupRef.current = popup;
    });
  }, [selectedRoadId, selectedCoords, popupContent]);

  return (
    <div className="absolute inset-0">
      <div
        ref={container}
        className="h-full w-full"
        aria-label={dynamic ? "Peta skor risiko relatif jalan Jakarta" : "Peta kerentanan historis jalan Jakarta"}
      />
      {/* Hidden Portal Container for MapLibre Popup */}
      <div className="hidden">
        <div ref={popupPortalRef}>{popupContent}</div>
      </div>
      {/* Map legend */}
      {showChrome && (
        <MapLegend
          dynamic={dynamic}
          hasBaseline={data.routes.some((route) => route.type === "baseline")}
          hasCandidate={data.routes.some((route) => route.type === "recovery")}
        />
      )}
    </div>
  );
}

function MapLegend({ dynamic, hasBaseline, hasCandidate }: { dynamic: boolean; hasBaseline: boolean; hasCandidate: boolean }) {
  return (
    <div className="absolute bottom-8 left-3 z-10 rounded-lg border border-outline bg-surface/95 p-3 text-[10px] shadow-lg backdrop-blur-sm">
      <div className="eyebrow mb-2">Legenda Peta</div>
      <div className="space-y-1.5">
        <LegendRow color="#b0b8b5" label="Jalan OSM (konteks)" dashed={false} thin />
        <div className="space-y-1">
          <div className="eyebrow text-[9px]">Jaringan Dianalisis ARUNA</div>
          {(["critical", "high", "medium", "low"] as const).map((risk) => (
            <LegendRow
              key={risk}
              color={RISK_COLORS[risk]}
              label={{ critical: "Kritis", high: "Tinggi", medium: "Sedang", low: "Rendah" }[risk]}
              dashed={false}
            />
          ))}
        </div>
        {hasBaseline && <LegendRow color="#ba1a1a" label={BASELINE_ROUTE_LABEL} dashed />}
        {hasCandidate && <LegendRow color={CANDIDATE_ROUTE_COLOR} label={RISK_AWARE_CANDIDATE_LABEL} dashed thick />}
        {!dynamic && <LegendRow color="#ba1a1a22" label="Zona Gangguan Historis" fill />}
      </div>
      <div className="mt-2 border-t border-outline pt-1.5 text-muted">
        © OpenStreetMap contributors
      </div>
    </div>
  );
}

function LegendRow({
  color, label, dashed = false, thin = false, thick = false, fill = false,
}: {
  color: string; label: string; dashed?: boolean; thin?: boolean; thick?: boolean; fill?: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      {fill ? (
        <span className="h-3 w-6 rounded-sm border border-danger/30" style={{ background: color }} />
      ) : (
        <svg width={24} height={8} aria-hidden>
          <line
            x1={0} y1={4} x2={24} y2={4}
            stroke={color}
            strokeWidth={thin ? 1 : thick ? 3 : 2}
            strokeDasharray={dashed ? "3,2" : undefined}
          />
        </svg>
      )}
      <span>{label}</span>
    </div>
  );
}
