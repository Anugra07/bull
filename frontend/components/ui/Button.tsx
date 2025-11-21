"use client";

import { ButtonHTMLAttributes } from "react";
import clsx from "clsx";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
};

export default function Button({ className, variant = "primary", size = "md", loading, children, ...rest }: Props) {
  const base = "inline-flex items-center justify-center rounded-2xl font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed shadow-sm";
  const variants: Record<string, string> = {
    primary: "bg-black text-white hover:bg-zinc-900 focus:ring-black",
    secondary: "bg-white text-black border border-zinc-200 hover:bg-zinc-50 focus:ring-zinc-300",
    ghost: "bg-transparent text-black hover:bg-zinc-100 focus:ring-zinc-300",
  };
  const sizes: Record<string, string> = {
    sm: "h-9 px-3 text-sm",
    md: "h-10 px-4 text-sm",
    lg: "h-12 px-5 text-base",
  };
  return (
    <button className={clsx(base, variants[variant], sizes[size], className)} {...rest}>
      {loading ? (
        <span className="animate-pulse">•••</span>
      ) : (
        children
      )}
    </button>
  );
}
