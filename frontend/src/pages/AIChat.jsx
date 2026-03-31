import { useState, useRef, useEffect } from "react";
import {
  Send, Bot, User, Sparkles, TrendingUp, Loader2, Trash2,
  BarChart3, Search, MessageSquare, Zap,
} from "lucide-react";
import { aiChat, aiAnalyze } from "../api";

const SUGGESTIONS = [
  { icon: TrendingUp, text: "How's the market looking today?" },
  { icon: BarChart3, text: "Analyze RELIANCE for me" },
  { icon: Search, text: "Best banking stocks to buy now?" },
  { icon: Zap, text: "Give me a NIFTY trade setup" },
];

function MarkdownText({ text }) {
  // Simple markdown: **bold**, ### headers, - lists, `code`
  const lines = text.split("\n");
  return (
    <div className="ai-markdown space-y-1.5">
      {lines.map((line, i) => {
        if (line.startsWith("### "))
          return <h3 key={i} className="text-gold font-semibold text-sm mt-3 mb-1">{line.slice(4)}</h3>;
        if (line.startsWith("## "))
          return <h2 key={i} className="text-gold-bright font-bold text-base mt-3 mb-1">{line.slice(3)}</h2>;
        if (line.startsWith("- ") || line.startsWith("* "))
          return (
            <div key={i} className="flex gap-2 text-[13px] leading-relaxed">
              <span className="text-gold/50 mt-0.5">•</span>
              <span dangerouslySetInnerHTML={{ __html: boldify(line.slice(2)) }} />
            </div>
          );
        if (line.trim() === "") return <div key={i} className="h-1" />;
        return <p key={i} className="text-[13px] leading-relaxed" dangerouslySetInnerHTML={{ __html: boldify(line) }} />;
      })}
    </div>
  );
}

function boldify(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-100 font-semibold">$1</strong>')
    .replace(/`(.+?)`/g, '<code class="bg-surface-2 px-1.5 py-0.5 rounded text-gold text-[12px] font-mono">$1</code>')
    .replace(/📊|📈|📉|💰|⚠️|✅|❌|🎯|🔥|💡|🏦|📌/g, '<span class="inline-block">$&</span>');
}

export default function AIChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const send = async (text) => {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput("");

    const userMsg = { role: "user", text: msg, time: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      // Build context from previous messages (last 8)
      const context = messages.slice(-8).map((m) => ({
        role: m.role === "user" ? "user" : "model",
        text: m.text,
      }));

      const res = await aiChat({ message: msg, context });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: res.response,
          time: new Date(),
          symbols: res.enriched_symbols,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `⚠️ ${err.message || "Failed to get response. Please try again."}`, time: new Date(), error: true },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const analyzeStock = async (symbol) => {
    setLoading(true);
    setMessages((prev) => [...prev, { role: "user", text: `Deep analysis: ${symbol}`, time: new Date() }]);

    try {
      const res = await aiAnalyze({ symbol });
      const dataLine = res.stock_data
        ? `\n\n📊 **${res.stock_data.name}** — ₹${res.stock_data.price} (${res.stock_data.change_pct >= 0 ? "+" : ""}${res.stock_data.change_pct}%) | RSI: ${res.stock_data.rsi} | PE: ${res.stock_data.pe}`
        : "";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: res.response + dataLine, time: new Date() },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `⚠️ ${err.message}`, time: new Date(), error: true },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clear = () => {
    setMessages([]);
    inputRef.current?.focus();
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-[calc(100vh-48px)] animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gold/20 to-gold/5 flex items-center justify-center border border-gold/20">
            <Sparkles size={20} className="text-gold" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gold-bright font-display tracking-tight">STONKS AI</h1>
            <p className="text-[11px] text-muted font-mono">Powered by Gemini · Real-time market intelligence</p>
          </div>
        </div>
        {messages.length > 0 && (
          <button onClick={clear} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium text-muted hover:text-red-400 hover:bg-red-500/10 transition-all border border-transparent hover:border-red-500/20">
            <Trash2 size={12} /> Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-1">
        {isEmpty && (
          <div className="flex flex-col items-center justify-center h-full pb-20">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-gold/15 to-gold/5 flex items-center justify-center mb-5 border border-gold/15">
              <Bot size={32} className="text-gold/70" />
            </div>
            <h2 className="text-lg font-semibold text-gray-200 mb-1">What would you like to know?</h2>
            <p className="text-sm text-muted mb-8 text-center max-w-md">
              Ask about any stock, market trends, trade setups, or portfolio advice. I use real-time market data.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => send(s.text)}
                  className="flex items-center gap-3 px-4 py-3 rounded-xl bg-surface-2/50 border border-gold/10 text-left text-sm text-gray-300 hover:border-gold/25 hover:bg-surface-2 transition-all group"
                >
                  <s.icon size={16} className="text-gold/50 group-hover:text-gold transition-colors flex-shrink-0" />
                  <span>{s.text}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 py-3 px-2 rounded-lg ${msg.role === "user" ? "" : "bg-surface-2/30"}`}>
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
              msg.role === "user"
                ? "bg-gold/15 border border-gold/20"
                : msg.error
                  ? "bg-red-500/15 border border-red-500/20"
                  : "bg-matrix/10 border border-matrix/20"
            }`}>
              {msg.role === "user"
                ? <User size={14} className="text-gold" />
                : <Bot size={14} className={msg.error ? "text-red-400" : "text-matrix"} />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[11px] font-semibold text-muted uppercase tracking-wider">
                  {msg.role === "user" ? "You" : "Stonks AI"}
                </span>
                <span className="text-[10px] text-muted/50 font-mono">
                  {msg.time?.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
              {msg.role === "user" ? (
                <p className="text-[13px] text-gray-200 leading-relaxed">{msg.text}</p>
              ) : (
                <MarkdownText text={msg.text} />
              )}
              {msg.symbols?.length > 0 && (
                <div className="flex gap-1.5 mt-2 flex-wrap">
                  {msg.symbols.map((s) => (
                    <button
                      key={s}
                      onClick={() => analyzeStock(s)}
                      disabled={loading}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-gold/10 border border-gold/20 text-[10px] font-mono font-semibold text-gold hover:bg-gold/20 transition-colors"
                    >
                      <BarChart3 size={10} /> Deep Analyze {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 py-3 px-2 rounded-lg bg-surface-2/30">
            <div className="w-7 h-7 rounded-lg bg-matrix/10 border border-matrix/20 flex items-center justify-center flex-shrink-0">
              <Bot size={14} className="text-matrix" />
            </div>
            <div className="flex items-center gap-2 pt-1">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-gold/60 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-gold/60 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-gold/60 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
              <span className="text-[11px] text-muted font-mono">Analyzing markets...</span>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="pt-3 mt-auto">
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about any stock, market trend, or trade idea..."
              disabled={loading}
              className="w-full bg-surface-2/50 border border-gold/15 rounded-xl px-4 py-3 pr-12 text-sm text-gray-200 placeholder-muted/50 outline-none focus:border-gold/30 transition-colors resize-none font-sans disabled:opacity-50"
              style={{ minHeight: "46px", maxHeight: "120px" }}
              onInput={(e) => {
                e.target.style.height = "46px";
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
              }}
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || loading}
              className="absolute right-2 bottom-2 p-2 rounded-lg bg-gold/15 text-gold hover:bg-gold/25 transition-all disabled:opacity-30 disabled:hover:bg-gold/15"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </div>
        </div>
        <p className="text-[10px] text-muted/40 text-center mt-2 font-mono">
          AI analysis is for educational purposes only. Not financial advice. Always do your own research.
        </p>
      </div>
    </div>
  );
}
