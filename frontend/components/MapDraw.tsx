"use client";

import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, FeatureGroup, useMap } from "react-leaflet";
import L, { FeatureGroup as LeafletFeatureGroup } from "leaflet";
import "leaflet-draw/dist/leaflet.draw.css";
import "leaflet/dist/leaflet.css";

// Dynamically add draw controls once map is ready
function DrawControls({ onPolygon }: { onPolygon: (geojson: any) => void }) {
  const map = useMap();
  const drawnItemsRef = useRef<LeafletFeatureGroup | null>(null);

  useEffect(() => {
    if (!map) return;
    let drawControl: any | null = null;
    const setup = async () => {
      // Ensure leaflet-draw JS is loaded (side-effect import attaches L.Draw)
      await import("leaflet-draw");

      const drawnItems = new L.FeatureGroup();
      drawnItemsRef.current = drawnItems;
      map.addLayer(drawnItems);

      // @ts-expect-error: Control.Draw is added by leaflet-draw side-effect
      drawControl = new (L as any).Control.Draw({
        edit: { featureGroup: drawnItems },
        draw: {
          polygon: true,
          rectangle: true,
          polyline: false,
          marker: false,
          circle: false,
          circlemarker: false,
        },
      });
      map.addControl(drawControl);

      // @ts-expect-error: Draw.Event is added by leaflet-draw side-effect
      map.on((L as any).Draw.Event.CREATED, (e: any) => {
        const layer = e.layer as L.Layer;
        drawnItems.addLayer(layer);
        const gj = (layer as any).toGeoJSON();
        if (gj.geometry.type === "Polygon" || gj.geometry.type === "MultiPolygon") {
          onPolygon(gj);
        }
      });
    };

    setup();

    return () => {
      if (drawControl) {
        try { map.removeControl(drawControl); } catch {}
      }
      if (drawnItemsRef.current) {
        try { map.removeLayer(drawnItemsRef.current); } catch {}
      }
    };
  }, [map, onPolygon]);

  return null;
}

export default function MapDraw({ onPolygon }: { onPolygon: (geojson: any) => void }) {
  return (
    <div className="h-[500px] w-full rounded border overflow-hidden">
      <MapContainer center={[20, 0]} zoom={2} style={{ height: "100%", width: "100%" }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap contributors" />
        <FeatureGroup>{/* Drawn features injected via control */}</FeatureGroup>
        <DrawControls onPolygon={onPolygon} />
      </MapContainer>
    </div>
  );
}
