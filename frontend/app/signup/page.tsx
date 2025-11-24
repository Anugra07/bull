"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";

export default function SignupPage() {
  const router = useRouter();
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
          shouldCreateUser: true
        } 
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
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div className="flex min-h-[calc(100vh-200px)] items-center justify-center py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-gray-900 text-white font-semibold text-xl mb-4">
              OG
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Create Your Account</h1>
            <p className="text-gray-600">
              Get started with Offset Guesser. We'll send you a magic link to sign in.
            </p>
          </div>

          <Card className="border-gray-300">
            {!sent ? (
              <>
                <CardContent className="pt-8">
                  <form onSubmit={onSubmit} className="space-y-6">
                    <div>
                      <label htmlFor="email" className="block text-sm font-medium text-gray-900 mb-2">
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
                      <p className="mt-2 text-sm text-gray-500">
                        We'll never share your email with anyone.
                      </p>
                    </div>

                    {error && (
                      <div className="rounded-xl bg-red-50 border border-red-200 p-4">
                        <p className="text-sm text-red-900">{error}</p>
                      </div>
                    )}

                    <Button 
                      type="submit" 
                      className="w-full"
                      loading={loading}
                      disabled={loading || !email}
                    >
                      Send Magic Link
                    </Button>
                  </form>

                  <div className="mt-6 text-center">
                    <p className="text-sm text-gray-600">
                      Already have an account?{" "}
                      <Link href="/login" className="font-medium text-gray-900">
                        Sign in instead
                      </Link>
                    </p>
                  </div>
                </CardContent>
              </>
            ) : (
              <CardContent className="text-center py-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
                  <svg className="w-8 h-8 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Check Your Email</h2>
                <p className="text-gray-600 mb-6">
                  We've sent a magic link to <span className="font-medium text-gray-900">{email}</span>
                </p>
                <p className="text-sm text-gray-500 mb-6">
                  Click the link in the email to complete your signup and access your dashboard.
                </p>
                <button
                  onClick={() => {
                    setSent(false);
                    setEmail("");
                  }}
                  className="text-sm font-medium text-gray-900 active:opacity-70"
                >
                  Use a different email
                </button>
              </CardContent>
            )}
          </Card>

          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500">
              By continuing, you agree to our Terms of Service and Privacy Policy
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
