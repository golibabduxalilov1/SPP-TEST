// Mirrors backend/manufacturing/units.py — single source of truth for
// production-stage measurement units on the frontend. Backend does the
// actual value calculations; this only maps measure_unit -> display text.
export const MEASURE_UNIT_OPTIONS = [
  { value: "m2", label: "m²" },
  { value: "meter", label: "metr" },
  { value: "piece", label: "dona" },
  { value: "package", label: "qadoq" },
];

export const MEASURE_UNIT_LABELS = Object.fromEntries(
  MEASURE_UNIT_OPTIONS.map(({ value, label }) => [value, label])
);

export const DEFAULT_MEASURE_UNIT = "piece";

export function measureUnitLabel(unit) {
  return MEASURE_UNIT_LABELS[unit] || unit;
}
