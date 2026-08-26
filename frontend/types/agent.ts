export type AgentRole = "user" | "assistant";
export type ConfidenceLevel =
  | "verified"
  | "document_based"
  | "inferred"
  | "unavailable";
export type DataStatus =
  | "mock"
  | "end_of_day"
  | "delayed"
  | "real_time"
  | "unavailable";
export type ToolStatus = "running" | "success" | "error";

export type AgentHistoryMessage = {
  role: AgentRole;
  content: string;
};

export type AgentChatRequest = {
  message: string;
  history?: AgentHistoryMessage[];
};

export type ResearchSource = {
  label: string;
  url?: string | null;
  as_of?: string | null;
};

export type ToolExecution = {
  name: string;
  status: ToolStatus;
  arguments?: Record<string, unknown>;
  duration_ms?: number | null;
  error?: string | null;
};

/** Supports both the initial endpoint and the evidence-aware agent response. */
export type AgentChatResponse = {
  answer: string;
  trace_id: string;
  provider: string;
  model: string;
  tools_used: string[];
  tool_activity?: ToolExecution[];
  sources: Array<ResearchSource | string>;
  confidence?: ConfidenceLevel;
  data_status?: DataStatus;
  warning?: string;
  warnings?: string[];
  disclaimer?: string;
};

export type AgentChatMessage = {
  id: string;
  role: AgentRole;
  content: string;
  createdAt?: string;
  traceId?: string;
  confidence?: ConfidenceLevel;
  dataStatus?: DataStatus;
  tools?: ToolExecution[];
  sources?: ResearchSource[];
  warnings?: string[];
};

export type UseAgentChatOptions = {
  initialMessages?: AgentChatMessage[];
  maxHistory?: number;
};

export type UseAgentChatResult = {
  messages: AgentChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (message: string) => Promise<void>;
  retryLastMessage: () => Promise<void>;
  stop: () => void;
  clearMessages: () => void;
  clearError: () => void;
};
