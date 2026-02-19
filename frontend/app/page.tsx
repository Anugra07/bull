"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import Button from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";

export default function HomePage() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      const { data } = await supabase.auth.getSession();
      setIsAuthenticated(!!data.session);
    };
    checkAuth();
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 section-fade">
      <section className="pt-16 pb-10">
        <div className="border-2 border-[var(--line-strong)] bg-[var(--surface)] p-8 md:p-12 rounded-xl shadow-[var(--shadow-soft)] relative overflow-hidden">
          <div className="absolute -right-12 -top-12 w-56 h-56 rounded-full bg-[var(--accent)]/10" />
          <div className="absolute -left-10 -bottom-16 w-60 h-60 rounded-full bg-[var(--warn)]/10" />

          <div className="relative z-10 max-w-4xl">
            <div className="inline-flex items-center gap-2 rounded-md border-2 border-[var(--line)] bg-[var(--surface-strong)] px-3 py-1.5 text-[11px] font-semibold tracking-[0.12em] uppercase text-[var(--muted)] mb-6">
              Carbon Project Intelligence
            </div>

            <h1 className="text-4xl md:text-6xl font-bold leading-tight text-[var(--ink)] mb-6">
              Professional land-carbon screening
              <span className="block text-[var(--accent)] mt-1">without black-box guesswork.</span>
            </h1>

            <p className="text-lg md:text-xl text-[var(--muted)] max-w-3xl mb-8 leading-relaxed">
              Draw or upload a parcel, run Earth Engine analysis, and get biomass, SOC, trend, risk, and credit-oriented projections.
              Built for pre-feasibility workflows with transparent, source-traceable outputs.
            </p>

            <div className="flex flex-col sm:flex-row items-start gap-3">
              {isAuthenticated ? (
                <>
                  <Link href="/dashboard">
                    <Button size="lg" className="min-w-[180px]">Open Dashboard</Button>
                  </Link>
                  <Link href="/guide">
                    <Button variant="secondary" size="lg" className="min-w-[180px]">Read Methodology</Button>
                  </Link>
                </>
              ) : (
                <>
                  <Link href="/signup">
                    <Button size="lg" className="min-w-[180px]">Create Account</Button>
                  </Link>
                  <Link href="/login">
                    <Button variant="secondary" size="lg" className="min-w-[180px]">Sign In</Button>
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="pb-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            ["10m", "Optical Resolution"],
            ["GEDI", "Lidar Biomass Layer"],
            ["0-200cm", "Depth-Selectable SOC"],
            ["20yr", "Forecast Horizon"],
          ].map(([value, label]) => (
            <Card key={label} className="p-4">
              <div className="text-2xl md:text-3xl font-bold text-[var(--ink)]">{value}</div>
              <div className="text-sm text-[var(--muted)] mt-1">{label}</div>
            </Card>
          ))}
        </div>
      </section>

      <section className="py-10">
        <h2 className="text-2xl md:text-3xl font-bold text-[var(--ink)] mb-6">Core Capabilities</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <Card className="h-full">
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-[var(--ink)] mb-2">Biomass + Structure</h3>
              <p className="text-[var(--muted)] text-sm leading-relaxed">
                GEDI canopy structure and AGBD routing with model-driven correction in compute workflows.
              </p>
            </CardContent>
          </Card>
          <Card className="h-full">
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-[var(--ink)] mb-2">SOC by Depth</h3>
              <p className="text-[var(--muted)] text-sm leading-relaxed">
                Layer-aware OpenLandMap SOC and bulk density calculations for 0-30cm, 0-100cm, and 0-200cm.
              </p>
            </CardContent>
          </Card>
          <Card className="h-full">
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-[var(--ink)] mb-2">Risk and Additionality</h3>
              <p className="text-[var(--muted)] text-sm leading-relaxed">
                Trend/fire/rainfall-informed risk adjustments and baseline vs project additionality outputs.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="py-10 mb-10">
        <Card className="p-8 bg-[var(--surface)]">
          <h2 className="text-2xl font-bold text-[var(--ink)] mb-3">Workflow</h2>
          <div className="grid md:grid-cols-3 gap-5 text-sm text-[var(--muted)]">
            <div className="border-2 border-[var(--line)] bg-[var(--surface-strong)] rounded-lg p-4">
              <div className="font-semibold text-[var(--ink)] mb-1">1. Define Area</div>
              Draw polygons on the map or upload GeoJSON/KML.
            </div>
            <div className="border-2 border-[var(--line)] bg-[var(--surface-strong)] rounded-lg p-4">
              <div className="font-semibold text-[var(--ink)] mb-1">2. Run Analysis</div>
              Extract environmental features and evaluate model-ready metrics.
            </div>
            <div className="border-2 border-[var(--line)] bg-[var(--surface-strong)] rounded-lg p-4">
              <div className="font-semibold text-[var(--ink)] mb-1">3. Evaluate Carbon</div>
              Review carbon stock, risk-adjusted CO₂, and additionality indicators.
            </div>
          </div>
        </Card>
      </section>
    </div>
  );
}
