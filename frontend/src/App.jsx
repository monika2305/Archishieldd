import React, { useState, useEffect } from "react";
import HomeDashboard from "./components/HomeDashboard";
import ModelAnalysis from "./components/ModelAnalysis";
import Visualization from "./components/Visualization";
import ValidationCompliance from "./components/ValidationCompliance";
import CorrectionsDashboard from "./components/CorrectionsDashboard";
import ReportsExport from "./components/ReportsExport";
import AskModel from "./components/AskModel";
import LandingPage from "./components/LandingPage";
import CloudLibrary from "./components/CloudLibrary";
import AutomationCenter from "./components/AutomationCenter";
import { API_BASE_URL } from "./config";

export default function App() {
  const [showPlatform, setShowPlatform] = useState(false);
  const [activeNav, setActiveNav] = useState("Home");
  const [userContext, setUserContext] = useState({ name: "", role: "", domain: "", purpose: "" });
  const [analysis, setAnalysis] = useState(null);
  const [viewMode, setViewMode] = useState("Technical"); // Technical, Business, Full

  const [loginForm, setLoginForm] = useState({
    name: "",
    role: "— Select —",
    domain: "— Select —",
    purpose: "— Select —"
  });

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
  if (!loginForm.name.trim() || loginForm.name === "e.g. Moni") missingFields.push("Name");
  if (loginForm.role === "— Select —") missingFields.push("Role");
  if (loginForm.domain === "— Select —") missingFields.push("Project Domain");
  if (loginForm.purpose === "— Select —") missingFields.push("Purpose of IFC");

  const loginComplete = missingFields.length === 0;

  // Load session on startup
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/auth/session`)
      .then(res => res.json())
      .then(data => {
        if (data.logged_in) {
          setUserContext(data.context);
          setShowPlatform(true);
        }
      })
      .catch(() => {
        console.log("Backend not connected yet. Waiting for start.");
      });
  }, []);

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
      // fallback mock mode
      setUserContext({
        name: loginForm.name.trim(),
        role: loginForm.role,
        domain: loginForm.domain,
        purpose: loginForm.purpose
      });
    }
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, { method: "POST" });
    } catch(e){}
    setUserContext({ name: "", role: "", domain: "", purpose: "" });
    setLoginForm({ name: "", role: "— Select —", domain: "— Select —", purpose: "— Select —" });
    setAnalysis(null);
    setActiveNav("Home");
  };

  const handleUploadSuccess = () => {
    setActiveNav("Home");
  };

  const handleApplySuccess = () => {
    fetch(`${API_BASE_URL}/api/analyze/results`)
      .then(res => res.json())
      .then(data => {
        setAnalysis(data);
      })
      .catch(err => console.error(err));
  };

  // Sidebar items definition
  const menuItems = [
    { id: "Home", name: "Home", icon: "🏠" },
    { id: "Model Analysis", name: "Model Analysis", icon: "🔬" },
    { id: "Visualization", name: "Visualization & Insights", icon: "📊" },
    { id: "Validation & Compliance", name: "Validation & Compliance", icon: "✅" },
    { id: "Corrections", name: "Corrections", icon: "🛠️" },
    { id: "Reports & Export", name: "Reports & Export", icon: "📁" },
    { id: "Cloud Library", name: "cloud library", icon: "☁️" },
    { id: "Ask Your Model", name: "Ask Your Model", icon: "💬" },
    { id: "Automation", name: "Automation Center", icon: "⚡" },
  ];

  if (!showPlatform) {
    return (
      <LandingPage 
        onLoginSuccess={(ctx) => {
          setUserContext(ctx);
          setShowPlatform(true);
        }} 
        onLaunchPlatform={() => {
          setShowPlatform(true);
        }}
      />
    );
  }

  return (
    <div className="app-container sidebar-active">
      {/* Sidebar */}
      <aside className="sidebar">
        {/* Back navigation */}
        <div style={{ padding: "10px 24px 0" }}>
          <button 
            onClick={() => {
              handleLogout();
              setShowPlatform(false);
            }}
            style={{ 
              background: "none", 
              border: "none", 
              color: "var(--text-secondary)", 
              fontSize: "14px", 
              fontWeight: "600", 
              cursor: "pointer",
              padding: "8px 0",
              display: "flex",
              alignItems: "center",
              gap: "8px"
            }}
          >
            <span>Back</span>
          </button>
        </div>

        <div className="logo-container" style={{ paddingTop: "10px" }}>
          <span className="logo-icon">🛡️</span>
          <span className="logo-text">ArchiShield</span>
        </div>

        <nav className="nav-menu">
          {menuItems.map(item => (
            <a
              key={item.id}
              className={`nav-item ${activeNav === item.id ? "active" : ""}`}
              onClick={() => setActiveNav(item.id)}
            >
              <span>{item.icon}</span> {item.name}
            </a>
          ))}
        </nav>

        {/* User badge */}
        {userContext.name && (
          <div className="user-badge">
            <div className="user-badge-name">👤 {userContext.name}</div>
            <div className="user-badge-role">{userContext.role}</div>
            <button 
              className="btn-secondary" 
              style={{ padding: "6px", fontSize: "11px", marginTop: "10px", width: "100%" }}
              onClick={handleLogout}
            >
              Sign Out
            </button>
          </div>
        )}
      </aside>

      {/* Main viewport */}
      <main className="main-content">
        {/* Header metadata banner */}
        {userContext.name && (
          <header className="header-banner">
            <div style={{ fontSize: "12px" }}>
              👤 Logged in as: <strong>{userContext.name}</strong> ({userContext.role})
            </div>
            <div className="banner-meta">
              <div>Domain: <strong>{userContext.domain}</strong></div>
              <div>Purpose: <strong>{userContext.purpose}</strong></div>
            </div>
          </header>
        )}

        {/* View switching router */}
        <div style={{ flex: 1 }}>
          {!userContext.name ? (
            /* Streamlit Style Login Page */
            <div style={{ maxWidth: "600px", margin: "20px auto", padding: "20px" }}>
              <h2 style={{ fontSize: "32px", fontWeight: "800", color: "#fff", marginBottom: "6px" }}>Login</h2>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "28px" }}>
                Please fill in all fields to continue.
              </p>

              <form onSubmit={handleLoginSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                <div>
                  <label style={{ fontSize: "13px", display: "block", marginBottom: "6px", color: "var(--text-secondary)", fontWeight: "600" }}>
                    Your Name *
                  </label>
                  <input 
                    type="text" 
                    className="form-input" 
                    value={loginForm.name} 
                    placeholder="e.g. Moni"
                    onChange={e => setLoginForm({...loginForm, name: e.target.value})} 
                    style={{ width: "100%", padding: "10px 14px", background: "rgba(0,0,0,0.2)", border: "1.5px solid var(--border-color)", borderRadius: "6px", color: "#fff" }}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: "13px", display: "block", marginBottom: "6px", color: "var(--text-secondary)", fontWeight: "600" }}>
                    Your Role *
                  </label>
                  <select 
                    className="form-select" 
                    value={loginForm.role} 
                    onChange={e => setLoginForm({...loginForm, role: e.target.value})}
                    style={{ width: "100%", padding: "10px" }}
                  >
                    {roles.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "13px", display: "block", marginBottom: "6px", color: "var(--text-secondary)", fontWeight: "600" }}>
                    Project Domain *
                  </label>
                  <select 
                    className="form-select" 
                    value={loginForm.domain} 
                    onChange={e => setLoginForm({...loginForm, domain: e.target.value})}
                    style={{ width: "100%", padding: "10px" }}
                  >
                    {domains.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "13px", display: "block", marginBottom: "6px", color: "var(--text-secondary)", fontWeight: "600" }}>
                    Purpose of IFC *
                  </label>
                  <select 
                    className="form-select" 
                    value={loginForm.purpose} 
                    onChange={e => setLoginForm({...loginForm, purpose: e.target.value})}
                    style={{ width: "100%", padding: "10px" }}
                  >
                    {purposes.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>

                {missingFields.length > 0 && (
                  <div style={{ 
                    padding: "16px", 
                    backgroundColor: "rgba(210,153,34,0.1)", 
                    border: "1.5px solid rgba(210,153,34,0.3)", 
                    borderRadius: "8px", 
                    color: "#ffb347", 
                    fontSize: "13px",
                    fontWeight: "600",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px"
                  }}>
                    <span>⚠️</span>
                    <span>Please fill in: {missingFields.join(", ")}</span>
                  </div>
                )}

                <button 
                  type="submit" 
                  className="btn-primary" 
                  disabled={!loginComplete} 
                  style={{ width: "100%", padding: "14px", fontSize: "14px", fontWeight: "700" }}
                >
                  Continue →
                </button>
              </form>

              <div style={{ borderTop: "1px solid var(--border-color)", marginTop: "40px", paddingTop: "20px", textAlign: "center" }}>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "12px" }}>
                  👇 Don't have an IFC file? Download our sample model and upload it above.
                </p>
                <a 
                  href={`${API_BASE_URL}/api/analyze/download-sample`} 
                  download 
                  className="btn-secondary" 
                  style={{ display: "inline-block", fontSize: "12px", textDecoration: "none", padding: "10px 20px" }}
                >
                  ⬇️ Download Sample IFC Model
                </a>
              </div>
            </div>
          ) : (
            /* Router of tabs */
            <>
              {activeNav === "Home" && (
                <HomeDashboard 
                  userContext={userContext} 
                  setUserContext={setUserContext}
                  analysis={analysis} 
                  setAnalysis={setAnalysis}
                  onUploadSuccess={handleUploadSuccess}
                  viewMode={viewMode}
                  setViewMode={setViewMode}
                  activeNav={activeNav}
                  setActiveNav={setActiveNav}
                />
              )}

              {activeNav === "Model Analysis" && (
                <ModelAnalysis analysis={analysis} />
              )}

              {activeNav === "Visualization" && (
                <Visualization analysis={analysis} />
              )}

              {activeNav === "Validation & Compliance" && (
                <ValidationCompliance analysis={analysis} />
              )}

              {activeNav === "Corrections" && (
                <CorrectionsDashboard analysis={analysis} onApplySuccess={handleApplySuccess} />
              )}

              {activeNav === "Reports & Export" && (
                <ReportsExport analysis={analysis} />
              )}

              {activeNav === "Cloud Library" && (
                <CloudLibrary onModelLoaded={(res) => {
                  setAnalysis(res);
                  setActiveNav("Home");
                }} />
              )}

              {activeNav === "Ask Your Model" && (
                <AskModel analysis={analysis} />
              )}

              {activeNav === "Automation" && (
                <AutomationCenter analysis={analysis} userContext={userContext} />
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
