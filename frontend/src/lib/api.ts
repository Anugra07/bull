const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

async function http<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export type Project = { id: string; user_id: string; name: string; description?: string | null };
export type PolygonResult = { id: string; project_id: string; area_m2: number; bbox: number[] };
export type PolygonWithGeometry = PolygonResult & { geometry: any };
export type AnalysisResult = {
  ndvi: number;
  evi: number;
  biomass: number;
  canopy_height: number;
  soc: number;
  bulk_density: number;
  rainfall: number;
  elevation: number;
  slope: number;
  // Time-series trends
  ndvi_trend: number;
  ndvi_trend_interpretation: string;
  fire_burn_percent: number;
  fire_recent_burn: boolean;
  rainfall_anomaly_percent: number;
  trend_classification: string;
  // QA/QC Metrics
  pixel_count?: number;
  ndvi_stddev?: number;
  soc_stddev?: number;
  rainfall_stddev?: number;
  cloud_coverage_percent?: number;
  gedi_shot_count?: number;
  data_confidence_score?: number;
};

export type ComputeResult = {
  id: string;
  project_id: string;
  ndvi?: number;
  evi?: number;
  biomass?: number;
  canopy_height?: number;
  soc?: number;
  bulk_density?: number;
  rainfall?: number;
  elevation?: number;
  slope?: number;
  land_cover?: number;
  carbon_biomass?: number;
  carbon_biomass_total?: number; // NEW
  soc_total?: number;
  total_carbon_stock?: number;   // NEW
  biomass_source?: string;       // NEW: Track data source (gedi_l4a_monthly, esa_cci_2020, etc.)
  annual_co2?: number;
  co2_20yr?: number;
  risk_adjusted_co2?: number;
  ecosystem_type?: string;
  // Time-series trends
  ndvi_trend?: number;
  ndvi_trend_interpretation?: string;
  fire_burn_percent?: number;
  fire_recent_burn?: boolean;
  rainfall_anomaly_percent?: number;
  trend_classification?: string;
  baseline_condition?: string;

  // BASELINE Carbon Stock (MRV Compliance)
  baseline_biomass_carbon?: number;
  baseline_soc_total?: number;
  baseline_annual_co2?: number;
  baseline_co2_20yr?: number;
  baseline_scenario?: string;

  // PROJECT Carbon Stock (with intervention)
  project_annual_co2?: number;
  project_co2_20yr?: number;

  // ADDITIONALITY (Carbon Credits)
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
};

export const api = {
  createProject: (payload: { user_id: string; name: string; description?: string | null }) =>
    http<Project>(`/projects`, { method: "POST", body: JSON.stringify(payload) }),

  getProject: (project_id: string) =>
    http<Project>(`/projects/${encodeURIComponent(project_id)}`),

  listProjects: (user_id: string) =>
    http<Project[]>(`/projects?user_id=${encodeURIComponent(user_id)}`),

  deleteProject: (project_id: string) =>
    http<{ message: string; id: string }>(`/projects/${encodeURIComponent(project_id)}`, { method: "DELETE" }),

  createPolygon: (payload: { project_id: string; geometry: any }) =>
    http<PolygonResult>(`/polygons`, { method: "POST", body: JSON.stringify(payload) }),

  getPolygon: (polygon_id: string) =>
    http<PolygonWithGeometry>(`/polygons/${encodeURIComponent(polygon_id)}`),

  listPolygons: (project_id?: string) => {
    const url = project_id
      ? `/polygons?project_id=${encodeURIComponent(project_id)}`
      : `/polygons`;
    return http<PolygonWithGeometry[]>(url);
  },

  analyze: (payload: { polygon_id?: string; geometry?: any; soil_depth?: string }) =>
    http<AnalysisResult>(`/analysis`, { method: "POST", body: JSON.stringify(payload) }),

  compute: (payload: { project_id: string; polygon_id: string; fire_risk?: number; drought_risk?: number; trend_loss?: number; soil_depth?: string }) =>
    http<ComputeResult>(`/compute`, { method: "POST", body: JSON.stringify(payload) }),

  getResults: (project_id?: string) => {
    const url = project_id
      ? `/compute?project_id=${encodeURIComponent(project_id)}`
      : `/compute`;
    return http<ComputeResult[]>(url);
  },
};
