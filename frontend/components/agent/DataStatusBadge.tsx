import type { DataStatus } from "../../types/agent";

export type { DataStatus } from "../../types/agent";

const STATUS_LABELS: Record<DataStatus, string> = {
  mock: "Mock data",
  end_of_day: "End of day",
  delayed: "Delayed",
  real_time: "Real time",
  unavailable: "Unavailable",
};

type DataStatusBadgeProps = {
  status: DataStatus;
  compact?: boolean;
  className?: string;
};

export default function DataStatusBadge({
  status,
  compact = false,
  className = "",
}: DataStatusBadgeProps) {
  return (
    <span
      className={[
        "data-status-badge",
        `data-status-badge--${status.replaceAll("_", "-")}`,
        compact ? "data-status-badge--compact" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      title={`Market data status: ${STATUS_LABELS[status]}`}
    >
      <span className="data-status-badge__dot" aria-hidden="true" />
      {STATUS_LABELS[status]}
    </span>
  );
}
