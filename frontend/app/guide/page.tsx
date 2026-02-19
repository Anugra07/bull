"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { BookOpen, Satellite, Calculator, AlertTriangle, Leaf, Layers, Droplets } from "lucide-react";
import { Card } from "@/components/ui/Card";

export default function GuidePage() {
  const [activeSection, setActiveSection] = useState("overview");

  const sections = [
    { id: "overview", label: "Overview", icon: BookOpen },
    { id: "data-sources", label: "Data Sources", icon: Satellite },
    { id: "carbon-logic", label: "Carbon Logic", icon: Calculator },
    { id: "risk-factors", label: "Risk Factors", icon: AlertTriangle },
  ];

  const scrollToSection = (id: string) => {
    setActiveSection(id);
    const element = document.getElementById(id);
    if (element) element.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="min-h-screen text-[var(--ink)] pt-6 section-fade">
      <div className="max-w-7xl mx-auto w-full px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        <aside className="hidden lg:block lg:col-span-3">
          <div className="sticky top-24 space-y-2">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => scrollToSection(section.id)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-md text-xs font-semibold tracking-wide border-2 transition-colors ${
                  activeSection === section.id
                    ? "bg-[var(--accent)] text-white border-[var(--accent-strong)]"
                    : "bg-[var(--surface-strong)] text-[var(--muted)] border-[var(--line)] hover:text-[var(--ink)]"
                }`}
              >
                <section.icon className="w-4 h-4" />
                {section.label}
              </button>
            ))}
          </div>
        </aside>

        <div className="lg:col-span-9 space-y-12 pb-16">
          <section id="overview" className="scroll-mt-24">
            <Card className="p-7 bg-[var(--surface)]">
              <h2 className="text-3xl font-bold mb-3">Methodology Overview</h2>
              <p className="text-[var(--muted)] leading-relaxed">
                The platform combines Earth Engine feature extraction, ecosystem-aware carbon logic, and model-assisted inference in the compute pipeline.
                It is designed for pre-feasibility analysis, screening, and portfolio-level prioritization.
              </p>

              <div className="grid md:grid-cols-3 gap-4 mt-6">
                <div className="p-4 rounded-lg border-2 border-[var(--line)] bg-[var(--surface-strong)]">
                  <Satellite className="w-6 h-6 text-[var(--accent)] mb-2" />
                  <h3 className="font-semibold mb-1">Satellite Inputs</h3>
                  <p className="text-sm text-[var(--muted)]">Sentinel-2, GEDI, OpenLandMap, CHIRPS, MODIS, SRTM.</p>
                </div>
                <div className="p-4 rounded-lg border-2 border-[var(--line)] bg-[var(--surface-strong)]">
                  <Leaf className="w-6 h-6 text-[var(--accent)] mb-2" />
                  <h3 className="font-semibold mb-1">Ecosystem Rules</h3>
                  <p className="text-sm text-[var(--muted)]">WorldCover-based class logic and climate-aware sequestration rates.</p>
                </div>
                <div className="p-4 rounded-lg border-2 border-[var(--line)] bg-[var(--surface-strong)]">
                  <Layers className="w-6 h-6 text-[var(--accent)] mb-2" />
                  <h3 className="font-semibold mb-1">Depth-Aware SOC</h3>
                  <p className="text-sm text-[var(--muted)]">SOC layer summation for 0-30cm, 0-100cm, and 0-200cm depths.</p>
                </div>
              </div>
            </Card>
          </section>

          <section id="data-sources" className="scroll-mt-24">
            <h2 className="text-2xl font-bold mb-5">Data Sources</h2>
            <Card className="overflow-hidden">
              <div className="divide-y-2 divide-[var(--line)]">
                <SourceRow
                  icon={<Satellite className="w-5 h-5" />}
                  title="Sentinel-2 (COPERNICUS/S2_SR_HARMONIZED)"
                  text="NDVI/EVI vegetation features from cloud-masked composites at 10m-scale analysis."
                />
                <SourceRow
                  icon={<Leaf className="w-5 h-5" />}
                  title="GEDI (L2A/L4A)"
                  text="Canopy structure (`rh98`) and aboveground biomass density (`agbd`) with quality-aware routing and fallback handling."
                />
                <SourceRow
                  icon={<Layers className="w-5 h-5" />}
                  title="OpenLandMap Soil Layers"
                  text="Soil organic carbon and bulk density rasters used in layer-sum SOC calculations."
                />
                <SourceRow
                  icon={<Droplets className="w-5 h-5" />}
                  title="CHIRPS, MODIS, SRTM"
                  text="Rainfall totals/anomalies, burn history, and terrain derivatives (elevation/slope/aspect)."
                />
              </div>
            </Card>
          </section>

          <section id="carbon-logic" className="scroll-mt-24">
            <h2 className="text-2xl font-bold mb-5">Carbon Logic</h2>
            <div className="space-y-5">
              <FormulaCard
                title="Biomass Carbon"
                formula="C_biomass (tC/ha) = biomass_total (t/ha) × 0.47"
                text="Total biomass includes aboveground and belowground components; carbon fraction is fixed at 0.47."
              />
              <FormulaCard
                title="SOC Layer Summation"
                formula="SOC_layer (tC/ha) = 0.1 × BD(g/cm³) × SOC(g/kg) × thickness(cm)"
                text="Selected depth profile is summed across all included layers to produce SOC per hectare."
              />
              <FormulaCard
                title="Annual and 20-Year CO₂"
                formula="annual_co2 = sequestration_rate × area_ha,  co2_20yr = annual_co2 × 20"
                text="Sequestration rate depends on ecosystem and climate/rainfall rules in the backend ecosystem service."
              />
            </div>
          </section>

          <section id="risk-factors" className="scroll-mt-24">
            <h2 className="text-2xl font-bold mb-5">Risk Factors</h2>
            <Card className="p-6 bg-[var(--surface)] border-[var(--line-strong)]">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-6 h-6 text-[var(--warn)] mt-1" />
                <div>
                  <h3 className="text-lg font-semibold mb-2">Risk-Adjusted Outcome</h3>
                  <p className="text-[var(--muted)] text-sm mb-4">
                    Fire risk, drought risk, and trend-loss factors are combined with trend indicators (NDVI trend, burn history, rainfall anomaly)
                    to produce conservative risk-adjusted 20-year CO₂ estimates.
                  </p>
                  <div className="grid sm:grid-cols-3 gap-3 text-sm">
                    <div className="rounded-lg border-2 border-[var(--line)] bg-[var(--surface-strong)] p-3">
                      <div className="font-semibold">Fire Risk</div>
                      <div className="text-[var(--muted)] text-xs mt-1">Base ecosystem risk + burn-history adjustments</div>
                    </div>
                    <div className="rounded-lg border-2 border-[var(--line)] bg-[var(--surface-strong)] p-3">
                      <div className="font-semibold">Drought Risk</div>
                      <div className="text-[var(--muted)] text-xs mt-1">Raised under severe rainfall anomaly</div>
                    </div>
                    <div className="rounded-lg border-2 border-[var(--line)] bg-[var(--surface-strong)] p-3">
                      <div className="font-semibold">Trend Loss</div>
                      <div className="text-[var(--muted)] text-xs mt-1">Adjusted by NDVI trajectory class</div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </section>
        </div>
      </div>
    </div>
  );
}

function SourceRow({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="p-5 flex gap-4 items-start bg-[var(--surface-strong)]">
      <div className="p-2 border-2 border-[var(--line)] rounded-md text-[var(--accent)] mt-0.5">{icon}</div>
      <div>
        <h3 className="font-semibold text-[var(--ink)]">{title}</h3>
        <p className="text-sm text-[var(--muted)] mt-1">{text}</p>
      </div>
    </div>
  );
}

function FormulaCard({ title, formula, text }: { title: string; formula: string; text: string }) {
  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-[var(--ink)] mb-3">{title}</h3>
      <div className="bg-[var(--surface)] rounded-md p-3 font-mono text-sm text-[var(--ink)] mb-3 border-2 border-[var(--line)]">
        {formula}
      </div>
      <p className="text-sm text-[var(--muted)]">{text}</p>
    </Card>
  );
}
