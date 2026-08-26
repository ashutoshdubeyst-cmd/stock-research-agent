"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type Stock = {
  symbol: string;
  name: string;
  exchange: string;
  currency: string;
  price: number;
  change_percent: number;
  data_status: string;
  source: string;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  traceId?: string;
};

type AgentResponse = {
  answer: string;
  trace_id: string;
  provider: string;
  model: string;
  tools_used: string[];
  sources: string[];
  warning: string;
};

const FALLBACK_STOCKS: Stock[] = [
  { symbol: "TCS", name: "Tata Consultancy Services", exchange: "NSE", currency: "INR", price: 3045.2, change_percent: -0.35, data_status: "mock", source: "mock_provider" },
  { symbol: "INFY", name: "Infosys Limited", exchange: "NSE", currency: "INR", price: 1422.75, change_percent: 0.82, data_status: "mock", source: "mock_provider" },
  { symbol: "RELIANCE", name: "Reliance Industries", exchange: "NSE", currency: "INR", price: 1428.4, change_percent: 1.15, data_status: "mock", source: "mock_provider" },
];

const QUICK_PROMPTS = [
  "Compare TCS and INFY",
  "Explain RSI simply",
  "What does P/E mean?",
];

function formatPrice(value: number, currency: string) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

export default function HomePage() {
  const [stocks, setStocks] = useState<Stock[]>(FALLBACK_STOCKS);
  const [selectedSymbol, setSelectedSymbol] = useState("TCS");
  const [query, setQuery] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [dataNotice, setDataNotice] = useState("Loading market workspace…");

  const loadWorkspace = useCallback(async () => {
    try {
      const [healthResponse, stocksResponse] = await Promise.all([
        fetch(`${API_URL}/api/v1/health`, { cache: "no-store" }),
        fetch(`${API_URL}/api/v1/stocks`, { cache: "no-store" }),
      ]);
      if (!healthResponse.ok || !stocksResponse.ok) throw new Error("Backend unavailable");
      const stockData = (await stocksResponse.json()) as Stock[];
      setStocks(stockData);
      setApiOnline(true);
      setDataNotice(`${stockData[0]?.data_status ?? "mock"} data · ${stockData[0]?.source ?? "local provider"}`);
    } catch {
      setApiOnline(false);
      setDataNotice("Preview data · start the backend to connect");
    }
  }, []);

  useEffect(() => {
    void loadWorkspace();
  }, [loadWorkspace]);

  const visibleStocks = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return stocks;
    return stocks.filter(
      (stock) =>
        stock.symbol.toLowerCase().includes(term) ||
        stock.name.toLowerCase().includes(term),
    );
  }, [query, stocks]);

  const selectedStock =
    stocks.find((stock) => stock.symbol === selectedSymbol) ?? stocks[0];

  async function sendMessage(messageText?: string) {
    const content = (messageText ?? input).trim();
    if (!content || isSending) return;

    const previousMessages = messages;
    setMessages([...previousMessages, { role: "user", content }]);
    setInput("");
    setIsSending(true);

    try {
      const response = await fetch(`${API_URL}/api/v1/agent/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: content,
          history: previousMessages.map(({ role, content: historyContent }) => ({
            role,
            content: historyContent,
          })),
        }),
      });
      const body = (await response.json()) as AgentResponse | { detail?: string };
      if (!response.ok || !("answer" in body)) {
        throw new Error("detail" in body ? body.detail : "The agent could not respond.");
      }
      setMessages((current) => [
        ...current,
        { role: "assistant", content: body.answer, traceId: body.trace_id },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            error instanceof Error
              ? error.message
              : "The research agent is currently unavailable.",
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage();
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Ledger AI home">
          <span className="brand-mark">L</span>
          <span>Ledger<span className="brand-accent">AI</span></span>
        </a>
        <nav className="primary-nav" aria-label="Primary navigation">
          <a className="active" href="#workspace">Workspace</a>
          <a href="#watchlist">Watchlist</a>
          <a href="#methodology">Methodology</a>
        </nav>
        <div className="topbar-actions">
          <span className={`status-pill ${apiOnline ? "online" : ""}`}>
            <span className="status-dot" />
            {apiOnline === null ? "Checking" : apiOnline ? "API connected" : "Preview mode"}
          </span>
          <button className="avatar" type="button" aria-label="Open account menu">AR</button>
        </div>
      </header>

      <section className="workspace" id="workspace">
        <div className="intro" id="top">
          <div>
            <p className="eyebrow">RESEARCH DESK · INDIA</p>
            <h1>Read the market.<br /><em>Question the signal.</em></h1>
          </div>
          <p className="intro-copy">
            Evidence-aware stock research with transparent sources, reproducible
            indicators, and an assistant that knows when data is missing.
          </p>
        </div>

        <div className="dashboard-grid">
          <section className="market-panel" id="watchlist" aria-labelledby="watchlist-title">
            <div className="panel-heading">
              <div>
                <p className="section-label">MARKET PULSE</p>
                <h2 id="watchlist-title">Your watchlist</h2>
              </div>
              <button className="refresh-button" onClick={() => void loadWorkspace()} type="button">↻ Refresh</button>
            </div>

            <label className="search-box">
              <span aria-hidden="true">⌕</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search symbol or company"
                aria-label="Search stocks"
              />
            </label>

            <div className="stock-list">
              {visibleStocks.map((stock) => {
                const positive = stock.change_percent >= 0;
                return (
                  <button
                    className={`stock-row ${selectedSymbol === stock.symbol ? "selected" : ""}`}
                    key={stock.symbol}
                    onClick={() => setSelectedSymbol(stock.symbol)}
                    type="button"
                  >
                    <span className="symbol-tile">{stock.symbol.slice(0, 2)}</span>
                    <span className="stock-identity">
                      <strong>{stock.symbol}</strong>
                      <small>{stock.name}</small>
                    </span>
                    <span className="stock-value">
                      <strong>{formatPrice(stock.price, stock.currency)}</strong>
                      <small className={positive ? "gain" : "loss"}>
                        {positive ? "+" : ""}{stock.change_percent.toFixed(2)}%
                      </small>
                    </span>
                  </button>
                );
              })}
              {visibleStocks.length === 0 && <p className="empty-state">No matching stocks found.</p>}
            </div>

            {selectedStock && (
              <article className="selected-summary">
                <div>
                  <span className="summary-symbol">{selectedStock.symbol}</span>
                  <span>{selectedStock.exchange}</span>
                </div>
                <strong>{formatPrice(selectedStock.price, selectedStock.currency)}</strong>
                <p>{selectedStock.name}</p>
                <div className="mini-chart" aria-label="Illustrative price pattern">
                  {[34, 42, 38, 55, 49, 64, 59, 76, 68, 84, 79, 92].map((height, index) => (
                    <span key={index} style={{ height: `${height}%` }} />
                  ))}
                </div>
                <small>{dataNotice}</small>
              </article>
            )}
          </section>

          <section className="agent-panel" aria-labelledby="agent-title">
            <div className="agent-heading">
              <div className="agent-icon">✦</div>
              <div>
                <p className="section-label">RESEARCH COPILOT</p>
                <h2 id="agent-title">Ask Ledger</h2>
              </div>
              <span className="model-label">GROUNDED MODE</span>
            </div>

            <div className="conversation" aria-live="polite">
              {messages.length === 0 ? (
                <div className="agent-welcome">
                  <span className="welcome-glyph">✦</span>
                  <h3>What are you investigating?</h3>
                  <p>
                    Ask for a comparison, an indicator explanation, or a stock
                    snapshot. Market facts are labeled with their data status.
                  </p>
                  <div className="quick-prompts">
                    {QUICK_PROMPTS.map((prompt) => (
                      <button key={prompt} onClick={() => void sendMessage(prompt)} type="button">
                        {prompt}<span>↗</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="message-list">
                  {messages.map((message, index) => (
                    <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
                      <span className="message-author">{message.role === "user" ? "You" : "Ledger AI"}</span>
                      <p>{message.content}</p>
                      {message.traceId && <small>Trace {message.traceId.slice(0, 8)}</small>}
                    </article>
                  ))}
                  {isSending && <div className="thinking"><span /><span /><span /> Researching</div>}
                </div>
              )}
            </div>

            <form className="chat-form" onSubmit={handleSubmit}>
              <label htmlFor="agent-input" className="sr-only">Ask the research agent</label>
              <textarea
                id="agent-input"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void sendMessage();
                  }
                }}
                placeholder={`Ask about ${selectedStock?.symbol ?? "a stock"}, indicators, or comparisons…`}
                maxLength={2000}
                rows={2}
              />
              <button disabled={!input.trim() || isSending} type="submit" aria-label="Send message">↑</button>
              <small>Answers are educational, not investment advice.</small>
            </form>
          </section>
        </div>

        <footer id="methodology">
          <span>LEDGER AI · RESEARCH WORKSPACE</span>
          <p>Sources first. Calculations reproducible. Uncertainty visible.</p>
          <span>v0.1</span>
        </footer>
      </section>
    </main>
  );
}
