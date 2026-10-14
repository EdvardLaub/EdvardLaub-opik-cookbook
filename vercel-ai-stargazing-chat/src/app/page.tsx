"use client";

import { useState } from "react";
import { useChat } from "@ai-sdk/react";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const { messages, sendMessage, status } = useChat();
  const busy = status === "submitted" || status === "streaming";

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "2rem 1rem", minHeight: "100vh", boxSizing: "border-box", display: "flex", flexDirection: "column" }}>
      <h1 style={{ fontSize: "1.25rem", marginBottom: "0.25rem" }}>Nova, the Lantern Ridge night-sky assistant</h1>
      <p style={{ color: "#9aa3c2", marginTop: 0, fontSize: "0.9rem" }}>
        Ask about targets, telescopes or upcoming sky events. Replies stream; each turn is an Opik trace.
      </p>
      <div style={{ flex: 1 }}>
        {messages.map((m) => (
          <div key={m.id} style={{ margin: "0.75rem 0", display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{ maxWidth: "85%", padding: "0.6rem 0.9rem", borderRadius: 12, whiteSpace: "pre-wrap", lineHeight: 1.45, background: m.role === "user" ? "#5b6cff" : "#1a2040", color: "#fff" }}>
              {m.parts.map((p, i) => (p.type === "text" ? <span key={i}>{p.text}</span> : null))}
            </div>
          </div>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!input.trim() || busy) return;
          sendMessage({ text: input });
          setInput("");
        }}
        style={{ display: "flex", gap: "0.5rem", paddingTop: "1rem" }}
      >
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="When is Jupiter at opposition?" style={{ flex: 1, padding: "0.6rem 0.9rem", borderRadius: 10, border: "1px solid #2c3463", background: "#121731", color: "#fff", fontSize: "1rem" }} />
        <button type="submit" disabled={busy} style={{ padding: "0.6rem 1.1rem", borderRadius: 10, border: "none", background: busy ? "#4a5178" : "#5b6cff", color: "#fff", fontSize: "1rem" }}>
          Send
        </button>
      </form>
    </main>
  );
}
