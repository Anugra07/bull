import clsx from "clsx";
import { InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
};

export default function Input({ className, label, hint, ...rest }: Props) {
  return (
    <label className="block">
      {label && <div className="mb-1 text-sm text-zinc-700">{label}</div>}
      <input
        className={clsx(
          "w-full rounded-2xl border border-zinc-200 bg-white/80 backdrop-blur px-4 py-2 text-sm outline-none",
          "focus:ring-2 focus:ring-black",
          className
        )}
        {...rest}
      />
      {hint && <div className="mt-1 text-xs text-zinc-500">{hint}</div>}
    </label>
  );
}
