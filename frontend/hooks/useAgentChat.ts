"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, apiClient } from "../lib/api-client";
import type {
  AgentChatMessage,
  AgentChatResponse,
  ResearchSource,
  UseAgentChatOptions,
  UseAgentChatResult,
} from "../types/agent";

function createId() {
  return globalThis.crypto?.randomUUID?.() ??
    `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function normalizeSources(response: AgentChatResponse): ResearchSource[] {
  return (response.sources ?? []).map((source) =>
    typeof source === "string" ? { label: source } : source,
  );
}

function responseWarnings(response: AgentChatResponse) {
  return Array.from(
    new Set(
      [response.warning, ...(response.warnings ?? [])].filter(
        (warning): warning is string => Boolean(warning?.trim()),
      ),
    ),
  );
}

export default function useAgentChat(
  options: UseAgentChatOptions = {},
): UseAgentChatResult {
  const { initialMessages = [], maxHistory = 20 } = options;
  const [messages, setMessages] = useState<AgentChatMessage[]>(initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const messagesRef = useRef(messages);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const sendMessage = useCallback(
    async (rawMessage: string) => {
      const content = rawMessage.trim();
      if (!content || controllerRef.current) return;

      const previousMessages = messagesRef.current;
      const userMessage: AgentChatMessage = {
        id: createId(),
        role: "user",
        content,
        createdAt: new Date().toISOString(),
      };
      setMessages([...previousMessages, userMessage]);
      setError(null);
      setIsLoading(true);

      const controller = new AbortController();
      controllerRef.current = controller;
      try {
        const response = await apiClient.chat(
          {
            message: content,
            history: previousMessages
              .slice(-maxHistory)
              .map(({ role, content: historyContent }) => ({
                role,
                content: historyContent,
              })),
          },
          controller.signal,
        );
        const assistantMessage: AgentChatMessage = {
          id: createId(),
          role: "assistant",
          content: response.answer,
          createdAt: new Date().toISOString(),
          traceId: response.trace_id,
          confidence: response.confidence ?? "inferred",
          dataStatus: response.data_status,
          tools: response.tool_activity ?? [],
          sources: normalizeSources(response),
          warnings: responseWarnings(response),
        };
        setMessages((current) => [...current, assistantMessage]);
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setError(
          caught instanceof ApiError || caught instanceof Error
            ? caught.message
            : "The research agent could not complete the request.",
        );
      } finally {
        if (controllerRef.current === controller) controllerRef.current = null;
        setIsLoading(false);
      }
    },
    [maxHistory],
  );

  const retryLastMessage = useCallback(async () => {
    const lastUserMessage = [...messagesRef.current]
      .reverse()
      .find((message) => message.role === "user");
    if (!lastUserMessage) return;
    setMessages((current) => {
      const index = current.findIndex((message) => message.id === lastUserMessage.id);
      return index < 0 ? current : current.slice(0, index);
    });
    messagesRef.current = messagesRef.current.slice(
      0,
      messagesRef.current.findIndex((message) => message.id === lastUserMessage.id),
    );
    await sendMessage(lastUserMessage.content);
  }, [sendMessage]);

  const stop = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setIsLoading(false);
  }, []);

  const clearMessages = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    messagesRef.current = [];
    setMessages([]);
    setError(null);
    setIsLoading(false);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    retryLastMessage,
    stop,
    clearMessages,
    clearError,
  };
}
