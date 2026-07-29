import React, { useState } from "react";
import { API_BASE_URL } from "../config";

const BUILTIN_RULES = [
  { id: "NM01", name: "Elements must have a Name", category: "Naming", severity: "High", description: "Every physical element must have a non-empty Name attribute.", applies_to: "" },
  { id: "NM02", name: "No 'Unnamed' placeholders", category: "Naming", severity: "Medium", description: "Element names must not contain 'Unnamed', 'Unknown' or 'Generic'.", applies_to: "" },
  { id: "NM03", name: "GlobalId must be unique", category: "Naming", severity: "Critical", description: "Every element's GlobalId must be unique within the model.", applies_to: "" },
  { id: "CL01", name: "No IfcBuildingElementProxy", category: "Classification", severity: "High", description: "Generic proxies indicate lost semantic meaning. All elements should have a specific IFC type.", applies_to: "IfcBuildingElementProxy" },
  { id: "CL02", name: "Elements must be typed", category: "Classification", severity: "Medium", description: "Physical elements should reference an IfcElementType for consistent properties.", applies_to: "" },
  { id: "PS01", name: "Walls must have Pset_WallCommon", category: "Property Sets", severity: "High", description: "All IfcWall elements must include Pset_WallCommon with fire rating, load bearing status etc.", applies_to: "IfcWall" },
  { id: "PS02", name: "Doors must have Pset_DoorCommon", category: "Property Sets", severity: "High", description: "All IfcDoor elements must include Pset_DoorCommon.", applies_to: "IfcDoor" },
  { id: "PS03", name: "Windows must have Pset_WindowCommon", category: "Property Sets", severity: "High", description: "All IfcWindow elements must include Pset_WindowCommon.", applies_to: "IfcWindow" },
  { id: "PS04", name: "Slabs must have Pset_SlabCommon", category: "Property Sets", severity: "Medium", description: "All IfcSlab elements must include Pset_SlabCommon.", applies_to: "IfcSlab" },
  { id: "PS05", name: "Walls: IsExternal must be defined", category: "Property Sets", severity: "Medium", description: "Pset_WallCommon.IsExternal must be explicitly set (True or False).", applies_to: "IfcWall" },
  { id: "PS06", name: "Walls: FireRating must be defined", category: "Property Sets", severity: "High", description: "Pset_WallCommon.FireRating must be explicitly set for fire safety compliance.", applies_to: "IfcWall" },
  { id: "PS07", name: "Columns must have Pset_ColumnCommon", category: "Property Sets", severity: "Medium", description: "All IfcColumn elements must include Pset_ColumnCommon.", applies_to: "IfcColumn" },
  { id: "GM01", name: "Elements must have placement", category: "Geometry", severity: "High", description: "Every physical element must have an ObjectPlacement defined.", applies_to: "" },
  { id: "GM02", name: "Elements must have geometry", category: "Geometry", severity: "High", description: "Every physical element must have a Representation (geometry).", applies_to: "" },
  { id: "MT01", name: "Elements must have material assigned", category: "Materials", severity: "Medium", description: "Every physical element should have at least one material association.", applies_to: "" },
  { id: "IC01", name: "No deprecated IfcWallStandardCase", category: "IFC Compliance", severity: "Low", description: "IfcWallStandardCase is deprecated in IFC4. Use IfcWall instead.", applies_to: "IfcWallStandardCase" },
  { id: "IC02", name: "Elements must belong to a storey", category: "IFC Compliance", severity: "Medium", description: "Every physical element should be contained in an IfcBuildingStorey.", applies_to: "" },
];

const CATEGORIES = ["Naming", "Classification", "Property Sets", "Geometry", "Materials", "IFC Compliance"];

export default function ValidationCompliance({ analysis }) {
  const [activeTab, setActiveTab] = useState("Rules"); // Rules, NBC
  const [activeSubTab, setActiveSubTab] = useState("Library"); // Library, Custom, Results, Report

  // Rule selection states
  const [selectedBuiltinIds, setSelectedBuiltinIds] = useState(
    new Set(BUILTIN_RULES.map(r => r.id))
  );
  
  // Custom rules states
  const [customRules, setCustomRules] = useState([]);
  const [selectedCustomIds, setSelectedCustomIds] = useState(new Set());
  
  // Custom Rule Form states
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formSeverity, setFormSeverity] = useState("Medium");
  const [formCategory, setFormCategory] = useState("Naming");
  const [formApplies, setFormApplies] = useState("All Elements");
  const [formPset, setFormPset] = useState("");
  const [formProp, setFormProp] = useState("");
  const [formValue, setFormValue] = useState("");

  // Accordion toggle states
  const [expandedCats, setExpandedCats] = useState(
    CATEGORIES.reduce((acc, cat) => ({ ...acc, [cat]: true }), {})
  );

  // Validation execution states
  const [runningValidation, setRunningValidation] = useState(false);
  const [validationResults, setValidationResults] = useState(null);
  const [validationError, setValidationError] = useState("");

  // Result filters states
  const [filterCat, setFilterCat] = useState("All");
  const [filterSev, setFilterSev] = useState("All");
  const [filterType, setFilterType] = useState("All");
  const [filterSearch, setFilterSearch] = useState("");

  // NBC UI states
  const [expandedNbcIndex, setExpandedNbcIndex] = useState(null);

  if (!analysis) {
    return (
      <div style={{ padding: "40px", textAlign: "center", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px" }}>
        <h3>⚠️ No analysis data available</h3>
        <p style={{ color: "var(--text-secondary)", marginTop: "8px" }}>Please upload an IFC file on the Home page first.</p>
      </div>
    );
  }

  // --- built-in toggles helpers ---
  const handleToggleBuiltin = (id) => {
    const next = new Set(selectedBuiltinIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedBuiltinIds(next);
  };

  const handleSelectAllBuiltin = () => {
    setSelectedBuiltinIds(new Set(BUILTIN_RULES.map(r => r.id)));
  };

  const handleClearAllBuiltin = () => {
    setSelectedBuiltinIds(new Set());
  };

  // --- custom rules helpers ---
  const handleAddCustomRule = (e) => {
    e.preventDefault();
    if (!formName || !formDesc) return;

    const newId = `CR${(customRules.length + 1).toString().padStart(2, "0")}`;
    const newRule = {
      id: newId,
      name: formName,
      description: formDesc,
      severity: formSeverity,
      category: formCategory,
      applies_to: formApplies === "All Elements" ? null : formApplies,
      pset: formPset || null,
      prop: formProp || null,
      value: formValue || null,
      custom: true,
    };

    setCustomRules([...customRules, newRule]);
    const nextCustomIds = new Set(selectedCustomIds);
    nextCustomIds.add(newId);
    setSelectedCustomIds(nextCustomIds);

    // reset fields
    setFormName("");
    setFormDesc("");
    setFormSeverity("Medium");
    setFormCategory("Naming");
    setFormApplies("All Elements");
    setFormPset("");
    setFormProp("");
    setFormValue("");
  };

  const handleToggleCustom = (id) => {
    const next = new Set(selectedCustomIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedCustomIds(next);
  };

  const handleDeleteCustomRule = (idx, id) => {
    const nextRules = [...customRules];
    nextRules.splice(idx, 1);
    setCustomRules(nextRules);

    const nextCustomIds = new Set(selectedCustomIds);
    nextCustomIds.delete(id);
    setSelectedCustomIds(nextCustomIds);
  };

  // --- run validation ---
  const handleRunValidation = async () => {
    setRunningValidation(true);
    setValidationError("");
    
    // Prepare active custom rules payload
    const activeCustomRules = customRules.filter(r => selectedCustomIds.has(r.id));
    const activeBuiltinIds = Array.from(selectedBuiltinIds);

    try {
      const res = await fetch(`${API_BASE_URL}/api/rules/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          selected_builtin_rule_ids: activeBuiltinIds,
          custom_rules: activeCustomRules
        })
      });

      if (!res.ok) {
        throw new Error("Failed to run compliance checks.");
      }

      const data = await res.json();
      setValidationResults(data);
      setActiveSubTab("Results");
    } catch (err) {
      setValidationError(err.message || "Something went wrong.");
    } finally {
      setRunningValidation(false);
    }
  };

  // --- download report pdf ---
  const handleDownloadPDF = async () => {
    const activeCustomRules = customRules.filter(r => selectedCustomIds.has(r.id));
    const activeBuiltinIds = Array.from(selectedBuiltinIds);

    try {
      const res = await fetch(`${API_BASE_URL}/api/rules/pdf-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          selected_builtin_rule_ids: activeBuiltinIds,
          custom_rules: activeCustomRules
        })
      });

      if (!res.ok) throw new Error("Could not compile report PDF.");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "IFC_Validation_Report.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      alert("Error exporting PDF: " + err.message);
    }
  };

  // --- export CSV ---
  const handleDownloadCSV = (filteredRows) => {
    if (!filteredRows || filteredRows.length === 0) return;
    
    const headers = ["Rule ID", "Severity", "Category", "Rule", "Element", "IFC Type", "Message"];
    const csvRows = [headers.join(",")];

    filteredRows.forEach(row => {
      const values = [
        row["Rule ID"],
        row.Severity,
        row.Category,
        `"${row.Rule.replace(/"/g, '""')}"`,
        `"${row.Element.replace(/"/g, '""')}"`,
        row["IFC Type"],
        `"${row.Message.replace(/"/g, '""')}"`
      ];
      csvRows.push(values.join(","));
    });

    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "IFC_Validation_Results.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  // --- dynamic calculations of results stats ---
  let totalChecks = 0;
  let passCount = 0;
  let failCount = 0;
  let passPct = 0;
  let healthScore = 0;
  let healthColor = "#238636";
  let healthGrade = "Excellent";
  let failures = [];
  let filteredFailures = [];

  let criticalCount = 0;
  let highCount = 0;
  let mediumCount = 0;
  let lowCount = 0;

  if (validationResults) {
    passCount = validationResults.pass_count || 0;
    failCount = validationResults.fail_count || 0;
    totalChecks = validationResults.total_checks || 0;
    failures = validationResults.results || [];

    passPct = totalChecks ? ((passCount / totalChecks) * 100).toFixed(1) : 100;
    healthScore = Math.round(Number(passPct));

    if (healthScore >= 90) { healthColor = "#238636"; healthGrade = "Excellent"; }
    else if (healthScore >= 70) { healthColor = "#d29922"; healthGrade = "Good"; }
    else { healthColor = "#da3633"; healthGrade = "Poor"; }

    criticalCount = failures.filter(f => f.Severity === "Critical").length;
    highCount = failures.filter(f => f.Severity === "High").length;
    mediumCount = failures.filter(f => f.Severity === "Medium").length;
    lowCount = failures.filter(f => f.Severity === "Low").length;

    // Filter validation results table
    filteredFailures = failures.filter(row => {
      const matchCat = filterCat === "All" || row.Category === filterCat;
      const matchSev = filterSev === "All" || row.Severity === filterSev;
      const matchType = filterType === "All" || row["IFC Type"] === filterType;
      
      const searchStr = filterSearch.toLowerCase();
      const matchText = !filterSearch || 
        (row.Element || "").toLowerCase().includes(searchStr) || 
        (row.Message || "").toLowerCase().includes(searchStr);

      return matchCat && matchSev && matchType && matchText;
    });
  }

  // --- NBC Compliance Calcs ---
  const nbcResults = analysis.nbc_results || [];
  const nbcOverall = analysis.nbc_overall_score || 0;
  const nbcTotal = nbcResults.length;
  const nbcPassed = nbcResults.filter(r => r.status === "Pass").length;
  const nbcFailed = nbcResults.filter(r => r.status === "Fail").length;

  let nbcColor = "#238636";
  let nbcVerdict = "Fully Compliant";
  let nbcSubtext = "This model meets NBC 2016 standards.";

  if (nbcOverall < 60) {
    nbcColor = "#da3633";
    nbcVerdict = "Non-Compliant";
    nbcSubtext = "This model has critical non-compliance issues. Review failed checks.";
  } else if (nbcOverall < 90) {
    nbcColor = "#d29922";
    nbcVerdict = "Largely Compliant";
    nbcSubtext = "This model partially meets NBC 2016. Fix the failed checks before submission.";
  }

  return (
    <div>
      <div className="title-group">
        <h1 className="page-title">✅ Validation & Compliance</h1>
        <p className="page-caption">Validate the model against semantic standard rules and National Building Code guidelines.</p>
      </div>

      {/* Main Tabs */}
      <div className="tabs-header" style={{ marginBottom: "28px" }}>
        <button className={`tab-btn ${activeTab === "Rules" ? "active" : ""}`} onClick={() => setActiveTab("Rules")}>📋 Rule Validation</button>
        <button className={`tab-btn ${activeTab === "NBC" ? "active" : ""}`} onClick={() => setActiveTab("NBC")}>🏛️ NBC Compliance</button>
      </div>

      {/* T1: RULE VALIDATION SECTION */}
      {activeTab === "Rules" && (
        <div>
          {/* Sub Navigation */}
          <div style={{ display: "flex", gap: "12px", background: "rgba(16,22,42,0.4)", border: "1px solid var(--border-color)", borderRadius: "8px", padding: "6px", marginBottom: "24px", width: "fit-content" }}>
            <button className={`tab-btn ${activeSubTab === "Library" ? "active" : ""}`} onClick={() => setActiveSubTab("Library")} style={{ fontSize: "12px", padding: "6px 14px" }}>📋 Rule Library</button>
            <button className={`tab-btn ${activeSubTab === "Custom" ? "active" : ""}`} onClick={() => setActiveSubTab("Custom")} style={{ fontSize: "12px", padding: "6px 14px" }}>✏️ Custom Rules</button>
            <button className={`tab-btn ${activeSubTab === "Results" ? "active" : ""}`} onClick={() => setActiveSubTab("Results")} style={{ fontSize: "12px", padding: "6px 14px" }}>✅ Validation Results</button>
            <button className={`tab-btn ${activeSubTab === "Report" ? "active" : ""}`} onClick={() => setActiveSubTab("Report")} style={{ fontSize: "12px", padding: "6px 14px" }}>📄 Export Report</button>
          </div>

          {/* SUBTAB 1: RULE LIBRARY ACCORDION */}
          {activeSubTab === "Library" && (
            <div>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "20px" }}>
                {BUILTIN_RULES.length} built-in rules across {CATEGORIES.length} categories.
              </p>

              <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px", marginBottom: "20px" }}>
                <h4 style={{ fontSize: "15px", fontWeight: "700", marginBottom: "14px" }}>🎛️ Select Built-in Rules To Validate</h4>
                
                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center", marginBottom: "14px" }}>
                  <button className="btn-secondary" onClick={handleSelectAllBuiltin} style={{ padding: "6px 14px", fontSize: "12px" }}>✅ Select All</button>
                  <button className="btn-secondary" onClick={handleClearAllBuiltin} style={{ padding: "6px 14px", fontSize: "12px" }}>🧹 Clear All</button>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)", marginLeft: "10px" }}>Tip: Toggle Use inside each rule card below.</span>
                </div>

                <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "24px" }}>
                  Selected <strong>{selectedBuiltinIds.size}</strong> of <strong>{BUILTIN_RULES.length}</strong> built-in rules | Showing all rules grouped by category
                </div>

                {/* Collapsible categories accordion */}
                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  {CATEGORIES.map(cat => {
                    const catRules = BUILTIN_RULES.filter(r => r.category === cat);
                    const isExpanded = !!expandedCats[cat];
                    return (
                      <div key={cat} style={{ border: "1px solid rgba(255,255,255,0.06)", borderRadius: "8px", background: "rgba(0,0,0,0.15)", overflow: "hidden" }}>
                        <div 
                          onClick={() => setExpandedCats({ ...expandedCats, [cat]: !isExpanded })}
                          style={{ padding: "14px 18px", background: "rgba(255,255,255,0.03)", display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", userSelect: "none" }}
                        >
                          <span style={{ fontWeight: "700", fontSize: "14px" }}>{cat} — {catRules.length} rules</span>
                          <span>{isExpanded ? "▲" : "▼"}</span>
                        </div>

                        {isExpanded && (
                          <div style={{ padding: "14px", display: "flex", flexDirection: "column", gap: "10px" }}>
                            {catRules.map(rule => {
                              const isChecked = selectedBuiltinIds.has(rule.id);
                              const sevColors = { Critical: "#da3633", High: "#d29922", Medium: "#58a6ff", Low: "#238636" };
                              const col = sevColors[rule.severity] || "var(--text-secondary)";
                              return (
                                <div key={rule.id} style={{ display: "flex", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "8px", padding: "14px", justifyContent: "space-between", alignItems: "center", gap: "16px" }}>
                                  <div style={{ flex: 1 }}>
                                    <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "4px" }}>
                                      <code style={{ background: "rgba(0,0,0,0.4)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontSize: "11px", fontWeight: "700" }}>{rule.id}</code>
                                      <span style={{ fontWeight: "700", fontSize: "13px", color: "#fff" }}>{rule.name}</span>
                                    </div>
                                    <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "4px" }}>{rule.description}</p>
                                    <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>Applies to: {rule.applies_to ? <code>{rule.applies_to}</code> : "All elements"}</span>
                                  </div>
                                  
                                  <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                                    <span style={{ 
                                      fontSize: "10px", 
                                      fontWeight: "700", 
                                      color: col, 
                                      background: `${col}18`, 
                                      padding: "3px 10px", 
                                      borderRadius: "10px",
                                      border: `1.5px solid ${col}44`
                                    }}>{rule.severity}</span>
                                    
                                    <input 
                                      type="checkbox" 
                                      checked={isChecked} 
                                      onChange={() => handleToggleBuiltin(rule.id)}
                                      style={{ width: "18px", height: "18px", cursor: "pointer" }}
                                    />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* SUBTAB 2: CUSTOM RULES FORM */}
          {activeSubTab === "Custom" && (
            <div>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "20px" }}>
                Define your own project-specific rules. Custom rules are combined with built-in rules during validation.
              </p>

              <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "24px", marginBottom: "24px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "18px" }}>➕ Add Custom Validation Rule</h3>
                
                <form onSubmit={handleAddCustomRule} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                  <div style={{ gridColumn: "span 2" }}>
                    <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>Rule Name *</label>
                    <input type="text" className="form-input" value={formName} onChange={e => setFormName(e.target.value)} placeholder="e.g. External walls must have U-value defined" style={{ width: "100%" }} required />
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>Description *</label>
                    <input type="text" className="form-input" value={formDesc} onChange={e => setFormDesc(e.target.value)} placeholder="Explain the check objective" style={{ width: "100%" }} required />
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>Severity</label>
                    <select className="form-select" value={formSeverity} onChange={e => setFormSeverity(e.target.value)} style={{ width: "100%" }}>
                      <option value="Critical">Critical</option>
                      <option value="High">High</option>
                      <option value="Medium">Medium</option>
                      <option value="Low">Low</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>Category</label>
                    <select className="form-select" value={formCategory} onChange={e => setFormCategory(e.target.value)} style={{ width: "100%" }}>
                      {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                      <option value="Custom">Custom</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>Applies to (IFC Type)</label>
                    <select className="form-select" value={formApplies} onChange={e => setFormApplies(e.target.value)} style={{ width: "100%" }}>
                      <option value="All Elements">All Elements</option>
                      <option value="IfcWall">IfcWall</option>
                      <option value="IfcDoor">IfcDoor</option>
                      <option value="IfcWindow">IfcWindow</option>
                      <option value="IfcSlab">IfcSlab</option>
                      <option value="IfcColumn">IfcColumn</option>
                      <option value="IfcBeam">IfcBeam</option>
                      <option value="IfcStair">IfcStair</option>
                      <option value="IfcRoof">IfcRoof</option>
                      <option value="IfcBuildingElementProxy">IfcBuildingElementProxy</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>Required Property Set (Pset) Name</label>
                    <input type="text" className="form-input" value={formPset} onChange={e => setFormPset(e.target.value)} placeholder="e.g. Pset_WallCommon" style={{ width: "100%" }} />
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>Required Property Name</label>
                    <input type="text" className="form-input" value={formProp} onChange={e => setFormProp(e.target.value)} placeholder="e.g. ThermalTransmittance" style={{ width: "100%" }} />
                  </div>

                  <div style={{ gridColumn: "span 2" }}>
                    <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>Expected Value (optional comparison: e.g. `&lt;= 0.3`, `&gt;= 1.5`, `= True` or `True` )</label>
                    <input type="text" className="form-input" value={formValue} onChange={e => setFormValue(e.target.value)} placeholder="e.g. <= 0.3" style={{ width: "100%" }} />
                  </div>

                  <button type="submit" className="btn-primary" style={{ gridColumn: "span 2", padding: "12px" }}>
                    ➕ Add Custom Rule
                  </button>
                </form>
              </div>

              {/* List of custom rules */}
              {customRules.length > 0 ? (
                <div>
                  <h4 style={{ fontSize: "14px", fontWeight: "700", marginBottom: "12px" }}>{customRules.length} Custom Rules Added</h4>
                  
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {customRules.map((rule, idx) => {
                      const isChecked = selectedCustomIds.has(rule.id);
                      return (
                        <div key={rule.id} style={{ display: "flex", background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-color)", borderRadius: "8px", padding: "14px 18px", alignItems: "center", justifyContent: "space-between", gap: "14px" }}>
                          <div style={{ display: "flex", gap: "14px", alignItems: "center" }}>
                            <input 
                              type="checkbox" 
                              checked={isChecked} 
                              onChange={() => handleToggleCustom(rule.id)}
                              style={{ width: "16px", height: "16px", cursor: "pointer" }}
                            />
                            
                            <div>
                              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                                <code style={{ color: "#8ee8ff", background: "#0B1E3D", padding: "2px 6px", borderRadius: "4px", fontSize: "11px" }}>{rule.id}</code>
                                <strong style={{ color: "#fff", fontSize: "13px" }}>{rule.name}</strong>
                                <span style={{ fontSize: "10px", background: "rgba(255,255,255,0.06)", padding: "1px 6px", borderRadius: "4px", color: "var(--text-secondary)" }}>{rule.category}</span>
                              </div>
                              <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "4px" }}>{rule.description}</p>
                              {rule.pset && (
                                <div style={{ color: "var(--text-muted)", fontSize: "10px", marginTop: "2px" }}>
                                  Requires: <code>{rule.pset}.{rule.prop}</code> {rule.value ? `(${rule.value})` : ""}
                                </div>
                              )}
                            </div>
                          </div>

                          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                            <span style={{ fontSize: "9px", background: "rgba(210,153,34,0.15)", color: "#ffb347", border: "1.5px solid rgba(210,153,34,0.3)", borderRadius: "10px", padding: "2px 8px", fontWeight: "700" }}>{rule.severity}</span>
                            <button className="btn-secondary" onClick={() => handleDeleteCustomRule(idx, rule.id)} style={{ padding: "4px 8px", color: "#ff6b6b", borderColor: "#ff6b6b33", fontSize: "12px" }}>🗑</button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div style={{ padding: "30px", background: "rgba(255,255,255,0.02)", border: "1px dashed var(--border-color)", borderRadius: "10px", textAlign: "center", color: "var(--text-secondary)" }}>
                  No custom rules defined yet. Use the form above to add custom compliance rules.
                </div>
              )}
            </div>
          )}

          {/* SUBTAB 3: VALIDATION RESULTS */}
          {activeSubTab === "Results" && (
            <div>
              <div style={{ display: "flex", gap: "20px", alignItems: "center", marginBottom: "24px" }}>
                <button className="btn-primary" onClick={handleRunValidation} disabled={runningValidation} style={{ padding: "12px 28px" }}>
                  {runningValidation ? "🔍 Checking Elements..." : "▶ Run Validation Now"}
                </button>
                <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  <strong>{selectedBuiltinIds.size + selectedCustomIds.size} rules</strong> will be checked against the model.
                </span>
              </div>

              {validationError && (
                <div style={{ padding: "12px", background: "var(--color-danger-bg)", border: "1px solid rgba(218,54,51,0.2)", color: "#ff6b6b", borderRadius: "6px", marginBottom: "20px", fontSize: "13px" }}>
                  ⚠️ {validationError}
                </div>
              )}

              {validationResults ? (
                <div>
                  <h3 style={{ fontSize: "18px", fontWeight: "800", marginBottom: "14px" }}>📊 Validation Summary</h3>
                  
                  {/* Summary Metric Cards Row */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "24px" }}>
                    <div className="metric-card">
                      <div className="metric-label">Total Checks</div>
                      <div className="metric-value">{totalChecks}</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">✔ Passed</div>
                      <div className="metric-value" style={{ color: "#7ee787" }}>
                        {passCount}
                      </div>
                      <div style={{ color: "#7ee787", fontSize: "11px", fontWeight: "700" }}>{passPct}% Rate</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">✘ Failed</div>
                      <div className="metric-value" style={{ color: "#ff6b6b" }}>
                        {failCount}
                      </div>
                      <div style={{ color: "#ff6b6b", fontSize: "11px", fontWeight: "700" }}>-{totalChecks ? (100 - passPct).toFixed(1) : 0}% Rate</div>
                    </div>

                    <div style={{ 
                      background: `rgba(${healthColor === "#238636" ? "35,134,54" : healthColor === "#da3633" ? "218,54,51" : "210,153,34"}, 0.08)`,
                      border: `1.5px solid ${healthColor}`, 
                      borderRadius: "12px", 
                      padding: "16px", 
                      textAlign: "center" 
                    }}>
                      <div style={{ color: "var(--text-secondary)", fontSize: "12px", textTransform: "uppercase" }}>Health Score</div>
                      <div style={{ fontSize: "28px", fontWeight: "900", color: healthColor, marginTop: "4px" }}>
                        {healthScore}%
                      </div>
                      <div style={{ fontSize: "10px", color: healthColor, fontWeight: "700" }}>{healthGrade}</div>
                    </div>
                  </div>

                  {/* Failure Severity Counts Row */}
                  <h4 style={{ fontSize: "14px", fontWeight: "700", marginBottom: "10px" }}>Failures by Severity</h4>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px", marginBottom: "24px" }}>
                    {[
                      { name: "🔴 Critical", count: criticalCount, col: "#da3633" },
                      { name: "🟠 High", count: highCount, col: "#d29922" },
                      { name: "🟡 Medium", count: mediumCount, col: "#58a6ff" },
                      { name: "🔵 Low", count: lowCount, col: "#238636" }
                    ].map(sev => (
                      <div key={sev.name} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "8px", padding: "12px", textAlign: "center" }}>
                        <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{sev.name}</div>
                        <div style={{ fontSize: "22px", fontWeight: "800", color: sev.count > 0 ? sev.col : "var(--text-muted)", marginTop: "4px" }}>{sev.count}</div>
                      </div>
                    ))}
                  </div>

                  {/* Detailed failures list */}
                  {failures.length > 0 ? (
                    <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "20px" }}>
                      <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "14px" }}>🔍 Failure Details</h3>
                      
                      {/* Filter Controls Row */}
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "10px", marginBottom: "16px" }}>
                        <div>
                          <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Category</label>
                          <select className="form-select" value={filterCat} onChange={e => setFilterCat(e.target.value)} style={{ width: "100%" }}>
                            <option value="All">All Categories</option>
                            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                            <option value="Custom">Custom</option>
                          </select>
                        </div>

                        <div>
                          <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Severity</label>
                          <select className="form-select" value={filterSev} onChange={e => setFilterSev(e.target.value)} style={{ width: "100%" }}>
                            <option value="All">All Severities</option>
                            <option value="Critical">Critical</option>
                            <option value="High">High</option>
                            <option value="Medium">Medium</option>
                            <option value="Low">Low</option>
                          </select>
                        </div>

                        <div>
                          <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>IFC Type</label>
                          <select className="form-select" value={filterType} onChange={e => setFilterType(e.target.value)} style={{ width: "100%" }}>
                            <option value="All">All Types</option>
                            {Array.from(new Set(failures.map(f => f["IFC Type"]))).map(t => (
                              <option key={t} value={t}>{t}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Search element / msg</label>
                          <input type="text" className="form-input" value={filterSearch} onChange={e => setFilterSearch(e.target.value)} placeholder="Search..." style={{ width: "100%" }} />
                        </div>
                      </div>

                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                        <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Showing <strong>{filteredFailures.length}</strong> of {failCount} failures</span>
                        <button className="btn-secondary" onClick={() => handleDownloadCSV(filteredFailures)} style={{ padding: "6px 12px", fontSize: "12px" }}>
                          ⬇ Download CSV
                        </button>
                      </div>

                      {/* Failures Table */}
                      <div className="data-table-container" style={{ margin: 0, maxHeight: "350px", overflowY: "auto" }}>
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Rule ID</th>
                              <th>Severity</th>
                              <th>Category</th>
                              <th>Rule</th>
                              <th>Element</th>
                              <th>IFC Type</th>
                              <th>Message</th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredFailures.map((row, idx) => (
                              <tr key={idx}>
                                <td style={{ fontWeight: "700" }}>{row["Rule ID"]}</td>
                                <td>
                                  <span style={{ 
                                    fontSize: "9px", 
                                    fontWeight: "700", 
                                    color: row.Severity === "Critical" ? "#da3633" : row.Severity === "High" ? "#d29922" : row.Severity === "Medium" ? "#58a6ff" : "#238636"
                                  }}>{row.Severity}</span>
                                </td>
                                <td>{row.Category}</td>
                                <td style={{ fontWeight: "600" }}>{row.Rule}</td>
                                <td>{row.Element}</td>
                                <td><code>{row["IFC Type"]}</code></td>
                                <td style={{ color: "#ff6b6b" }}>{row.Message}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: "40px", background: "rgba(35,134,54,0.05)", border: "1.5px solid #238636", borderRadius: "10px", textAlign: "center", color: "#7ee787" }}>
                      <h3>🎉 All Checks Passed!</h3>
                      <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>The selected rules generated zero failure messages.</p>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ padding: "80px", background: "var(--bg-card)", border: "1px dashed var(--border-color)", borderRadius: "12px", textAlign: "center", color: "var(--text-secondary)" }}>
                  Click the <strong>▶ Run Validation Now</strong> button above to run compliance checks on your IFC file.
                </div>
              )}
            </div>
          )}

          {/* SUBTAB 4: EXPORT REPORT */}
          {activeSubTab === "Report" && (
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "28px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "6px" }}>📄 Export Validation Report</h3>
              
              {validationResults ? (
                <div>
                  <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "20px" }}>
                    Generate a PDF report summarising the model compliance checklist.
                  </p>

                  <button className="btn-primary" onClick={handleDownloadPDF} style={{ padding: "12px 24px", display: "inline-flex", gap: "8px" }}>
                    📄 Generate PDF Report
                  </button>

                  <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", marginTop: "24px", paddingTop: "20px" }}>
                    <h5 style={{ fontSize: "13px", fontWeight: "700", marginBottom: "10px", color: "#fff" }}>Report includes:</h5>
                    <ul style={{ paddingLeft: "20px", fontSize: "12px", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "4px" }}>
                      <li>Validation health scorecard.</li>
                      <li>Critical, high, medium, and low failure summary breakdowns.</li>
                      <li>Detailed failures list (rule code, element name, IFC entity, error message).</li>
                      <li>Capped inline details for high efficiency.</li>
                    </ul>
                  </div>
                </div>
              ) : (
                <div style={{ padding: "20px", background: "rgba(0,200,255,0.03)", border: "1.5px solid rgba(0,200,255,0.15)", borderRadius: "6px", color: "var(--color-primary)", fontSize: "13px" }}>
                  ℹ️ Run validation first (go to <strong>Validation Results</strong> tab) to generate a report.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* T2: NBC COMPLIANCE TAB */}
      {activeTab === "NBC" && (
        <div>
          <h2 style={{ fontSize: "28px", fontWeight: "800", marginBottom: "4px" }}>🏛️ Overall NBC 2016 Compliance</h2>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "24px" }}>
            Audit building components against compliance regulations in the National Building Code (NBC) of India 2016.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "24px" }}>
            <div className="metric-card">
              <div className="metric-label">Overall Score</div>
              <div className="metric-value">{nbcOverall.toFixed(1)}%</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Total Checks</div>
              <div className="metric-value">{nbcTotal}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Checks Passed</div>
              <div className="metric-value" style={{ color: "#7ee787" }}>{nbcPassed}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Checks Failed</div>
              <div className="metric-value" style={{ color: "#ff6b6b" }}>{nbcFailed}</div>
            </div>
          </div>

          {/* NBC 2016 compliance verdict banner (Streamlit Parity) */}
          <div style={{ 
            background: `rgba(${nbcColor === "#238636" ? "35,134,54" : nbcColor === "#da3633" ? "218,54,51" : "210,153,34"}, 0.08)`, 
            border: `2px solid ${nbcColor}`, 
            borderRadius: "12px", 
            padding: "24px 28px", 
            marginBottom: "30px" 
          }}>
            <div style={{ fontSize: "10px", color: "var(--text-secondary)", letterSpacing: "1px", fontWeight: "700", marginBottom: "4px" }}>NBC 2016 COMPLIANCE VERDICT</div>
            <h3 style={{ fontSize: "24px", fontWeight: "900", color: nbcColor }}>
              {nbcVerdict} — {nbcOverall.toFixed(1)}%
            </h3>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "6px" }}>
              {nbcSubtext}
            </p>
          </div>

          {/* NBC Section wise Results collapsible Accordions */}
          <h3 style={{ fontSize: "18px", fontWeight: "800", marginBottom: "14px" }}>📋 NBC 2016 Section-wise Results</h3>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {nbcResults.map((item, idx) => {
              const isExpanded = expandedNbcIndex === idx;
              const isPass = item.status === "Pass";
              
              return (
                <div key={idx} style={{ border: `1.5px solid ${isPass ? "rgba(35,134,54,0.3)" : "rgba(218,54,51,0.3)"}`, borderRadius: "8px", background: "rgba(0,0,0,0.15)", overflow: "hidden" }}>
                  <div 
                    onClick={() => setExpandedNbcIndex(isExpanded ? null : idx)}
                    style={{ padding: "14px 18px", display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", userSelect: "none" }}
                  >
                    <span style={{ fontWeight: "700", fontSize: "14px", color: isPass ? "#7ee787" : "#ff6b6b" }}>
                      {isPass ? "✔ Pass" : "❌ Fail"} | {item.section} — {item.score.toFixed(1)}%
                    </span>
                    <span>{isExpanded ? "▲" : "▼"}</span>
                  </div>

                  {isExpanded && (
                    <div style={{ padding: "18px", background: "rgba(255,255,255,0.02)", borderTop: "1px solid rgba(255,255,255,0.06)", fontSize: "13px" }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>
                        <div>
                          <strong style={{ color: "var(--text-secondary)" }}>Standard: </strong>
                          <code>{item.standard}</code>
                        </div>
                        <div>
                          <strong style={{ color: "var(--text-secondary)" }}>Severity: </strong>
                          <span style={{ color: item.severity === "Critical" ? "#da3633" : "#ff9500", fontWeight: "700" }}>{item.severity}</span>
                        </div>
                        <div style={{ gridColumn: "span 2" }}>
                          <strong style={{ color: "var(--text-secondary)" }}>Audit Target: </strong>
                          {item.check}
                        </div>
                        <div style={{ gridColumn: "span 2" }}>
                          <strong style={{ color: "var(--text-secondary)" }}>Pass count: </strong>
                          {item.passed} / {item.total} elements checked ({item.score}%)
                        </div>
                      </div>

                      {item.failed > 0 && item.failed_samples && (
                        <div style={{ borderTop: "1px dashed rgba(255,255,255,0.08)", paddingTop: "12px", marginTop: "12px" }}>
                          <strong style={{ color: "#ff6b6b", display: "block", marginBottom: "6px" }}>Failed Samples ({item.failed} elements total):</strong>
                          <div style={{ background: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "6px", fontFamily: "Space Mono", fontSize: "11px", color: "var(--text-secondary)", lineHeight: "1.5", maxHeight: "100px", overflowY: "auto" }}>
                            {item.failed_samples.join(", ")}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
