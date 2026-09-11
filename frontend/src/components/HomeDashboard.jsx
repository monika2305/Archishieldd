import React, { useState } from "react";
import { API_BASE_URL } from "../config";

export default function HomeDashboard({ 
  userContext, 
  setUserContext, 
  analysis, 
  setAnalysis, 
  onUploadSuccess, 
  viewMode, 
  setViewMode, 
  activeNav, 
  setActiveNav 
}) {
  const [loginForm, setLoginForm] = useState({
    name: "",
    role: "— Select —",
    domain: "— Select —",
    purpose: "— Select —"
  });
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showStepChecks, setShowStepChecks] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [cloudUploaded, setCloudUploaded] = useState(false);

  const roles = [
    "— Select —", "Architect", "Structural Engineer",
    "BIM Manager", "Contractor", "Facility Manager", "Student / Researcher"
  ];
  
  const domains = [
    "— Select —", "Architecture", "Structural",
    "MEP", "Infrastructure", "Facility Management"
  ];

  const purposes = [
    "— Select —", "Design coordination", "Compliance",
    "Construction", "Handover / FM", "Academic / Research"
  ];

  const missingFields = [];
  if (!loginForm.name.trim()) missingFields.push("Name");
  if (loginForm.role === "— Select —") missingFields.push("Role");
  if (loginForm.domain === "— Select —") missingFields.push("Project Domain");
  if (loginForm.purpose === "— Select —") missingFields.push("Purpose of IFC");

  const loginComplete = missingFields.length === 0;

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    if (!loginComplete) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginForm)
      });
      const data = await res.json();
      if (data.status === "success") {
        setUserContext(data.context);
      }
    } catch (err) {
      alert(`Backend server not running on ${API_BASE_URL}. Start the backend first!`);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.toLowerCase().endsWith(".ifc")) {
        await uploadFile(file);
      } else {
        alert("Please upload only .ifc files.");
      }
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    await uploadFile(file);
  };

  const uploadFile = async (file) => {
    setUploading(true);
    setUploadProgress(10);
    setCloudUploaded(false);
    const formData = new FormData();
    formData.append("file", file);
    try {
      setUploadProgress(40);
      const res = await fetch(`${API_BASE_URL}/api/analyze/upload`, {
        method: "POST",
        body: formData
      });
      setUploadProgress(80);
      if (!res.ok) {
        let errDetail = "Server returned status " + res.status;
        try {
          const errData = await res.json();
          if (errData.detail) errDetail = errData.detail;
        } catch (_) {}
        alert("Upload failed: " + errDetail);
        return;
      }
      const data = await res.json();
      setUploadProgress(100);
      if (data.status === "success") {
        setAnalysis(data.results);
        if (data.cloud_uploaded) {
          setCloudUploaded(true);
        }
        onUploadSuccess();
      } else {
        alert("Parsing failed: " + (data.detail || "Unknown error"));
      }
    } catch (err) {
      console.error("Upload error:", err);
      alert("Connection to backend failed. Please check network connectivity or wait 30 seconds if backend is waking up on Render.");
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDownloadSample = () => {
    // Standard mock file trigger or fetch from backend
    window.open(`${API_BASE_URL}/api/analyze/download-sample`, "_blank");
  };

  const handleDownloadPDF = () => {
    window.open(`${API_BASE_URL}/api/analyze/pdf-report`, "_blank");
  };

  // If not logged in, show Login Page
  if (!userContext.name) {
    return (
      <div style={{ maxWidth: "600px", margin: "80px auto", padding: "32px", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", backdropFilter: "blur(10px)" }}>
        <h2 style={{ fontSize: "24px", fontWeight: "800", marginBottom: "12px", textAlign: "center" }}>🔍 IFC Semantic Data-Loss Analyser</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "14px", textAlign: "center", marginBottom: "24px" }}>Please fill in all fields to enter the dashboard.</p>
        
        <form onSubmit={handleLoginSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ fontSize: "12px", display: "block", marginBottom: "6px", color: "var(--text-secondary)" }}>Your Name *</label>
            <input type="text" className="form-input" placeholder="e.g. Moni" value={loginForm.name} onChange={e => setLoginForm({...loginForm, name: e.target.value})} />
          </div>

          <div>
            <label style={{ fontSize: "12px", display: "block", marginBottom: "6px", color: "var(--text-secondary)" }}>Your Role *</label>
            <select className="form-select" value={loginForm.role} onChange={e => setLoginForm({...loginForm, role: e.target.value})}>
              {roles.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          <div>
            <label style={{ fontSize: "12px", display: "block", marginBottom: "6px", color: "var(--text-secondary)" }}>Project Domain *</label>
            <select className="form-select" value={loginForm.domain} onChange={e => setLoginForm({...loginForm, domain: e.target.value})}>
              {domains.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>

          <div>
            <label style={{ fontSize: "12px", display: "block", marginBottom: "6px", color: "var(--text-secondary)" }}>Purpose of IFC *</label>
            <select className="form-select" value={loginForm.purpose} onChange={e => setLoginForm({...loginForm, purpose: e.target.value})}>
              {purposes.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          {missingFields.length > 0 && (
            <div style={{ padding: "12px", backgroundColor: "var(--color-warning-bg)", border: "1px solid rgba(210,153,34,0.3)", borderRadius: "6px", color: "#ffb347", fontSize: "13px" }}>
              ⚠️ Please fill in: <strong>{missingFields.join(", ")}</strong>
            </div>
          )}

          <button type="submit" className="btn-primary" disabled={!loginComplete} style={{ width: "100%", padding: "14px" }}>
            Continue →
          </button>
        </form>

        <div style={{ borderTop: "1px solid var(--border-color)", marginTop: "24px", paddingTop: "20px", textAlign: "center" }}>
          <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "12px" }}>Don't have an IFC file? Download our sample model and explore the dashboards.</p>
          <a href="/sample_model.ifc" download className="btn-secondary" style={{ display: "inline-block", fontSize: "12px", textDecoration: "none" }}>
            ⬇️ Download Sample IFC Model
          </a>
        </div>
      </div>
    );
  }

  // --- RENDER MAIN HOMEPAGE (IF LOGGED IN) ---
  const severityColors = { LOW: "#238636", MEDIUM: "#58a6ff", HIGH: "#d29922", CRITICAL: "#da3633" };
  const hasAnalysis = analysis && analysis.total_elements > 0;

  // View Mode Toggles styles
  const viewOptions = [
    { mode: "Technical", icon: "🔬", desc: "IFC classes · GlobalIds · Psets · Schema · Relationships" },
    { mode: "Business", icon: "💼", desc: "Cost impact · Delay risk · Project readiness · Plain English" },
    { mode: "Full", icon: "📊", desc: "Complete view — Technical + Business combined" }
  ];

  return (
    <div>
      <div className="title-group">
        <h1 className="page-title">🔍 IFC Semantic Data-Loss Analyser</h1>
        <p className="page-caption">Upload your IFC file to diagnose semantic type drop-outs and metadata completeness.</p>
      </div>

      {/* File Upload Success Alert */}
      {cloudUploaded && (
        <div style={{ 
          background: "rgba(35, 134, 54, 0.15)", 
          border: "1.5px solid #238636", 
          color: "#7ee787", 
          padding: "12px 18px", 
          borderRadius: "8px", 
          marginBottom: "20px", 
          fontSize: "13px", 
          display: "flex", 
          alignItems: "center", 
          gap: "10px" 
        }}>
          <span>☁️</span>
          <strong>IFC file uploaded to cloud storage successfully!</strong>
        </div>
      )}

      {/* File Upload Section */}
      <div 
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        style={{ 
          background: "var(--bg-card)", 
          border: `2.5px dashed ${dragActive ? "var(--color-primary)" : "var(--border-color)"}`, 
          borderRadius: "12px", 
          padding: "36px 28px", 
          marginBottom: "28px", 
          textAlign: "center", 
          backdropFilter: "blur(10px)",
          transition: "all 0.2s ease"
        }}
      >
        <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "12px" }}>
          📂 {dragActive ? "Drop your IFC file now!" : "Upload your IFC model"}
        </h3>
        <input type="file" accept=".ifc" id="ifc-upload" style={{ display: "none" }} onChange={handleFileUpload} disabled={uploading} />
        
        <div style={{ marginBottom: "12px" }}>
          <label htmlFor="ifc-upload" className="btn-primary" style={{ padding: "12px 32px", cursor: "pointer", display: "inline-flex" }}>
            {uploading ? "Processing IFC..." : "Select IFC file"}
          </label>
        </div>
        
        <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
          Drag and drop file here, or click to browse. Supports files up to 800 MB.
        </p>
        
        {uploading && (
          <div style={{ marginTop: "16px", maxWidth: "400px", margin: "16px auto" }}>
            <div style={{ height: "6px", background: "rgba(0,200,255,0.1)", borderRadius: "4px", overflow: "hidden" }}>
              <div style={{ width: `${uploadProgress}%`, background: "var(--color-primary)", height: "100%", transition: "width 0.2s ease" }}></div>
            </div>
            <p style={{ fontSize: "11px", color: "var(--color-primary)", marginTop: "6px" }}>Analyzing structure... {uploadProgress}%</p>
          </div>
        )}
      </div>

      {hasAnalysis && (
        <div>
          {/* Export Source Risk */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "24px", marginBottom: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "14px" }}>🏗️ IFC Export Source Risk Analysis</h3>
            
            <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: "220px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "8px", padding: "16px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "1px", marginBottom: "6px" }}>EXPORT SOFTWARE</div>
                <div style={{ fontSize: "16px", fontWeight: "800", color: "#fff" }}>{analysis.export_source.tool}</div>
                <div style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "12px", marginBottom: "2px" }}>IFC Schema Version</div>
                <div style={{ fontSize: "12px", fontWeight: "700", color: "var(--color-info)" }}>{analysis.export_source.version}</div>
              </div>

              <div style={{ flex: 2, minWidth: "300px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "8px", padding: "16px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "1px", marginBottom: "10px" }}>PREDICTED SEMANTIC LOSS RISKS</div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {analysis.export_source.risks.map((r, i) => (
                    <div key={i} style={{ display: "flex", gap: "8px", alignItems: "center", fontSize: "12px" }}>
                      <span style={{ 
                        fontSize: "9px", 
                        fontWeight: "700", 
                        padding: "1px 6px", 
                        borderRadius: "3px", 
                        border: "1px solid",
                        background: r[1] === "Critical" || r[1] === "High" ? "var(--color-danger-bg)" : "var(--color-warning-bg)",
                        color: r[1] === "Critical" || r[1] === "High" ? "#ff6b6b" : "#ffb347",
                        borderColor: r[1] === "Critical" || r[1] === "High" ? "rgba(218,54,51,0.5)" : "rgba(210,153,34,0.5)"
                      }}>{r[1].toUpperCase()}</span>
                      <span style={{ color: "var(--text-primary)" }}>{r[0]}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Key Metrics row */}
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Total Scanned</div>
              <div className="metric-value">{analysis.total_elements}</div>
              <div className="metric-subtext">Physical products loaded</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Semantic Type OK</div>
              <div className="metric-value" style={{ color: "var(--color-info)" }}>{analysis.semantic_elements} ({analysis.semantic_pct.toFixed(1)}%)</div>
              <div className="metric-subtext">Correct class linked</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Proxy Objects</div>
              <div className="metric-value" style={{ color: "var(--color-danger)" }}>{analysis.proxy_elements} ({analysis.proxy_pct.toFixed(1)}%)</div>
              <div className="metric-subtext">Lost structural meaning</div>
            </div>
          </div>

          {/* STEP Syntax validation */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "24px", marginBottom: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: "700" }}>🔎 STEP Syntax & Schema Integrity Check</h3>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Verifies that the uploaded file complies structurally with standard ISO 10303-21 parser specifications.</p>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <span className="status-badge status-pass">{analysis.step_verdict.pass} Pass</span>
                {analysis.step_verdict.warn > 0 && <span className="status-badge status-warn">{analysis.step_verdict.warn} Warn</span>}
                {analysis.step_verdict.fail > 0 && <span className="status-badge status-fail">{analysis.step_verdict.fail} Fail</span>}
              </div>
            </div>

            <button className="btn-secondary" style={{ fontSize: "12px", padding: "6px 12px", marginBottom: "12px" }} onClick={() => setShowStepChecks(!showStepChecks)}>
              {showStepChecks ? "Hide checklist ▲" : "View complete checklist ▼"}
            </button>

            {showStepChecks && (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", background: "rgba(0,0,0,0.2)", borderRadius: "8px", padding: "14px" }}>
                {analysis.step_verdict.checks.map((c, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <div>
                      <span style={{ fontWeight: "700" }}>{c.check}</span>
                      <div style={{ color: "var(--text-secondary)", fontSize: "11px", marginTop: "2px" }}>{c.detail}</div>
                    </div>
                    <span className={`status-badge ${c.status === "pass" ? "status-pass" : c.status === "fail" ? "status-fail" : "status-warn"}`}>
                      {c.status.toUpperCase()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 5-Level Analysis */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "24px", marginBottom: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "4px" }}>🔬 5-Level Data Loss Analysis</h3>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "16px" }}>Weighted structural evaluation representing total model data integrity.</p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "12px", marginBottom: "20px" }}>
              {[
                { lvl: "L1", title: "Semantic Loss", pct: analysis.type_loss_pct, count: analysis.type_loss_count, label: "Proxy elements", w: "30%" },
                { lvl: "L2", title: "Property Loss", pct: analysis.prop_loss_pct, count: analysis.prop_loss_count, label: "Missing Psets", w: "20%" },
                { lvl: "L3", title: "Quantity Loss", pct: analysis.qty_loss_pct, count: analysis.qty_loss_count, label: "No volume/area", w: "15%" },
                { lvl: "L4", title: "Relationship Loss", pct: analysis.rel_loss_pct, count: analysis.rel_loss_count, label: "No storey container", w: "25%" },
                { lvl: "L5", title: "Geometry Loss", pct: analysis.geo_loss_pct, count: analysis.geo_loss_count, label: "No 3D representation", w: "10%" }
              ].map(level => {
                const c = level.pct === 0 ? "var(--color-success)" : level.pct <= 15 ? "var(--color-warning)" : "var(--color-danger)";
                return (
                  <div key={level.lvl} style={{ background: "#161b22", border: `1px solid ${c}`, borderRadius: "8px", padding: "14px", textAlign: "center" }}>
                    <div style={{ fontSize: "9px", color: "var(--text-secondary)", letterSpacing: "0.5px" }}>{level.lvl} · Weight {level.w}</div>
                    <div style={{ fontSize: "12px", fontWeight: "700", margin: "4px 0" }}>{level.title}</div>
                    <div style={{ fontSize: "22px", fontWeight: "800", color: c }}>{level.pct.toFixed(1)}%</div>
                    <div style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "2px" }}>{level.count} {level.label}</div>
                  </div>
                );
              })}
            </div>

            {/* Model Integrity Score */}
            <div style={{ background: "#161b22", border: `1.5px solid ${analysis.quality_color}`, borderRadius: "10px", padding: "16px 24px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
              <div>
                <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "1px" }}>MODEL INTEGRITY SCORE</div>
                <div style={{ fontSize: "24px", fontWeight: "900", color: analysis.quality_color, marginTop: "4px" }}>
                  {analysis.data_integrity}/100 — {analysis.quality_grade}
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                  Score = 100 − Total Loss % (Weighted L1–L5 Loss percentages)
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Total Loss</div>
                <div style={{ fontSize: "20px", fontWeight: "800", color: analysis.quality_color }}>{analysis.data_loss_score}%</div>
              </div>
            </div>
          </div>

          {/* Automated conclusion */}
          <div style={{ 
            background: "rgba(255,255,255,0.02)", 
            border: "1px solid var(--border-color)", 
            borderRadius: "10px", 
            padding: "16px 20px", 
            marginBottom: "24px",
            borderLeft: `4px solid ${analysis.quality_color}` 
          }}>
            <h4 style={{ fontSize: "14px", fontWeight: "700", marginBottom: "6px" }}>🧠 Automated Conclusion</h4>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
              {analysis.proxy_pct <= 10 ? "The IFC model preserves semantic representation across all analyzed elements. No semantic degradation detected." :
               analysis.proxy_pct < 20 ? "The IFC model largely preserves semantic meaning, with minor semantic degradation observed in a small subset of elements." :
               analysis.proxy_pct < 50 ? "The IFC model exhibits mixed semantic representation. Several building components are represented as proxy elements." :
               "The IFC model shows significant semantic degradation. A large portion of elements are represented as generic proxy objects."}
            </p>
          </div>

          {/* Element Level Tracing (Proxy List) */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "24px", marginBottom: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "4px" }}>🔎 Element-Level Tracing (Proxies)</h3>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "14px" }}>Scanned list of elements whose physical type was mapped to a generic proxy container during export.</p>

            <div className="data-table-container" style={{ maxHeight: "300px", overflowY: "auto", margin: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Element Name</th>
                    <th>Global ID</th>
                    <th>IFC Class</th>
                    <th>Issue Details</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.proxy_list.map((item, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: "600" }}>{item.Name}</td>
                      <td style={{ fontFamily: "Space Mono", fontSize: "11px" }}>{item.GlobalId}</td>
                      <td><span className="status-badge status-fail">{item["IFC Type"]}</span></td>
                      <td style={{ color: "#ff6b6b" }}>{item.Issue}</td>
                    </tr>
                  ))}
                  {analysis.proxy_list.length === 0 && (
                    <tr>
                      <td colSpan="4" style={{ textAlign: "center", color: "var(--text-secondary)", padding: "20px" }}>
                        ✅ No proxy elements detected in this model!
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* IFC Relationships Table */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "24px", marginTop: "24px", marginBottom: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "4px" }}>🔗 IFC Relationships</h3>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "14px" }}>Relationship types and counts mapping topology and spatial association structures in the model.</p>

            <div className="data-table-container" style={{ maxHeight: "300px", overflowY: "auto", margin: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Relationship</th>
                    <th>Meaning</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {(analysis.relationship_summary || []).map((rel, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: "700" }}>{rel.Relationship}</td>
                      <td>{rel.Meaning}</td>
                      <td><span className="status-badge status-pass" style={{ fontFamily: "Space Mono" }}>{rel.Count}</span></td>
                    </tr>
                  ))}
                  {(analysis.relationship_summary || []).length === 0 && (
                    <tr>
                      <td colSpan="3" style={{ textAlign: "center", color: "var(--text-secondary)", padding: "20px" }}>
                        No relationship entities found in this IFC model.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {analysis.relationship_summary && analysis.relationship_summary.length > 0 && (
              <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "8px" }}>
                {analysis.relationship_summary.length} relationship types parsed in this model.
              </p>
            )}
          </div>

          {/* Download PDF & IFC options */}
          <div style={{ display: "flex", gap: "12px" }}>
            <button className="btn-primary" onClick={handleDownloadPDF}>📄 Generate PDF Report</button>
            <button className="btn-secondary" onClick={() => setActiveNav("Reports & Export")}>📊 Full Report Breakdown</button>
          </div>
        </div>
      )}
    </div>
  );
}
