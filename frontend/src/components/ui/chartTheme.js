/** Shared Recharts palette + styles, aligned to the walnut + bronze wood system. */
export const CHART = {
  accent: "#6B4423",
  accentBright: "#855A34",
  signal: "#B08D57",
  signalBright: "#C6A473",
  danger: "#C0392B",
  grid: "#E4D8C4",
  axis: "#A89B8C",
  series: ["#6B4423", "#B08D57", "#8B6544", "#4A3223", "#C6A473", "#96754F"],
};

export const tooltipStyle = {
  contentStyle: {
    borderRadius: 10,
    border: "1px solid var(--border)",
    background: "rgba(253,251,247,0.95)",
    backdropFilter: "blur(12px)",
    boxShadow: "0 12px 32px rgba(74,50,35,0.14)",
    fontSize: 12,
  },
  labelStyle: { color: "var(--ink)", fontWeight: 600 },
  cursor: { fill: "rgba(107,68,35,0.07)" },
};
