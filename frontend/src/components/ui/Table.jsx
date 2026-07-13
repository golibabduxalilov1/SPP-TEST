import clsx from "clsx";

export function Table({ children, className }) {
  return (
    <div className="overflow-x-auto scrollbar-thin rounded-[14px] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]">
      <table className={clsx("w-full text-sm border-collapse", className)}>{children}</table>
    </div>
  );
}

export function Thead({ children }) {
  return (
    <thead className="bg-[var(--surface-muted)] text-[var(--ink-faint)] text-[11px] uppercase tracking-[0.07em]">
      {children}
    </thead>
  );
}

export function Th({ children, className }) {
  return (
    <th className={clsx("text-left font-semibold px-4 py-3 whitespace-nowrap", className)}>{children}</th>
  );
}

export function Tbody({ children }) {
  return <tbody className="divide-y divide-[var(--border-subtle)] bg-[var(--surface)]">{children}</tbody>;
}

export function Tr({ children, className, ...props }) {
  return (
    <tr className={clsx("transition-colors duration-150 hover:bg-[var(--accent-soft)]", className)} {...props}>
      {children}
    </tr>
  );
}

export function Td({ children, className }) {
  return <td className={clsx("px-4 py-3.5 text-[var(--ink)] align-middle", className)}>{children}</td>;
}

export function EmptyRow({ colSpan, message = "Ma'lumot topilmadi" }) {
  return (
    <tr>
      <td colSpan={colSpan} className="text-center text-[var(--ink-soft)] py-12 text-sm">
        {message}
      </td>
    </tr>
  );
}
