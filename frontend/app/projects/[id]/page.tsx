"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import dynamic from "next/dynamic";
import FileUpload from "@/components/FileUpload";
import { ArrowLeft, Activity, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
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
    // Time-series trends
    ndvi_trend: number;
    ndvi_trend_interpretation: string;
    fire_burn_percent: number;
    fire_recent_burn: boolean;
    rainfall_anomaly_percent: number;
    trend_classification: string;
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
    baseline_condition?: string;
    // Baseline Carbon Stock (MRV)
    baseline_biomass_carbon?: number;
    baseline_soc_total?: number;
    baseline_annual_co2?: number;
    baseline_co2_20yr?: number;
    baseline_scenario?: string;
    // Project Carbon Stock
    project_annual_co2?: number;
    project_co2_20yr?: number;
    // Additionality (Credits)
    additionality_annual_co2?: number;
    additionality_20yr?: number;
    // QA/QC Metrics
    pixel_count?: number;
    ndvi_stddev?: number;
    soc_stddev?: number;
    rainfall_stddev?: number;
    cloud_coverage_percent?: number;
    gedi_shot_count?: number;
    data_confidence_score?: number;
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
                  // Time-series trends
                  ndvi_trend: latestResult.ndvi_trend ?? 0,
                  ndvi_trend_interpretation: latestResult.ndvi_trend_interpretation ?? 'Unknown',
                  fire_burn_percent: latestResult.fire_burn_percent ?? 0,
                  fire_recent_burn: latestResult.fire_recent_burn ?? false,
                  rainfall_anomaly_percent: latestResult.rainfall_anomaly_percent ?? 0,
                  trend_classification: latestResult.trend_classification ?? 'Unknown',
                });
              }
              // Set compute results
              setCompute({
                carbon_biomass: latestResult.carbon_biomass,
                soc_total: latestResult.soc_total,
                annual_co2: latestResult.annual_co2,
                co2_20yr: latestResult.co2_20yr,
                risk_adjusted_co2: latestResult.risk_adjusted_co2,
                ecosystem_type: latestResult.ecosystem_type ?? undefined,
                baseline_condition: latestResult.baseline_condition ?? undefined,
                // Baseline Carbon Stock (MRV)
                baseline_biomass_carbon: latestResult.baseline_biomass_carbon,
                baseline_soc_total: latestResult.baseline_soc_total,
                baseline_annual_co2: latestResult.baseline_annual_co2,
                baseline_co2_20yr: latestResult.baseline_co2_20yr,
                baseline_scenario: latestResult.baseline_scenario,
                // Project Carbon Stock
                project_annual_co2: latestResult.project_annual_co2,
                project_co2_20yr: latestResult.project_co2_20yr,
                // Additionality (Credits)
                additionality_annual_co2: latestResult.additionality_annual_co2,
                additionality_20yr: latestResult.additionality_20yr,
                // QA/QC Metrics
                pixel_count: latestResult.pixel_count,
                ndvi_stddev: latestResult.ndvi_stddev,
                soc_stddev: latestResult.soc_stddev,
                rainfall_stddev: latestResult.rainfall_stddev,
                cloud_coverage_percent: latestResult.cloud_coverage_percent,
                gedi_shot_count: latestResult.gedi_shot_count,
                data_confidence_score: latestResult.data_confidence_score,
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

  const [soilDepth, setSoilDepth] = useState<string>("0-30cm");

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
        const analysis = await api.analyze({ polygon_id: res.id, soil_depth: soilDepth });
        console.log("📊 Analysis Results:", analysis);
        setMetrics(analysis);
      } catch (e: any) {
        // If GEE not configured, show a helpful message
        alert(`Analysis error: ${e.message || e}. Ensure GEE credentials are set in backend/.env`);
      }

      // Compute carbon figures and store in project_results
      try {
        const c = await api.compute({ project_id: projectId, polygon_id: res.id, soil_depth: soilDepth });
        console.log("💰 Compute Results:", c);
        setCompute({
          carbon_biomass: c.carbon_biomass,
          soc_total: c.soc_total,
          annual_co2: c.annual_co2,
          co2_20yr: c.co2_20yr,
          risk_adjusted_co2: c.risk_adjusted_co2,
          ecosystem_type: c.ecosystem_type ?? undefined,
          baseline_condition: c.baseline_condition ?? undefined,
          // Baseline Carbon Stock (MRV)
          baseline_biomass_carbon: c.baseline_biomass_carbon,
          baseline_soc_total: c.baseline_soc_total,
          baseline_annual_co2: c.baseline_annual_co2,
          baseline_co2_20yr: c.baseline_co2_20yr,
          baseline_scenario: c.baseline_scenario,
          // Project Carbon Stock
          project_annual_co2: c.project_annual_co2,
          project_co2_20yr: c.project_co2_20yr,
          // Additionality (Credits)
          additionality_annual_co2: c.additionality_annual_co2,
          additionality_20yr: c.additionality_20yr,
          // QA/QC Metrics
          pixel_count: c.pixel_count,
          ndvi_stddev: c.ndvi_stddev,
          soc_stddev: c.soc_stddev,
          rainfall_stddev: c.rainfall_stddev,
          cloud_coverage_percent: c.cloud_coverage_percent,
          gedi_shot_count: c.gedi_shot_count,
          data_confidence_score: c.data_confidence_score,
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
    <div className="min-h-screen pb-12 font-sans text-gray-900">
      {/* Project Controls Bar */}
      <div className="sticky top-16 z-20 bg-[#F5F5F7]/95 backdrop-blur-sm border-b border-gray-200/50">
        <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push("/dashboard")}
              className="p-2 -ml-2 rounded-full hover:bg-gray-200/50 transition-colors text-gray-500"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-lg font-semibold tracking-tight">
              {project ? project.name : "Loading..."}
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <select
                value={soilDepth}
                onChange={(e) => setSoilDepth(e.target.value)}
                className="appearance-none bg-white pl-4 pr-10 py-2 rounded-full text-sm font-medium shadow-sm border border-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-200 cursor-pointer hover:bg-gray-50 transition-colors"
              >
                <option value="0-30cm">0-30 cm Depth</option>
                <option value="0-100cm">0-100 cm Depth</option>
                <option value="0-200cm">0-200 cm Depth</option>
              </select>
              <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
              </div>
            </div>

            <Button
              onClick={onAnalyze}
              disabled={!polygon || busy}
              className="shadow-lg shadow-gray-900/20"
            >
              {busy ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : metrics ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Re-run Analysis
                </>
              ) : (
                <>
                  <Activity className="w-4 h-4 mr-2" />
                  Run Analysis
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      <main className="max-w-[1600px] mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

          {/* Main Content: Map & Metrics */}
          <div className="lg:col-span-8 space-y-8">

            {/* Interactive Map */}
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-b from-gray-900/5 to-transparent rounded-[2rem] pointer-events-none" />
              <div className="h-[500px] lg:h-[600px] rounded-[2rem] overflow-hidden shadow-xl shadow-gray-200/50 border border-white/50 ring-1 ring-gray-900/5">
                <MapDraw onPolygon={onPolygon} />
              </div>

              {/* Floating Status Pill */}
              <div className="absolute top-6 left-6 bg-white/90 backdrop-blur shadow-sm border border-gray-100 px-4 py-2 rounded-full flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${polygon ? 'bg-green-500' : 'bg-amber-500'}`} />
                <span className="text-xs font-semibold text-gray-600">
                  {polygon ? "Area Selected" : "Draw Polygon"}
                </span>
              </div>
            </div>

            {/* Analysis Results */}
            {metrics && (
              <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-900">Environmental Metrics</h2>
                  <span className="text-sm text-gray-500">Based on satellite analysis</span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <MetricCardMinimal title="NDVI" value={metrics.ndvi.toFixed(2)} unit="Index" color="green" />
                  <MetricCardMinimal title="EVI" value={metrics.evi.toFixed(2)} unit="Index" color="emerald" />
                  <MetricCardMinimal title="Biomass" value={metrics.biomass.toFixed(0)} unit="t/ha" color="stone" />
                  <MetricCardMinimal title="Canopy" value={metrics.canopy_height.toFixed(1)} unit="m" color="teal" />
                  <MetricCardMinimal title="SOC" value={metrics.soc.toFixed(1)} unit="tC/ha" sub={`0-${soilDepth.replace("0-", "")}`} color="amber" />
                  <MetricCardMinimal title="Rainfall" value={metrics.rainfall.toFixed(0)} unit="mm" color="blue" />
                  <MetricCardMinimal title="Elevation" value={metrics.elevation.toFixed(0)} unit="m" color="gray" />
                  <MetricCardMinimal title="Slope" value={metrics.slope.toFixed(1)} unit="°" color="gray" />
                </div>
              </div>
            )}

            {/* Trends & Risk Indicators (Time-Series Analysis) */}
            {metrics && (
              <div className="animate-in fade-in slide-in-from-bottom-6 duration-700 delay-75">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-900">Trends &amp; Risk Indicators</h2>
                  <span className="text-sm text-gray-500">5-year analysis (2020-2024)</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* NDVI Trend */}
                  <Card className="p-6 bg-gradient-to-br from-white to-gray-50/50">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-1">NDVI Trend</h3>
                        <p className="text-xs text-gray-500">Vegetation change over time</p>
                      </div>
                      <div className={`px-3 py-1 rounded-full text-xs font-semibold ${metrics.ndvi_trend_interpretation === 'Degrading' ? 'bg-red-100 text-red-700' :
                        metrics.ndvi_trend_interpretation === 'Improving' ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                        {metrics.ndvi_trend_interpretation === 'Degrading' ? '↓ Degrading' :
                          metrics.ndvi_trend_interpretation === 'Improving' ? '↑ Improving' :
                            '→ Stable'}
                      </div>
                    </div>
                    <div className="text-3xl font-bold text-gray-900 mb-1">
                      {metrics.ndvi_trend.toFixed(4)}
                    </div>
                    <div className="text-sm text-gray-500">units/year</div>
                  </Card>

                  {/* Fire History */}
                  <Card className="p-6 bg-gradient-to-br from-white to-gray-50/50">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-1">Fire History</h3>
                        <p className="text-xs text-gray-500">Burned area detection</p>
                      </div>
                      {metrics.fire_recent_burn && (
                        <div className="px-3 py-1 rounded-full text-xs font-semibold bg-orange-100 text-orange-700 flex items-center gap-1">
                          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
                          Recent Burn
                        </div>
                      )}
                    </div>
                    <div className="text-3xl font-bold text-gray-900 mb-1">
                      {metrics.fire_burn_percent.toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-500">of area burned (5 years)</div>
                  </Card>

                  {/* Rainfall Anomaly */}
                  <Card className="p-6 bg-gradient-to-br from-white to-gray-50/50">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-1">Rainfall Pattern</h3>
                        <p className="text-xs text-gray-500">vs. long-term average</p>
                      </div>
                      <div className={`px-3 py-1 rounded-full text-xs font-semibold ${metrics.rainfall_anomaly_percent < -20 ? 'bg-amber-100 text-amber-700' :
                        metrics.rainfall_anomaly_percent > 20 ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                        {metrics.rainfall_anomaly_percent < -20 ? 'Drought' :
                          metrics.rainfall_anomaly_percent > 20 ? 'Wet' :
                            'Normal'}
                      </div>
                    </div>
                    <div className="text-3xl font-bold text-gray-900 mb-1">
                      {metrics.rainfall_anomaly_percent > 0 ? '+' : ''}{metrics.rainfall_anomaly_percent.toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-500">anomaly from baseline</div>
                  </Card>

                  {/* Overall Trend Classification */}
                  <Card className="p-6 bg-gradient-to-br from-white to-gray-50/50">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-1">Overall Trend</h3>
                        <p className="text-xs text-gray-500">Combined assessment</p>
                      </div>
                    </div>
                    <div className={`inline-block px-4 py-2 rounded-xl text-xl font-bold mb-2 ${metrics.trend_classification.includes('Degrading') || metrics.trend_classification.includes('Fire-Impacted') || metrics.trend_classification.includes('Drought')
                      ? 'bg-red-100 text-red-700' :
                      metrics.trend_classification.includes('Improving') || metrics.trend_classification.includes('Regenerating')
                        ? 'bg-green-100 text-green-700' :
                        metrics.trend_classification.includes('Recovering')
                          ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-700'
                      }`}>
                      {metrics.trend_classification}
                    </div>
                    <div className="text-sm text-gray-500">Based on multi-indicator analysis</div>
                  </Card>
                </div>
              </div>
            )}

            {/*Carbon Estimates */}
            {compute && (
              <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Carbon Offset Potential</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <Card className="p-6 flex flex-col justify-between bg-gradient-to-br from-gray-900 to-gray-800 text-white border-none shadow-xl shadow-gray-900/10">
                    <div>
                      <div className="text-gray-400 text-sm font-medium mb-1">Risk-Adjusted CO₂</div>
                      <div className="text-4xl font-bold tracking-tight">{(compute.risk_adjusted_co2 ?? 0).toFixed(0)}</div>
                      <div className="text-gray-400 text-sm mt-1">tCO₂e (20yr)</div>
                    </div>
                    <div className="mt-8 pt-6 border-t border-white/10">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Ecosystem</span>
                        <span className="font-medium">{getEcosystemName(compute.ecosystem_type)}</span>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-6 flex flex-col justify-center">
                    <div className="text-gray-500 text-sm font-medium mb-1">Total Carbon Stock</div>
                    <div className="text-3xl font-bold text-gray-900">
                      {((compute.carbon_biomass ?? 0) + (compute.soc_total ?? 0)).toFixed(0)}
                    </div>
                    <div className="text-gray-400 text-sm mt-1">tC (Biomass + SOC)</div>
                  </Card>

                  <Card className="p-6 flex flex-col justify-center">
                    <div className="text-gray-500 text-sm font-medium mb-1">Annual Sequestration</div>
                    <div className="text-3xl font-bold text-gray-900">{(compute.annual_co2 ?? 0).toFixed(1)}</div>
                    <div className="text-gray-400 text-sm mt-1">tCO₂e / year</div>
                  </Card>
                </div>
              </div>
            )}

            {/* Carbon Credits (MRV Baseline) */}
            {compute && compute.baseline_scenario && (
              <div className="animate-in fade-in slide-in-from-bottom-10 duration-700 delay-150">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-900">Carbon Credits (MRV Baseline)</h2>
                  <span className="text-sm text-gray-500 px-3 py-1 bg-gray-100 rounded-full">
                    Baseline: {compute.baseline_scenario}
                  </span>
                </div>

                <Card className="p-6 bg-gradient-to-br from-blue-50 to-green-50 border-blue-200/50">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    {/* Headers */}
                    <div className="text-center">
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Metric</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Baseline (BAU)</div>
                      <div className="text-xs text-gray-400 mt-1">Without Project</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Project</div>
                      <div className="text-xs text-gray-400 mt-1">With Intervention</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xs font-semibold text-green-600 uppercase tracking-wider">Additionality</div>
                      <div className="text-xs text-green-500 mt-1">Carbon Credits</div>
                    </div>

                    {/* Annual CO2 Row */}
                    <div className="flex items-center">
                      <div className="text-sm font-medium text-gray-700">Annual CO₂</div>
                    </div>
                    <div className="text-center p-3 bg-gray-100/50 rounded-xl">
                      <div className="text-2xl font-bold text-gray-600">
                        {(compute.baseline_annual_co2 ?? 0).toFixed(1)}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">tCO₂e/yr</div>
                    </div>
                    <div className="text-center p-3 bg-green-100/50 rounded-xl border border-green-200/30">
                      <div className="text-2xl font-bold text-green-700">
                        {(compute.project_annual_co2 ?? 0).toFixed(1)}
                      </div>
                      <div className="text-xs text-green-600 mt-1">tCO₂e/yr</div>
                    </div>
                    <div className="text-center p-3 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl shadow-lg">
                      <div className="text-2xl font-bold text-white">
                        +{(compute.additionality_annual_co2 ?? 0).toFixed(1)}
                      </div>
                      <div className="text-xs text-green-100 mt-1">tCO₂e/yr</div>
                    </div>

                    {/* 20-Year Total Row */}
                    <div className="flex items-center">
                      <div className="text-sm font-medium text-gray-700">20-Year Total</div>
                    </div>
                    <div className="text-center p-3 bg-gray-100/50 rounded-xl">
                      <div className="text-2xl font-bold text-gray-600">
                        {(compute.baseline_co2_20yr ?? 0).toFixed(0)}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">tCO₂e</div>
                    </div>
                    <div className="text-center p-3 bg-green-100/50 rounded-xl border border-green-200/30">
                      <div className="text-2xl font-bold text-green-700">
                        {(compute.project_co2_20yr ?? 0).toFixed(0)}
                      </div>
                      <div className="text-xs text-green-600 mt-1">tCO₂e</div>
                    </div>
                    <div className="text-center p-3 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl shadow-lg">
                      <div className="text-3xl font-bold text-white">
                        +{(compute.additionality_20yr ?? 0).toFixed(0)}
                      </div>
                      <div className="text-xs text-green-100 mt-1">tCO₂e</div>
                    </div>
                  </div>

                  {/* Explanation */}
                  <div className="mt-6 p-4 bg-white/60 rounded-xl border border-gray-200/50">
                    <div className="flex items-start gap-3">
                      <svg className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                      </svg>
                      <div className="text-sm text-gray-600">
                        <strong className="font-semibold text-gray-900">Additionality</strong> represents carbon sequestration
                        that <strong>wouldn't occur</strong> without your project. This is calculated by comparing the
                        <strong className="text-green-600"> project scenario</strong> (with intervention) against the
                        <strong className="text-gray-700"> baseline scenario</strong> ({compute.baseline_scenario?.toLowerCase()}).
                        This methodology meets MRV (Monitoring, Reporting, Verification) standards for carbon offset projects.
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {/* Data Quality & Accuracy (QA/QC) */}
            {compute && compute.data_confidence_score !== undefined && (
              <div className="animate-in fade-in slide-in-from-bottom-12 duration-700 delay-200">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Data Quality & Accuracy</h2>

                <Card className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    {/* Confidence Score - Large Display */}
                    <div className="md:col-span-4 text-center p-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl border border-blue-200/50">
                      <div className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-2">Overall Confidence Score</div>
                      <div className={`text-6xl font-bold mb-2 ${(compute.data_confidence_score ?? 0) >= 80 ? 'text-green-600' :
                        (compute.data_confidence_score ?? 0) >= 60 ? 'text-yellow-600' :
                          'text-red-600'
                        }`}>
                        {(compute.data_confidence_score ?? 0).toFixed(0)}
                      </div>
                      <div className="text-sm text-gray-500">out of 100</div>
                      <div className="mt-4 text-xs text-gray-600">
                        {(compute.data_confidence_score ?? 0) >= 80 && '✓ High confidence - Excellent data quality'}
                        {(compute.data_confidence_score ?? 0) >= 60 && (compute.data_confidence_score ?? 0) < 80 && '⚠ Moderate confidence - Good data quality'}
                        {(compute.data_confidence_score ?? 0) < 60 && '⚠ Low confidence - Limited data quality'}
                      </div>
                    </div>

                    {/* Cloud Coverage */}
                    <Card className="p-4 flex flex-col justify-center bg-white">
                      <div className="flex items-center gap-3 mb-2">
                        <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M5.5 16a3.5 3.5 0 01-.369-6.98 4 4 0 117.753-1.977A4.5 4.5 0 1113.5 16h-8z" />
                        </svg>
                        <div className="text-sm font-medium text-gray-500">Cloud Coverage</div>
                      </div>
                      <div className="text-2xl font-bold text-gray-900">{(compute.cloud_coverage_percent ?? 0).toFixed(1)}%</div>
                      <div className="text-xs text-gray-400 mt-1">Sentinel-2 scenes</div>
                    </Card>

                    {/* GEDI Shots */}
                    <Card className="p-4 flex flex-col justify-center bg-white">
                      <div className="flex items-center gap-3 mb-2">
                        <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                        </svg>
                        <div className="text-sm font-medium text-gray-500">GEDI Shots</div>
                      </div>
                      <div className="text-2xl font-bold text-gray-900">{compute.gedi_shot_count ?? 0}</div>
                      <div className="text-xs text-gray-400 mt-1">Lidar measurements</div>
                    </Card>

                    {/* Pixel Count */}
                    <Card className="p-4 flex flex-col justify-center bg-white">
                      <div className="flex items-center gap-3 mb-2">
                        <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
                        </svg>
                        <div className="text-sm font-medium text-gray-500">Valid Pixels</div>
                      </div>
                      <div className="text-2xl font-bold text-gray-900">{(compute.pixel_count ?? 0).toLocaleString()}</div>
                      <div className="text-xs text-gray-400 mt-1">Data points analyzed</div>
                    </Card>

                    {/* Variability (StdDev) */}
                    <Card className="p-4 flex flex-col justify-center bg-white">
                      <div className="flex items-center gap-3 mb-2">
                        <svg className="w-5 h-5 text-purple-500" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
                        </svg>
                        <div className="text-sm font-medium text-gray-500">NDVI Variability</div>
                      </div>
                      <div className="text-2xl font-bold text-gray-900">{(compute.ndvi_stddev ?? 0).toFixed(3)}</div>
                      <div className="text-xs text-gray-400 mt-1">Standard deviation</div>
                    </Card>
                  </div>

                  {/* Explanation */}
                  <div className="mt-6 p-4 bg-gray-50 rounded-xl border border-gray-200/50">
                    <div className="flex items-start gap-3">
                      <svg className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                      </svg>
                      <div className="text-sm text-gray-600">
                        <strong className="font-semibold text-gray-900">Quality Indicators:</strong> The confidence score reflects data availability and reliability.
                        High pixel counts, low cloud coverage, and GEDI measurements increase confidence.
                        Variability (StdDev) indicates spatial heterogeneity in the analyzed area.
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            )}
          </div>

          {/* Sidebar: Tools & Upload */}
          <div className="lg:col-span-4 space-y-6">
            <Card className="p-6">
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">Tools</h3>
              <div className="space-y-4">
                <div className="p-4 rounded-2xl bg-gray-50 border border-gray-100">
                  <div className="text-sm font-medium text-gray-900 mb-2">Polygon Data</div>
                  <div className="font-mono text-xs text-gray-500 bg-white p-3 rounded-xl border border-gray-100 overflow-hidden text-ellipsis h-24">
                    {polygon ? JSON.stringify(polygon.geometry || polygon) : "No polygon selected"}
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-gray-50 border border-gray-100">
                  <div className="text-sm font-medium text-gray-900 mb-2">Upload Geometry</div>
                  <FileUpload onGeoJSON={onPolygon} />
                </div>
              </div>
            </Card>
          </div>

        </div>
      </main>
    </div>
  );
}

function MetricCardMinimal({ title, value, unit, sub, color }: { title: string, value: string, unit: string, sub?: string, color: string }) {
  return (
    <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100/50 flex flex-col items-start hover:shadow-md transition-shadow">
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-auto">{title}</span>
      <div className="mt-2">
        <span className="text-2xl font-bold text-gray-900 tracking-tight">{value}</span>
        <span className="text-xs text-gray-400 ml-1 font-medium">{unit}</span>
      </div>
      {sub && <span className="text-[10px] text-gray-400 font-medium mt-1 bg-gray-50 px-2 py-0.5 rounded-full">{sub}</span>}
    </div>
  );
}
