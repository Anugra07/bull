"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, Project } from "@/lib/api";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [authed, setAuthed] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    const init = async () => {
      const { data } = await supabase.auth.getSession();
      const uid = data.session?.user.id || null;
      setAuthed(!!uid);
      setUserId(uid);
      setLoading(false);
      if (uid) {
        try {
          const list = await api.listProjects(uid);
          setProjects(list);
        } catch (e) {
          console.error("Failed to load projects:", e);
        }
      }
    };
    init();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="inline-block h-8 w-8 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin mb-4"></div>
          <p className="text-gray-600">Loading your projects...</p>
        </div>
      </div>
    );
  }

  if (!authed) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="max-w-md w-full">
          <Card>
            <CardHeader className="text-center pb-4">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-gray-900 text-white font-semibold text-xl mb-4 mx-auto">
                OG
              </div>
              <CardTitle className="text-2xl">Welcome to Offset Guesser</CardTitle>
            </CardHeader>
            <CardContent className="text-center space-y-4">
              <p className="text-gray-600">
                Please sign in to access your carbon offset analysis projects.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center pt-4">
                <Link href="/login">
                  <Button className="w-full sm:w-auto">Sign In</Button>
                </Link>
                <Link href="/signup">
                  <Button variant="secondary" className="w-full sm:w-auto">Create Account</Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const handleCreateProject = async () => {
    if (!userId || !name.trim()) return;
    try {
      setCreating(true);
      const p = await api.createProject({ user_id: userId, name: name.trim(), description: desc.trim() || null });
      setProjects((prev) => [p, ...prev]);
      setName("");
      setDesc("");
      setShowCreate(false);
      router.push(`/projects/${p.id}`);
    } catch (e: any) {
      alert(e.message || "Failed to create project");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
      {/* Header Section */}
      <div className="mb-8 lg:mb-12">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Your Projects</h1>
            <p className="text-lg text-gray-600">
              Analyze land parcels and estimate carbon offset potential
            </p>
          </div>
          {projects.length > 0 && (
            <Button
              onClick={() => setShowCreate(!showCreate)}
              className="hidden sm:flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Project
            </Button>
          )}
        </div>
        
        {/* Stats Bar */}
        {projects.length > 0 && (
          <div className="flex items-center gap-6 mt-6">
            <span className="text-sm text-gray-600">
              <span className="font-semibold text-gray-900">{projects.length}</span> project{projects.length !== 1 ? 's' : ''}
            </span>
          </div>
        )}
      </div>

      {/* Create Project Section */}
      {showCreate && (
        <Card className="mb-8 border-gray-300">
          <CardHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <CardTitle className="text-xl">Create New Project</CardTitle>
            </div>
            <p className="text-sm text-gray-600">Start analyzing a new land parcel for carbon offset potential</p>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">
                  Project Name <span className="text-red-500">*</span>
                </label>
                <Input
                  placeholder="e.g. Karnataka Mangrove Restoration"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && name.trim()) handleCreateProject();
                  }}
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">
                  Description <span className="text-gray-400 text-xs font-normal">(Optional)</span>
                </label>
                <Input
                  placeholder="Brief description of your project..."
                  value={desc}
                  onChange={(e) => setDesc(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && name.trim()) handleCreateProject();
                  }}
                  className="w-full"
                />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button
                onClick={handleCreateProject}
                disabled={!userId || !name.trim() || creating}
                loading={creating}
              >
                Create Project
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setShowCreate(false);
                  setName("");
                  setDesc("");
                }}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Projects Grid or Empty State */}
      {projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center min-h-[500px]">
          <div className="max-w-2xl w-full">
            {/* Empty State Card */}
            <Card className="border-dashed">
              <CardContent className="text-center py-16 px-8">
                {/* Icon */}
                <div className="inline-flex items-center justify-center w-20 h-20 rounded-xl bg-gray-100 mb-6">
                  <svg className="w-10 h-10 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                
                {/* Heading */}
                <h2 className="text-2xl font-bold text-gray-900 mb-2">No Projects Yet</h2>
                <p className="text-lg text-gray-600 mb-2 max-w-md mx-auto">
                  Create your first project to start analyzing land parcels and estimating carbon offset potential.
                </p>
                <p className="text-sm text-gray-500 mb-8 max-w-md mx-auto">
                  Get detailed biomass analysis, ecosystem classification, and 20-year carbon forecasts in minutes.
                </p>

                {/* CTA Button */}
                <Button
                  onClick={() => setShowCreate(true)}
                  size="lg"
                  className="px-8"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Create Your First Project
                </Button>

                {/* Quick Info Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-12 pt-8 border-t border-gray-200">
                  <div className="text-center">
                    <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center mx-auto mb-2">
                      <svg className="w-5 h-5 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                    </div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-1">GEDI Biomass</h3>
                    <p className="text-xs text-gray-600">LIDAR-based measurements</p>
                  </div>
                  <div className="text-center">
                    <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center mx-auto mb-2">
                      <svg className="w-5 h-5 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-1">Ecosystem Class</h3>
                    <p className="text-xs text-gray-600">Automatic land cover</p>
                  </div>
                  <div className="text-center">
                    <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center mx-auto mb-2">
                      <svg className="w-5 h-5 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                    </div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-1">20-Year Forecast</h3>
                    <p className="text-xs text-gray-600">Risk-adjusted estimates</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Projects Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((p) => (
              <Card
                key={p.id}
                className="cursor-pointer active:opacity-70"
                onClick={() => router.push(`/projects/${p.id}`)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-lg font-bold text-gray-900 line-clamp-2 mb-1">
                        {p.name}
                      </CardTitle>
                    </div>
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                      <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>
                </CardHeader>
                
                <CardContent>
                  <p className="text-sm text-gray-600 mb-4 line-clamp-2 min-h-[40px]">
                    {p.description || (
                      <span className="text-gray-400">No description provided</span>
                    )}
                  </p>
                  
                  <div className="flex items-center justify-between pt-4 border-t border-gray-200">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      <span className="text-xs text-gray-500">
                        {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </span>
                    </div>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/projects/${p.id}`);
                      }}
                    >
                      Open
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Create Project Floating Button for Mobile */}
          {!showCreate && (
            <div className="fixed bottom-6 right-6 sm:hidden z-50">
              <button
                onClick={() => setShowCreate(true)}
                className="w-14 h-14 rounded-full bg-gray-900 text-white active:opacity-80 flex items-center justify-center"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
