import React, { useState } from "react";
import { API_BASE_URL } from "../config";

export default function AskModel({ analysis }) {
  const [chatQuery, setChatQuery] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [thinking, setThinking] = useState(false);
  const [listening, setListening] = useState(false);

  const sampleQuestions = [
    "How many proxy elements are on floor 2?",
    "Which walls are missing fire rating?",
    "What is the overall quality score and why?",
    "List all doors that have no Pset_DoorCommon.",
    "Which floor has the most issues?",
    "Is this model ready for NBC 2016 compliance?"
  ];

  const handleAskQuestion = async (qText) => {
    const text = qText || chatQuery;
    if (!text.trim()) return;

    setThinking(true);
    const userTurn = { q: text, a: null };
    setChatHistory(prev => [...prev, userTurn]);
    setChatQuery("");

    try {
      const res = await fetch(`${API_BASE_URL}/api/assistant/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text })
      });
      const data = await res.json();
      
      setChatHistory(prev => {
        const copy = [...prev];
        if (copy.length > 0) {
          copy[copy.length - 1].a = data.answer;
        }
        return copy;
      });
    } catch (err) {
      setChatHistory(prev => {
        const copy = [...prev];
        if (copy.length > 0) {
          copy[copy.length - 1].a = "⚠️ Groq API connection failed. Check your GROQ_API_KEY environment variable in the backend folder.";
        }
        return copy;
      });
    } finally {
      setThinking(false);
    }
  };

  // Mock voice speech-to-text
  const handleVoiceRecord = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice speech recognition is not supported in this browser. Please try in Chrome or Edge.");
      return;
    }

    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = 'en-US';

    rec.onstart = () => {
      setListening(true);
    };

    rec.onend = () => {
      setListening(false);
    };

    rec.onerror = (e) => {
      console.error(e);
      setListening(false);
    };

    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setChatQuery(transcript);
    };

    rec.start();
  };

  const handleClearHistory = () => {
    setChatHistory([]);
  };

  if (!analysis) {
    return (
      <div style={{ padding: "40px", textAlign: "center", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px" }}>
        <h3>⚠️ No analysis data available</h3>
        <p style={{ color: "var(--text-secondary)", marginTop: "8px" }}>Please upload an IFC file on the Home page first.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="title-group">
        <h1 className="page-title">💬 Ask Your Model</h1>
        <p className="page-caption">Type or speak plain English questions — ArchiShield reads your model data and answers using live parameters.</p>
      </div>

      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px", marginBottom: "20px" }}>
        <h3 style={{ fontSize: "14px", fontWeight: "700", marginBottom: "10px" }}>💡 Example questions you can ask:</h3>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {sampleQuestions.map((q, i) => (
            <button 
              key={i} 
              className="btn-secondary" 
              style={{ fontSize: "11px", padding: "6px 12px", border: "1px dashed var(--border-color)" }}
              onClick={() => handleAskQuestion(q)}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Query Bar */}
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px", marginBottom: "20px" }}>
        <div style={{ display: "flex", gap: "10px" }}>
          <input 
            type="text" 
            className="form-input" 
            placeholder="Type your question here (e.g. How many wall elements are in the model?)..." 
            value={chatQuery}
            onChange={e => setChatQuery(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") handleAskQuestion(); }}
          />
          <button 
            className="btn-secondary" 
            style={{ 
              fontSize: "18px", 
              padding: "10px 14px", 
              backgroundColor: listening ? "var(--color-danger)" : "rgba(16,22,42,0.8)",
              borderColor: listening ? "var(--color-danger)" : "var(--border-color)",
              color: listening ? "#fff" : "inherit"
            }} 
            onClick={handleVoiceRecord}
          >
            {listening ? "🔴" : "🎤"}
          </button>
          <button className="btn-primary" onClick={() => handleAskQuestion()} disabled={thinking || !chatQuery.trim()}>
            {thinking ? "Thinking..." : "🔍 Ask"}
          </button>
        </div>
        <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "8px" }}>🎤 Click the mic to speak your question (Chrome/Edge only).</p>
      </div>

      {/* History */}
      {chatHistory.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {chatHistory.map((turn, i) => (
            <div key={i} style={{ display: "flex", flexDirection: "column", gap: "0px" }}>
              {/* Question */}
              <div style={{ 
                background: "#161b22", 
                border: "1px solid #30363d", 
                padding: "12px 16px", 
                borderRadius: "10px 10px 0 0", 
                fontSize: "14px",
                borderBottom: "none"
              }}>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)", letterSpacing: "1px", marginBottom: "4px", textTransform: "uppercase" }}>YOU ASKED</div>
                <div style={{ fontWeight: "600", color: "#fff" }}>{turn.q}</div>
              </div>

              {/* Answer */}
              <div style={{ 
                background: "rgba(255,255,255,0.015)", 
                border: "1px solid #30363d", 
                padding: "14px 18px", 
                borderRadius: "0 0 10px 10px", 
                fontSize: "14px", 
                lineHeight: "1.6",
                marginBottom: "12px"
              }}>
                <div style={{ fontSize: "11px", color: "var(--color-primary)", letterSpacing: "1px", marginBottom: "6px" }}>💬 ARCHISHIELD</div>
                {turn.a ? (
                  <div style={{ color: "#e6edf3", whiteSpace: "pre-wrap" }}>{turn.a}</div>
                ) : (
                  <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>Thinking...</div>
                )}
              </div>
            </div>
          ))}

          <button className="btn-secondary" style={{ alignSelf: "flex-start", marginTop: "12px" }} onClick={handleClearHistory}>
            🗑️ Clear conversation
          </button>
        </div>
      ) : (
        <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "60px 10px", background: "rgba(0,0,0,0.15)", borderRadius: "12px", border: "1px dashed var(--border-color)" }}>
          💬 Type a question above or click the sample buttons to start asking the model assistant about scanned geometries and validation statuses.
        </div>
      )}
    </div>
  );
}
