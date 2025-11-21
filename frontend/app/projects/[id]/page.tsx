"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import dynamic from "next/dynamic";
import FileUpload from "@/components/FileUpload";
import Sidebar from "@/components/Sidebar";
import { api } from "@/lib/api";

const MapDraw = dynamic(() => import("@/components/MapDraw"), { ssr: false });

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [project, setProject] = useState<{ name: string; description?: string | null } | null>(null);
  const [polygon, setPolygon] = useState<any | null>(null);
  const [busy, setBusy] = useState(false);
  const [metrics, setMetrics] = useState<null | {
    ndvi: number;
    evi: number;
    biomass: number;
    canopy_height: number;
    soc: number;
    bulk_density: number;
    rainfall: number;
    elevation: number;
    slope: number;
  }>(null);

  // Helpers to scale values into 0-100% widths for preview bars
  const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v));
  const pct = (v: number, min: number, max: number) => {
    const c = clamp(v, min, max);
    return ((c - min) / (max - min)) * 100;
  };
  const [compute, setCompute] = useState<null | {
    carbon_biomass?: number;
    soc_total?: number;
    annual_co2?: number;
    co2_20yr?: number;
    risk_adjusted_co2?: number;
  }>(null);

  useEffect(() => {
    const init = async () => {
      const { data } = await supabase.auth.getSession();
      setAuthed(!!data.session);
      if (!data.session) {
        router.push("/login");
        return;
      }

      // Load existing project data if project ID is valid
      const projectId = String(params.id);
      if (projectId && projectId !== "demo") {
        try {
          // Load project info
          const projectData = await api.getProject(projectId);
          setProject({ name: projectData.name, description: projectData.description });
          
          // Load existing polygons
          const polygons = await api.listPolygons(projectId);
          if (polygons && polygons.length > 0) {
            // Use the most recent polygon
            const latestPolygon = polygons[0];
            setPolygon(latestPolygon.geometry);
            
            // Load existing results
            const results = await api.getResults(projectId);
            if (results && results.length > 0) {
              const latestResult = results[0];
              // Set metrics if available
              if (latestResult.ndvi !== null && latestResult.ndvi !== undefined) {
                setMetrics({
                  ndvi: latestResult.ndvi ?? 0,
                  evi: latestResult.evi ?? 0,
                  biomass: latestResult.biomass ?? 0,
                  canopy_height: latestResult.canopy_height ?? 0,
                  soc: latestResult.soc ?? 0,
                  bulk_density: latestResult.bulk_density ?? 0,
                  rainfall: latestResult.rainfall ?? 0,
                  elevation: latestResult.elevation ?? 0,
                  slope: latestResult.slope ?? 0,
                });
              }
              // Set compute results
              setCompute({
                carbon_biomass: latestResult.carbon_biomass,
                soc_total: latestResult.soc_total,
                annual_co2: latestResult.annual_co2,
                co2_20yr: latestResult.co2_20yr,
                risk_adjusted_co2: latestResult.risk_adjusted_co2,
              });
            }
          }
        } catch (e) {
          // Silently fail - project might not have data yet
          console.log("Could not load existing project data:", e);
        }
      }
    };
    init();
  }, [router, params.id]);

  const onPolygon = (gj: any) => {
    setPolygon(gj);
    setMetrics(null);
    setCompute(null);
  };

  const onAnalyze = async () => {
    if (!polygon) return;
    try {
      setBusy(true);
      const { data: sess } = await supabase.auth.getSession();
      if (!sess.session) {
        router.push("/login");
        return;
      }
      const userId = sess.session.user.id;

      let projectId = String(params.id);
      if (!projectId || projectId === "demo") {
        const project = await api.createProject({ user_id: userId, name: "Demo Project", description: "MVP demo" });
        projectId = project.id;
      }

      const res = await api.createPolygon({ project_id: projectId, geometry: polygon.geometry ?? polygon });
      // Call analysis with polygon_id to compute metrics via GEE
      try {
        const analysis = await api.analyze({ polygon_id: res.id });
        setMetrics(analysis);
      } catch (e: any) {
        // If GEE not configured, show a helpful message
        alert(`Analysis error: ${e.message || e}. Ensure GEE credentials are set in backend/.env`);
      }

      // Compute carbon figures and store in project_results
      try {
        const c = await api.compute({ project_id: projectId, polygon_id: res.id });
        setCompute({
          carbon_biomass: c.carbon_biomass,
          soc_total: c.soc_total,
          annual_co2: c.annual_co2,
          co2_20yr: c.co2_20yr,
          risk_adjusted_co2: c.risk_adjusted_co2,
        });
      } catch (e: any) {
        alert(`Compute error: ${e.message || e}`);
      }
    } catch (e: any) {
      alert(`Analyze failed: ${e.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  if (authed === null) return <main className="py-10">Loading...</main>;

  return (
    <main className="py-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold">
          {project ? project.name : `Project: ${String(params.id)}`}
        </h1>
        {project?.description && (
          <p className="text-sm text-gray-600 mt-1">{project.description}</p>
        )}
      </div>
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 space-y-4">
          <MapDraw onPolygon={onPolygon} />
          <div className="rounded border bg-white p-4 shadow-sm">
            <h2 className="font-medium">Upload Polygon</h2>
            <p className="text-sm text-gray-600 mb-2">Upload GeoJSON or KML file.</p>
            <FileUpload onGeoJSON={onPolygon} />
          </div>

          {metrics && (
            <div className="rounded border bg-white p-4 shadow-sm">
              <h2 className="text-lg font-semibold mb-2">Analysis Results</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
                <div className="rounded border p-3"><div className="text-gray-600">NDVI (mean)</div><div className="font-semibold">{metrics.ndvi.toFixed(3)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">EVI (mean)</div><div className="font-semibold">{metrics.evi.toFixed(3)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">Biomass</div><div className="font-semibold">{metrics.biomass.toFixed(2)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">Canopy Height (m)</div><div className="font-semibold">{metrics.canopy_height.toFixed(2)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">SOC (%)</div><div className="font-semibold">{metrics.soc.toFixed(2)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">Bulk Density</div><div className="font-semibold">{metrics.bulk_density.toFixed(2)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">Rainfall (mm)</div><div className="font-semibold">{metrics.rainfall.toFixed(0)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">Elevation (m)</div><div className="font-semibold">{metrics.elevation.toFixed(1)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">Slope (°)</div><div className="font-semibold">{metrics.slope.toFixed(1)}</div></div>
              </div>
            </div>
          )}

          {metrics && (
            <div className="rounded border bg-white p-4 shadow-sm">
              <h2 className="text-lg font-semibold mb-3">Layer Previews</h2>
              <div className="space-y-3 text-sm">
                {/* NDVI (0 to 1 typical for Sentinel-2 SR) */}
                <div>
                  <div className="flex justify-between text-gray-600"><span>NDVI</span><span>{metrics.ndvi.toFixed(3)}</span></div>
                  <div className="h-2 w-full bg-gray-200 rounded">
                    <div className="h-2 rounded bg-green-500" style={{ width: `${pct(metrics.ndvi, 0, 1)}%` }} />
                  </div>
                </div>
                {/* Biomass (proxy). Scale 0–300 t/ha cap for preview */}
                <div>
                  <div className="flex justify-between text-gray-600"><span>Biomass</span><span>{metrics.biomass.toFixed(1)}</span></div>
                  <div className="h-2 w-full bg-gray-200 rounded">
                    <div className="h-2 rounded bg-emerald-600" style={{ width: `${pct(metrics.biomass, 0, 300)}%` }} />
                  </div>
                </div>
                {/* SOC % (0–10% preview window) */}
                <div>
                  <div className="flex justify-between text-gray-600"><span>SOC (%)</span><span>{metrics.soc.toFixed(2)}%</span></div>
                  <div className="h-2 w-full bg-gray-200 rounded">
                    <div className="h-2 rounded bg-yellow-600" style={{ width: `${pct(metrics.soc, 0, 10)}%` }} />
                  </div>
                </div>
                {/* Elevation (0–3000 m preview) */}
                <div>
                  <div className="flex justify-between text-gray-600"><span>Elevation (m)</span><span>{metrics.elevation.toFixed(0)}</span></div>
                  <div className="h-2 w-full bg-gray-200 rounded">
                    <div className="h-2 rounded bg-blue-600" style={{ width: `${pct(metrics.elevation, 0, 3000)}%` }} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {compute && (
            <div className="rounded border bg-white p-4 shadow-sm">
              <h2 className="text-lg font-semibold mb-2">Carbon Results</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
                <div className="rounded border p-3"><div className="text-gray-600">Biomass Carbon (tC/ha proxy)</div><div className="font-semibold">{(compute.carbon_biomass ?? 0).toFixed(2)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">Total SOC (tC)</div><div className="font-semibold">{(compute.soc_total ?? 0).toFixed(2)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">Annual CO₂ (tCO₂e/yr)</div><div className="font-semibold">{(compute.annual_co2 ?? 0).toFixed(2)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">20-year CO₂ (tCO₂e)</div><div className="font-semibold">{(compute.co2_20yr ?? 0).toFixed(2)}</div></div>
                <div className="rounded border p-3"><div className="text-gray-600">Risk-adjusted CO₂ (tCO₂e)</div><div className="font-semibold">{(compute.risk_adjusted_co2 ?? 0).toFixed(2)}</div></div>
              </div>
            </div>
          )}
        </div>
        <div className="md:w-80 w-full">
          <Sidebar hasPolygon={!!polygon} onAnalyze={onAnalyze} />
          {busy && <p className="mt-2 text-sm text-gray-600">Processing…</p>}
        </div>
      </div>
    </main>
  );
}
