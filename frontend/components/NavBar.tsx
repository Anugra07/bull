"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { usePathname } from "next/navigation";

export default function NavBar() {
  const [email, setEmail] = useState<string | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    let mounted = true;
    const init = async () => {
      const { data } = await supabase.auth.getSession();
      if (!mounted) return;
      setEmail(data.session?.user?.email ?? null);
    };
    init();

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setEmail(session?.user?.email ?? null);
    });

    return () => {
      mounted = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  const logout = async () => {
    await supabase.auth.signOut();
    window.location.href = "/";
  };

  const isActive = (path: string) => pathname === path;

  return (
    <nav className="sticky top-0 z-50 border-b-2 border-[var(--line-strong)] bg-[var(--surface)]/95 backdrop-blur-sm relative">
      <div className="absolute inset-x-0 bottom-0 h-px bg-[var(--line)]" />
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex items-center justify-center w-9 h-9 rounded-md border-2 border-[var(--accent-strong)] bg-[var(--accent)] text-white font-bold text-sm">
                OG
              </div>
              <span className="text-base font-semibold tracking-wide text-[var(--ink)] uppercase">
                Offset Guesser
              </span>
            </Link>
            {email && (
              <div className="hidden md:flex items-center gap-2">
                <Link
                  href="/dashboard"
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold tracking-wide border-2 transition-colors ${isActive("/dashboard")
                    ? "border-[var(--accent-strong)] bg-[var(--accent)] text-white"
                    : "border-[var(--line)] text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-strong)]"
                    }`}
                >
                  Dashboard
                </Link>
                <Link
                  href="/guide"
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold tracking-wide border-2 transition-colors ${isActive("/guide")
                    ? "border-[var(--accent-strong)] bg-[var(--accent)] text-white"
                    : "border-[var(--line)] text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-strong)]"
                    }`}
                >
                  Methodology
                </Link>
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            {email ? (
              <>
                <div className="hidden sm:flex items-center gap-2 text-xs font-medium text-[var(--muted)] border-2 border-[var(--line)] px-3 py-1 rounded-md bg-[var(--surface-strong)]">
                  <span className="max-w-[170px] truncate">{email}</span>
                </div>
                <button
                  onClick={logout}
                  className="px-3 py-1.5 rounded-md border-2 border-[var(--line-strong)] bg-[var(--surface-strong)] text-[var(--ink)] text-xs font-semibold tracking-wide hover:bg-[var(--surface)]"
                >
                  Logout
                </button>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className="px-3 py-1.5 rounded-md border-2 border-[var(--line)] text-[var(--ink)] text-xs font-semibold tracking-wide hover:bg-[var(--surface-strong)]"
                >
                  Sign In
                </Link>
                <Link
                  href="/signup"
                  className="px-3 py-1.5 rounded-md border-2 border-[var(--accent-strong)] bg-[var(--accent)] text-white text-xs font-semibold tracking-wide hover:bg-[var(--accent-strong)]"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
