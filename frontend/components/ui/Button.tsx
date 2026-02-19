"use client";

import { ButtonHTMLAttributes } from "react";
import clsx from "clsx";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
};

export default function Button({ className, variant = "primary", size = "md", loading, children, ...rest }: Props) {
  const base = "inline-flex items-center justify-center rounded-md border-2 font-semibold tracking-wide transition-all active:translate-y-[1px] focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed";
  const variants: Record<string, string> = {
    primary: "border-[var(--accent-strong)] bg-[var(--accent)] text-white shadow-[var(--shadow-soft)] hover:bg-[var(--accent-strong)]",
    secondary: "border-[var(--line-strong)] bg-[var(--surface-strong)] text-[var(--ink)] hover:bg-[var(--surface)]",
    ghost: "border-transparent bg-transparent text-[var(--ink)] hover:bg-[var(--surface)]",
  };
  const sizes: Record<string, string> = {
    sm: "h-9 px-4 text-xs",
    md: "h-11 px-5 text-sm",
    lg: "h-12 px-6 text-base",
  };
  return (
    <button className={clsx(base, variants[variant], sizes[size], className)} {...rest}>
      {loading ? (
        <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        children
      )}
    </button>
  );
}
