export type Units = "kg" | "lbs";

const KG_PER_LB = 0.45359237;

/** Weights are stored in kg everywhere; conversion happens only at the UI edge. */
export function toDisplay(kg: number | null | undefined, units: Units): number | null {
  if (kg == null) return null;
  return units === "kg" ? kg : kg / KG_PER_LB;
}

export function fromDisplay(value: number | null | undefined, units: Units): number | null {
  if (value == null || Number.isNaN(value)) return null;
  const kg = units === "kg" ? value : value * KG_PER_LB;
  return Math.round(kg * 100) / 100;
}

export function formatWeight(kg: number | null | undefined, units: Units): string {
  const v = toDisplay(kg, units);
  if (v == null) return "—";
  const rounded = Math.round(v * 10) / 10;
  return `${rounded}${units === "kg" ? "kg" : "lb"}`;
}

/** Sensible plate-math increment for steppers. */
export function weightStep(units: Units): number {
  return units === "kg" ? 2.5 : 5;
}
