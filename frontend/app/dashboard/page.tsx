"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { api, Project } from "@/lib/api";
import { Plus, ArrowRight, FolderOpen, LogOut } from "lucide-react";
import Link from "next/link";
import Button from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export default function Dashboard() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const checkAuth = async () => {
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        router.push("/login");
        return;
      }
      setUser(data.session.user);
      loadProjects(data.session.user.id);
    };
    checkAuth();
  }, [router]);

  const loadProjects = async (userId: string) => {
    try {
      setLoading(true);
      const data = await api.listProjects(userId);
      setProjects(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!user) return;
    const name = prompt("Enter project name:");
    if (!name) return;
    try {
      const newProject = await api.createProject({
        user_id: user.id,
        name,
        description: "New carbon analysis project",
      });
      router.push(`/projects/${newProject.id}`);
    } catch (err) {
      alert("Failed to create project");
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push("/");
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F5F5F7]">
        <div className="animate-pulse flex flex-col items-center">
          <div className="h-12 w-12 bg-gray-200 rounded-full mb-4"></div>
          <div className="h-4 w-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F5F5F7] font-sans text-gray-900">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-[#F5F5F7]/80 backdrop-blur-md border-b border-gray-200/50">
        <div className="max-w-5xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-900 rounded-xl flex items-center justify-center text-white shadow-lg shadow-gray-900/20">
              <FolderOpen className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold tracking-tight">My Projects</h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500 hidden sm:inline-block">{user?.email}</span>
            <button
              onClick={handleSignOut}
              className="p-2 text-gray-400 hover:text-gray-900 transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-12">
        {/* Actions */}
        <div className="flex justify-end mb-8">
          <Button onClick={handleCreate} className="shadow-lg shadow-gray-900/20 pl-4 pr-5">
            <Plus className="w-5 h-5 mr-2" />
            New Project
          </Button>
        </div>

        {/* Project Grid */}
        {projects.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-400">
              <FolderOpen className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No projects yet</h3>
            <p className="text-gray-500 mb-6">Create your first project to start analyzing.</p>
            <Button onClick={handleCreate} variant="secondary">
              Create Project
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <Link key={project.id} href={`/projects/${project.id}`} className="group block">
                <Card className="h-full p-6 transition-all duration-300 hover:shadow-md hover:-translate-y-1 group-hover:border-gray-200">
                  <div className="flex flex-col h-full justify-between">
                    <div>
                      <div className="w-10 h-10 bg-gray-50 rounded-full flex items-center justify-center mb-4 text-gray-900 group-hover:bg-gray-900 group-hover:text-white transition-colors">
                        <FolderOpen className="w-5 h-5" />
                      </div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-1 group-hover:text-blue-600 transition-colors">
                        {project.name}
                      </h3>
                      <p className="text-sm text-gray-500 line-clamp-2">
                        {project.description || "No description provided."}
                      </p>
                    </div>

                    <div className="mt-6 flex items-center text-sm font-medium text-gray-400 group-hover:text-gray-900 transition-colors">
                      Open Project
                      <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
