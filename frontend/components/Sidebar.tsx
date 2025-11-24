"use client";

import Button from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";

export default function Sidebar({
  hasPolygon,
  onAnalyze,
  busy = false,
}: {
  hasPolygon: boolean;
  onAnalyze: () => void;
  busy?: boolean;
}) {
  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Project Inputs Card */}
      <Card className="border-gray-300">
        <CardHeader className="bg-gray-50 border-b border-gray-200/60">
          <CardTitle className="text-base sm:text-lg flex items-center gap-2">
            <svg className="w-5 h-5 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            Project Inputs
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 rounded-xl bg-gray-50 border border-gray-200">
              <svg className="w-5 h-5 text-gray-900 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-gray-900">Draw on Map</p>
                <p className="text-xs text-gray-600 mt-0.5">Use the drawing tools on the map</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-xl bg-gray-50 border border-gray-200">
              <svg className="w-5 h-5 text-gray-900 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <div>
                <p className="text-sm font-medium text-gray-900">Upload File</p>
                <p className="text-xs text-gray-600 mt-0.5">Upload GeoJSON or KML file</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Polygon Status & Analyze */}
      <Card className={`border-gray-300 ${hasPolygon ? 'bg-gray-50/50' : ''}`}>
        <CardHeader className={`border-b border-gray-200/60 ${hasPolygon ? 'bg-gray-50' : ''}`}>
          <CardTitle className="text-base sm:text-lg flex items-center gap-2">
            <svg className={`w-5 h-5 ${hasPolygon ? 'text-gray-900' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Polygon Status
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-xl bg-white border border-gray-200">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${hasPolygon ? 'bg-gray-900' : 'bg-gray-300'}`}></div>
                <span className={`font-medium ${hasPolygon ? 'text-gray-900' : 'text-gray-500'}`}>
                  {hasPolygon ? 'Ready' : 'Not Ready'}
                </span>
              </div>
              {hasPolygon && (
                <svg className="w-5 h-5 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>

            <Button
              disabled={!hasPolygon || busy}
              onClick={onAnalyze}
              loading={busy}
              className={`w-full py-4 text-base font-semibold`}
            >
              {busy ? (
                <span className="flex items-center gap-2">
                  Analyzing...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Analyze Land
                </span>
              )}
            </Button>

            {busy && (
              <div className="mt-4 p-4 rounded-xl bg-gray-50 border border-gray-200">
                <p className="text-sm text-gray-900 font-medium mb-1">Processing Analysis</p>
                <p className="text-xs text-gray-600">
                  This may take 30-60 seconds. We're analyzing vegetation, biomass, soil, and terrain metrics...
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Quick Info */}
      <Card className="border-gray-300 bg-gray-50/50">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Analysis Includes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              GEDI LIDAR Biomass
            </li>
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Ecosystem Classification
            </li>
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              20-Year Carbon Forecast
            </li>
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Risk-Adjusted Estimates
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
