"use client";

import { ButtonHTMLAttributes } from "react";
import clsx from "clsx";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
};

export default function Button({ className, variant = "primary", size = "md", loading, children, ...rest }: Props) {
  const base = "inline-flex items-center justify-center rounded-full font-medium transition-transform active:scale-95 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed";
  const variants: Record<string, string> = {
    primary: "bg-gray-900 text-white focus:ring-gray-900",
    secondary: "bg-gray-100 text-gray-900 border border-gray-200 focus:ring-gray-300",
    ghost: "bg-transparent text-gray-900 focus:ring-gray-300",
  };
  const sizes: Record<string, string> = {
    sm: "h-9 px-4 text-sm",
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
