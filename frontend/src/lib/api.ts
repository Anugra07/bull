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
  carbon_biomass?: number;
  soc_total?: number;
  annual_co2?: number;
  co2_20yr?: number;
  risk_adjusted_co2?: number;
};

export const api = {
  createProject: (payload: { user_id: string; name: string; description?: string | null }) =>
    http<Project>(`/projects`, { method: "POST", body: JSON.stringify(payload) }),

  getProject: (project_id: string) =>
    http<Project>(`/projects/${encodeURIComponent(project_id)}`),

  listProjects: (user_id: string) =>
    http<Project[]>(`/projects?user_id=${encodeURIComponent(user_id)}`),

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

  analyze: (payload: { polygon_id?: string; geometry?: any }) =>
    http<AnalysisResult>(`/analysis`, { method: "POST", body: JSON.stringify(payload) }),

  compute: (payload: { project_id: string; polygon_id: string; fire_risk?: number; drought_risk?: number; trend_loss?: number }) =>
    http<ComputeResult>(`/compute`, { method: "POST", body: JSON.stringify(payload) }),

  getResults: (project_id?: string) => {
    const url = project_id 
      ? `/compute?project_id=${encodeURIComponent(project_id)}`
      : `/compute`;
    return http<ComputeResult[]>(url);
  },
};
