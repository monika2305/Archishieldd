import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "../config";

export default function CorrectionsDashboard({ analysis, onApplySuccess }) {
  const [correctionsList, setCorrectionsList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeEngineTab, setActiveEngineTab] = useState("Proxy"); // Proxy, Pset, Qty, Rel

  // Filter states
  const [filterType, setFilterType] = useState("All");
  const [filterConf, setFilterConf] = useState("All");
  const [filterSearch, setFilterSearch] = useState("");

  // Cumulative selections (matches Streamlit session state)
  const [appliedFixes, setAppliedFixes] = useState([]); // List of proxy GlobalIds applied
  const [selections, setSelections] = useState({}); // GlobalId -> TargetClass
  const [removedProxies, setRemovedProxies] = useState([]); // List of proxy GlobalIds removed/ignored
  
  const [psetFixes, setPsetFixes] = useState([]); // List of pset GlobalIds applied
  const [psetFixSelections, setPsetFixSelections] = useState({}); // GlobalId -> { PsetName, IFCType }

  const [manualShowAll, setManualShowAll] = useState({}); // GlobalId -> bool (show manual class dropdown)
  
  // Progress/API status
  const [applying, setApplying] = useState(false);
  const [validating, setValidating] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [applyMessage, setApplyMessage] = useState("");

  // Fetch corrections list
  useEffect(() => {
    if (analysis) {
      setLoading(true);
      fetch(`${API_BASE_URL}/api/analyze/corrections`)
        .then(res => res.json())
        .then(data => {
          setCorrectionsList(data);
          
          // Pre-populate selections with initial suggestions
          const initialSel = {};
          const initialPset = {};
          data.forEach(item => {
            if (item.category === "proxy" && item.SuggestedType !== "—") {
              initialSel[item.GlobalId] = item.SuggestedType;
            }
            if (item.category === "missing_pset") {
              initialPset[item.GlobalId] = {
                PsetName: item.req_pset,
                IFCType: item.CurrentType
              };
            }
          });
          setSelections(initialSel);
          setPsetFixSelections(initialPset);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setLoading(false);
        });
    }
  }, [analysis]);

  // Handlers for individual proxy edits
  const handleSelectClass = (gid, cls) => {
    setSelections(prev => ({ ...prev, [gid]: cls }));
  };

  const handleToggleShowAll = (gid) => {
    setManualShowAll(prev => ({ ...prev, [gid]: !prev[gid] }));
  };

  const handleApplySingleProxy = (gid, targetClass) => {
    const cls = selections[gid] || targetClass;
    if (!cls || cls === "— Select IFC Class —") {
      alert("Please select a valid IFC Class first.");
      return;
    }
    setAppliedFixes(prev => [...prev.filter(id => id !== gid), gid]);
    setRemovedProxies(prev => prev.filter(id => id !== gid));
    setSelections(prev => ({ ...prev, [gid]: cls }));
    setApplyMessage(`Queued reclassification of ${gid} to ${cls}`);
  };

  const handleRemoveSingleProxy = (gid) => {
    setAppliedFixes(prev => prev.filter(id => id !== gid));
    setRemovedProxies(prev => [...prev.filter(id => id !== gid), gid]);
    setApplyMessage(`Removed suggestion for proxy element ${gid}`);
  };

  const handleUndoRemoveProxy = (gid) => {
    setRemovedProxies(prev => prev.filter(id => id !== gid));
    setApplyMessage(`Restored suggestion for proxy element ${gid}`);
  };

  // Handlers for batch proxy actions (Matches Streamlit buttons exactly)
  const handleApplyAllSuggestions = () => {
    let count = 0;
    const newApplied = [...appliedFixes];
    const newSelections = { ...selections };

    proxyItems.forEach(item => {
      const gid = item.GlobalId;
      const sug = item.SuggestedType;

      if (!sug || sug === "—") {
        return;
      }

      if (!newApplied.includes(gid)) {
        newApplied.push(gid);
      }
      newSelections[gid] = sug;
      count++;
    });

    setAppliedFixes(newApplied);
    setSelections(newSelections);
    setRemovedProxies([]); // Reset removed lists on apply all

    setApplyMessage(`Successfully applied ${count} proxy reclassifications!`);
  };

  const handleRemoveAllSuggestions = () => {
    const newRemoved = [...removedProxies];
    const newApplied = appliedFixes.filter(gid => {
      const isProxy = proxyItems.some(p => p.GlobalId === gid);
      return !isProxy; // Keep pset/other fixes, clear only proxies
    });

    proxyItems.forEach(item => {
      const gid = item.GlobalId;
      if (!newRemoved.includes(gid)) {
        newRemoved.push(gid);
      }
    });

    setAppliedFixes(newApplied);
    setRemovedProxies(newRemoved);
    setApplyMessage(`Ignored/removed all ${proxyItems.length} proxy element suggestions.`);
  };

  // Handlers for individual pset fixes
  const handleApplyPset = (gid, item) => {
    setPsetFixes(prev => [...prev.filter(id => id !== gid), gid]);
    setPsetFixSelections(prev => ({
      ...prev,
      [gid]: { PsetName: item.req_pset, IFCType: item.CurrentType }
    }));
    setApplyMessage(`Queued property set ${item.req_pset} injection for ${item.ElementName}`);
  };

  const handleRemovePset = (gid) => {
    setPsetFixes(prev => prev.filter(id => id !== gid));
    setApplyMessage(`Removed property set injection for ${gid}`);
  };

  const handleApplyAllPsets = () => {
    const newPsets = [...psetFixes];
    const newSelections = { ...psetFixSelections };
    psetItems.forEach(item => {
      const gid = item.GlobalId;
      if (!newPsets.includes(gid)) {
        newPsets.push(gid);
      }
      newSelections[gid] = {
        PsetName: item.req_pset,
        IFCType: item.CurrentType
      };
    });
    setPsetFixes(newPsets);
    setPsetFixSelections(newSelections);
    setApplyMessage(`Applied all ${psetItems.length} Pset fixes.`);
  };

  const handleRemoveAllPsets = () => {
    setPsetFixes([]);
    setApplyMessage("Removed all queued Pset fixes.");
  };

  // Compile and Download Corrected IFC (Matches final download button workflow)
  const handleDownloadCorrected = async () => {
    setApplying(true);
    setApplyMessage("Compiling corrected IFC file in-memory...");

    // Filter selections and pset_fixes to ONLY contain applied keys
    const finalSelections = {};
    appliedFixes.forEach(gid => {
      if (selections[gid]) {
        finalSelections[gid] = selections[gid];
      }
    });

    const finalPsets = {};
    psetFixes.forEach(gid => {
      if (psetFixSelections[gid]) {
        finalPsets[gid] = psetFixSelections[gid];
      }
    });

    try {
      const res = await fetch(`${API_BASE_URL}/api/analyze/apply-corrections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          selections: finalSelections,
          pset_fixes: finalPsets
        })
      });

      if (!res.ok) throw new Error("Correction compiler failed.");
      const data = await res.json();

      if (data.status === "success") {
        setApplyMessage("In-memory compilation successful. Starting download...");
        
        // Trigger download
        window.open(`${API_BASE_URL}/api/analyze/download-corrected`, "_blank");
      }
    } catch (err) {
      alert("Error compiling corrections: " + err.message);
    } finally {
      setApplying(false);
    }
  };

  const handleValidatePreview = async () => {
    setValidating(true);
    setApplyMessage("Validating corrections and calculating preview score...");

    const finalSelections = {};
    appliedFixes.forEach(gid => {
      if (selections[gid]) {
        finalSelections[gid] = selections[gid];
      }
    });

    const finalPsets = {};
    psetFixes.forEach(gid => {
      if (psetFixSelections[gid]) {
        finalPsets[gid] = psetFixSelections[gid];
      }
    });

    try {
      const res = await fetch(`${API_BASE_URL}/api/analyze/apply-corrections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          selections: finalSelections,
          pset_fixes: finalPsets
        })
      });

      if (!res.ok) throw new Error("Correction validation failed.");
      const data = await res.json();

      if (data.status === "success") {
        setPreviewData(data);
        setApplyMessage("Score preview calculated successfully!");
      }
    } catch (err) {
      alert("Error validating corrections: " + err.message);
    } finally {
      setValidating(false);
    }
  };

  if (!analysis) {
    return (
      <div style={{ padding: "40px", textAlign: "center", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px" }}>
        <h3>⚠️ No analysis data available</h3>
        <p style={{ color: "var(--text-secondary)", marginTop: "8px" }}>Please upload an IFC file on the Home page first.</p>
      </div>
    );
  }

  // Lists
  const proxyItems = correctionsList.filter(c => c.category === "proxy");
  const psetItems = correctionsList.filter(c => c.category === "missing_pset");
  const qtyItems = correctionsList.filter(c => c.category === "quantity_loss");
  const relItems = correctionsList.filter(c => c.category === "relationship_loss");
  
  const totalIssues = correctionsList.length;

  // Filter Table Results
  const filteredCorrections = correctionsList.filter(row => {
    const matchType = filterType === "All" || row.category === filterType;
    
    // Confidence filter
    let matchConf = true;
    if (filterConf === "High") matchConf = row.Confidence >= 80;
    else if (filterConf === "Medium") matchConf = row.Confidence >= 50 && row.Confidence < 80;
    else if (filterConf === "Low") matchConf = row.Confidence > 0 && row.Confidence < 50;

    // Search filter
    const searchStr = filterSearch.toLowerCase();
    const matchSearch = !filterSearch || 
      (row.ElementName || "").toLowerCase().includes(searchStr) || 
      (row.GlobalId || "").toLowerCase().includes(searchStr);

    return matchType && matchConf && matchSearch;
  });

  const totalActions = appliedFixes.length + psetFixes.length;

  return (
    <div>
      <div className="title-group">
        <h1 className="page-title">🛠️ Correction Suggestions</h1>
        <p className="page-caption">Audit lost semantic mappings and automatically inject missing Psets and materials.</p>
      </div>

      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)" }}>
          🔍 Scanning IFC STEP stream for corrections...
        </div>
      ) : (
        <div>
          {/* Metrics Top Row */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "30px" }}>
            <div className="metric-card">
              <div className="metric-label">Total Issues</div>
              <div className="metric-value">{totalIssues}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #da3633" }}>
              <div className="metric-label">Proxy Reclassifications</div>
              <div className="metric-value" style={{ color: "#da3633" }}>{proxyItems.length}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #d29922" }}>
              <div className="metric-label">Missing Pset Fixes</div>
              <div className="metric-value" style={{ color: "#d29922" }}>{psetItems.length}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #58a6ff" }}>
              <div className="metric-label">Quantity Loss</div>
              <div className="metric-value" style={{ color: "#58a6ff" }}>{qtyItems.length}</div>
            </div>
            <div className="metric-card" style={{ borderLeft: "4px solid #8b949e" }}>
              <div className="metric-label">Relationship Loss</div>
              <div className="metric-value" style={{ color: "#8b949e" }}>{relItems.length}</div>
            </div>
          </div>

          {/* Section: Filter and Explore suggestions */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px", marginBottom: "30px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "14px" }}>🔍 Filter & Explore Suggestions</h3>
            
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", marginBottom: "14px" }}>
              <div>
                <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Issue Type</label>
                <select className="form-select" value={filterType} onChange={e => setFilterType(e.target.value)} style={{ width: "100%" }}>
                  <option value="All">All Categories</option>
                  <option value="proxy">Proxy Reclassifications</option>
                  <option value="missing_pset">Missing Pset Fixes</option>
                  <option value="quantity_loss">Quantity Loss</option>
                  <option value="relationship_loss">Relationship Loss</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Confidence</label>
                <select className="form-select" value={filterConf} onChange={e => setFilterConf(e.target.value)} style={{ width: "100%" }}>
                  <option value="All">All</option>
                  <option value="High">High (≥80%)</option>
                  <option value="Medium">Medium (50-79%)</option>
                  <option value="Low">Low (&lt;50%)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Search by name or GlobalId</label>
                <input type="text" className="form-input" value={filterSearch} onChange={e => setFilterSearch(e.target.value)} placeholder="e.g. Wall_001 or 0A3..." style={{ width: "100%" }} />
              </div>
            </div>

            <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "14px" }}>
              Showing <strong>{filteredCorrections.length}</strong> of {totalIssues} suggestions
            </div>

            {/* Table */}
            <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "14px" }}>
              <h4 style={{ fontSize: "14px", fontWeight: "700", marginBottom: "10px" }}>📝 Correction Table</h4>
              <div className="data-table-container" style={{ margin: 0, maxHeight: "280px", overflowY: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Element Name</th>
                      <th>GlobalId</th>
                      <th>Current Type</th>
                      <th>Suggested Type</th>
                      <th>Confidence %</th>
                      <th>Issue</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCorrections.map((row, idx) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: "700" }}>{row.ElementName}</td>
                        <td><code>{row.GlobalId}</code></td>
                        <td><span style={{ fontSize: "10px", background: "rgba(218,54,51,0.08)", border: "1px solid rgba(218,54,51,0.25)", color: "#ff6b6b", borderRadius: "3px", padding: "1px 6px" }}>{row.CurrentType}</span></td>
                        <td><span style={{ fontSize: "10px", background: "rgba(35,134,54,0.08)", border: "1px solid rgba(35,134,54,0.25)", color: "#7ee787", borderRadius: "3px", padding: "1px 6px" }}>{row.SuggestedType}</span></td>
                        <td>
                          {row.Confidence > 0 ? (
                            <div style={{ 
                              background: row.Confidence >= 80 ? "#238636" : row.Confidence >= 50 ? "#d29922" : "#da3633",
                              color: "#fff",
                              fontWeight: "700",
                              fontSize: "11px",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              width: "fit-content"
                            }}>{row.Confidence}%</div>
                          ) : "—"}
                        </td>
                        <td>{row.Issue}</td>
                        <td><code style={{ color: "var(--color-primary)" }}>{row.Action}</code></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Interactive correction engine tabs */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px", marginBottom: "30px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "14px" }}>🔧 Interactive IFC Correction Engine</h3>
            
            <div style={{ display: "flex", gap: "10px", borderBottom: "1px solid var(--border-color)", paddingBottom: "10px", marginBottom: "20px", overflowX: "auto" }}>
              <button className={`tab-btn ${activeEngineTab === "Proxy" ? "active" : ""}`} onClick={() => setActiveEngineTab("Proxy")} style={{ fontSize: "12px", padding: "6px 12px" }}>🔴 Proxy Reclassification ({proxyItems.length})</button>
              <button className={`tab-btn ${activeEngineTab === "Pset" ? "active" : ""}`} onClick={() => setActiveEngineTab("Pset")} style={{ fontSize: "12px", padding: "6px 12px" }}>🟠 Pset Addition ({psetItems.length})</button>
              <button className={`tab-btn ${activeEngineTab === "Qty" ? "active" : ""}`} onClick={() => setActiveEngineTab("Qty")} style={{ fontSize: "12px", padding: "6px 12px" }}>📐 Quantity Loss ({qtyItems.length})</button>
              <button className={`tab-btn ${activeEngineTab === "Rel" ? "active" : ""}`} onClick={() => setActiveEngineTab("Rel")} style={{ fontSize: "12px", padding: "6px 12px" }}>🔗 Relationship Loss ({relItems.length})</button>
            </div>

            {/* Sub-engine actions */}
            {activeEngineTab === "Proxy" && (
              <div>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "14px" }}>
                  Review each proxy element, confirm or change the suggested IFC class, then apply fixes.
                </p>

                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center", marginBottom: "20px" }}>
                  <button className="btn-primary" onClick={handleApplyAllSuggestions} style={{ background: "#7f5af0", borderColor: "#7f5af0", color: "#fff", padding: "8px 20px", fontWeight: "700" }}>
                    ⚡ Apply All Suggestions
                  </button>
                  <button className="btn-secondary" onClick={handleRemoveAllSuggestions} style={{ padding: "8px 20px", color: "#ff6b6b", borderColor: "#ff6b6b33" }}>
                    🗑 Remove All Suggestions
                  </button>
                  <div style={{ 
                    background: appliedFixes.length > 0 ? "rgba(35, 134, 54, 0.15)" : "rgba(255,255,255,0.05)", 
                    border: appliedFixes.length > 0 ? "1px solid #238636" : "1px solid var(--border-color)", 
                    color: appliedFixes.length > 0 ? "#7ee787" : "inherit",
                    padding: "8px 16px", 
                    borderRadius: "6px", 
                    fontSize: "12px", 
                    fontWeight: "600" 
                  }}>
                    {appliedFixes.length} / {proxyItems.length} elements corrected
                  </div>
                </div>

                {applyMessage && (
                  <div style={{ padding: "10px", background: "rgba(35,134,54,0.15)", border: "1px solid #238636", color: "#7ee787", borderRadius: "6px", marginBottom: "14px", fontSize: "12px" }}>
                    {applyMessage}
                  </div>
                )}

                {/* Table Header Columns */}
                <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 2fr 0.8fr", padding: "10px 14px", borderBottom: "1px solid var(--border-color)", fontWeight: "700", fontSize: "13px", color: "#fff" }}>
                  <div>Element</div>
                  <div>Current Class</div>
                  <div>💡 SMART SUGGESTIONS</div>
                  <div style={{ textAlign: "right" }}>Action</div>
                </div>

                {/* Cards List */}
                <div style={{ display: "flex", flexDirection: "column", gap: "1px", maxHeight: "400px", overflowY: "auto" }}>
                  {proxyItems.map((item, idx) => {
                    const gid = item.GlobalId;
                    const isApplied = appliedFixes.includes(gid);
                    const isRemoved = removedProxies.includes(gid);
                    
                    const bestSug = item.smart_suggestions?.[0] || { class: item.SuggestedType, confidence: item.Confidence };
                    const isShowAll = !!manualShowAll[gid];
                    
                    const cardBg = isRemoved ? "rgba(218,54,51,0.04)" : isApplied ? "rgba(35,134,54,0.04)" : "rgba(255,255,255,0.01)";

                    return (
                      <div key={idx} style={{ 
                        background: cardBg, 
                        borderBottom: "1px solid rgba(255,255,255,0.06)", 
                        padding: "16px 14px", 
                        display: "grid", 
                        gridTemplateColumns: "1.5fr 1fr 2fr 0.8fr", 
                        gap: "16px", 
                        alignItems: "center" 
                      }}>
                        <div>
                          <strong style={{ fontSize: "13px", color: "#fff" }}>{item.ElementName}</strong>
                          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}><code>{gid}</code></div>
                        </div>

                        <div>
                          <span className="status-badge status-fail" style={{ fontSize: "11px" }}>
                            {item.CurrentType}
                          </span>
                        </div>

                        <div>
                          {isApplied ? (
                            <div style={{ color: "#7ee787", fontSize: "12px", fontWeight: "700" }}>
                              ✅ Applied: {selections[gid]}
                            </div>
                          ) : isRemoved ? (
                            <div style={{ color: "#ff6b6b", fontSize: "12px", fontWeight: "600" }}>
                              ❌ Ignored/Removed
                            </div>
                          ) : (
                            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                              <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                                <span style={{ fontSize: "10px", background: "rgba(35,134,54,0.15)", border: "1px solid #238636", color: "#7ee787", padding: "2px 6px", borderRadius: "4px", fontWeight: "700" }}>
                                  ★ Best
                                </span>
                                <span style={{ fontSize: "13px", fontWeight: "700", color: "#fff" }}>{bestSug.class}</span>
                                <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>({bestSug.confidence}%)</span>
                              </div>
                              
                              <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", marginTop: "6px", cursor: "pointer" }}>
                                <input 
                                  type="checkbox" 
                                  checked={selections[gid] === bestSug.class}
                                  onChange={(e) => {
                                    if (e.target.checked) handleSelectClass(gid, bestSug.class);
                                    else handleSelectClass(gid, "");
                                  }}
                                />
                                Apply Best: {bestSug.class}
                              </label>

                              <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", cursor: "pointer", marginTop: "2px" }}>
                                <input 
                                  type="checkbox" 
                                  checked={isShowAll} 
                                  onChange={() => handleToggleShowAll(gid)}
                                />
                                Show all IFC classes
                              </label>

                              {isShowAll && (
                                <select 
                                  className="form-select" 
                                  style={{ padding: "4px 8px", fontSize: "11px", marginTop: "6px" }}
                                  value={selections[gid] || ""}
                                  onChange={(e) => handleSelectClass(gid, e.target.value)}
                                >
                                  <option value="">— Select manual class —</option>
                                  <option value="IfcWall">IfcWall</option>
                                  <option value="IfcDoor">IfcDoor</option>
                                  <option value="IfcWindow">IfcWindow</option>
                                  <option value="IfcSlab">IfcSlab</option>
                                  <option value="IfcColumn">IfcColumn</option>
                                  <option value="IfcBeam">IfcBeam</option>
                                  <option value="IfcRoof">IfcRoof</option>
                                  <option value="IfcStair">IfcStair</option>
                                  <option value="IfcFlowTerminal">IfcFlowTerminal</option>
                                </select>
                              )}
                            </div>
                          )}
                        </div>

                        <div style={{ textAlign: "right" }}>
                          {isApplied ? (
                            <button 
                              className="btn-secondary" 
                              onClick={() => handleRemoveSingleProxy(gid)}
                              style={{ padding: "6px 12px", fontSize: "12px", borderColor: "#ff6b6b55", color: "#ff6b6b" }}
                            >
                              🗑️ Remove
                            </button>
                          ) : isRemoved ? (
                            <button 
                              className="btn-secondary" 
                              onClick={() => handleUndoRemoveProxy(gid)}
                              style={{ padding: "6px 12px", fontSize: "12px" }}
                            >
                              Undo
                            </button>
                          ) : (
                            <button 
                              className="btn-secondary" 
                              onClick={() => handleApplySingleProxy(gid, bestSug.class)}
                              style={{ padding: "6px 12px", fontSize: "12px", borderColor: "#7ee78755", color: "#7ee787" }}
                            >
                              ✔ Apply
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Pset Addition */}
            {activeEngineTab === "Pset" && (
              <div>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "14px" }}>
                  11 elements are missing a Pset. Select the correct IFC class for each element — the required Pset will be shown automatically.
                </p>

                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center", marginBottom: "20px" }}>
                  <button className="btn-primary" onClick={handleApplyAllPsets} style={{ background: "#7f5af0", borderColor: "#7f5af0", color: "#fff", padding: "8px 20px", fontWeight: "700" }}>
                    📦 Apply All Pset Fixes
                  </button>
                  <button className="btn-secondary" onClick={handleRemoveAllPsets} style={{ padding: "8px 20px", color: "#ff6b6b", borderColor: "#ff6b6b33" }}>
                    🗑 Remove All Pset Fixes
                  </button>
                </div>

                {/* Applied success banner */}
                {psetFixes.length > 0 && (
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
                    <span>✔</span>
                    <strong>{psetFixes.length} Pset fixes applied — click Validate Now to preview, then Download.</strong>
                  </div>
                )}

                {/* Elements List */}
                <div style={{ display: "flex", flexDirection: "column", gap: "16px", maxHeight: "400px", overflowY: "auto" }}>
                  {psetItems.map((item, idx) => {
                    const gid = item.GlobalId;
                    const isApplied = psetFixes.includes(gid);
                    
                    const cardBg = isApplied ? "rgba(35,134,54,0.03)" : "rgba(255,255,255,0.01)";
                    const cardBorder = isApplied ? "rgba(35,134,54,0.25)" : "var(--border-color)";

                    return (
                      <div key={idx} style={{ 
                        background: cardBg, 
                        border: `1.5px solid ${cardBorder}`, 
                        padding: "18px", 
                        borderRadius: "10px"
                      }}>
                        {/* Header row */}
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", borderBottom: "1px solid rgba(255,255,255,0.04)", paddingBottom: "10px" }}>
                          <div>
                            <strong style={{ fontSize: "14px", color: "#fff" }}>{item.ElementName}</strong>
                            <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px", fontFamily: "Space Mono" }}>{gid}</div>
                          </div>
                          <button 
                            className="btn-secondary" 
                            onClick={() => isApplied ? handleRemovePset(gid) : handleApplyPset(gid, item)} 
                            style={{ padding: "6px 14px", fontSize: "12px", borderColor: isApplied ? "#ff6b6b55" : "#7ee78755", color: isApplied ? "#ff6b6b" : "#7ee787" }}
                          >
                            {isApplied ? "🗑️ Remove" : "Apply"}
                          </button>
                        </div>

                        {/* Dropdown selectors row */}
                        <div style={{ display: "flex", gap: "20px", flexWrap: "wrap" }}>
                          <div style={{ flex: 1, minWidth: "200px" }}>
                            <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>IFC Class</label>
                            <select 
                              className="form-select" 
                              style={{ width: "100%", padding: "8px" }}
                              value={psetFixSelections[gid]?.IFCType || item.CurrentType}
                              onChange={(e) => {
                                const newType = e.target.value;
                                let reqPset = "Pset_WallCommon";
                                if (newType === "IfcDoor") reqPset = "Pset_DoorCommon";
                                else if (newType === "IfcWindow") reqPset = "Pset_WindowCommon";
                                else if (newType === "IfcSlab") reqPset = "Pset_SlabCommon";
                                else if (newType === "IfcColumn") reqPset = "Pset_ColumnCommon";
                                else if (newType === "IfcBeam") reqPset = "Pset_BeamCommon";
                                else if (newType === "IfcRoof") reqPset = "Pset_RoofCommon";
                                
                                setPsetFixSelections(prev => ({
                                  ...prev,
                                  [gid]: { PsetName: reqPset, IFCType: newType }
                                }));
                                if (!psetFixes.includes(gid)) {
                                  setPsetFixes(prev => [...prev, gid]);
                                }
                              }}
                            >
                              <option value="IfcWall">IfcWall</option>
                              <option value="IfcDoor">IfcDoor</option>
                              <option value="IfcWindow">IfcWindow</option>
                              <option value="IfcSlab">IfcSlab</option>
                              <option value="IfcColumn">IfcColumn</option>
                              <option value="IfcBeam">IfcBeam</option>
                              <option value="IfcRoof">IfcRoof</option>
                              <option value="IfcStair">IfcStair</option>
                              <option value="IfcRailing">IfcRailing</option>
                              <option value="IfcPipeSegment">IfcPipeSegment</option>
                              <option value="IfcFlowTerminal">IfcFlowTerminal</option>
                            </select>
                          </div>

                          <div style={{ flex: 1, minWidth: "200px" }}>
                            <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>Required Pset</label>
                            <div style={{ 
                              background: "rgba(210,153,34,0.1)", 
                              border: "1px solid rgba(210,153,34,0.3)", 
                              borderRadius: "6px", 
                              padding: "8px 14px", 
                              color: "#ffb347",
                              fontSize: "13px",
                              display: "flex",
                              alignItems: "center",
                              gap: "8px",
                              height: "38px",
                              boxSizing: "border-box"
                            }}>
                              <span>📦</span>
                              <strong>{psetFixSelections[gid]?.PsetName || item.req_pset}</strong>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Quantity Loss */}
            {activeEngineTab === "Qty" && (
              <div>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "14px" }}>
                  Quantity data (area, volume, weight) is missing. Ensure your authoring tool (Revit / ArchiCAD) exports Base Quantities.
                </p>
                <div className="data-table-container" style={{ margin: 0, maxHeight: "300px", overflowY: "auto" }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Element Name</th>
                        <th>IFC Type</th>
                        <th>Issue</th>
                        <th>Fix Instruction</th>
                      </tr>
                    </thead>
                    <tbody>
                      {qtyItems.map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: "700" }}>{item.ElementName}</td>
                          <td><code>{item.CurrentType}</code></td>
                          <td style={{ color: "#ffb347" }}>{item.Issue}</td>
                          <td><span style={{ color: "#00bcd4" }}>{item.Action}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Relationship Loss */}
            {activeEngineTab === "Rel" && (
              <div>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "14px" }}>
                  Topology containment matches are broken or missing.
                </p>
                <div className="data-table-container" style={{ margin: 0, maxHeight: "300px", overflowY: "auto" }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Element Name</th>
                        <th>IFC Type</th>
                        <th>Issue</th>
                        <th>Fix Instruction</th>
                      </tr>
                    </thead>
                    <tbody>
                      {relItems.map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: "700" }}>{item.ElementName}</td>
                          <td><code>{item.CurrentType}</code></td>
                          <td style={{ color: "#ff6b6b" }}>{item.Issue}</td>
                          <td><span style={{ color: "#58a6ff" }}>{item.Action}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Validate Now Button and Score Preview */}
          <div style={{ marginTop: "30px", display: "flex", flexDirection: "column", gap: "20px" }}>
            <button 
              onClick={handleValidatePreview} 
              disabled={validating || (appliedFixes.length === 0 && psetFixes.length === 0)}
              style={{ 
                background: "rgba(127, 90, 240, 0.08)", 
                border: "1.5px solid #7f5af0", 
                borderRadius: "8px", 
                color: "#fff", 
                padding: "14px", 
                width: "100%", 
                cursor: "pointer", 
                display: "flex", 
                alignItems: "center", 
                justifyContent: "center", 
                gap: "8px", 
                fontSize: "14px",
                fontWeight: "700",
                transition: "all 0.2s"
              }}
            >
              🔍 {validating ? "Validating & Recalculating..." : "Validate Now — Preview Improved Score"}
            </button>

            {previewData && (
              <div style={{ 
                background: "rgba(16,22,42,0.4)", 
                border: "1px solid var(--border-color)", 
                borderRadius: "12px", 
                padding: "20px" 
              }}>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)", letterSpacing: "1px", fontWeight: "700", textTransform: "uppercase", marginBottom: "16px" }}>
                  SCORE PREVIEW — BEFORE VS AFTER CORRECTION
                </div>
                
                <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr 1.2fr", gap: "20px", alignItems: "center", marginBottom: "20px" }}>
                  {/* BEFORE */}
                  <div style={{ border: "1.5px solid #238636", borderRadius: "8px", padding: "16px", textAlign: "center", background: "rgba(35,134,54,0.02)" }}>
                    <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "1px", fontWeight: "700" }}>BEFORE</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#e6edf3", margin: "8px 0 4px" }}>
                      {previewData.original_score.toFixed(1)}
                    </div>
                    <div style={{ fontSize: "12px", color: "#7ee787", fontWeight: "600" }}>
                      Excellent
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "4px" }}>
                      {proxyItems.length} proxies
                    </div>
                  </div>

                  {/* ARROW */}
                  <div style={{ fontSize: "20px", color: "var(--text-secondary)", fontWeight: "bold" }}>→</div>

                  {/* AFTER */}
                  <div style={{ border: "1.5px solid #238636", borderRadius: "8px", padding: "16px", textAlign: "center", background: "rgba(35,134,54,0.02)" }}>
                    <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "1px", fontWeight: "700" }}>AFTER</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#e6edf3", margin: "8px 0 4px" }}>
                      {previewData.improved_score.toFixed(1)}
                    </div>
                    <div style={{ fontSize: "12px", color: "#7ee787", fontWeight: "600" }}>
                      Excellent
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "4px" }}>
                      {Math.max(0, proxyItems.length - appliedFixes.length)} proxies remaining
                    </div>
                  </div>

                  {/* IMPROVEMENT */}
                  <div style={{ border: "1.5px solid #238636", borderRadius: "8px", padding: "16px", textAlign: "center", background: "rgba(35,134,54,0.02)" }}>
                    <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "1px", fontWeight: "700" }}>IMPROVEMENT</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#7ee787", margin: "8px 0 4px" }}>
                      +{Math.max(0, previewData.improved_score - previewData.original_score).toFixed(1)}
                    </div>
                    <div style={{ fontSize: "12px", color: "#7ee787", fontWeight: "600" }}>points gained</div>
                    <div style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "4px", lineHeight: "1.4" }}>
                      {appliedFixes.length} proxy fixes · 0 with Psets · 0 with Materials · {psetFixes.length} standalone Pset fixes
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: "12px", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "6px", borderTop: "1px solid var(--border-color)", paddingTop: "14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ color: "#7ee787" }}>✔</span>
                    <span>Preserved: GlobalId · ObjectPlacement · Representation · IfcRelContainedInSpatialStructure (storey) · IfcRelConnectsElements · IfcRelFillsElement</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ color: "#7ee787" }}>✔</span>
                    <span>Added: IfcRelDefinesByProperties (Pset) · IfcRelAssociatesMaterial (Material)</span>
                  </div>
                </div>
              </div>
            )}

            {/* Pset fixes queued banner */}
            {psetFixes.length > 0 && (
              <div style={{ 
                background: "rgba(35, 134, 255, 0.05)", 
                border: "1.5px solid rgba(35, 134, 255, 0.25)", 
                borderRadius: "8px", 
                padding: "14px 18px", 
                fontSize: "13px", 
                color: "#58a6ff", 
                display: "flex", 
                alignItems: "center", 
                gap: "10px"
              }}>
                <span>📦</span>
                <span>{psetFixes.length} Pset fixes queued — included in Validate preview and injected into the corrected IFC on download.</span>
              </div>
            )}

            {/* Generate & Download button */}
            <button 
              className="btn-primary" 
              onClick={handleDownloadCorrected} 
              disabled={applying || (appliedFixes.length === 0 && psetFixes.length === 0)}
              style={{ 
                width: "100%", 
                padding: "16px", 
                fontSize: "15px", 
                fontWeight: "800", 
                display: "flex", 
                alignItems: "center", 
                justifyContent: "center", 
                gap: "10px",
                background: "rgba(127, 90, 240, 0.15)",
                border: "1.5px solid #7f5af0",
                color: "#fff",
                borderRadius: "8px",
                cursor: "pointer"
              }}
            >
              📥 {applying ? "Compiling & Packing..." : "Generate & Download Corrected IFC"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
