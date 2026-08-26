import type { ConfidenceLevel, DataStatus } from "../types/agent";

export function formatCurrency(
  value: number | null | undefined,
  currency = "INR",
  locale = "en-IN",
) {
  if (value == null || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(
  value: number | null | undefined,
  maximumFractionDigits = 2,
) {
  if (value == null || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits }).format(value);
}

export function formatPercent(
  value: number | null | undefined,
  options: { decimal?: boolean; showSign?: boolean; digits?: number } = {},
) {
  if (value == null || !Number.isFinite(value)) return "—";
  const { decimal = false, showSign = false, digits = 2 } = options;
  const percentage = decimal ? value * 100 : value;
  const sign = showSign && percentage > 0 ? "+" : "";
  return `${sign}${percentage.toFixed(digits)}%`;
}

export function formatCompactNumber(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("en-IN", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatDate(
  value: string | Date | null | undefined,
  includeTime = false,
) {
  if (!value) return "—";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    ...(includeTime
      ? { hour: "2-digit", minute: "2-digit", timeZoneName: "short" }
      : {}),
  }).format(date);
}

export function formatDataStatus(status: DataStatus | string) {
  const labels: Record<DataStatus, string> = {
    mock: "Mock data",
    end_of_day: "End of day",
    delayed: "Delayed",
    real_time: "Real time",
    unavailable: "Unavailable",
  };
  return labels[status as DataStatus] ?? titleCase(status);
}

export function formatConfidence(confidence: ConfidenceLevel) {
  const labels: Record<ConfidenceLevel, string> = {
    verified: "Verified",
    document_based: "Document based",
    inferred: "Inferred",
    unavailable: "Unavailable",
  };
  return labels[confidence];
}

export function titleCase(value: string) {
  return value
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export function truncate(value: string, maximumLength = 80) {
  if (value.length <= maximumLength) return value;
  return `${value.slice(0, Math.max(0, maximumLength - 1)).trimEnd()}…`;
}
