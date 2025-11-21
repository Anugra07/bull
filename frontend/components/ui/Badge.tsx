import clsx from "clsx";
import { HTMLAttributes } from "react";

type Props = HTMLAttributes<HTMLSpanElement> & {
  variant?: "green" | "blue" | "yellow" | "gray";
};

export default function Badge({ className, variant = "gray", ...rest }: Props) {
  const variants: Record<string, string> = {
    green: "bg-emerald-100 text-emerald-700 ring-emerald-200",
    blue: "bg-blue-100 text-blue-700 ring-blue-200",
    yellow: "bg-yellow-100 text-yellow-800 ring-yellow-200",
    gray: "bg-zinc-100 text-zinc-700 ring-zinc-200",
  };
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1",
        variants[variant],
        className
      )}
      {...rest}
    />
  );
}
