"use client";

import { useRef, useState } from "react";
import Button from "@/components/ui/Button";

export default function FileUpload({ onGeoJSON }: { onGeoJSON: (gj: any) => void }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    console.log("📁 File upload started:", file.name);
    const ext = file.name.toLowerCase().split(".").pop();
    console.log("📝 File extension:", ext);

    if (ext === "geojson" || ext === "json") {
      try {
        console.log("🔄 Reading file text...");
        const text = await file.text();
        console.log("📄 Raw file content (first 200 chars):", text.substring(0, 200));
        console.log("📏 File size:", text.length, "characters");

        // Remove trailing commas before closing brackets/braces (common JSON error)
        console.log("🧹 Cleaning JSON...");
        const cleanedText = text
          .replace(/,(\s*[}\]])/g, '$1')  // Remove trailing commas
          .replace(/\/\/.*/g, '')          // Remove single-line comments
          .replace(/\/\*[\s\S]*?\*\//g, ''); // Remove multi-line comments

        console.log("📄 Cleaned content (first 200 chars):", cleanedText.substring(0, 200));

        console.log("🔨 Parsing JSON...");
        const gj = JSON.parse(cleanedText);
        console.log("✅ JSON parsed successfully!");
        console.log("📊 GeoJSON type:", gj.type);
        console.log("📊 GeoJSON structure:", JSON.stringify(gj, null, 2).substring(0, 300));

        console.log("📤 Sending GeoJSON to parent component...");
        onGeoJSON(gj);
        setFileName(file.name);
        console.log("✅ File upload complete!");
      } catch (error) {
        console.error("❌ JSON parse error:", error);
        console.error("Error details:", {
          message: error instanceof Error ? error.message : 'Unknown error',
          name: error instanceof Error ? error.name : 'Unknown',
        });
        alert(`Invalid GeoJSON file: ${error instanceof Error ? error.message : 'Unable to parse JSON'}. Please check your file format.`);
      }
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
      setFileName(file.name);
    } else {
      alert("Unsupported file. Please upload GeoJSON or KML.");
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          accept=".geojson,.json,.kml"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
          className="hidden"
          id="file-upload"
        />
        <label htmlFor="file-upload">
          <div
            onClick={() => inputRef.current?.click()}
            className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 cursor-pointer transition-colors"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Choose File
          </div>
        </label>
        {fileName && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="font-medium">{fileName}</span>
            <button
              onClick={() => {
                setFileName(null);
                if (inputRef.current) inputRef.current.value = '';
              }}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
      </div>
      <p className="text-xs text-gray-500">
        Supported formats: GeoJSON (.geojson, .json) or KML (.kml)
      </p>
    </div>
  );
}
