import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "../config";

export default function AutomationCenter({ analysis, userContext }) {
  const [autoStatus, setAutoStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [showPayload, setShowPayload] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  const [pingResult, setPingResult] = useState(null);
  const [pinging, setPinging] = useState(false);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE_URL}/api/automation/status`);
      if (res.ok) {
        const data = await res.json();
        setAutoStatus(data);
      }
    } catch (e) {
      console.error("Failed to fetch automation status:", e);
    } finally {
      setLoading(false);
    }
  };

  const handlePingWebhook = async () => {
    try {
      setPinging(true);
      const res = await fetch(`${API_BASE_URL}/api/automation/ping-webhook`);
      const data = await res.json();
      setPingResult(data);
      if (data.connected) {
        alert("✅ n8n Webhook is reachable and actively responding on " + data.webhook_url);
      } else {
        alert("⚠️ n8n Webhook is offline or unreachable: " + (data.reason || "Please ensure your n8n workflow is active on n8n Cloud."));
      }
    } catch (e) {
      alert("Failed to ping webhook: " + e.message);
    } finally {
      setPinging(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleManualTrigger = async () => {
    try {
      setTriggering(true);
      const res = await fetch(`${API_BASE_URL}/api/automation/trigger`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok) {
        await fetchStatus();
      } else {
        alert("Trigger failed: " + (data.detail || "Unknown error"));
      }
    } catch (err) {
      alert("Error triggering n8n automation: " + err.message);
    } finally {
      setTriggering(false);
    }
  };

  const hasAnalysis = Boolean(analysis && analysis.total_elements);
  const latestAutomation = autoStatus?.latest_automation;
  const qualityScore = autoStatus?.quality_score ?? analysis?.quality_score ?? 0;
  const criticalCount = autoStatus?.critical_issues_count ?? 0;
  const dispatchStatus = autoStatus?.dispatch_status || "idle";

  const getStatusBadge = () => {
    if (!autoStatus?.n8n_enabled) {
      return { label: "n8n Disabled (Bypass Mode)", bg: "rgba(100, 116, 139, 0.2)", color: "#94a3b8", border: "rgba(100, 116, 139, 0.4)" };
    }
    if (latestAutomation) {
      if (latestAutomation.requires_immediate_action) {
        return { label: "Workflow Completed (Severe)", bg: "rgba(218, 54, 51, 0.2)", color: "#da3633", border: "rgba(218, 54, 51, 0.4)" };
      }
      return { label: "Workflow Completed (Clear)", bg: "rgba(35, 134, 54, 0.2)", color: "#238636", border: "rgba(35, 134, 54, 0.4)" };
    }
    if (dispatchStatus === "completed") {
      return { label: "Workflow Completed", bg: "rgba(35, 134, 54, 0.2)", color: "#238636", border: "rgba(35, 134, 54, 0.4)" };
    }
    if (dispatchStatus === "dispatched") {
      return { label: "Processing in n8n...", bg: "rgba(0, 200, 255, 0.2)", color: "#00c8ff", border: "rgba(0, 200, 255, 0.4)" };
    }
    if (pingResult?.connected) {
      return { label: "n8n Connected & Active", bg: "rgba(35, 134, 54, 0.2)", color: "#238636", border: "rgba(35, 134, 54, 0.4)" };
    }
    if (dispatchStatus.startsWith("error") || dispatchStatus.startsWith("failed")) {
      return { label: "n8n Webhook Pending (Awaiting activation or dispatch)", bg: "rgba(210, 153, 34, 0.2)", color: "#d29922", border: "rgba(210, 153, 34, 0.4)" };
    }
    return { label: "Ready / Awaiting Upload", bg: "rgba(56, 189, 248, 0.15)", color: "#38bdf8", border: "rgba(56, 189, 248, 0.3)" };
  };

  const badge = getStatusBadge();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Header Card */}
      <div style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border-color)",
        borderRadius: "12px",
        padding: "24px 28px",
        backdropFilter: "blur(12px)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "16px"
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <span style={{ fontSize: "24px" }}>⚡</span>
            <h1 style={{ fontSize: "22px", fontWeight: "800", color: "#fff", margin: 0 }}>
              n8n Automation Center
            </h1>
            <span style={{
              fontSize: "11px",
              fontWeight: "700",
              textTransform: "uppercase",
              padding: "3px 10px",
              borderRadius: "20px",
              background: badge.bg,
              color: badge.color,
              border: `1px solid ${badge.border}`,
              letterSpacing: "0.08em"
            }}>
              {badge.label}
            </span>
          </div>
          <p style={{ color: "var(--text-secondary)", fontSize: "13px", margin: 0 }}>
            Event-driven pipeline orchestrating IfcOpenShell analysis, AI risk synthesis, and cloud persistence.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={handlePingWebhook}
            disabled={pinging}
            className="btn-secondary"
            style={{ fontSize: "12px", padding: "8px 14px" }}
            title="Tests if configured n8n webhook listener is reachable"
          >
            {pinging ? "Pinging..." : "🔌 Ping Webhook"}
          </button>
          <button
            onClick={fetchStatus}
            disabled={loading}
            className="btn-secondary"
            style={{ fontSize: "12px", padding: "8px 14px" }}
          >
            {loading ? "Refreshing..." : "🔄 Refresh"}
          </button>
          <button
            onClick={handleManualTrigger}
            disabled={!hasAnalysis || triggering}
            className="btn-primary"
            style={{
              fontSize: "12px",
              padding: "8px 18px",
              opacity: !hasAnalysis ? 0.5 : 1,
              cursor: !hasAnalysis ? "not-allowed" : "pointer"
            }}
          >
            {triggering ? "Triggering..." : "⚡ Run n8n Automation"}
          </button>
        </div>
      </div>

      {!hasAnalysis ? (
        <div style={{
          padding: "60px 40px",
          textAlign: "center",
          background: "var(--bg-card)",
          border: "1px solid var(--border-color)",
          borderRadius: "12px"
        }}>
          <div style={{ fontSize: "40px", marginBottom: "16px" }}>📥</div>
          <h3 style={{ fontSize: "18px", color: "#fff", marginBottom: "8px" }}>No Model Loaded</h3>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px", maxWidth: "480px", margin: "0 auto" }}>
            Please upload an IFC model from the <strong>Home</strong> tab or load a sample from the <strong>Cloud Library</strong>. Once analysis completes, n8n will automatically ingest the results.
          </p>
        </div>
      ) : (
        <>
          {/* Workflow Pipeline Step Indicator */}
          <div style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-color)",
            borderRadius: "12px",
            padding: "20px 24px"
          }}>
            <div style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", color: "var(--text-secondary)", letterSpacing: "0.1em", marginBottom: "16px" }}>
              Pipeline Execution Sequence
            </div>
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "12px"
            }}>
              {[
                { step: "01", title: "IFC Analysis", desc: "IfcOpenShell Engine", active: true, done: true },
                { step: "02", title: "n8n Webhook", desc: "Metadata Dispatch", active: Boolean(autoStatus?.current_job_id), done: dispatchStatus === "dispatched" || dispatchStatus === "completed" },
                { step: "03", title: "Risk Filter", desc: "Quality & Severity Check", active: Boolean(autoStatus?.current_job_id), done: Boolean(latestAutomation) },
                { step: "04", title: "AI Briefing", desc: "Groq LLaMA Synthesis", active: Boolean(latestAutomation), done: Boolean(latestAutomation?.summary) },
                { step: "05", title: "Supabase Sync", desc: "Cloud Audit Artifact", active: Boolean(latestAutomation), done: Boolean(latestAutomation?.cloud_saved) },
              ].map((s, idx) => (
                <div key={idx} style={{
                  padding: "14px 16px",
                  borderRadius: "8px",
                  background: s.done ? "rgba(35, 134, 54, 0.12)" : s.active ? "rgba(0, 200, 255, 0.08)" : "rgba(10, 15, 29, 0.6)",
                  border: s.done ? "1px solid rgba(35, 134, 54, 0.4)" : s.active ? "1px solid rgba(0, 200, 255, 0.3)" : "1px solid var(--border-color)",
                  position: "relative"
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ fontSize: "11px", fontWeight: "800", color: s.done ? "#238636" : "var(--color-primary)" }}>
                      {s.step}
                    </span>
                    <span style={{ fontSize: "12px" }}>
                      {s.done ? "✅" : s.active ? "⏳" : "⚪"}
                    </span>
                  </div>
                  <div style={{ fontSize: "13px", fontWeight: "700", color: "#fff" }}>{s.title}</div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>{s.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Metric Highlights Grid */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "16px"
          }}>
            <div style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: "12px",
              padding: "20px"
            }}>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>
                Model Quality Score
              </div>
              <div style={{ fontSize: "32px", fontWeight: "900", color: qualityScore >= 70 ? "#238636" : "#da3633", marginTop: "8px" }}>
                {qualityScore} <span style={{ fontSize: "16px", color: "var(--text-secondary)", fontWeight: "500" }}>/ 100</span>
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "6px" }}>
                Status: <strong>{qualityScore >= 85 ? "Excellent" : qualityScore >= 70 ? "Good" : "Action Required"}</strong>
              </div>
            </div>

            <div style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: "12px",
              padding: "20px"
            }}>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>
                Active Issues & Rules
              </div>
              <div style={{ fontSize: "32px", fontWeight: "900", color: criticalCount > 0 ? "#ffb347" : "#238636", marginTop: "8px" }}>
                {criticalCount}
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "6px" }}>
                Across naming, geometry, & NBC checks
              </div>
            </div>

            <div style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: "12px",
              padding: "20px"
            }}>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>
                Active Job ID
              </div>
              <div style={{ fontSize: "16px", fontWeight: "700", color: "var(--color-primary)", marginTop: "12px", fontFamily: "Space Mono, monospace" }}>
                {autoStatus?.current_job_id || "None"}
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "8px" }}>
                File: {autoStatus?.current_file_id || "model.ifc"}
              </div>
            </div>

            <div style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: "12px",
              padding: "20px"
            }}>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>
                Deliverables Ready
              </div>
              <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
                <a
                  href={`${API_BASE_URL}/api/analyze/pdf-report`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-secondary"
                  style={{ fontSize: "11px", padding: "6px 12px", textDecoration: "none" }}
                >
                  📄 Audit PDF
                </a>
                <button
                  onClick={() => {
                    const fails = (analysis.rule_checks || []).flatMap(r => 
                      (r.fails || []).map(gid => ({
                        GlobalId: gid,
                        Rule: r.name,
                        Severity: r.severity,
                        Category: r.category,
                        Message: `Violation of ${r.name}`
                      }))
                    );
                    fetch(`${API_BASE_URL}/api/analyze/bcf`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify(fails.slice(0, 100))
                    })
                    .then(res => res.blob())
                    .then(blob => {
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = "issues.bcfzip";
                      a.click();
                    });
                  }}
                  className="btn-secondary"
                  style={{ fontSize: "11px", padding: "6px 12px" }}
                >
                  📦 BCF Zip
                </button>
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "8px" }}>
                BuildingSMART & NBC compliant
              </div>
            </div>
          </div>

          {/* AI Executive Summary Box */}
          <div style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-color)",
            borderRadius: "12px",
            padding: "24px",
            backdropFilter: "blur(12px)"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontSize: "18px" }}>🤖</span>
                <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#fff", margin: 0 }}>
                  Automated BIM Executive Summary
                </h3>
                {latestAutomation && (
                  <span style={{
                    padding: "3px 10px",
                    borderRadius: "16px",
                    fontSize: "11px",
                    fontWeight: "700",
                    background: latestAutomation.requires_immediate_action ? "rgba(218, 54, 51, 0.2)" : "rgba(35, 134, 54, 0.2)",
                    color: latestAutomation.requires_immediate_action ? "#da3633" : "#238636",
                    border: `1px solid ${latestAutomation.requires_immediate_action ? "rgba(218, 54, 51, 0.4)" : "rgba(35, 134, 54, 0.4)"}`
                  }}>
                    {latestAutomation.requires_immediate_action ? "⚠️ Severe Risks Flagged" : "✅ Clear Model Verified"}
                  </span>
                )}
              </div>
              {latestAutomation?.received_at && (
                <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontFamily: "Space Mono, monospace" }}>
                  Generated: {new Date(latestAutomation.received_at).toLocaleTimeString()}
                </span>
              )}
            </div>

            {latestAutomation?.summary ? (
              <div style={{
                background: "rgba(10, 15, 29, 0.7)",
                border: "1px solid rgba(0, 200, 255, 0.2)",
                borderRadius: "8px",
                padding: "20px",
                color: "var(--text-primary)",
                fontSize: "14px",
                lineHeight: "1.7",
                whiteSpace: "pre-wrap"
              }}>
                {latestAutomation.summary}
              </div>
            ) : (
              <div style={{
                padding: "24px",
                textAlign: "center",
                background: "rgba(10, 15, 29, 0.4)",
                borderRadius: "8px",
                border: "1px dashed var(--border-color)"
              }}>
                <p style={{ color: "var(--text-secondary)", fontSize: "13px", margin: "0 0 12px 0" }}>
                  No automated summary received yet. Run the n8n automation workflow or click below to synthesize now.
                </p>
                <button
                  onClick={handleManualTrigger}
                  disabled={triggering}
                  className="btn-secondary"
                  style={{ fontSize: "12px", padding: "8px 16px" }}
                >
                  {triggering ? "Synthesizing..." : "⚡ Generate AI Summary"}
                </button>
              </div>
            )}
          </div>

          {/* Cloud Storage & Integration Diagnostic */}
          <div style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-color)",
            borderRadius: "12px",
            padding: "20px 24px"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h4 style={{ fontSize: "14px", fontWeight: "700", color: "#fff", margin: "0 0 4px 0" }}>
                  n8n Webhook & Supabase Integration Diagnostics
                </h4>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: 0 }}>
                  Webhook Target: <code style={{ color: "var(--color-primary)" }}>{autoStatus?.n8n_webhook_url || "Not configured"}</code>
                </p>
              </div>
              <button
                onClick={() => setShowPayload(!showPayload)}
                className="btn-secondary"
                style={{ fontSize: "11px", padding: "6px 12px" }}
              >
                {showPayload ? "Hide Details ▲" : "Inspect Payload ▼"}
              </button>
            </div>

            {showPayload && (
              <div style={{ marginTop: "16px" }}>
                <pre style={{
                  background: "#050810",
                  padding: "16px",
                  borderRadius: "8px",
                  fontSize: "11px",
                  color: "#38bdf8",
                  overflowX: "auto",
                  border: "1px solid var(--border-color)",
                  margin: 0
                }}>
                  {JSON.stringify(autoStatus, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
