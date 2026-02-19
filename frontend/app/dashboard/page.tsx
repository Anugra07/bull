"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { api, Project } from "@/lib/api";
import { Plus, ArrowRight, FolderOpen, Trash2 } from "lucide-react";
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

  const handleDelete = async (e: React.MouseEvent, projectId: string, projectName: string) => {
    e.preventDefault();
    e.stopPropagation();

    if (!confirm(`Are you sure you want to delete project "${projectName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await api.deleteProject(projectId);
      setProjects(projects.filter((p) => p.id !== projectId));
    } catch (err) {
      console.error(err);
      alert("Failed to delete project");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse flex flex-col items-center gap-3">
          <div className="h-10 w-10 bg-[var(--line)] rounded-md" />
          <div className="h-3 w-36 bg-[var(--line)] rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-[var(--ink)]">
      <main className="max-w-6xl mx-auto px-6 py-10 section-fade">
        <Card className="p-6 md:p-8 mb-8 bg-[var(--surface)]">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold">Project Workspace</h1>
              <p className="text-[var(--muted)] mt-1 text-sm">Manage parcels, run analyses, and review carbon outcomes.</p>
            </div>
            <Button onClick={handleCreate} className="w-full md:w-auto">
              <Plus className="w-4 h-4 mr-2" />
              New Project
            </Button>
          </div>
        </Card>

        {projects.length === 0 ? (
          <Card className="text-center py-16 px-6">
            <div className="w-14 h-14 mx-auto border-2 border-[var(--line-strong)] rounded-md flex items-center justify-center text-[var(--muted)] bg-[var(--surface)] mb-4">
              <FolderOpen className="w-7 h-7" />
            </div>
            <h3 className="text-xl font-semibold text-[var(--ink)] mb-2">No projects yet</h3>
            <p className="text-[var(--muted)] mb-6 text-sm">Create your first workspace to start carbon analysis.</p>
            <Button onClick={handleCreate} variant="secondary">Create Project</Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {projects.map((project) => (
              <Link key={project.id} href={`/projects/${project.id}`} className="group block">
                <Card className="h-full p-5 transition-transform duration-200 hover:-translate-y-0.5">
                  <div className="flex flex-col h-full justify-between">
                    <div>
                      <div className="flex justify-between items-start mb-4">
                        <div className="w-10 h-10 border-2 border-[var(--line)] rounded-md flex items-center justify-center text-[var(--ink)] bg-[var(--surface)]">
                          <FolderOpen className="w-5 h-5" />
                        </div>
                        <button
                          onClick={(e) => handleDelete(e, project.id, project.name)}
                          className="text-[var(--muted)] hover:text-red-700 p-1 rounded-md border border-transparent hover:border-red-300"
                          title="Delete Project"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      <h3 className="text-lg font-semibold text-[var(--ink)] mb-2 line-clamp-1">
                        {project.name}
                      </h3>
                      <p className="text-sm text-[var(--muted)] line-clamp-2">
                        {project.description || "No description provided."}
                      </p>
                    </div>

                    <div className="mt-6 flex items-center text-sm font-semibold text-[var(--accent)]">
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
