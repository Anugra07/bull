"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import Link from "next/link";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: window.location.origin + "/dashboard",
          shouldCreateUser: true,
        },
      });

      if (error) {
        setError(error.message);
      } else {
        setSent(true);
      }
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 section-fade">
      <div className="flex min-h-[calc(100vh-210px)] items-center justify-center py-12">
        <div className="w-full max-w-md">
          <Card className="border-[var(--line-strong)]">
            <CardContent className="pt-8">
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-md border-2 border-[var(--accent-strong)] bg-[var(--accent)] text-white font-bold text-base mb-4">
                  OG
                </div>
                <h1 className="text-3xl font-bold text-[var(--ink)] mb-2">Create Account</h1>
                <p className="text-[var(--muted)] text-sm">
                  Start a workspace and run carbon analysis with your own projects.
                </p>
              </div>

              {!sent ? (
                <form onSubmit={onSubmit} className="space-y-5">
                  <div>
                    <label htmlFor="email" className="block text-sm font-semibold text-[var(--ink)] mb-2">
                      Email Address
                    </label>
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      required
                      className="w-full"
                    />
                    <p className="mt-2 text-xs text-[var(--muted)]">Only used for authentication and project ownership.</p>
                  </div>

                  {error && (
                    <div className="rounded-md bg-red-50 border-2 border-red-200 p-3">
                      <p className="text-sm text-red-800">{error}</p>
                    </div>
                  )}

                  <Button type="submit" className="w-full" loading={loading} disabled={loading || !email}>
                    Send Magic Link
                  </Button>

                  <div className="text-center text-sm text-[var(--muted)]">
                    Already registered?{" "}
                    <Link href="/login" className="font-semibold text-[var(--accent)] hover:underline">
                      Sign in
                    </Link>
                  </div>
                </form>
              ) : (
                <div className="text-center py-4">
                  <div className="inline-flex items-center justify-center w-14 h-14 rounded-md bg-[var(--surface)] border-2 border-[var(--line)] mb-4">
                    <svg className="w-7 h-7 text-[var(--accent)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <h2 className="text-xl font-semibold text-[var(--ink)] mb-2">Check your inbox</h2>
                  <p className="text-[var(--muted)] mb-6 text-sm">
                    Magic link sent to <span className="font-semibold text-[var(--ink)]">{email}</span>
                  </p>
                  <button
                    onClick={() => {
                      setSent(false);
                      setEmail("");
                    }}
                    className="text-sm font-semibold text-[var(--accent)] hover:underline"
                  >
                    Use a different email
                  </button>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="mt-5 text-center text-xs text-[var(--muted)]">
            By continuing, you agree to the product Terms and Privacy policy.
          </div>
        </div>
      </div>
    </div>
  );
}
