"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, BookOpen, Satellite, Calculator, AlertTriangle, Leaf, Layers, Droplets } from "lucide-react";
import { Card } from "@/components/ui/Card";
import Button from "@/components/ui/Button";

export default function GuidePage() {
    const router = useRouter();
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
        if (element) {
            element.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    };

    return (
        <div className="min-h-screen bg-[#F5F5F7] font-sans text-gray-900 flex flex-col pt-6">
            <div className="flex-1 max-w-7xl mx-auto w-full px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Sidebar Navigation */}
                <div className="hidden lg:block lg:col-span-3">
                    <div className="sticky top-24 space-y-2">
                        {sections.map((section) => (
                            <button
                                key={section.id}
                                onClick={() => scrollToSection(section.id)}
                                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${activeSection === section.id
                                    ? "bg-white text-gray-900 shadow-sm"
                                    : "text-gray-500 hover:bg-white/50 hover:text-gray-700"
                                    }`}
                            >
                                <section.icon className={`w-4 h-4 ${activeSection === section.id ? "text-blue-600" : "text-gray-400"}`} />
                                {section.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Main Content */}
                <div className="lg:col-span-9 space-y-12 pb-24">

                    {/* Overview */}
                    <section id="overview" className="scroll-mt-24">
                        <div className="mb-6">
                            <h2 className="text-2xl font-bold text-gray-900 mb-2">Overview</h2>
                            <p className="text-gray-600 leading-relaxed">
                                The Carbon Offset Land Analyzer uses advanced satellite imagery and geospatial data to estimate the environmental impact and carbon sequestration potential of land parcels. This guide explains how we calculate these metrics.
                            </p>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <Card className="p-5 border-none shadow-sm bg-blue-50/50">
                                <Satellite className="w-8 h-8 text-blue-600 mb-3" />
                                <h3 className="font-semibold text-gray-900 mb-1">Satellite Analysis</h3>
                                <p className="text-sm text-gray-600">Real-time analysis using Sentinel-2 and GEDI data.</p>
                            </Card>
                            <Card className="p-5 border-none shadow-sm bg-green-50/50">
                                <Leaf className="w-8 h-8 text-green-600 mb-3" />
                                <h3 className="font-semibold text-gray-900 mb-1">Ecosystem Logic</h3>
                                <p className="text-sm text-gray-600">Tailored calculations for Forests, Wetlands, and more.</p>
                            </Card>
                            <Card className="p-5 border-none shadow-sm bg-amber-50/50">
                                <Layers className="w-8 h-8 text-amber-600 mb-3" />
                                <h3 className="font-semibold text-gray-900 mb-1">Soil Depth</h3>
                                <p className="text-sm text-gray-600">Variable soil depth analysis for accurate SOC estimates.</p>
                            </Card>
                        </div>
                    </section>

                    {/* Data Sources */}
                    <section id="data-sources" className="scroll-mt-24">
                        <h2 className="text-2xl font-bold text-gray-900 mb-6">Data Sources</h2>
                        <Card className="overflow-hidden">
                            <div className="divide-y divide-gray-100">
                                <div className="p-5 flex gap-4 items-start">
                                    <div className="p-2 bg-blue-100 rounded-lg text-blue-600 mt-1"><Satellite className="w-5 h-5" /></div>
                                    <div>
                                        <h3 className="font-semibold text-gray-900">Sentinel-2 (ESA)</h3>
                                        <p className="text-sm text-gray-600 mt-1">Used for calculating Vegetation Indices (NDVI, EVI) to assess plant health and density. 10m resolution.</p>
                                    </div>
                                </div>
                                <div className="p-5 flex gap-4 items-start">
                                    <div className="p-2 bg-green-100 rounded-lg text-green-600 mt-1"><Leaf className="w-5 h-5" /></div>
                                    <div>
                                        <h3 className="font-semibold text-gray-900">GEDI (NASA)</h3>
                                        <p className="text-sm text-gray-600 mt-1">Global Ecosystem Dynamics Investigation lidar data used for Canopy Height and Biomass estimation.</p>
                                    </div>
                                </div>
                                <div className="p-5 flex gap-4 items-start">
                                    <div className="p-2 bg-amber-100 rounded-lg text-amber-600 mt-1"><Layers className="w-5 h-5" /></div>
                                    <div>
                                        <h3 className="font-semibold text-gray-900">OpenLandMap</h3>
                                        <p className="text-sm text-gray-600 mt-1">Provides Soil Organic Carbon (SOC) and Bulk Density data at various depths.</p>
                                    </div>
                                </div>
                                <div className="p-5 flex gap-4 items-start">
                                    <div className="p-2 bg-cyan-100 rounded-lg text-cyan-600 mt-1"><Droplets className="w-5 h-5" /></div>
                                    <div>
                                        <h3 className="font-semibold text-gray-900">CHIRPS & SRTM</h3>
                                        <p className="text-sm text-gray-600 mt-1">Rainfall data (CHIRPS) and Elevation/Slope data (SRTM) for environmental context.</p>
                                    </div>
                                </div>
                            </div>
                        </Card>
                    </section>

                    {/* Carbon Logic */}
                    <section id="carbon-logic" className="scroll-mt-24">
                        <h2 className="text-2xl font-bold text-gray-900 mb-6">Carbon Calculation Logic</h2>
                        <div className="space-y-6">
                            <Card className="p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-green-500" />
                                    Biomass Carbon
                                </h3>
                                <div className="bg-gray-50 rounded-xl p-4 font-mono text-sm text-gray-700 mb-4 border border-gray-200">
                                    Carbon = Biomass (t/ha) × 0.47
                                </div>
                                <p className="text-gray-600 text-sm">
                                    We estimate the total above-ground biomass density and multiply it by the carbon fraction (0.47) to get the carbon stock in vegetation.
                                </p>
                            </Card>

                            <Card className="p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-amber-500" />
                                    Soil Organic Carbon (SOC)
                                </h3>
                                <div className="bg-gray-50 rounded-xl p-4 font-mono text-sm text-gray-700 mb-4 border border-gray-200">
                                    SOC Total = (SOC% / 100) × Bulk Density × Depth × Area
                                </div>
                                <p className="text-gray-600 text-sm">
                                    Calculated based on the selected soil depth (0-30cm, 0-100cm, etc.). We aggregate SOC percentage and bulk density layers to determine the total carbon stored in the soil.
                                </p>
                            </Card>

                            <Card className="p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                                    Sequestration Potential
                                </h3>
                                <div className="bg-gray-50 rounded-xl p-4 font-mono text-sm text-gray-700 mb-4 border border-gray-200">
                                    Annual CO₂ = Ecosystem Rate × Area (ha)
                                </div>
                                <p className="text-gray-600 text-sm mb-4">
                                    We classify the land cover (Forest, Wetland, etc.) and apply specific sequestration rates:
                                </p>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                                    <div className="bg-gray-100 p-2 rounded text-center">Forest: 8.0 t/ha/yr</div>
                                    <div className="bg-gray-100 p-2 rounded text-center">Mangrove: 10.0 t/ha/yr</div>
                                    <div className="bg-gray-100 p-2 rounded text-center">Wetland: 4.0 t/ha/yr</div>
                                    <div className="bg-gray-100 p-2 rounded text-center">Grassland: 1.5 t/ha/yr</div>
                                </div>
                            </Card>
                        </div>
                    </section>

                    {/* Risk Factors */}
                    <section id="risk-factors" className="scroll-mt-24">
                        <h2 className="text-2xl font-bold text-gray-900 mb-6">Risk Factors</h2>
                        <Card className="p-6 bg-red-50/30 border-red-100">
                            <div className="flex items-start gap-4">
                                <AlertTriangle className="w-6 h-6 text-red-500 mt-1" />
                                <div>
                                    <h3 className="font-semibold text-gray-900 mb-2">Risk-Adjusted Estimates</h3>
                                    <p className="text-gray-600 text-sm mb-4">
                                        We discount the potential carbon revenue based on ecosystem-specific risks to ensure conservative and realistic estimates.
                                    </p>
                                    <div className="bg-white rounded-xl p-4 border border-red-100 space-y-2">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600">Fire Risk</span>
                                            <span className="font-medium text-gray-900">1% - 8% deduction</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600">Drought Risk</span>
                                            <span className="font-medium text-gray-900">1% - 8% deduction</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600">Trend Loss</span>
                                            <span className="font-medium text-gray-900">1% - 5% deduction</span>
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
