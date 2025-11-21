"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const { error } = await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: window.location.origin + "/dashboard" } });
    if (error) setError(error.message);
    else setSent(true);
  };

  return (
    <main className="max-w-md mx-auto py-10">
      <h1 className="text-2xl font-semibold">Login</h1>
      <p className="text-gray-600 mt-2">Magic link will be sent to your email.</p>
      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <Input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
                    required
        />
        <Button className="w-full" type="submit">
          Send Magic Link
        </Button>
      </form>
      {sent && <p className="text-green-600 mt-4">Check your inbox for a magic link.</p>}
      {error && <p className="text-red-600 mt-4">{error}</p>}
    </main>
  );
}
