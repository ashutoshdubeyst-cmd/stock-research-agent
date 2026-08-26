import type { ResearchSource } from "../../types/agent";

export type { ResearchSource } from "../../types/agent";

type SourceListProps = {
  sources: ResearchSource[];
  title?: string;
  emptyMessage?: string;
};

export default function SourceList({
  sources,
  title = "Sources",
  emptyMessage = "No external sources were used.",
}: SourceListProps) {
  const uniqueSources = sources.filter(
    (source, index, all) =>
      all.findIndex(
        (candidate) =>
          candidate.label === source.label && candidate.url === source.url,
      ) === index,
  );

  return (
    <section className="source-list" aria-labelledby="source-list-title">
      <h4 id="source-list-title">{title}</h4>
      {uniqueSources.length === 0 ? (
        <p className="source-list__empty">{emptyMessage}</p>
      ) : (
        <ol>
          {uniqueSources.map((source, index) => (
            <li key={`${source.label}-${source.url ?? index}`}>
              <span className="source-list__number">{index + 1}</span>
              <span className="source-list__details">
                {source.url ? (
                  <a href={source.url} target="_blank" rel="noreferrer noopener">
                    {source.label}<span aria-hidden="true"> ↗</span>
                  </a>
                ) : (
                  <strong>{source.label}</strong>
                )}
                {source.as_of && <small>As of {source.as_of}</small>}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
