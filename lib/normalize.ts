export function normalizeValues(values: number[]): number[] {
  const total = values.reduce((sum, value) => sum + value, 0);
  if (!values.length || total <= 0 || values.some((value) => value <= 0)) return [];
  const rounded = values.map((value) => Math.round((value / total) * 1000) / 10);
  const difference = Math.round((100 - rounded.reduce((sum, value) => sum + value, 0)) * 10) / 10;
  rounded[rounded.length - 1] = Math.round((rounded[rounded.length - 1] + difference) * 10) / 10;
  return rounded;
}
