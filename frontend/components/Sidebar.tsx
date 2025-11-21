"use client";

export default function Sidebar({
  hasPolygon,
  onAnalyze,
}: {
  hasPolygon: boolean;
  onAnalyze: () => void;
}) {
  return (
    <aside className="w-full md:w-80 shrink-0 space-y-4">
      <div className="rounded border bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold">Project Inputs</h2>
        <ul className="mt-2 text-sm text-gray-600">
          <li>• Draw a polygon on the map</li>
          <li>• Or upload GeoJSON / KML</li>
        </ul>
      </div>

      <div className="rounded border bg-white p-4 shadow-sm">
        <p className="text-sm">Polygon: {hasPolygon ? <span className="text-green-700">Ready</span> : <span className="text-red-700">Missing</span>}</p>
        <button
          disabled={!hasPolygon}
          onClick={onAnalyze}
          className={`mt-3 w-full rounded px-4 py-2 text-white ${hasPolygon ? "bg-emerald-600 hover:bg-emerald-700" : "bg-gray-400"}`}
        >
          Analyze Land
        </button>
      </div>
    </aside>
  );
}
