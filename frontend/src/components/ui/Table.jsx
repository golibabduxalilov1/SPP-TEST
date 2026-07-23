import clsx from "clsx";

export function Table({ children, className, containerClassName, label = "Ma'lumotlar jadvali" }) {
  return (
    <div
      role="region"
      aria-label={label}
      tabIndex={0}
      className={clsx(
        "overflow-x-auto overscroll-x-contain scrollbar-thin touch-pan-x rounded-[14px] border border-(--border) bg-(--surface) shadow-(--shadow-sm) [-webkit-overflow-scrolling:touch]",
        containerClassName
      )}
    >
      <table className={clsx("w-full min-w-[640px] table-auto border-collapse text-sm", className)}>{children}</table>
    </div>
  );
}

export function Thead({ children, className, ...props }) {
  return (
    <thead className={clsx("bg-(--surface-muted) text-(--ink-faint) text-[11px] uppercase tracking-[0.07em]", className)} {...props}>
      {children}
    </thead>
  );
}

export function Th({ children, className, ...props }) {
  return (
    <th className={clsx("px-3 py-3 text-left font-semibold leading-4 whitespace-normal sm:px-4", className)} {...props}>{children}</th>
  );
}

export function Tbody({ children, className, ...props }) {
  return <tbody className={clsx("divide-y divide-(--border-subtle) bg-(--surface)", className)} {...props}>{children}</tbody>;
}

export function Tr({ children, className, ...props }) {
  return (
    <tr className={clsx("transition-colors duration-150 hover:bg-(--accent-soft)", className)} {...props}>
      {children}
    </tr>
  );
}

export function Td({ children, className, ...props }) {
  return <td className={clsx("px-3 py-3.5 text-(--ink) align-middle wrap-break-word sm:px-4", className)} {...props}>{children}</td>;
}

export function EmptyRow({ colSpan, message = "Ma'lumot topilmadi" }) {
  return (
    <tr>
      <td colSpan={colSpan} className="text-center text-(--ink-soft) py-12 text-sm">
        {message}
      </td>
    </tr>
  );
}
