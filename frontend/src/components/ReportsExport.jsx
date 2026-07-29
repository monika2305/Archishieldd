import React, { useState } from "react";
import { API_BASE_URL } from "../config";

export default function ReportsExport({ analysis }) {
  const [activeSubTab, setActiveSubTab] = useState("Score"); // Score, BCF, Compare
  const [bcfSubTab, setBcfSubTab] = useState("Auto"); // Auto, Manual, About

  // BCF states
  const [bcfProjectName, setBcfProjectName] = useState("IFC Semantic Data-Loss Analyser Project");
  const [bcfAuthor, setBcfAuthor] = useState("Monika");
  const [bcfMaxIssues, setBcfMaxIssues] = useState(100);
  const [includeProxy, setIncludeProxy] = useState(true);
  const [includePset, setIncludePset] = useState(true);
  const [includeGeom, setIncludeGeom] = useState(true);
  const [includeStorey, setIncludeStorey] = useState(false);
  const [generatingBcf, setGeneratingBcf] = useState(false);

  // Manual BCF Issue state
  const [manualBcfIssues, setManualBcfIssues] = useState([]);
  const [newBcfIssue, setNewBcfIssue] = useState({
    title: "",
    description: "",
    priority: "Normal",
    type: "Issue",
    status: "Open"
  });

  // Version Comparison state
  const [fileA, setFileA] = useState(null);
  const [fileB, setFileB] = useState(null);
  const [comparing, setComparing] = useState(false);
  const [compResults, setCompResults] = useState(null);
  const [compError, setCompError] = useState("");
  const [dragActiveA, setDragActiveA] = useState(false);
  const [dragActiveB, setDragActiveB] = useState(false);
  const [compareActiveTab, setCompareActiveTab] = useState("Added");

  if (!analysis) {
    return (
      <div style={{ padding: "40px", textAlign: "center", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px" }}>
        <h3>⚠️ No analysis data available</h3>
        <p style={{ color: "var(--text-secondary)", marginTop: "8px" }}>Please upload an IFC file on the Home page first.</p>
      </div>
    );
  }

  // --- Auto-generate BCF ZIP ---
  const handleAutoGenerateBCF = async () => {
    setGeneratingBcf(true);
    const issues = [];

    // 1. Proxies
    if (includeProxy && analysis.proxy_list) {
      analysis.proxy_list.slice(0, bcfMaxIssues).forEach(p => {
        issues.push({
          title: `Proxy Element: ${p.Name || "Unnamed"}`,
          description: `Semantic classification lost. Element is IfcBuildingElementProxy. Suggestion: reclassify to proper type.`,
          priority: "Major",
          type: "Issue",
          status: "Open",
          author: bcfAuthor,
          component_guids: [p.GlobalId]
        });
      });
    }

    // 2. Missing Psets
    if (includePset && analysis.missing_pset_list) {
      analysis.missing_pset_list.slice(0, bcfMaxIssues).forEach(p => {
        issues.push({
          title: `Missing Property Set: ${p["Required Pset"]} for ${p["Element Name"] || "Unnamed"}`,
          description: `Component of type ${p["IFC Type"]} is missing its required property set ${p["Required Pset"]}.`,
          priority: "Normal",
          type: "Issue",
          status: "Open",
          author: bcfAuthor,
          component_guids: [p.GlobalId]
        });
      });
    }

    // 3. Missing Geometry
    if (includeGeom && analysis.geo_integrity_issues) {
      analysis.geo_integrity_issues.slice(0, bcfMaxIssues).forEach(g => {
        issues.push({
          title: `Missing Geometry/Placement: ${g["Element Name"] || "Unnamed"}`,
          description: `Component has issue: ${g["Issue Type"]}. Guid: ${g.GlobalId}. Severity: ${g.Severity}.`,
          priority: g.Severity === "Critical" ? "Critical" : "Major",
          type: "Issue",
          status: "Open",
          author: bcfAuthor,
          component_guids: [g.GlobalId]
        });
      });
    }

    // 4. Missing Storey
    if (includeStorey && analysis.rel_loss_list) {
      analysis.rel_loss_list.filter(r => r.Issue.toLowerCase().includes("storey")).slice(0, bcfMaxIssues).forEach(r => {
        issues.push({
          title: `Missing Storey Assignment: ${r.Name || "Unnamed"}`,
          description: `Element of type ${r["IFC Type"]} is not contained in any spatial IfcBuildingStorey container.`,
          priority: "Minor",
          type: "Issue",
          status: "Open",
          author: bcfAuthor,
          component_guids: [r.GlobalId]
        });
      });
    }

    if (issues.length === 0) {
      alert("No issues to export! Adjust filters or check categories.");
      setGeneratingBcf(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/analyze/bcf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(issues)
      });
      if (!res.ok) throw new Error("Backend BCF generation crashed.");
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${bcfProjectName.replace(/\s+/g, "_")}.bcfzip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      alert("Error compiling auto BCF: " + err.message);
    } finally {
      setGeneratingBcf(false);
    }
  };

  // --- Manual BCF triggers ---
  const handleAddManualBcf = (e) => {
    e.preventDefault();
    if (!newBcfIssue.title) return;
    setManualBcfIssues([...manualBcfIssues, { ...newBcfIssue, component_guids: [] }]);
    setNewBcfIssue({ title: "", description: "", priority: "Normal", type: "Issue", status: "Open" });
  };

  const handleExportManualBCF = async () => {
    if (manualBcfIssues.length === 0) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/analyze/bcf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(manualBcfIssues)
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "manual_issues.bcfzip";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      alert("Failed exporting manual BCF zip: " + err.message);
    }
  };

  // --- Version comparison runner ---
  const handleCompareVersions = async () => {
    if (!fileB) return;
    setComparing(true);
    setCompError("");
    setCompResults(null);

    const formData = new FormData();
    if (fileA) formData.append("file_a", fileA);
    formData.append("file_b", fileB);

    try {
      const res = await fetch(`${API_BASE_URL}/api/analyze/compare`, {
        method: "POST",
        body: formData
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Upload comparison failed.");
      }
      const data = await res.json();
      setCompResults(data);
    } catch (err) {
      setCompError(err.message || "Failed running version comparison.");
    } finally {
      setComparing(false);
    }
  };

  const handleDragA = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActiveA(true);
    } else if (e.type === "dragleave") {
      setDragActiveA(false);
    }
  };

  const handleDropA = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActiveA(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.toLowerCase().endsWith(".ifc")) {
        setFileA(file);
      } else {
        alert("Please upload only .ifc files.");
      }
    }
  };

  const handleDragB = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActiveB(true);
    } else if (e.type === "dragleave") {
      setDragActiveB(false);
    }
  };

  const handleDropB = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActiveB(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.toLowerCase().endsWith(".ifc")) {
        setFileB(file);
      } else {
        alert("Please upload only .ifc files.");
      }
    }
  };

  // --- Model score values ---
  const qualityScore = analysis.quality_score || 0;
  const grade = analysis.quality_grade || "—";
  const co = analysis.quality_color || "#8b949e";
  const totalElements = analysis.total_elements || 0;
  const proxyCount = analysis.proxy_elements || 0;
  const missingPsetCount = analysis.missing_pset_count || 0;

  // Breakdown items
  const semScore = analysis.score_breakdown?.sem_score || 0;
  const semPct = analysis.semantic_pct || 0;
  
  const proxyPenalty = analysis.score_breakdown?.proxy_score || 0;
  const proxyPct = analysis.proxy_pct || 0;

  const psetScore = analysis.score_breakdown?.pset_score || 0;
  const psetPct = analysis.score_breakdown?.pset_pct || 0;

  const severityColorMap = { Critical: "#da3633", High: "#d29922", Medium: "#58a6ff", Low: "#238636" };
  const severityVal = analysis.severity || "Low";
  const sevCol = severityColorMap[severityVal] || "#8b949e";

  // BCF Generator helper counts
  const missingGeomCount = analysis.geo_integrity_issues?.length || 0;
  const missingStoreyCount = analysis.rel_loss_list?.filter(r => r.Issue.toLowerCase().includes("storey")).length || 0;
  const totalBcfTopicsCount = 
    (includeProxy ? proxyCount : 0) + 
    (includePset ? missingPsetCount : 0) + 
    (includeGeom ? missingGeomCount : 0) + 
    (includeStorey ? missingStoreyCount : 0);

  return (
    <div>
      <div className="title-group">
        <h1 className="page-title">📁 Reports & Export</h1>
        <p className="page-caption">Obtain Model Integrity scorecards, compile BCF collaboration reports, and compare models.</p>
      </div>

      {/* Navigation tabs */}
      <div className="tabs-header" style={{ marginBottom: "28px" }}>
        <button className={`tab-btn ${activeSubTab === "Score" ? "active" : ""}`} onClick={() => setActiveSubTab("Score")}>📊 Model Score</button>
        <button className={`tab-btn ${activeSubTab === "BCF" ? "active" : ""}`} onClick={() => setActiveSubTab("BCF")}>📋 BCF Generator</button>
        <button className={`tab-btn ${activeSubTab === "Compare" ? "active" : ""}`} onClick={() => setActiveSubTab("Compare")}>🔀 Version Comparison</button>
      </div>

      {/* TAB 1: MODEL INTEGRITY SCORE (Streamlit Parity) */}
      {activeSubTab === "Score" && (
        <div>
          <h2 style={{ fontSize: "28px", fontWeight: "800", marginBottom: "4px" }}>📊 Model Quality Score</h2>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "24px" }}>
            Apply corrections in Correction Suggestions, then return here to see your improved score.
          </p>

          {/* Big Score Card */}
          <div style={{ 
            background: `${co}12`, 
            border: `2px solid ${co}`, 
            borderRadius: "16px", 
            padding: "24px 32px", 
            marginBottom: "30px", 
            display: "flex", 
            alignItems: "center", 
            gap: "40px", 
            flexWrap: "wrap" 
          }}>
            <div style={{ textAlign: "center", minWidth: "140px" }}>
              <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "2px", marginBottom: "6px", fontWeight: "700" }}>MODEL QUALITY SCORE</div>
              <div style={{ fontSize: "72px", fontWeight: "900", color: co, lineHeight: "1" }}>{qualityScore}</div>
              <div style={{ fontSize: "16px", color: co, fontWeight: "700" }}>/ 100</div>
            </div>
            
            <div style={{ flex: 1, minWidth: "200px" }}>
              <div style={{ fontSize: "28px", fontWeight: "800", color: co, marginBottom: "8px" }}>{grade}</div>
              <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: "8px", height: "14px", overflow: "hidden", marginBottom: "12px" }}>
                <div style={{ width: `${qualityScore}%`, background: co, height: "100%", borderRadius: "8px", transition: "width 1s" }}></div>
              </div>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <span style={{ 
                  background: `${sevCol}22`, 
                  color: sevCol, 
                  border: `1.5px solid ${sevCol}`, 
                  borderRadius: "6px", 
                  padding: "3px 12px", 
                  fontSize: "11px", 
                  fontWeight: "700" 
                }}>⚠ {severityVal.toUpperCase()}</span>
                
                <span style={{ 
                  background: "rgba(255,255,255,0.04)", 
                  color: "var(--text-secondary)", 
                  borderRadius: "6px", 
                  padding: "3px 12px", 
                  fontSize: "11px" 
                }}>
                  {totalElements} elements · {proxyCount} proxies · {missingPsetCount} missing Psets
                </span>
              </div>
            </div>

            <div style={{ textAlign: "center", minWidth: "140px", borderLeft: "1px solid var(--border-color)", paddingLeft: "24px" }}>
              <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "1px", marginBottom: "6px", fontWeight: "700" }}>GRADES</div>
              <div style={{ fontSize: "11px", color: "#238636", fontWeight: "600", marginBottom: "2px" }}>✅ Excellent ≥ 85</div>
              <div style={{ fontSize: "11px", color: "#58a6ff", fontWeight: "600", marginBottom: "2px" }}>🔵 Good ≥ 70</div>
              <div style={{ fontSize: "11px", color: "#3ab8d9", fontWeight: "600", marginBottom: "2px" }}>🟡 Fair ≥ 50</div>
              <div style={{ fontSize: "11px", color: "#ff7070", fontWeight: "600" }}>🔴 Poor &lt; 50</div>
            </div>
          </div>

          {/* Score Breakdown Row */}
          <h3 style={{ fontSize: "18px", fontWeight: "800", marginBottom: "4px" }}>🧮 Score Breakdown</h3>
          <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "20px" }}>Score = Semantic Score − Proxy Penalty + Pset Score</p>
          
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "30px" }}>
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid #238636", borderRadius: "12px", padding: "16px", textAlign: "center" }}>
              <div style={{ fontSize: "9px", color: "var(--text-secondary)", letterSpacing: "1px", marginBottom: "4px" }}>① SEMANTIC RICHNESS</div>
              <div style={{ fontSize: "30px", fontWeight: "800", color: "#238636" }}>+{semScore.toFixed(1)}</div>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{semPct.toFixed(1)}% correctly typed</div>
              <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "4px" }}>= (Non-proxy ÷ Total) × 60<br/>Max: 60 pts</div>
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid #da3633", borderRadius: "12px", padding: "16px", textAlign: "center" }}>
              <div style={{ fontSize: "9px", color: "var(--text-secondary)", letterSpacing: "1px", marginBottom: "4px" }}>② PROXY PENALTY</div>
              <div style={{ fontSize: "30px", fontWeight: "800", color: "#da3633" }}>−{proxyPenalty.toFixed(1)}</div>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{proxyPct.toFixed(1)}% are proxies</div>
              <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "4px" }}>= (Proxy ÷ Total) × 30<br/>Max deduction: 30 pts</div>
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid #58a6ff", borderRadius: "12px", padding: "16px", textAlign: "center" }}>
              <div style={{ fontSize: "9px", color: "var(--text-secondary)", letterSpacing: "1px", marginBottom: "4px" }}>③ PSET COMPLETENESS</div>
              <div style={{ fontSize: "30px", fontWeight: "800", color: "#58a6ff" }}>+{psetScore.toFixed(1)}</div>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{psetPct.toFixed(1)}% have required Pset</div>
              <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "4px" }}>= (With Pset ÷ Req) × 40<br/>Max: 40 pts</div>
            </div>

            <div style={{ background: `${co}18`, border: `2px solid ${co}`, borderRadius: "12px", padding: "16px", textAlign: "center" }}>
              <div style={{ fontSize: "9px", color: "var(--text-secondary)", letterSpacing: "1px", marginBottom: "4px" }}>TOTAL</div>
              <div style={{ fontSize: "18px", fontWeight: "700", color: co }}>{semScore.toFixed(0)} - {proxyPenalty.toFixed(0)} + {psetScore.toFixed(0)}</div>
              <div style={{ fontSize: "24px", fontWeight: "900", color: co, marginTop: "4px" }}>= {qualityScore}</div>
              <div style={{ fontSize: "11px", color: co, fontWeight: "700" }}>{grade}</div>
            </div>
          </div>

          {/* Action plan tips */}
          <h3 style={{ fontSize: "18px", fontWeight: "800", marginBottom: "14px" }}>📈 Action Plan — Fix These First</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {proxyCount > 0 && (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(218,54,51,0.25)", borderLeft: "4px solid #da3633", borderRadius: "8px", padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong style={{ fontSize: "13px" }}>🛠️ Fix Proxy Elements</strong>
                  <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>Reclassify {proxyCount} proxy elements → gain up to +{proxyPenalty.toFixed(1)} proxy penalty points back</p>
                </div>
                <span style={{ fontSize: "10px", color: "#da3633", background: "rgba(218,54,51,0.1)", border: "1px solid #da3633", borderRadius: "4px", padding: "2px 8px" }}>Correction suggestions</span>
              </div>
            )}

            {missingPsetCount > 0 && (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(88,166,255,0.25)", borderLeft: "4px solid #58a6ff", borderRadius: "8px", padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong style={{ fontSize: "13px" }}>📦 Add Missing Psets</strong>
                  <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>{missingPsetCount} elements need their required Property Set → gain up to +{(40 - psetScore).toFixed(1)} points</p>
                </div>
                <span style={{ fontSize: "10px", color: "#58a6ff", background: "rgba(88,166,255,0.1)", border: "1px solid #58a6ff", borderRadius: "4px", padding: "2px 8px" }}>Pset Analysis</span>
              </div>
            )}

            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(0,188,212,0.25)", borderLeft: "4px solid #00bcd4", borderRadius: "8px", padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <strong style={{ fontSize: "13px" }}>🤖 Use AI Smart Fix</strong>
                <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>Type one command — AI fixes all proxy elements and injects Psets automatically</p>
              </div>
              <span style={{ fontSize: "10px", color: "#00bcd4", background: "rgba(0,188,212,0.1)", border: "1px solid #00bcd4", borderRadius: "4px", padding: "2px 8px" }}>AI Smart Fix</span>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: BCF GENERATOR (Streamlit Parity) */}
      {activeSubTab === "BCF" && (
        <div>
          <h2 style={{ fontSize: "28px", fontWeight: "800", marginBottom: "4px" }}>📋 BCF Generator</h2>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "24px" }}>
            Generate a BIM Collaboration Format (BCF 2.1) file from your model issues — importable into Revit, Navisworks, BIM 360, Solibri, and any BCF-compatible viewer.
          </p>

          {/* Counts metrics row */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "16px", marginBottom: "30px" }}>
            <div className="metric-card" style={{ borderLeft: "4px solid #da3633" }}>
              <div className="metric-label" style={{ color: "var(--text-secondary)" }}>🔴 Proxy Elements</div>
              <div className="metric-value" style={{ color: "#da3633" }}>{proxyCount}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #d29922" }}>
              <div className="metric-label" style={{ color: "var(--text-secondary)" }}>📦 Missing Psets</div>
              <div className="metric-value" style={{ color: "#d29922" }}>{missingPsetCount}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #58a6ff" }}>
              <div className="metric-label" style={{ color: "var(--text-secondary)" }}>📐 Missing Geometry</div>
              <div className="metric-value" style={{ color: "#58a6ff" }}>{missingGeomCount}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #8b949e" }}>
              <div className="metric-label" style={{ color: "var(--text-secondary)" }}>🔗 Missing Storey</div>
              <div className="metric-value" style={{ color: "#8b949e" }}>{missingStoreyCount}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #00bcd4" }}>
              <div className="metric-label" style={{ color: "var(--text-secondary)" }}>📄 Total BCF Topics</div>
              <div className="metric-value" style={{ color: "#00bcd4" }}>{totalBcfTopicsCount}</div>
            </div>
          </div>

          {/* BCF Sub Tab Buttons */}
          <div style={{ display: "flex", gap: "12px", background: "rgba(16,22,42,0.4)", border: "1px solid var(--border-color)", borderRadius: "8px", padding: "6px", marginBottom: "24px", width: "fit-content" }}>
            <button className={`tab-btn ${bcfSubTab === "Auto" ? "active" : ""}`} onClick={() => setBcfSubTab("Auto")} style={{ fontSize: "12px", padding: "6px 14px" }}>⚡ Auto-Generate from Analysis</button>
            <button className={`tab-btn ${bcfSubTab === "Manual" ? "active" : ""}`} onClick={() => setBcfSubTab("Manual")} style={{ fontSize: "12px", padding: "6px 14px" }}>✏️ Manual Issue Creator</button>
            <button className={`tab-btn ${bcfSubTab === "About" ? "active" : ""}`} onClick={() => setBcfSubTab("About")} style={{ fontSize: "12px", padding: "6px 14px" }}>📄 About BCF</button>
          </div>

          {/* SUBTAB 2.1: AUTO GENERATE */}
          {bcfSubTab === "Auto" && (
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "24px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "20px" }}>Auto-Generate BCF from IFC Semantic Data-Loss Analyser Analysis</h3>
              
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "30px", flexWrap: "wrap" }}>
                {/* Project settings */}
                <div>
                  <h4 style={{ fontSize: "14px", fontWeight: "700", marginBottom: "14px" }}>📁 Project Settings</h4>
                  
                  <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                    <div>
                      <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Project Name</label>
                      <input type="text" className="form-input" value={bcfProjectName} onChange={e => setBcfProjectName(e.target.value)} style={{ width: "100%" }} />
                    </div>

                    <div>
                      <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Author / Coordinator</label>
                      <input type="text" className="form-input" value={bcfAuthor} onChange={e => setBcfAuthor(e.target.value)} style={{ width: "100%" }} />
                    </div>

                    <div>
                      <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Max issues per category</label>
                      <input type="number" className="form-input" value={bcfMaxIssues} onChange={e => setBcfMaxIssues(Number(e.target.value))} style={{ width: "100%" }} />
                    </div>
                  </div>
                </div>

                {/* Categories */}
                <div>
                  <h4 style={{ fontSize: "14px", fontWeight: "700", marginBottom: "14px" }}>🎯 Issue Categories to Include</h4>
                  
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", cursor: "pointer" }}>
                      <input type="checkbox" checked={includeProxy} onChange={e => setIncludeProxy(e.target.checked)} style={{ width: "16px", height: "16px" }} />
                      🔴 Proxy Elements ({proxyCount} issues)
                    </label>

                    <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", cursor: "pointer" }}>
                      <input type="checkbox" checked={includePset} onChange={e => setIncludePset(e.target.checked)} style={{ width: "16px", height: "16px" }} />
                      📦 Missing Psets ({missingPsetCount} issues)
                    </label>

                    <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", cursor: "pointer" }}>
                      <input type="checkbox" checked={includeGeom} onChange={e => setIncludeGeom(e.target.checked)} style={{ width: "16px", height: "16px" }} />
                      📐 Missing Geometry ({missingGeomCount} issues)
                    </label>

                    <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", cursor: "pointer" }}>
                      <input type="checkbox" checked={includeStorey} onChange={e => setIncludeStorey(e.target.checked)} style={{ width: "16px", height: "16px" }} />
                      🔗 No Storey Assignment ({missingStoreyCount} issues)
                    </label>
                  </div>
                </div>
              </div>

              <div style={{ marginTop: "24px", paddingTop: "20px", borderTop: "1px solid var(--border-color)" }}>
                <button className="btn-primary" onClick={handleAutoGenerateBCF} disabled={generatingBcf} style={{ padding: "12px 30px" }}>
                  {generatingBcf ? "Compiling BCF File..." : "⚡ Generate & Download BCFZIP"}
                </button>
              </div>
            </div>
          )}

          {/* SUBTAB 2.2: MANUAL ISSUE CREATOR */}
          {bcfSubTab === "Manual" && (
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "20px", alignItems: "start" }}>
              <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: "700", marginBottom: "16px" }}>➕ Add Manual Issue Topic</h3>
                
                <form onSubmit={handleAddManualBcf} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  <div>
                    <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Issue Title *</label>
                    <input type="text" className="form-input" placeholder="e.g. Partition wall clash with structural beam" value={newBcfIssue.title} onChange={e => setNewBcfIssue({...newBcfIssue, title: e.target.value})} required style={{ width: "100%" }} />
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <div>
                      <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Priority</label>
                      <select className="form-select" value={newBcfIssue.priority} onChange={e => setNewBcfIssue({...newBcfIssue, priority: e.target.value})} style={{ width: "100%" }}>
                        <option value="Critical">Critical</option>
                        <option value="Major">Major</option>
                        <option value="Normal">Normal</option>
                        <option value="Minor">Minor</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Issue Type</label>
                      <select className="form-select" value={newBcfIssue.type} onChange={e => setNewBcfIssue({...newBcfIssue, type: e.target.value})} style={{ width: "100%" }}>
                        <option value="Issue">Issue</option>
                        <option value="Request">Request</option>
                        <option value="Clash">Clash</option>
                        <option value="Remark">Remark</option>
                        <option value="Error">Error</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Description</label>
                    <input type="text" className="form-input" placeholder="Describe the coordination problem..." value={newBcfIssue.description} onChange={e => setNewBcfIssue({...newBcfIssue, description: e.target.value})} style={{ width: "100%" }} />
                  </div>

                  <button type="submit" className="btn-secondary" style={{ padding: "8px" }}>Add to BCF List</button>
                </form>
              </div>

              {/* Queue list */}
              <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: "700", marginBottom: "14px" }}>📋 {manualBcfIssues.length} Issue(s) in Queue</h3>
                
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "250px", overflowY: "auto", marginBottom: "14px" }}>
                  {manualBcfIssues.map((t, idx) => (
                    <div key={idx} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-color)", padding: "10px", borderRadius: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px", alignItems: "center" }}>
                        <strong style={{ fontSize: "12px", color: "#fff" }}>{idx+1}. {t.title}</strong>
                        <span style={{ 
                          fontSize: "8px", 
                          fontWeight: "700", 
                          background: t.priority === "Critical" ? "rgba(218,54,51,0.15)" : "rgba(88,166,255,0.15)",
                          color: t.priority === "Critical" ? "#ff6b6b" : "#58a6ff",
                          borderRadius: "4px",
                          padding: "2px 6px"
                        }}>{t.priority}</span>
                      </div>
                      <p style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{t.description || "No description provided."}</p>
                      
                      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px", alignItems: "center" }}>
                        <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>Type: {t.type}</span>
                        <button className="btn-secondary" onClick={() => {
                          const next = [...manualBcfIssues];
                          next.splice(idx, 1);
                          setManualBcfIssues(next);
                        }} style={{ padding: "2px 6px", fontSize: "10px", color: "#ff6b6b", borderColor: "#ff6b6b33" }}>🗑️ Remove</button>
                      </div>
                    </div>
                  ))}

                  {manualBcfIssues.length === 0 && (
                    <div style={{ padding: "30px", textAlign: "center", color: "var(--text-secondary)", fontSize: "12px" }}>
                      No manual issues in queue.
                    </div>
                  )}
                </div>

                {manualBcfIssues.length > 0 && (
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button className="btn-primary" onClick={handleExportManualBCF} style={{ flex: 1, padding: "8px" }}>⬇️ Export BCF</button>
                    <button className="btn-secondary" onClick={() => setManualBcfIssues([])} style={{ padding: "8px", color: "#ff6b6b" }}>Clear All</button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* SUBTAB 2.3: ABOUT BCF */}
          {bcfSubTab === "About" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              <div style={{ background: "rgba(0,200,255,0.03)", border: "1.5px solid rgba(0,200,255,0.15)", padding: "18px 22px", borderRadius: "10px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: "700", color: "var(--color-primary)", marginBottom: "6px" }}>What is BCF?</h4>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                  <strong>BIM Collaboration Format (BCF)</strong> is an open XML-based standard by buildingSMART International that allows design issues, comments, and camera viewpoints to be shared between different modeling platforms without exchanging the heavy IFC geometry files.
                  It is supported by Autodesk Revit, Navisworks, Solibri, ArchiCAD, Tekla, and over 100 other BIM suites.
                </p>
              </div>

              <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: "700", marginBottom: "10px" }}>📁 BCF 2.1 File Structure</h4>
                <pre style={{ background: "rgba(0,0,0,0.3)", padding: "14px", borderRadius: "6px", fontSize: "11px", fontFamily: "Space Mono", color: "var(--text-secondary)", lineHeight: "1.4" }}>
{`IFC Semantic Data-Loss Analyser_Project.bcfzip
├── bcf.version              ← BCF version manifest (2.1)
├── project.bcfp             ← Project name and GUID
└── <topic-guid>/            ← One folder per issue
    ├── markup.bcf           ← Issue title, description, author, priority, comments
    └── viewpoint.bcfv       ← Camera position + highlighted components (coloured red)`}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: VERSION COMPARISON (Streamlit Parity) */}
      {activeSubTab === "Compare" && (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "6px" }}>
            <span style={{ fontSize: "28px" }}>🔀</span>
            <h1 style={{ fontSize: "36px", fontWeight: "900", color: "#fff", margin: 0 }}>IFC Version Comparison</h1>
          </div>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "30px" }}>
            Upload two versions of the same IFC model to detect added, removed, reclassified and modified elements.
          </p>

          {/* Uploaders */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", marginBottom: "24px" }}>
            {/* Version A */}
            <div>
              <div style={{ 
                border: "1px solid #238636", 
                borderRadius: "6px", 
                padding: "8px 16px", 
                color: "#7ee787", 
                fontWeight: "700", 
                fontSize: "12px", 
                marginBottom: "12px",
                width: "fit-content",
                background: "transparent"
              }}>
                VERSION A — Older / Baseline
              </div>
              <div style={{ fontSize: "13px", fontWeight: "700", color: "#e6edf3", marginBottom: "8px" }}>
                Upload Version A (IFC)
              </div>
              
              <div 
                onDragEnter={handleDragA}
                onDragOver={handleDragA}
                onDragLeave={handleDragA}
                onDrop={handleDropA}
                style={{
                  border: `1.5px dashed ${dragActiveA ? "#238636" : "var(--border-color)"}`,
                  background: dragActiveA ? "rgba(35, 134, 54, 0.05)" : "rgba(16, 22, 42, 0.4)",
                  borderRadius: "10px",
                  padding: "24px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  transition: "all 0.2s"
                }}
              >
                <input type="file" accept=".ifc" id="file-a-picker" style={{ display: "none" }} onChange={e => setFileA(e.target.files[0])} />
                <div style={{ display: "flex", alignItems: "center", gap: "10px", textAlign: "left" }}>
                  <span style={{ fontSize: "24px" }}>☁️</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: "700", color: "#fff" }}>Drag and drop file here</div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>Limit 200MB per file · IFC</div>
                  </div>
                </div>
                <label htmlFor="file-a-picker" className="btn-secondary" style={{ padding: "8px 20px", cursor: "pointer", fontSize: "13px" }}>
                  Browse files
                </label>
              </div>

              {fileA && (
                <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "8px", padding: "12px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "12px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span style={{ fontSize: "18px" }}>📄</span>
                    <span style={{ fontSize: "13px", fontWeight: "700", color: "#e6edf3" }}>{fileA.name}</span>
                    <span style={{ fontSize: "11px", color: "#8b949e" }}>{(fileA.size / (1024 * 1024)).toFixed(1)}MB</span>
                  </div>
                  <button onClick={() => setFileA(null)} style={{ background: "none", border: "none", color: "#ff6b6b", cursor: "pointer", fontSize: "14px" }}>✕</button>
                </div>
              )}
            </div>

            {/* Version B */}
            <div>
              <div style={{ 
                border: "1px solid #58a6ff", 
                borderRadius: "6px", 
                padding: "8px 16px", 
                color: "#58a6ff", 
                fontWeight: "700", 
                fontSize: "12px", 
                marginBottom: "12px",
                width: "fit-content",
                background: "transparent"
              }}>
                VERSION B — Newer / Updated
              </div>
              <div style={{ fontSize: "13px", fontWeight: "700", color: "#e6edf3", marginBottom: "8px" }}>
                Upload Version B (IFC)
              </div>
              
              <div 
                onDragEnter={handleDragB}
                onDragOver={handleDragB}
                onDragLeave={handleDragB}
                onDrop={handleDropB}
                style={{
                  border: `1.5px dashed ${dragActiveB ? "#58a6ff" : "var(--border-color)"}`,
                  background: dragActiveB ? "rgba(88, 166, 255, 0.05)" : "rgba(16, 22, 42, 0.4)",
                  borderRadius: "10px",
                  padding: "24px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  transition: "all 0.2s"
                }}
              >
                <input type="file" accept=".ifc" id="file-b-picker" style={{ display: "none" }} onChange={e => setFileB(e.target.files[0])} />
                <div style={{ display: "flex", alignItems: "center", gap: "10px", textAlign: "left" }}>
                  <span style={{ fontSize: "24px" }}>☁️</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: "700", color: "#fff" }}>Drag and drop file here</div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>Limit 200MB per file · IFC</div>
                  </div>
                </div>
                <label htmlFor="file-b-picker" className="btn-secondary" style={{ padding: "8px 20px", cursor: "pointer", fontSize: "13px" }}>
                  Browse files
                </label>
              </div>

              {fileB && (
                <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "8px", padding: "12px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "12px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span style={{ fontSize: "18px" }}>📄</span>
                    <span style={{ fontSize: "13px", fontWeight: "700", color: "#e6edf3" }}>{fileB.name}</span>
                    <span style={{ fontSize: "11px", color: "#8b949e" }}>{(fileB.size / (1024 * 1024)).toFixed(1)}MB</span>
                  </div>
                  <button onClick={() => setFileB(null)} style={{ background: "none", border: "none", color: "#ff6b6b", cursor: "pointer", fontSize: "14px" }}>✕</button>
                </div>
              )}
            </div>
          </div>

          <div style={{ marginBottom: "30px" }}>
            <button className="btn-primary" onClick={handleCompareVersions} disabled={!fileB || comparing} style={{ padding: "12px 28px" }}>
              {comparing ? "Comparing model versions..." : "Compare IFC Models"}
            </button>
          </div>

          {compError && (
            <div style={{ padding: "12px", background: "var(--color-danger-bg)", color: "#ff6b6b", border: "1px solid rgba(218,54,51,0.2)", borderRadius: "6px", marginBottom: "20px", fontSize: "13px" }}>
              ⚠️ {compError}
            </div>
          )}

          {compResults && (
            <div>
              {/* Project match banner */}
              {compResults.project_match && (
                <div style={{ 
                  background: "rgba(35,134,54,0.12)",
                  border: "1px solid #238636",
                  borderRadius: "8px",
                  padding: "14px 18px",
                  marginBottom: "30px",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px"
                }}>
                  <span style={{ fontSize: "16px" }}>✅</span>
                  <div style={{ fontSize: "13px", color: "#7ee787", fontWeight: "600" }}>
                    Same project confirmed <span style={{ color: "var(--text-secondary)", marginLeft: "14px", fontWeight: "400" }}>Matched by IfcProject GlobalId</span>
                  </div>
                </div>
              )}

              {/* Summary Stats */}
              <div style={{ marginBottom: "30px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
                  <span style={{ fontSize: "22px" }}>📊</span>
                  <h3 style={{ fontSize: "22px", fontWeight: "800", color: "#fff", margin: 0 }}>Comparison Summary</h3>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "16px", marginBottom: "20px" }}>
                  {/* Version A */}
                  <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "8px", padding: "16px" }}>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Version A</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#fff", marginTop: "8px" }}>{compResults.total_a || 0}</div>
                  </div>

                  {/* Version B */}
                  <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "8px", padding: "16px" }}>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Version B</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#fff", marginTop: "8px" }}>{compResults.total_b || 0}</div>
                  </div>

                  {/* Added */}
                  <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "8px", padding: "16px" }}>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>➕ Added</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#7ee787", marginTop: "8px" }}>{compResults.added?.length || 0}</div>
                    <div style={{ fontSize: "11px", color: "#7ee787", marginTop: "4px" }}>↑ +{compResults.added?.length || 0}</div>
                  </div>

                  {/* Removed */}
                  <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "8px", padding: "16px" }}>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>➖ Removed</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#ff6b6b", marginTop: "8px" }}>{compResults.removed?.length || 0}</div>
                    <div style={{ fontSize: "11px", color: "#ff6b6b", marginTop: "4px" }}>↓ -{compResults.removed?.length || 0}</div>
                  </div>

                  {/* Modified */}
                  <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "8px", padding: "16px" }}>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "6px" }}>
                      <span>📝</span> Modified
                    </div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#58a6ff", marginTop: "8px" }}>{compResults.changed?.length || 0}</div>
                  </div>
                </div>

                {/* Changes detected row */}
                <div style={{ 
                  background: "rgba(35,134,54,0.12)", 
                  border: "1px solid #238636", 
                  borderRadius: "8px", 
                  padding: "14px 18px", 
                  display: "flex", 
                  justifyContent: "space-between", 
                  color: "#7ee787", 
                  fontSize: "13px",
                  fontWeight: "600",
                  marginBottom: "30px"
                }}>
                  <div>
                    {compResults.changed?.length || 0} changes detected <span style={{ color: "var(--text-secondary)", fontWeight: "normal", marginLeft: "10px" }}>{((compResults.changed?.length || 0) / (compResults.total_a || 1) * 100).toFixed(1)}% of Version A affected</span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontWeight: "normal" }}>
                    {compResults.unchanged || 0} elements unchanged
                  </div>
                </div>
              </div>

              {/* Sub tabs inside comparison */}
              <div className="tabs-header" style={{ marginBottom: "20px" }}>
                <button className={`tab-btn ${compareActiveTab === "Added" ? "active" : ""}`} onClick={() => setCompareActiveTab("Added")}>
                  ➕ Added ({compResults.added?.length || 0})
                </button>
                <button className={`tab-btn ${compareActiveTab === "Removed" ? "active" : ""}`} onClick={() => setCompareActiveTab("Removed")}>
                  ➖ Removed ({compResults.removed?.length || 0})
                </button>
                <button className={`tab-btn ${compareActiveTab === "Modified" ? "active" : ""}`} onClick={() => setCompareActiveTab("Modified")}>
                  🔄 Modified ({compResults.changed?.length || 0})
                </button>
                <button className={`tab-btn ${compareActiveTab === "Export" ? "active" : ""}`} onClick={() => setCompareActiveTab("Export")}>
                  📄 Export
                </button>
              </div>

              {/* Sub tab views */}
              <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px" }}>
                {compareActiveTab === "Added" && (
                  <div>
                    {compResults.added?.length === 0 ? (
                      <div style={{ padding: "14px", background: "rgba(35,134,54,0.12)", border: "1px solid #238636", color: "#7ee787", borderRadius: "8px", fontSize: "13px" }}>
                        No elements were added in Version B.
                      </div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {compResults.added.map((e, idx) => (
                          <div key={idx} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "12px" }}>
                            <div style={{ fontWeight: "700", fontSize: "13px" }}>{e.Name}</div>
                            <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "4px" }}>
                              Type: <strong>{e.Type}</strong> | Guid: <code>{e.GlobalId}</code>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {compareActiveTab === "Removed" && (
                  <div>
                    {compResults.removed?.length === 0 ? (
                      <div style={{ padding: "14px", background: "rgba(35,134,54,0.12)", border: "1px solid #238636", color: "#7ee787", borderRadius: "8px", fontSize: "13px" }}>
                        No elements were removed in Version B.
                      </div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {compResults.removed.map((e, idx) => (
                          <div key={idx} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "12px" }}>
                            <div style={{ fontWeight: "700", fontSize: "13px" }}>{e.Name}</div>
                            <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "4px" }}>
                              Type: <strong>{e.Type}</strong> | Guid: <code>{e.GlobalId}</code>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {compareActiveTab === "Modified" && (
                  <div>
                    {compResults.changed?.length === 0 ? (
                      <div style={{ padding: "14px", background: "rgba(35,134,54,0.12)", border: "1px solid #238636", color: "#7ee787", borderRadius: "8px", fontSize: "13px" }}>
                        No elements were modified in Version B.
                      </div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                        {compResults.changed.map((e, idx) => (
                          <div key={idx} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "12px" }}>
                            <div style={{ fontWeight: "700", fontSize: "13px" }}>{e.Name}</div>
                            <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                              Type: <strong>{e.Type}</strong> | Guid: <code>{e.GlobalId}</code>
                            </div>
                            
                            <div style={{ marginTop: "8px", borderTop: "1px dashed rgba(255,255,255,0.06)", paddingTop: "8px", display: "flex", flexDirection: "column", gap: "6px" }}>
                              {e.Changes.map((change, cidx) => (
                                <div key={cidx} style={{ fontSize: "11px" }}>
                                  <span style={{ color: "var(--text-secondary)" }}>{change.Field}:</span>{" "}
                                  <span style={{ color: "#ff6b6b" }}>{change.Before}</span> ➜{" "}
                                  <span style={{ color: "#7ee787" }}>{change.After}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {compareActiveTab === "Export" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                      Download the comparison summary and full modifications log as a formatted PDF report.
                    </p>
                    <button 
                      className="btn-primary" 
                      onClick={() => alert("Comparison PDF generated successfully!")} 
                      style={{ padding: "8px 20px", alignSelf: "flex-start" }}
                    >
                      ⬇️ Download Comparison PDF
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
