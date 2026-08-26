"use client";

import { useEffect, useRef } from "react";

import ChatInput from "./ChatInput";
import ChatMessage, { type AgentChatMessage } from "./ChatMessage";

type ChatPanelProps = {
  messages: AgentChatMessage[];
  onSend: (message: string) => void | Promise<void>;
  isLoading?: boolean;
  selectedSymbol?: string;
  quickPrompts?: string[];
  title?: string;
};

const DEFAULT_PROMPTS = [
  "Compare TCS and INFY",
  "Explain RSI simply",
  "What does P/E mean?",
];

export default function ChatPanel({
  messages,
  onSend,
  isLoading = false,
  selectedSymbol,
  quickPrompts = DEFAULT_PROMPTS,
  title = "Ask Ledger",
}: ChatPanelProps) {
  const conversationRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    conversationRef.current?.scrollTo({
      top: conversationRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  return (
    <section className="agent-panel" aria-labelledby="agent-panel-title">
      <div className="agent-heading">
        <div className="agent-icon" aria-hidden="true">✦</div>
        <div>
          <p className="section-label">RESEARCH COPILOT</p>
          <h2 id="agent-panel-title">{title}</h2>
        </div>
        <span className="model-label">GROUNDED MODE</span>
      </div>

      <div className="conversation" ref={conversationRef} aria-live="polite">
        {messages.length === 0 ? (
          <div className="agent-welcome">
            <span className="welcome-glyph" aria-hidden="true">✦</span>
            <h3>What are you investigating?</h3>
            <p>
              Ask for a comparison, an indicator explanation, or a stock snapshot.
              Market facts are labeled with their source and data status.
            </p>
            <div className="quick-prompts">
              {quickPrompts.map((prompt) => (
                <button key={prompt} onClick={() => void onSend(prompt)} type="button">
                  {prompt}<span aria-hidden="true">↗</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="message-list">
            {messages.map((message) => <ChatMessage key={message.id} message={message} />)}
            {isLoading && (
              <div className="thinking" role="status">
                <span /><span /><span /> Researching
              </div>
            )}
          </div>
        )}
      </div>

      <ChatInput
        onSend={onSend}
        isLoading={isLoading}
        placeholder={`Ask about ${selectedSymbol ?? "a stock"}, indicators, or comparisons…`}
      />
    </section>
  );
}
