import type { AgentChatMessage } from "../../types/agent";
import DataStatusBadge from "./DataStatusBadge";
import SourceList from "./SourceList";
import ToolActivity from "./ToolActivity";

export type { AgentChatMessage } from "../../types/agent";

type ChatMessageProps = {
  message: AgentChatMessage;
};

export default function ChatMessage({ message }: ChatMessageProps) {
  const isAssistant = message.role === "assistant";

  return (
    <article className={`message ${message.role}`} aria-label={`${message.role} message`}>
      <div className="message__meta">
        <span className="message-author">{isAssistant ? "Ledger AI" : "You"}</span>
        {message.createdAt && <time>{message.createdAt}</time>}
      </div>
      <p>{message.content}</p>

      {isAssistant && message.tools && <ToolActivity activities={message.tools} />}
      {isAssistant && message.sources && message.sources.length > 0 && (
        <SourceList sources={message.sources} />
      )}
      {isAssistant && message.warnings && message.warnings.length > 0 && (
        <ul className="message__warnings">
          {message.warnings.map((warning) => <li key={warning}>{warning}</li>)}
        </ul>
      )}
      {isAssistant && (message.dataStatus || message.confidence || message.traceId) && (
        <footer className="message__footer">
          {message.dataStatus && <DataStatusBadge status={message.dataStatus} compact />}
          {message.confidence && <span>Confidence: {message.confidence.replaceAll("_", " ")}</span>}
          {message.traceId && <span title={message.traceId}>Trace {message.traceId.slice(0, 8)}</span>}
        </footer>
      )}
    </article>
  );
}
