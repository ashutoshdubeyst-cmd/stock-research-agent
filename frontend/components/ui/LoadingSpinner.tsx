type LoadingSpinnerProps = {
  size?: "small" | "medium" | "large";
  label?: string;
  className?: string;
};

export default function LoadingSpinner({
  size = "medium",
  label = "Loading",
  className = "",
}: LoadingSpinnerProps) {
  return (
    <span
      className={`loading-spinner loading-spinner--${size} ${className}`.trim()}
      role="status"
      aria-live="polite"
    >
      <span className="loading-spinner__ring" aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </span>
  );
}
