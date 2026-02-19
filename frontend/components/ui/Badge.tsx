import clsx from "clsx";
import { HTMLAttributes } from "react";

type Props = HTMLAttributes<HTMLSpanElement> & {
  variant?: "green" | "blue" | "yellow" | "gray";
};

export default function Badge({ className, variant = "gray", ...rest }: Props) {
  const variants: Record<string, string> = {
    green: "bg-emerald-100 text-emerald-800 border-emerald-300",
    blue: "bg-cyan-100 text-cyan-800 border-cyan-300",
    yellow: "bg-amber-100 text-amber-800 border-amber-300",
    gray: "bg-stone-100 text-stone-700 border-stone-300",
  };
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold border",
        variants[variant],
        className,
      )}
      {...rest}
    />
  );
}
