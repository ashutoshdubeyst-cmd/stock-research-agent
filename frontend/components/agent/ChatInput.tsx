"use client";

import { FormEvent, KeyboardEvent, useState } from "react";

import LoadingSpinner from "../ui/LoadingSpinner";

type ChatInputProps = {
  onSend: (message: string) => void | Promise<void>;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
};

export default function ChatInput({
  onSend,
  isLoading = false,
  disabled = false,
  placeholder = "Ask about a stock, indicator, or comparison…",
  maxLength = 2_000,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const canSend = value.trim().length > 0 && !isLoading && !disabled;

  async function submit() {
    const message = value.trim();
    if (!message || !canSend) return;
    setValue("");
    await onSend(message);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void submit();
    }
  }

  return (
    <form className="chat-form" onSubmit={handleSubmit}>
      <label htmlFor="research-question" className="sr-only">Ask the research agent</label>
      <textarea
        id="research-question"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        maxLength={maxLength}
        rows={2}
        disabled={disabled}
      />
      <button disabled={!canSend} type="submit" aria-label="Send message">
        {isLoading ? <LoadingSpinner size="small" label="Researching" /> : "↑"}
      </button>
      <small>
        <span>Enter to send · Shift + Enter for a new line</span>
        <span>{value.length}/{maxLength}</span>
      </small>
    </form>
  );
}
