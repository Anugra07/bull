export default function HomePage() {
  return (
    <main className="py-12">
      <section className="text-center max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/70 px-3 py-1 text-xs text-zinc-700 shadow-sm">Carbon + Nature Intelligence</div>
        <h1 className="mt-6 text-4xl md:text-5xl font-semibold tracking-tight">Analyze land. Estimate carbon. Make climate projects real.</h1>
        <p className="mt-4 text-zinc-600 text-lg">Upload or draw a polygon and get NDVI, biomass, soil, and terrain metrics with a carbon forecast — in minutes.</p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <a href="/login" className="inline-flex h-12 rounded-2xl bg-black px-5 text-white items-center justify-center shadow-sm hover:bg-zinc-900">Get Started</a>
          <a href="/dashboard" className="inline-flex h-12 rounded-2xl border border-zinc-200 bg-white px-5 items-center justify-center hover:bg-zinc-50">Go to Dashboard</a>
        </div>
      </section>

      <section className="mt-14 grid grid-cols-1 md:grid-cols-3 gap-4 max-w-6xl mx-auto">
        <div className="rounded-3xl border border-zinc-200 bg-white/70 p-6 shadow-sm">
          <div className="text-sm font-medium text-zinc-700">Vegetation</div>
          <div className="mt-2 text-lg font-semibold">NDVI & EVI</div>
          <p className="mt-2 text-sm text-zinc-600">Sentinel-2 vegetation indices aggregated over your area of interest.</p>
        </div>
        <div className="rounded-3xl border border-zinc-200 bg-white/70 p-6 shadow-sm">
          <div className="text-sm font-medium text-zinc-700">Biomass & Soil</div>
          <div className="mt-2 text-lg font-semibold">Carbon Potential</div>
          <p className="mt-2 text-sm text-zinc-600">Proxy biomass, SOC %, bulk density — compute carbon over 20 years.</p>
        </div>
        <div className="rounded-3xl border border-zinc-200 bg-white/70 p-6 shadow-sm">
          <div className="text-sm font-medium text-zinc-700">Terrain & Rain</div>
          <div className="mt-2 text-lg font-semibold">Elevation & Climate</div>
          <p className="mt-2 text-sm text-zinc-600">SRTM elevation and CHIRPS rainfall to understand feasibility.</p>
        </div>
      </section>
    </main>
  );
}
