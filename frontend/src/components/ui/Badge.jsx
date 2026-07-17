import clsx from "clsx";

const TONES = {
  green: "text-status-green bg-status-green-bg border-status-green/20",
  yellow: "text-status-yellow bg-status-yellow-bg border-status-yellow/20",
  red: "text-status-red bg-status-red-bg border-status-red/20",
  gray: "text-status-gray bg-status-gray-bg border-status-gray/20",
  blue: "text-status-blue bg-status-blue-bg border-status-blue/20",
  orange: "text-status-orange bg-status-orange-bg border-status-orange/20",
  accent: "text-[var(--accent-strong)] bg-[var(--accent-soft)] border-[color-mix(in_srgb,var(--accent)_25%,transparent)]",
};

export const STATUS_TONE_MAP = {
  completed: "green",
  synced: "green",
  accepted: "green",
  delivered: "green",
  resolved: "green",
  active: "blue",
  draft: "blue",
  approved: "blue",
  ready_for_packaging: "blue",
  warehouse: "blue",
  in_progress: "yellow",
  in_production: "yellow",
  packaging: "yellow",
  pending: "yellow",
  syncing: "yellow",
  warning: "orange",
  review_required: "orange",
  partially_ready: "orange",
  maintenance: "orange",
  blocked: "red",
  conflict: "red",
  rejected: "red",
  failed: "red",
  cancelled: "red",
  stopped: "red",
  broken: "red",
  not_required: "gray",
  inactive: "gray",
  not_connected: "gray",
};

export default function Badge({ tone = "gray", children, className, dot = false }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border text-xs font-semibold whitespace-nowrap",
        TONES[tone] || TONES.gray,
        className
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />}
      {children}
    </span>
  );
}

export function StatusBadge({ status, labels = {}, className }) {
  const tone = STATUS_TONE_MAP[status] || "gray";
  return (
    <Badge tone={tone} dot className={className}>
      {labels[status] || status}
    </Badge>
  );
}
