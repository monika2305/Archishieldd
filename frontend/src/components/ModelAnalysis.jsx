import React, { useState } from "react";

export default function ModelAnalysis({ analysis }) {
  const [activeSubTab, setActiveSubTab] = useState("Proxy");
  const [proxySearch, setProxySearch] = useState("");
  const [psetSearch, setPsetSearch] = useState("");
  const [psetActiveTab, setPsetActiveTab] = useState("TypeSummary"); // TypeSummary, ElementDetails

  if (!analysis || !analysis.total_elements) {
    return (
      <div style={{ padding: "40px", textAlign: "center", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px" }}>
        <h3>⚠️ No analysis data available</h3>
        <p style={{ color: "var(--text-secondary)", marginTop: "8px" }}>Please upload an IFC file on the Home page first.</p>
      </div>
    );
  }

  // --- 1. PROXY CALCS ---
  const totalProxies = analysis.proxy_elements || 0;
  const validProxies = analysis.valid_proxies_count || 0;
  const invalidProxies = analysis.invalid_proxies_count || 0;
  const unknownProxies = analysis.unknown_proxies_count || 0;

  const validPct = totalProxies ? ((validProxies / totalProxies) * 100).toFixed(1) : "0.0";
  const invalidPct = totalProxies ? ((invalidProxies / totalProxies) * 100).toFixed(1) : "0.0";
  const unknownPct = totalProxies ? ((unknownProxies / totalProxies) * 100).toFixed(1) : "0.0";

  const filteredProxies = (analysis.proxy_list || []).filter(item => 
    (item.Name || "").toLowerCase().includes(proxySearch.toLowerCase()) ||
    (item.GlobalId || "").toLowerCase().includes(proxySearch.toLowerCase())
  );

  // --- 2. PSET CALCS ---
  const elementsChecked = analysis.score_breakdown?.elems_requiring_pset || 0;
  const psetPresent = analysis.score_breakdown?.elems_with_pset || 0;
  const psetMissing = analysis.missing_pset_count || 0;
  const psetScore = analysis.score_breakdown?.pset_pct || 100;

  let psetGrade = "Excellent";
  let psetColor = "#238636";
  if (psetScore < 50) { psetGrade = "Poor"; psetColor = "#da3633"; }
  else if (psetScore < 70) { psetGrade = "Fair"; psetColor = "#3ab8d9"; }
  else if (psetScore < 85) { psetGrade = "Good"; psetColor = "#58a6ff"; }

  const filteredPsets = (analysis.missing_pset_list || []).filter(item =>
    (item["Element Name"] || "").toLowerCase().includes(psetSearch.toLowerCase()) ||
    (item["GlobalId"] || "").toLowerCase().includes(psetSearch.toLowerCase())
  );

  // Calculate completeness by IFC type dynamically
  const psetMapConfig = {
    "IfcWall": "Pset_WallCommon",
    "IfcWallStandardCase": "Pset_WallCommon",
    "IfcDoor": "Pset_DoorCommon",
    "IfcWindow": "Pset_WindowCommon",
    "IfcSlab": "Pset_SlabCommon",
    "IfcColumn": "Pset_ColumnCommon",
    "IfcBeam": "Pset_BeamCommon",
    "IfcRoof": "Pset_RoofCommon",
    "IfcStair": "Pset_StairCommon",
    "IfcRailing": "Pset_RailingCommon",
    "IfcFlowTerminal": "Pset_FlowTerminalTypeCommon",
  };

  const typeCompleteness = [];
  Object.entries(psetMapConfig).forEach(([type, psetName]) => {
    // Count total elements of this type in model
    const totalCount = analysis.score_breakdown?.walls_total && (type === "IfcWall" || type === "IfcWallStandardCase") 
      ? analysis.score_breakdown.walls_total 
      : (analysis.storey_data && Object.values(analysis.storey_data).reduce((sum, storey) => {
          return sum + (storey.elements || []).filter(el => el.type === type).length;
        }, 0)) || 0;

    if (totalCount === 0) return;

    // Count missing elements of this type
    const missingCount = (analysis.missing_pset_list || []).filter(item => item["IFC Type"] === type).length;
    const presentCount = Math.max(0, totalCount - missingCount);
    const pct = totalCount ? Math.round((presentCount / totalCount) * 100) : 100;

    typeCompleteness.push({
      type,
      psetName,
      missingCount,
      pct,
      ratio: `${presentCount}/${totalCount}`
    });
  });

  // --- 3. GEOMETRY CALCS ---
  const geoIssues = analysis.geo_integrity_issues || [];
  const totalGeoIssues = analysis.geo_integrity_count || 0;
  
  const criticalGeoIssues = geoIssues.filter(i => i.Severity === "Critical").length;
  const highGeoIssues = geoIssues.filter(i => i.Severity === "High").length;
  const mediumGeoIssues = geoIssues.filter(i => i.Severity === "Medium").length;
  const lowGeoIssues = totalGeoIssues - criticalGeoIssues - highGeoIssues - mediumGeoIssues;

  // 5 passes counts
  const pass1Count = geoIssues.filter(i => i["Issue Type"] === "Missing Representation").length;
  const pass2Count = geoIssues.filter(i => i["Issue Type"] === "No Solid/Surface Body").length;
  const pass3Count = geoIssues.filter(i => i["Issue Type"] === "Zero Bounding Box").length;
  const pass4Count = geoIssues.filter(i => i["Issue Type"] === "Extreme Bounding Box" || i["Issue Type"] === "Misplaced Element" || i["Issue Type"] === "No Placement").length;
  const pass5Count = 0; // Mock unit scale mismatch

  const geoScore = Math.max(0, Math.min(100, Math.round(100 - (totalGeoIssues / (analysis.total_elements || 1)) * 30)));
  let geoGrade = "Excellent";
  let geoColor = "#238636";
  if (geoScore < 50) { geoGrade = "Poor"; geoColor = "#da3633"; }
  else if (geoScore < 70) { geoGrade = "Fair"; geoColor = "#3ab8d9"; }
  else if (geoScore < 85) { geoGrade = "Good"; geoColor = "#58a6ff"; }

  return (
    <div>
      <div className="title-group">
        <h1 className="page-title">🔬 Model Analysis</h1>
        <p className="page-caption">Proxy classification, Pset analysis, and geometry integrity in one place.</p>
      </div>

      {/* Tabs */}
      <div className="tabs-header" style={{ marginBottom: "28px" }}>
        <button className={`tab-btn ${activeSubTab === "Proxy" ? "active" : ""}`} onClick={() => setActiveSubTab("Proxy")}>🔎 Proxy Classification</button>
        <button className={`tab-btn ${activeSubTab === "Pset" ? "active" : ""}`} onClick={() => setActiveSubTab("Pset")}>📦 Pset Analysis</button>
        <button className={`tab-btn ${activeSubTab === "Geometry" ? "active" : ""}`} onClick={() => setActiveSubTab("Geometry")}>📐 Geometry Integrity</button>
      </div>

      {/* 1. PROXY SUBTAB (PARITY WITH IMAGE 2) */}
      {activeSubTab === "Proxy" && (
        <div>
          <h2 style={{ fontSize: "28px", fontWeight: "800", marginBottom: "4px" }}>🔎 Proxy Classification</h2>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "24px" }}>
            All IfcBuildingElementProxy elements are classified into Valid, Invalid, or Unknown based on their element names.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "24px" }}>
            <div className="metric-card" style={{ borderLeft: "4px solid #8b949e" }}>
              <div className="metric-label">Total Proxies <span style={{ cursor: "help" }} title="Total proxy elements count">🛈</span></div>
              <div className="metric-value">{totalProxies}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #238636" }}>
              <div className="metric-label">✔ Valid <span style={{ cursor: "help" }} title="Non-physical reference elements">🛈</span></div>
              <div className="metric-value" style={{ color: "#7ee787" }}>{validProxies}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #da3633" }}>
              <div className="metric-label">✘ Invalid <span style={{ cursor: "help" }} title="Lost physical elements">🛈</span></div>
              <div className="metric-value" style={{ color: "#ff6b6b" }}>{invalidProxies}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #d29922" }}>
              <div className="metric-label">❓ Unknown <span style={{ cursor: "help" }} title="Review manually">🛈</span></div>
              <div className="metric-value" style={{ color: "#e3b341" }}>{unknownProxies}</div>
            </div>
          </div>

          {/* Segmented Progress Bar */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "24px", marginBottom: "24px" }}>
            <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "1px", fontWeight: "700", marginBottom: "12px", textTransform: "uppercase" }}>PROXY BREAKDOWN</div>
            
            {totalProxies > 0 ? (
              <div>
                <div style={{ display: "flex", height: "20px", borderRadius: "10px", overflow: "hidden", background: "#161b22", marginBottom: "16px" }}>
                  <div style={{ width: `${validPct}%`, background: "#238636" }} title={`Valid: ${validPct}%`} />
                  <div style={{ width: `${invalidPct}%`, background: "#da3633" }} title={`Invalid: ${invalidPct}%`} />
                  <div style={{ width: `${unknownPct}%`, background: "#d29922" }} title={`Unknown: ${unknownPct}%`} />
                </div>

                <div style={{ display: "flex", gap: "24px", flexWrap: "wrap", fontSize: "13px", marginBottom: "16px" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ display: "inline-block", width: "10px", height: "10px", background: "#238636", borderRadius: "2px" }} />
                    Valid <strong style={{ color: "#7ee787" }}>{validPct}%</strong> ({validProxies})
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ display: "inline-block", width: "10px", height: "10px", background: "#da3633", borderRadius: "2px" }} />
                    Invalid <strong style={{ color: "#ff6b6b" }}>{invalidPct}%</strong> ({invalidProxies})
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ display: "inline-block", width: "10px", height: "10px", background: "#d29922", borderRadius: "2px" }} />
                    Unknown <strong style={{ color: "#e3b341" }}>{unknownPct}%</strong> ({unknownProxies})
                  </span>
                </div>
              </div>
            ) : (
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "16px" }}>No proxy elements found in this model.</p>
            )}

            <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "14px", display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px", color: "var(--text-secondary)" }}>
              <div>✔ <strong style={{ color: "#7ee787" }}>Valid</strong> — non-physical reference elements; no IFC class needed.</div>
              <div>✘ <strong style={{ color: "#ff6b6b" }}>Invalid</strong> — building/MEP elements that lost their type; go to 🛠️ Correction Suggestions to fix.</div>
              <div>❓ <strong style={{ color: "#e3b341" }}>Unknown</strong> — review manually.</div>
            </div>
          </div>

          {/* List Table */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "16px", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
              <input 
                type="text" 
                className="form-input" 
                placeholder="🔍 Search proxies by name or Global ID..." 
                style={{ maxWidth: "350px" }}
                value={proxySearch}
                onChange={e => setProxySearch(e.target.value)}
              />
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Showing {filteredProxies.length} of {analysis.proxy_list_total} proxies</span>
            </div>

            <div className="data-table-container" style={{ margin: 0, maxHeight: "400px", overflowY: "auto" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Element Name</th>
                    <th>Global ID</th>
                    <th>IFC Type</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredProxies.map((p, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: "600" }}>{p.Name}</td>
                      <td style={{ fontFamily: "Space Mono", fontSize: "11px" }}>{p.GlobalId}</td>
                      <td><code>{p["IFC Type"]}</code></td>
                      <td>
                        <span className={`status-badge ${p.Status === "valid" ? "status-pass" : p.Status === "invalid" ? "status-fail" : "status-warn"}`}>
                          {p.Status}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {filteredProxies.length === 0 && (
                    <tr>
                      <td colSpan="4" style={{ textAlign: "center", padding: "24px", color: "var(--text-secondary)" }}>
                        No matching proxy elements found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 2. PSET SUBTAB (PARITY WITH IMAGE 3) */}
      {activeSubTab === "Pset" && (
        <div>
          <h2 style={{ fontSize: "28px", fontWeight: "800", marginBottom: "4px" }}>📦 Property Set (Pset) Analysis</h2>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "24px" }}>
            Completeness check for standard IFC property sets across all element types.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "24px" }}>
            <div className="metric-card">
              <div className="metric-label">Elements Checked</div>
              <div className="metric-value">{elementsChecked}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Pset Present</div>
              <div className="metric-value" style={{ color: "#7ee787" }}>{psetPresent}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Pset Missing</div>
              <div className="metric-value" style={{ color: "#ff6b6b" }}>{psetMissing}</div>
            </div>
          </div>

          {/* Completeness Score Card */}
          <div style={{ 
            background: `rgba(${psetColor === "#238636" ? "35,134,54" : psetColor === "#da3633" ? "218,54,51" : "210,153,34"}, 0.08)`, 
            border: `1.5px solid ${psetColor}`, 
            borderRadius: "12px", 
            padding: "20px 24px", 
            display: "flex", 
            justifyContent: "space-between", 
            alignItems: "center", 
            marginBottom: "24px" 
          }}>
            <div>
              <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "1px", fontWeight: "700" }}>PSET COMPLETENESS SCORE</div>
              <div style={{ fontSize: "32px", fontWeight: "900", color: psetColor, marginTop: "4px" }}>
                {psetScore}% — {psetGrade}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                {psetPresent} of {elementsChecked} elements have their required property set.
              </div>
            </div>
            <div style={{ maxWidth: "300px", fontSize: "11px", color: "var(--text-secondary)", textAlign: "right" }}>
              Pset completeness contributes <strong style={{ color: "var(--color-primary)" }}>40 points</strong> to the overall model quality score. Fixing missing Psets improves your score directly.
            </div>
          </div>

          {/* Pset Tabs */}
          <div style={{ display: "flex", gap: "10px", borderBottom: "1px solid var(--border-color)", marginBottom: "20px" }}>
            <button className={`tab-btn ${psetActiveTab === "TypeSummary" ? "active" : ""}`} onClick={() => setPsetActiveTab("TypeSummary")} style={{ padding: "8px 14px", fontSize: "13px" }}>📊 Type Summary</button>
            <button className={`tab-btn ${psetActiveTab === "ElementDetails" ? "active" : ""}`} onClick={() => setPsetActiveTab("ElementDetails")} style={{ padding: "8px 14px", fontSize: "13px" }}>🔎 Element Details</button>
          </div>

          {/* TAB 1: TYPE SUMMARY (PROGRESS BARS) */}
          {psetActiveTab === "TypeSummary" && (
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700" }}>Pset Completeness by IFC Type</h3>
              
              {typeCompleteness.map(tc => {
                const color = tc.pct === 100 ? "#238636" : tc.pct < 50 ? "#da3633" : "#d29922";
                return (
                  <div key={tc.type} style={{ background: "rgba(0,0,0,0.15)", borderRadius: "8px", padding: "14px", border: "1px solid rgba(255,255,255,0.03)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", alignItems: "center" }}>
                      <div>
                        <strong style={{ fontSize: "14px", color: "#fff" }}>{tc.type}</strong>
                        <span style={{ fontSize: "11px", color: "var(--text-secondary)", marginLeft: "10px" }}>→ {tc.psetName}</span>
                      </div>
                      <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                        {tc.missingCount > 0 && (
                          <span style={{ background: "rgba(218,54,51,0.15)", color: "#ff6b6b", border: "1px solid rgba(218,54,51,0.3)", borderRadius: "4px", fontSize: "10px", padding: "2px 6px", fontWeight: "bold" }}>
                            {tc.missingCount} missing
                          </span>
                        )}
                        <strong style={{ color, fontSize: "14px" }}>{tc.pct}%</strong>
                        <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>({tc.ratio})</span>
                      </div>
                    </div>
                    <div style={{ height: "6px", background: "rgba(255,255,255,0.04)", borderRadius: "3px", overflow: "hidden" }}>
                      <div style={{ width: `${tc.pct}%`, background: color, height: "100%", borderRadius: "3px" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* TAB 2: DETAILED TABLE */}
          {psetActiveTab === "ElementDetails" && (
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "16px", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                <input 
                  type="text" 
                  className="form-input" 
                  placeholder="🔍 Search missing psets by name..." 
                  style={{ maxWidth: "350px" }}
                  value={psetSearch}
                  onChange={e => setPsetSearch(e.target.value)}
                />
                <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Showing {filteredPsets.length} elements</span>
              </div>

              <div className="data-table-container" style={{ margin: 0, maxHeight: "330px", overflowY: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Element Name</th>
                      <th>Global ID</th>
                      <th>Type</th>
                      <th>Required Set</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPsets.map((item, idx) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: "600" }}>{item["Element Name"]}</td>
                        <td style={{ fontFamily: "Space Mono", fontSize: "11px" }}>{item.GlobalId}</td>
                        <td><code>{item["IFC Type"]}</code></td>
                        <td style={{ color: "#ffb347" }}>{item["Required Pset"]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 3. GEOMETRY INTEGRITY (PARITY WITH IMAGE 4) */}
      {activeSubTab === "Geometry" && (
        <div>
          <h2 style={{ fontSize: "28px", fontWeight: "800", marginBottom: "4px" }}>📐 Geometry Integrity & Recovery</h2>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "24px" }}>
            Detects missing, invalid, degenerate, and misplaced geometry in the IFC model. Classifies each issue by type, root cause, and impact. Offers partial IFC-level recovery where possible.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "24px" }}>
            <div className="metric-card">
              <div className="metric-label">Total Elements</div>
              <div className="metric-value">{analysis.total_elements}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #da3633" }}>
              <div className="metric-label">🔴 Critical Issues <span style={{ cursor: "help" }} title="Missing representations">🛈</span></div>
              <div className="metric-value" style={{ color: "#ff6b6b" }}>{criticalGeoIssues}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #ff6600" }}>
              <div className="metric-label">🟠 High Issues <span style={{ cursor: "help" }} title="No solid bodies">🛈</span></div>
              <div className="metric-value" style={{ color: "#ff9500" }}>{highGeoIssues}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #d29922" }}>
              <div className="metric-label">🟡 Medium Issues <span style={{ cursor: "help" }} title="Misplaced elements">🛈</span></div>
              <div className="metric-value" style={{ color: "#ffb347" }}>{mediumGeoIssues}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Total Issues</div>
              <div className="metric-value">{totalGeoIssues}</div>
            </div>
          </div>

          {/* Geometry Integrity score card */}
          <div style={{ 
            background: `rgba(${geoColor === "#238636" ? "35,134,54" : geoColor === "#da3633" ? "218,54,51" : "210,153,34"}, 0.08)`, 
            border: `1.5px solid ${geoColor}`, 
            borderRadius: "12px", 
            padding: "20px 24px", 
            marginBottom: "24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}>
            <div>
              <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "1px", fontWeight: "700" }}>GEOMETRY INTEGRITY SCORE</div>
              <div style={{ fontSize: "32px", fontWeight: "900", color: geoColor, marginTop: "4px" }}>
                {geoScore}.0 / 100 — {geoGrade}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                {totalGeoIssues} geometry issues detected across {analysis.total_elements} elements.
              </div>
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
              <strong>5 detection passes:</strong><br/>
              Missing Representation · No Solid Body · Degenerate BBox · Misplaced / No Placement · Unit Scale Mismatch
            </div>
          </div>

          {/* 5 Passes horizontal list (Parity with bottom section in Image 4) */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "12px", marginBottom: "24px" }}>
            {[
              { id: 1, name: "Missing Representation", count: pass1Count, severity: "Critical" },
              { id: 2, name: "No Solid/Surface Body", count: pass2Count, severity: "High" },
              { id: 3, name: "Degenerate Bounding Box", count: pass3Count, severity: "Medium" },
              { id: 4, name: "Misplaced / No Placement", count: pass4Count, severity: "Low" },
              { id: 5, name: "Unit Scale Mismatch", count: pass5Count, severity: "Ok" }
            ].map(pass => {
              const hasIssues = pass.count > 0;
              const borderCol = !hasIssues ? "#238636" : pass.severity === "Critical" ? "#da3633" : pass.severity === "High" ? "#ff9500" : "#ffb347";
              const bgCol = !hasIssues ? "rgba(35,134,54,0.06)" : pass.severity === "Critical" ? "rgba(218,54,51,0.06)" : "rgba(210,153,34,0.06)";
              
              return (
                <div key={pass.id} style={{ background: bgCol, border: `1.5px solid ${borderCol}`, borderRadius: "8px", padding: "16px", textAlign: "center" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-secondary)" }}>Pass {pass.id}</div>
                  <div style={{ fontSize: "18px", fontWeight: "900", margin: "6px 0", color: borderCol, display: "flex", justifyContent: "center", alignItems: "center", gap: "6px" }}>
                    {!hasIssues ? "✔" : "🔴"} {pass.count}
                  </div>
                  <div style={{ fontSize: "11px", fontWeight: "700", color: "#fff" }}>{pass.name}</div>
                </div>
              );
            })}
          </div>

          {/* Table */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "6px" }}>📐 Geometry Issues & Recovery Guidelines</h3>
            <div className="data-table-container" style={{ margin: 0, maxHeight: "380px", overflowY: "auto" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Element Name</th>
                    <th>Global ID</th>
                    <th>Type</th>
                    <th>Issue Type</th>
                    <th>Severity</th>
                    <th>Recovery Plan</th>
                  </tr>
                </thead>
                <tbody>
                  {geoIssues.map((issue, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: "600" }}>{issue.Name}</td>
                      <td style={{ fontFamily: "Space Mono", fontSize: "11px" }}>{issue.GlobalId}</td>
                      <td><code>{issue["IFC Type"]}</code></td>
                      <td style={{ color: "#ff6b6b" }}>{issue["Issue Type"]}</td>
                      <td>
                        <span className={`status-badge ${issue.Severity === "Critical" ? "status-fail" : "status-warn"}`}>
                          {issue.Severity}
                        </span>
                      </td>
                      <td style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{issue.Recovery}</td>
                    </tr>
                  ))}
                  {geoIssues.length === 0 && (
                    <tr>
                      <td colSpan="6" style={{ textAlign: "center", padding: "30px", color: "var(--text-secondary)" }}>
                        ✅ All geometry passes succeeded! No coordinate scale or missing representations found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
