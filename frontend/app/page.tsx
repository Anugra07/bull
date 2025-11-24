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
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      {/* Hero Section */}
      <section className="pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-gray-300 bg-gray-50 px-4 py-1.5 text-xs font-medium text-gray-900 mb-6">
          AI-Powered Carbon Offset Analysis
        </div>
        
        <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-gray-900 mb-6">
          Estimate Carbon Potential
          <span className="block mt-2">
            For Any Land Parcel
          </span>
        </h1>
        
        <p className="text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto mb-10 leading-relaxed">
          Analyze land, estimate carbon sequestration potential, and make climate projects real with 
          <span className="font-semibold text-gray-900"> GEDI biomass data</span>, 
          <span className="font-semibold text-gray-900"> ecosystem classification</span>, and 
          <span className="font-semibold text-gray-900"> AI-powered geospatial analysis</span>.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          {isAuthenticated ? (
            <>
              <Link href="/dashboard">
                <Button size="lg" className="px-8">
                  Go to Dashboard
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button variant="secondary" size="lg" className="px-8">
                  View Projects
                </Button>
              </Link>
            </>
          ) : (
            <>
              <Link href="/signup">
                <Button size="lg" className="px-8">
                  Get Started Free
                </Button>
              </Link>
              <Link href="/login">
                <Button variant="secondary" size="lg" className="px-8">
                  Sign In
                </Button>
              </Link>
            </>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto mb-20">
          <div className="text-center">
            <div className="text-3xl md:text-4xl font-bold text-gray-900 mb-1">10m</div>
            <div className="text-sm text-gray-600">Resolution</div>
          </div>
          <div className="text-center">
            <div className="text-3xl md:text-4xl font-bold text-gray-900 mb-1">GEDI</div>
            <div className="text-sm text-gray-600">LIDAR Data</div>
          </div>
          <div className="text-center">
            <div className="text-3xl md:text-4xl font-bold text-gray-900 mb-1">100%</div>
            <div className="text-sm text-gray-600">Ecosystem-Aware</div>
          </div>
          <div className="text-center">
            <div className="text-3xl md:text-4xl font-bold text-gray-900 mb-1">20yr</div>
            <div className="text-sm text-gray-600">Forecast</div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-gray-900 mb-12">
          Everything You Need for Carbon Offset Projects
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="border-gray-300">
            <CardContent className="p-8">
              <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">GEDI Biomass Analysis</h3>
              <p className="text-gray-600 leading-relaxed">
                Direct LIDAR-based Above Ground Biomass measurements from NASA's GEDI mission. Most accurate biomass estimates available.
              </p>
            </CardContent>
          </Card>

          <Card className="border-gray-300">
            <CardContent className="p-8">
              <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Ecosystem Classification</h3>
              <p className="text-gray-600 leading-relaxed">
                Automatic land cover classification using ESA WorldCover. Ecosystem-specific sequestration rates and risk factors.
              </p>
            </CardContent>
          </Card>

          <Card className="border-gray-300">
            <CardContent className="p-8">
              <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Risk-Adjusted Forecasts</h3>
              <p className="text-gray-600 leading-relaxed">
                20-year carbon sequestration forecasts with fire, drought, and degradation risk adjustments. Realistic projections.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-16 bg-gray-50 rounded-3xl mb-16">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-center text-gray-900 mb-12">
            How It Works
          </h2>
          
          <div className="space-y-8">
            <div className="flex gap-6">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gray-900 text-white flex items-center justify-center font-bold text-lg">1</div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Draw or Upload Your Land Parcel</h3>
                <p className="text-gray-600">Use our interactive map to draw a polygon or upload a GeoJSON/KML file. Any size, anywhere in the world.</p>
              </div>
            </div>
            
            <div className="flex gap-6">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gray-900 text-white flex items-center justify-center font-bold text-lg">2</div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">AI Analyzes the Land</h3>
                <p className="text-gray-600">Our system analyzes vegetation indices, biomass (GEDI LIDAR), soil carbon, elevation, rainfall, and ecosystem type using Google Earth Engine.</p>
              </div>
            </div>
            
            <div className="flex gap-6">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gray-900 text-white flex items-center justify-center font-bold text-lg">3</div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Get Carbon Forecasts</h3>
                <p className="text-gray-600">Receive detailed carbon sequestration estimates with ecosystem-specific rates and risk-adjusted 20-year projections. Export reports for investors.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="text-center py-16 mb-16">
        <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
          Ready to Estimate Carbon Potential?
        </h2>
        <p className="text-xl text-gray-600 mb-8">
          Start analyzing your land parcels today. No credit card required.
        </p>
        {!isAuthenticated && (
          <Link href="/signup">
            <Button size="lg" className="px-8">
              Get Started Free
            </Button>
          </Link>
        )}
      </section>
    </div>
  );
}
