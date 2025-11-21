"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";

export default function NavBar() {
  const [email, setEmail] = useState<string | null>(null);

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
    // Full reload to clear client state
    window.location.href = "/login";
  };

  return (
    <nav className="flex items-center justify-between py-3">
      <div className="flex items-center gap-3">
        <Link href="/" className="text-lg font-semibold">Carbon Offset Land Analyzer</Link>
        <Link href="/dashboard" className="text-sm text-gray-600 hover:underline">Dashboard</Link>
      </div>
      <div className="flex items-center gap-3">
        {email ? (
          <>
            <span className="text-sm text-gray-700">{email}</span>
            <button onClick={logout} className="rounded bg-gray-800 px-3 py-1 text-white text-sm hover:bg-black">Logout</button>
          </>
        ) : (
          <Link href="/login" className="rounded bg-blue-600 px-3 py-1 text-white text-sm hover:bg-blue-700">Login</Link>
        )}
      </div>
    </nav>
  );
}
