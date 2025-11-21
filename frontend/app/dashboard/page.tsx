"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import Link from "next/link";
import { api, Project } from "@/lib/api";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [authed, setAuthed] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");

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
        } catch (e) {}
      }
    };
    init();
  }, []);

  if (loading) return <main className="py-10">Loading...</main>;
  if (!authed)
    return (
      <main className="py-10">
        <Card className="max-w-xl mx-auto">
          <CardHeader>
            <CardTitle>Welcome</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700">Please login to access your projects.</p>
            <div className="mt-4">
              <Link href="/login"><Button>Go to Login</Button></Link>
            </div>
          </CardContent>
        </Card>
      </main>
    );

  return (
    <main className="py-6 space-y-6">
      <h1 className="text-2xl font-semibold">Your Projects</h1>

      <Card>
        <CardHeader>
          <CardTitle>Create a Project</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <Input label="Name" placeholder="e.g. Karnataka Mangrove" value={name} onChange={(e) => setName(e.target.value)} />
            <Input label="Description" placeholder="Optional" value={desc} onChange={(e) => setDesc(e.target.value)} />
            <div className="flex items-end">
              <Button disabled={!userId || !name} loading={creating} onClick={async () => {
                if (!userId || !name) return;
                try {
                  setCreating(true);
                  const p = await api.createProject({ user_id: userId, name, description: desc });
                  setProjects((prev) => [p, ...prev]);
                  setName(""); setDesc("");
                  // Redirect to the new project page
                  window.location.href = `/projects/${p.id}`;
                } finally {
                  setCreating(false);
                }
              }}>Create</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {projects.length === 0 ? (
        <Card>
          <CardContent>
            <p className="text-gray-600">No projects yet. Create one above to get started, or try the demo.</p>
            <div className="mt-4">
              <Link href="/projects/demo"><Button variant="secondary">Open Demo Project</Button></Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <Card key={p.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <CardTitle>{p.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">{p.description || "No description"}</p>
                <div className="mt-4">
                  <Link href={`/projects/${p.id}`}><Button size="sm">Open</Button></Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
