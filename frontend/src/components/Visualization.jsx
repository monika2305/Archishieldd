import React, { useState } from "react";
import { API_BASE_URL } from "../config";

export default function Visualization({ analysis }) {
  const [activeSubTab, setActiveSubTab] = useState("3DViewer");
  
  // Storey tabs state
  const [storeyTab, setStoreyTab] = useState("Floorwise"); // Floorwise, Details, Summary
  const [selectedFloor, setSelectedFloor] = useState("");
  const [floorIssueFilter, setFloorIssueFilter] = useState("All");

  if (!analysis || !analysis.total_elements) {
    return (
      <div style={{ padding: "40px", textAlign: "center", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px" }}>
        <h3>⚠️ No analysis data available</h3>
        <p style={{ color: "var(--text-secondary)", marginTop: "8px" }}>Please upload an IFC file on the Home page first.</p>
      </div>
    );
  }

  // --- STOREY ANALYSIS CALCULATIONS ---
  const storeyData = analysis.storey_data || {};
  const storeyEntries = Object.entries(storeyData);
  const totalFloors = storeyEntries.length;
  
  let avgScore = 0;
  let bestFloor = "N/A";
  let bestScore = -1;
  let worstFloor = "N/A";
  let worstScore = 999;

  if (totalFloors > 0) {
    let sum = 0;
    storeyEntries.forEach(([name, data]) => {
      sum += data.score;
      if (data.score > bestScore) {
        bestScore = data.score;
        bestFloor = name;
      }
      if (data.score < worstScore) {
        worstScore = data.score;
        worstFloor = name;
      }
    });
    avgScore = (sum / totalFloors).toFixed(1);
  }

  // Default selected floor if not set
  if (totalFloors > 0 && !selectedFloor) {
    setSelectedFloor(storeyEntries[0][0]);
  }

  return (
    <div>
      <div className="title-group">
        <h1 className="page-title">📊 3D & Spatial Visualization</h1>
        <p className="page-caption">Interact with the building models, coordinate heatmaps, and floor risk meters.</p>
      </div>

      {/* Main Tabs */}
      <div className="tabs-header" style={{ marginBottom: "28px" }}>
        <button className={`tab-btn ${activeSubTab === "3DViewer" ? "active" : ""}`} onClick={() => setActiveSubTab("3DViewer")}>🧊 3D BIM Building Viewer</button>
        <button className={`tab-btn ${activeSubTab === "Heatmap" ? "active" : ""}`} onClick={() => setActiveSubTab("Heatmap")}>🔥 Issue Heatmap (2D)</button>
        <button className={`tab-btn ${activeSubTab === "Storeys" ? "active" : ""}`} onClick={() => setActiveSubTab("Storeys")}>🏢 Storey Quality Score</button>
      </div>

      {/* 1. 3D BIM BUILDING VIEWER (IFRAME EMULATOR) */}
      {activeSubTab === "3DViewer" && (
        <div>
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "16px", marginBottom: "24px" }}>
            <iframe 
              src={`${API_BASE_URL}/api/visualize/3d`} 
              style={{ width: "100%", height: "650px", border: "none", borderRadius: "8px", background: "#0a0e17" }}
              title="3D BIM Viewer"
            />
          </div>
        </div>
      )}

      {/* 2. ISSUE HEATMAP (IFRAME EMULATOR) */}
      {activeSubTab === "Heatmap" && (
        <div>
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "16px", marginBottom: "24px" }}>
            <iframe 
              src={`${API_BASE_URL}/api/visualize/heatmap`} 
              style={{ width: "100%", height: "650px", border: "none", borderRadius: "8px", background: "#0d1117" }}
              title="2D Floor Plan Overlay"
            />
          </div>
        </div>
      )}

      {/* 3. STOREY QUALITY SCORE */}
      {activeSubTab === "Storeys" && (
        <div>
          <h2 style={{ fontSize: "28px", fontWeight: "800", marginBottom: "4px" }}>🏢 Storey-wise Quality Score</h2>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "24px" }}>
            Individual BIM quality score for every floor. Elements assigned to a storey via IfcRelContainedInSpatialStructure are grouped per floor.
          </p>

          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Total Floors</div>
              <div className="metric-value">{totalFloors}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Average Score</div>
              <div className="metric-value" style={{ color: "var(--color-info)" }}>{avgScore}/100</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">🏆 Best Floor</div>
              <div className="metric-value" style={{ color: "#7ee787", fontSize: "16px", fontWeight: "800" }}>
                {bestFloor} ({bestScore}/100)
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">⚠️ Worst Floor</div>
              <div className="metric-value" style={{ color: "#ff6b6b", fontSize: "16px", fontWeight: "800" }}>
                {worstFloor} ({worstScore}/100)
              </div>
            </div>
          </div>

          {/* Storey Sub-Tabs */}
          <div style={{ display: "flex", gap: "10px", borderBottom: "1px solid var(--border-color)", marginBottom: "20px" }}>
            <button className={`tab-btn ${storeyTab === "Floorwise" ? "active" : ""}`} onClick={() => setStoreyTab("Floorwise")} style={{ padding: "8px 14px", fontSize: "13px" }}>📊 Floor-wise Score</button>
            <button className={`tab-btn ${storeyTab === "Details" ? "active" : ""}`} onClick={() => setStoreyTab("Details")} style={{ padding: "8px 14px", fontSize: "13px" }}>🔍 Element Details per Floor</button>
            <button className={`tab-btn ${storeyTab === "Summary" ? "active" : ""}`} onClick={() => setStoreyTab("Summary")} style={{ padding: "8px 14px", fontSize: "13px" }}>📋 Summary Table</button>
          </div>

          {/* SUBTAB 1: FLOOR-WISE CARD SCORE LIST */}
          {storeyTab === "Floorwise" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {storeyEntries.map(([floorName, data]) => {
                return (
                  <div key={floorName} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border-color)", borderRadius: "10px", padding: "18px 24px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                      <div>
                        <span style={{ fontSize: "16px", fontWeight: "700", color: "#f0f4f8" }}>{floorName}</span>
                        <span style={{ fontSize: "11px", color: "var(--text-secondary)", marginLeft: "12px" }}>
                          Elevation: {data.elevation === -9999 ? "Unassigned Group" : `${data.elevation.toFixed(2)}m`}
                        </span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <span style={{ fontSize: "22px", fontWeight: "800", color: data.color }}>{data.score}/100</span>
                        <span style={{ 
                          background: `${data.color}22`, 
                          color: data.color, 
                          border: `1.5px solid ${data.color}`, 
                          borderRadius: "4px", 
                          fontSize: "11px", 
                          fontWeight: "700", 
                          padding: "2px 8px" 
                        }}>{data.grade}</span>
                      </div>
                    </div>

                    <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: "6px", height: "12px", overflow: "hidden", marginBottom: "12px" }}>
                      <div style={{ width: `${data.score}%`, background: data.color, height: "100%", borderRadius: "6px" }} />
                    </div>

                    <div style={{ display: "flex", gap: "24px", flexWrap: "wrap", fontSize: "13px" }}>
                      <span>Total: <strong style={{ color: "#fff" }}>{data.total}</strong></span>
                      <span style={{ color: "#ff6b6b" }}>🔴 Proxy: <strong>{data.proxies}</strong></span>
                      <span style={{ color: "#ffb347" }}>🟠 Missing Pset: <strong>{data.missing_pset}</strong></span>
                      <span style={{ color: "#58a6ff" }}>🟢 Clean: <strong>{data.ok}</strong></span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* SUBTAB 2: DETAILED ELEMENT LIST PER SELECTED FLOOR */}
          {storeyTab === "Details" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 2.5fr", gap: "20px", alignItems: "start" }}>
              <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px" }}>
                <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "8px" }}>Select floor to inspect:</label>
                <select 
                  className="form-select" 
                  value={selectedFloor} 
                  onChange={e => setSelectedFloor(e.target.value)}
                  style={{ width: "100%" }}
                >
                  {storeyEntries.map(([floorName]) => (
                    <option key={floorName} value={floorName}>{floorName}</option>
                  ))}
                </select>

                {selectedFloor && storeyData[selectedFloor] && (
                  <div style={{ marginTop: "24px" }}>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "4px" }}>FLOOR QUALITY SCORE</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: storeyData[selectedFloor].color }}>
                      {storeyData[selectedFloor].score}/100
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "12px" }}>
                      Total elements: <strong>{storeyData[selectedFloor].total}</strong>
                    </div>
                  </div>
                )}
              </div>

              {selectedFloor && storeyData[selectedFloor] ? (
                <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
                    <h4 style={{ fontSize: "15px", fontWeight: "700" }}>📋 Problem Elements: {selectedFloor}</h4>
                    <select 
                      className="form-select" 
                      value={floorIssueFilter} 
                      onChange={e => setFloorIssueFilter(e.target.value)}
                      style={{ maxWidth: "200px" }}
                    >
                      <option value="All">All issues</option>
                      <option value="proxy">🔴 Proxy</option>
                      <option value="missing_pset">🟠 Missing Pset</option>
                      <option value="ok">🟢 Clean</option>
                    </select>
                  </div>

                  <div className="data-table-container" style={{ margin: 0, maxHeight: "380px", overflowY: "auto" }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Element Name</th>
                          <th>IFC Type</th>
                          <th>Issue Status</th>
                          <th>Global ID</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(storeyData[selectedFloor].elements || [])
                          .filter(el => floorIssueFilter === "All" || el.issue === floorIssueFilter)
                          .map((el, i) => (
                            <tr key={i}>
                              <td style={{ fontWeight: "600" }}>{el.name}</td>
                              <td><code>{el.type}</code></td>
                              <td>
                                <span className={`status-badge ${el.issue === "ok" ? "status-pass" : el.issue === "proxy" ? "status-fail" : "status-warn"}`}>
                                  {el.issue === "ok" ? "clean" : el.issue}
                                </span>
                              </td>
                              <td style={{ fontFamily: "Space Mono", fontSize: "11px" }}>{el.gid}</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: "80px", background: "var(--bg-card)", borderRadius: "12px" }}>
                  Select a floor to view element details.
                </div>
              )}
            </div>
          )}

          {/* SUBTAB 3: SUMMARY TABLE */}
          {storeyTab === "Summary" && (
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "14px" }}>📋 Floor-by-Floor Summary Table</h3>
              
              <div className="data-table-container" style={{ margin: 0, maxHeight: "400px", overflowY: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Floor Level</th>
                      <th>Elevation</th>
                      <th>Total Elements</th>
                      <th>Proxies</th>
                      <th>Missing Psets</th>
                      <th>Clean Elements</th>
                      <th>Quality Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {storeyEntries.map(([floorName, data]) => (
                      <tr key={floorName}>
                        <td style={{ fontWeight: "700" }}>{floorName}</td>
                        <td style={{ fontFamily: "Space Mono" }}>{data.elevation === -9999 ? "N/A" : `${data.elevation.toFixed(2)}m`}</td>
                        <td>{data.total}</td>
                        <td style={{ color: "#ff6b6b" }}>{data.proxies}</td>
                        <td style={{ color: "#ffb347" }}>{data.missing_pset}</td>
                        <td style={{ color: "#7ee787" }}>{data.ok}</td>
                        <td>
                          <span className="status-badge" style={{ background: `${data.color}22`, color: data.color, border: `1px solid ${data.color}` }}>
                            {data.score}/100
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
