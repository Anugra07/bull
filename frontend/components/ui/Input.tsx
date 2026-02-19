import clsx from "clsx";
import { InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
};

export default function Input({ className, label, hint, ...rest }: Props) {
  return (
    <label className="block">
      {label && <div className="mb-1 text-sm font-medium text-[var(--ink)]">{label}</div>}
      <input
        className={clsx(
          "w-full rounded-md border-2 border-[var(--line)] bg-[var(--surface)] px-4 py-2.5 text-sm text-[var(--ink)] outline-none",
          "focus:border-[var(--accent)]",
          className,
        )}
        {...rest}
      />
      {hint && <div className="mt-1 text-xs text-[var(--muted)]">{hint}</div>}
    </label>
  );
}
