"use client";

import { useRef } from "react";

export default function FileUpload({ onGeoJSON }: { onGeoJSON: (gj: any) => void }) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = async (file: File) => {
    const ext = file.name.toLowerCase().split(".").pop();
    if (ext === "geojson" || ext === "json") {
      const text = await file.text();
      const gj = JSON.parse(text);
      onGeoJSON(gj);
    } else if (ext === "kml") {
      // Minimal KML to GeoJSON conversion via DOMParser (limited). For robustness, use togeojson lib later.
      const text = await file.text();
      const parser = new DOMParser();
      const xml = parser.parseFromString(text, "text/xml");
      const coords = Array.from(xml.getElementsByTagName("coordinates"))[0]?.textContent || "";
      const pairs = coords.trim().split(/\s+/).map((p) => p.split(",").map(Number));
      const ring = pairs.map(([lon, lat]) => [lon, lat]);
      const gj = {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [ring] },
        properties: {},
      };
      onGeoJSON(gj);
    } else {
      alert("Unsupported file. Please upload GeoJSON or KML.");
    }
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept=".geojson,.json,.kml"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
        className="block w-full text-sm text-gray-600 file:mr-4 file:rounded file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-blue-700 hover:file:bg-blue-100"
      />
    </div>
  );
}
