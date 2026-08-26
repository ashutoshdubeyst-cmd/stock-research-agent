import LoadingSpinner from "../ui/LoadingSpinner";
import type { ToolExecution } from "../../types/agent";

export type { ToolExecution } from "../../types/agent";

type ToolActivityProps = {
  activities: ToolExecution[];
  expanded?: boolean;
};

function humanizeToolName(name: string) {
  return name
    .replace(/^get_/, "")
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export default function ToolActivity({
  activities,
  expanded = false,
}: ToolActivityProps) {
  if (activities.length === 0) return null;

  return (
    <section className="tool-activity" aria-label="Research tool activity">
      <div className="tool-activity__heading">
        <span>Research process</span>
        <small>{activities.length} tool{activities.length === 1 ? "" : "s"}</small>
      </div>
      <div className="tool-activity__items">
        {activities.map((activity, index) => (
          <details
            className={`tool-step tool-step--${activity.status}`}
            key={`${activity.name}-${index}`}
            open={expanded || activity.status === "error"}
          >
            <summary>
              <span className="tool-step__state" aria-hidden="true">
                {activity.status === "running" ? (
                  <LoadingSpinner size="small" />
                ) : activity.status === "success" ? (
                  "✓"
                ) : (
                  "!"
                )}
              </span>
              <span>{humanizeToolName(activity.name)}</span>
              {activity.duration_ms != null && <small>{activity.duration_ms} ms</small>}
            </summary>
            {(activity.arguments || activity.error) && (
              <div className="tool-step__content">
                {activity.arguments && (
                  <pre>{JSON.stringify(activity.arguments, null, 2)}</pre>
                )}
                {activity.error && <p>{activity.error}</p>}
              </div>
            )}
          </details>
        ))}
      </div>
    </section>
  );
}
