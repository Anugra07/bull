"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import dynamic from "next/dynamic";
import FileUpload from "@/components/FileUpload";
import Sidebar from "@/components/Sidebar";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import Button from "@/components/ui/Button";

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
    land_cover?: number;
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
    ecosystem_type?: string;
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
                  land_cover: latestResult.land_cover ?? undefined,
                });
              }
              // Set compute results
              setCompute({
                carbon_biomass: latestResult.carbon_biomass,
                soc_total: latestResult.soc_total,
                annual_co2: latestResult.annual_co2,
                co2_20yr: latestResult.co2_20yr,
                risk_adjusted_co2: latestResult.risk_adjusted_co2,
                ecosystem_type: (latestResult as any).ecosystem_type ?? undefined,
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
          ecosystem_type: (c as any).ecosystem_type ?? undefined,
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

  const getEcosystemName = (type?: string) => {
    if (!type) return "Unknown";
    return type.charAt(0) + type.slice(1).toLowerCase();
  };

  if (authed === null) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="inline-block h-8 w-8 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin mb-4"></div>
          <p className="text-gray-600">Loading project...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8">
      {/* Project Header */}
      <div className="mb-4 sm:mb-6">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <button
                onClick={() => router.push("/dashboard")}
                className="flex items-center gap-2 text-gray-600 active:opacity-70"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                <span className="text-sm font-medium">Back to Dashboard</span>
              </button>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 truncate">
              {project ? project.name : `Project: ${String(params.id)}`}
            </h1>
            {project?.description && (
              <p className="text-gray-600 mt-1 sm:mt-2 text-sm sm:text-base line-clamp-2">{project.description}</p>
            )}
          </div>
        </div>
      </div>

      {/* Main Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Left Column - Map and Analysis */}
        <div className="lg:col-span-2 space-y-4 sm:space-y-6">
          {/* Map Section */}
          <Card className="overflow-hidden border-gray-300">
            <CardHeader className="bg-gray-50 border-b border-gray-200/60 px-4 sm:px-5 py-3 sm:py-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base sm:text-lg flex items-center gap-2">
                  <svg className="w-5 h-5 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                  </svg>
                  Interactive Map
                </CardTitle>
                {polygon && (
                  <span className="px-3 py-1 rounded-full bg-gray-100 text-gray-900 text-xs font-medium flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-900"></div>
                    Ready
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="h-[500px] lg:h-[600px]">
                <MapDraw onPolygon={onPolygon} />
              </div>
            </CardContent>
          </Card>

          {/* Upload Section */}
          <Card className="border-gray-300">
            <CardHeader>
              <CardTitle className="text-base sm:text-lg flex items-center gap-2">
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Upload Polygon File
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600 mb-4">
                Upload a GeoJSON or KML file to define your land parcel boundaries.
              </p>
              <FileUpload onGeoJSON={onPolygon} />
            </CardContent>
          </Card>

          {/* Analysis Results */}
          {metrics && (
            <Card className="overflow-hidden border-gray-300">
              <CardHeader className="bg-gray-50 border-b border-gray-200/60 px-4 sm:px-5 py-3 sm:py-4">
                <CardTitle className="text-base sm:text-lg flex items-center gap-2">
                  <svg className="w-5 h-5 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  Analysis Results
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 sm:p-5">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {/* NDVI */}
                  <div className="rounded-xl border border-gray-200 bg-white p-3 min-w-0 overflow-hidden">
                    <div className="text-xs font-medium text-gray-500 mb-1.5">NDVI</div>
                    <div className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">{metrics.ndvi.toFixed(3)}</div>
                    <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-green-500" style={{ width: `${Math.min(Math.max(pct(metrics.ndvi, 0, 1) * 100, 0), 100)}%` }} />
                    </div>
                  </div>
                  
                  {/* EVI */}
                  <div className="rounded-xl border border-gray-200 bg-white p-3 min-w-0 overflow-hidden">
                    <div className="text-xs font-medium text-gray-500 mb-1.5">EVI</div>
                    <div className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">{metrics.evi.toFixed(3)}</div>
                    <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-green-500" style={{ width: `${Math.min(Math.max(pct(metrics.evi, 0, 1) * 100, 0), 100)}%` }} />
                    </div>
                  </div>
                  
                  {/* Biomass */}
                  <div className="rounded-xl border border-gray-200 bg-white p-3 min-w-0 overflow-hidden">
                    <div className="text-xs font-medium text-gray-500 mb-1.5">Biomass</div>
                    <div className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">{metrics.biomass.toFixed(1)}</div>
                    <div className="text-xs text-gray-500 mb-2">t/ha</div>
                    <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-gray-900" style={{ width: `${Math.min(Math.max(pct(metrics.biomass, 0, 300), 0), 100)}%` }} />
                    </div>
                  </div>
                  
                  {/* Canopy Height */}
                  <div className="rounded-xl border border-gray-200 bg-white p-3 min-w-0 overflow-hidden">
                    <div className="text-xs font-medium text-gray-500 mb-1.5">Canopy Height</div>
                    <div className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">{metrics.canopy_height.toFixed(1)}</div>
                    <div className="text-xs text-gray-500">meters</div>
                  </div>
                  
                  {/* SOC */}
                  <div className="rounded-xl border border-gray-200 bg-white p-3 min-w-0 overflow-hidden">
                    <div className="text-xs font-medium text-gray-500 mb-1.5">SOC</div>
                    <div className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">{metrics.soc.toFixed(2)}</div>
                    <div className="text-xs text-gray-500 mb-2">%</div>
                    <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-gray-700" style={{ width: `${Math.min(Math.max(pct(metrics.soc, 0, 10), 0), 100)}%` }} />
                    </div>
                  </div>
                  
                  {/* Bulk Density */}
                  <div className="rounded-xl border border-gray-200 bg-white p-3 min-w-0 overflow-hidden">
                    <div className="text-xs font-medium text-gray-500 mb-1.5">Bulk Density</div>
                    <div className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">{metrics.bulk_density.toFixed(2)}</div>
                    <div className="text-xs text-gray-500">g/cm³</div>
                  </div>
                  
                  {/* Rainfall */}
                  <div className="rounded-xl border border-gray-200 bg-white p-3 min-w-0 overflow-hidden">
                    <div className="text-xs font-medium text-gray-500 mb-1.5">Rainfall</div>
                    <div className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">{metrics.rainfall.toFixed(0)}</div>
                    <div className="text-xs text-gray-500">mm/year</div>
                  </div>
                  
                  {/* Elevation */}
                  <div className="rounded-xl border border-gray-200 bg-white p-3 min-w-0 overflow-hidden">
                    <div className="text-xs font-medium text-gray-500 mb-1.5">Elevation</div>
                    <div className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">{metrics.elevation.toFixed(0)}</div>
                    <div className="text-xs text-gray-500 mb-2">meters</div>
                    <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-gray-600" style={{ width: `${Math.min(Math.max(pct(metrics.elevation, 0, 3000), 0), 100)}%` }} />
                    </div>
                  </div>
                  
                  {/* Slope */}
                  <div className="rounded-xl border border-gray-200 bg-white p-3 min-w-0 overflow-hidden">
                    <div className="text-xs font-medium text-gray-500 mb-1.5">Slope</div>
                    <div className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">{metrics.slope.toFixed(1)}</div>
                    <div className="text-xs text-gray-500">degrees</div>
                  </div>
                  
                  {/* Land Cover - if available */}
                  {metrics.land_cover !== undefined && metrics.land_cover !== null && (
                    <div className="rounded-xl border-2 border-gray-300 bg-gray-50 p-3 min-w-0 overflow-hidden">
                      <div className="text-xs font-medium text-gray-700 mb-1.5">Land Cover</div>
                      <div className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">{metrics.land_cover}</div>
                      <div className="text-xs text-gray-600">ESA WorldCover</div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Carbon Results */}
          {compute && (
            <Card className="overflow-hidden border-gray-300 bg-gray-50/50">
              <CardHeader className="bg-gray-50 border-b border-gray-200/60 px-4 sm:px-5 py-3 sm:py-4">
                <CardTitle className="text-base sm:text-lg flex items-center gap-2">
                  <svg className="w-5 h-5 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                  Carbon Offset Estimates
                </CardTitle>
                {compute.ecosystem_type && (
                  <p className="text-sm text-gray-600 mt-2">
                    Ecosystem: <span className="font-semibold text-gray-900">{getEcosystemName(compute.ecosystem_type)}</span>
                  </p>
                )}
              </CardHeader>
              <CardContent className="p-4 sm:p-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                  <div className="rounded-xl border border-gray-200 bg-white p-4">
                    <div className="text-xs font-medium text-gray-500 mb-1">Biomass Carbon</div>
                    <div className="text-2xl sm:text-3xl font-bold text-gray-900 mb-1">{(compute.carbon_biomass ?? 0).toFixed(2)}</div>
                    <div className="text-xs text-gray-500">tC/ha</div>
                  </div>
                  <div className="rounded-xl border border-gray-200 bg-white p-4">
                    <div className="text-xs font-medium text-gray-500 mb-1">Total SOC</div>
                    <div className="text-2xl sm:text-3xl font-bold text-gray-900 mb-1">{(compute.soc_total ?? 0).toFixed(2)}</div>
                    <div className="text-xs text-gray-500">tC</div>
                  </div>
                  <div className="rounded-xl border border-gray-300 bg-gray-50 p-4">
                    <div className="text-xs font-medium text-gray-700 mb-1">Annual CO₂</div>
                    <div className="text-2xl sm:text-3xl font-bold text-gray-900 mb-1">{(compute.annual_co2 ?? 0).toFixed(2)}</div>
                    <div className="text-xs text-gray-600">tCO₂e/year</div>
                  </div>
                  <div className="rounded-xl border border-gray-300 bg-gray-50 p-4">
                    <div className="text-xs font-medium text-gray-700 mb-1">20-Year CO₂</div>
                    <div className="text-2xl sm:text-3xl font-bold text-gray-900 mb-1">{(compute.co2_20yr ?? 0).toFixed(2)}</div>
                    <div className="text-xs text-gray-600">tCO₂e</div>
                  </div>
                  <div className="rounded-xl border-2 border-gray-900 bg-gray-900 text-white p-4 sm:col-span-2 lg:col-span-1">
                    <div className="text-xs font-medium text-gray-300 mb-1">Risk-Adjusted CO₂</div>
                    <div className="text-2xl sm:text-3xl font-bold text-white mb-1">{(compute.risk_adjusted_co2 ?? 0).toFixed(2)}</div>
                    <div className="text-xs text-gray-300 mb-2">tCO₂e (20yr)</div>
                    <div className="text-xs text-gray-300">Accounts for fire, drought, and degradation risks</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Sidebar */}
        <div className="lg:col-span-1">
          <Sidebar hasPolygon={!!polygon} onAnalyze={onAnalyze} busy={busy} />
        </div>
      </div>
    </div>
  );
}
