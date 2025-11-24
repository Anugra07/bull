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
    <nav className="border-b border-gray-200/60 bg-white/80 backdrop-blur-xl sticky top-0 z-50">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-gray-900 text-white font-semibold text-base">
                OG
              </div>
              <span className="text-lg font-semibold text-gray-900">
                Offset Guesser
              </span>
            </Link>
            {email && (
              <div className="hidden md:flex items-center gap-1">
                <Link 
                  href="/dashboard" 
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                    isActive("/dashboard") 
                      ? "bg-gray-100 text-gray-900" 
                      : "text-gray-600"
                  }`}
                >
                  Dashboard
                </Link>
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            {email ? (
              <>
                <div className="hidden sm:flex items-center gap-2 text-sm text-gray-600">
                  <span className="max-w-[150px] truncate">{email}</span>
                </div>
                <button 
                  onClick={logout} 
                  className="px-4 py-2 rounded-xl bg-gray-100 text-gray-900 text-sm font-medium active:opacity-70"
                >
                  Logout
                </button>
              </>
            ) : (
              <div className="flex items-center gap-3">
                <Link 
                  href="/login" 
                  className="px-4 py-2 rounded-xl text-gray-900 text-sm font-medium active:opacity-70"
                >
                  Sign In
                </Link>
                <Link 
                  href="/signup" 
                  className="px-4 py-2 rounded-xl bg-gray-900 text-white text-sm font-medium active:opacity-80"
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
