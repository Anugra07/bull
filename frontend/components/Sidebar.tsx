"use client";

import Button from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";

export default function Sidebar({
  hasPolygon,
  onAnalyze,
  busy = false,
}: {
  hasPolygon: boolean;
  onAnalyze: () => void;
  busy?: boolean;
}) {
  return (
    <div className="space-y-4 sm:space-y-6">
      <Card>
        <CardHeader className="bg-[var(--surface)] border-b-2 border-[var(--line)]">
          <CardTitle className="text-base sm:text-lg">Project Inputs</CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 rounded-md bg-[var(--surface)] border-2 border-[var(--line)]">
              <div>
                <p className="text-sm font-medium text-[var(--ink)]">Draw on Map</p>
                <p className="text-xs text-[var(--muted)] mt-0.5">Use drawing tools to define polygon bounds.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-md bg-[var(--surface)] border-2 border-[var(--line)]">
              <div>
                <p className="text-sm font-medium text-[var(--ink)]">Upload File</p>
                <p className="text-xs text-[var(--muted)] mt-0.5">Upload GeoJSON or KML geometry.</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className={hasPolygon ? "bg-[var(--surface)]" : ""}>
        <CardHeader className="border-b-2 border-[var(--line)]">
          <CardTitle className="text-base sm:text-lg">Polygon Status</CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-md bg-[var(--surface-strong)] border-2 border-[var(--line)]">
              <div className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded ${hasPolygon ? "bg-[var(--accent)]" : "bg-[var(--line-strong)]"}`}></div>
                <span className={`font-semibold text-sm ${hasPolygon ? "text-[var(--ink)]" : "text-[var(--muted)]"}`}>
                  {hasPolygon ? "Ready" : "Not Ready"}
                </span>
              </div>
            </div>

            <Button disabled={!hasPolygon || busy} onClick={onAnalyze} loading={busy} className="w-full py-4 text-sm">
              {busy ? "Analyzing..." : "Analyze Land"}
            </Button>

            {busy && (
              <div className="mt-4 p-4 rounded-md bg-[var(--surface)] border-2 border-[var(--line)]">
                <p className="text-sm text-[var(--ink)] font-medium mb-1">Processing analysis</p>
                <p className="text-xs text-[var(--muted)]">
                  Extracting satellite features and computing carbon metrics.
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="bg-[var(--surface)]">
        <CardHeader>
          <CardTitle className="text-base">Analysis Includes</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-[var(--muted)]">
            <li>GEDI biomass and canopy structure</li>
            <li>Ecosystem classification</li>
            <li>Depth-aware SOC estimates</li>
            <li>Risk-adjusted forecasts</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
