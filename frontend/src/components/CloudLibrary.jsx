import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "../config";

export default function CloudLibrary({ onModelLoaded }) {
  const [files, setFiles] = useState([]);
  const [totalFiles, setTotalFiles] = useState(0);
  const [totalSize, setTotalSize] = useState(0);
  const [bucketName, setBucketName] = useState("innovescence-ifc-files");
  
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [loadingModel, setLoadingModel] = useState("");
  const [message, setMessage] = useState("");
  
  // File selection state (to emulate Streamlit file uploader selected state)
  const [selectedFile, setSelectedFile] = useState(null);

  const fetchCloudFiles = () => {
    setLoading(true);
    fetch(`${API_BASE_URL}/api/library/files`)
      .then(res => res.json())
      .then(data => {
        if (data.status === "success") {
          setFiles(data.files || []);
          setTotalFiles(data.total_files || 0);
          
          // Format size to MB
          const sizeInMb = (data.total_size || 0) / (1024 * 1024);
          setTotalSize(sizeInMb.toFixed(2));
          setBucketName(data.bucket || "innovescence-ifc-files");
        }
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchCloudFiles();
  }, []);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.toLowerCase().endsWith(".ifc")) {
        setSelectedFile(file);
      } else {
        alert("Please select only .ifc files.");
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const uploadFile = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setMessage("");
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch(`${API_BASE_URL}/api/library/upload`, {
        method: "POST",
        body: formData
      });
      if (!res.ok) throw new Error("Upload failed.");
      
      setMessage(`✅ ${selectedFile.name} uploaded successfully!`);
      setSelectedFile(null);
      fetchCloudFiles();
    } catch (err) {
      alert("Cloud upload failed: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (name) => {
    if (!confirm(`Are you sure you want to delete "${name}" from the cloud?`)) return;
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/library/files/${encodeURIComponent(name)}`, {
        method: "DELETE"
      });
      if (!res.ok) throw new Error("Delete failed.");
      
      setMessage(`🗑️ File "${name}" deleted from cloud.`);
      fetchCloudFiles();
    } catch (err) {
      alert("Delete failed: " + err.message);
    }
  };

  const handleDownloadFile = (name) => {
    window.open(`${API_BASE_URL}/api/library/download/${encodeURIComponent(name)}`, "_blank");
  };

  const handleLoadModel = async (name) => {
    setLoadingModel(name);
    setMessage("");
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/library/load`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: name })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Load failed");
      }
      const data = await res.json();
      
      if (onModelLoaded) {
        onModelLoaded(data.results);
      }
    } catch (err) {
      alert("Error loading model: " + err.message);
    } finally {
      setLoadingModel("");
    }
  };

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "20px" }}>
      {/* Title block */}
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "32px", fontWeight: "800", color: "#fff", margin: 0 }}>☁️ Cloud IFC Library</h1>
        <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginTop: "4px" }}>
          Upload, download, and manage all IFC files in your private Supabase bucket.
        </p>
      </div>

      {message && (
        <div style={{ padding: "12px 18px", background: "rgba(35,134,54,0.15)", border: "1.5px solid #238636", color: "#7ee787", borderRadius: "8px", marginBottom: "20px", fontSize: "13px" }}>
          {message}
        </div>
      )}

      {/* ── UPLOAD SECTION ── */}
      <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "10px", padding: "20px", marginBottom: "20px" }}>
        <div style={{ fontSize: "13px", fontWeight: "700", color: "#e6edf3", marginBottom: "4px" }}>
          ⬆️ Upload IFC File to Cloud
        </div>
        <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "16px" }}>
          Files are stored privately in Supabase. Max recommended size: 200MB.
        </div>

        {/* Drag and Drop Dropzone */}
        <div 
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          style={{
            border: `1.5px dashed ${dragActive ? "var(--color-primary)" : "#30363d"}`,
            background: dragActive ? "rgba(0, 200, 255, 0.05)" : "#161b22",
            borderRadius: "8px",
            padding: "24px",
            textAlign: "center",
            position: "relative",
            transition: "all 0.2s ease",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "16px"
          }}
        >
          <input 
            type="file" 
            accept=".ifc" 
            id="cloud-file-picker" 
            style={{ display: "none" }} 
            onChange={handleFileChange} 
            disabled={uploading} 
          />
          <div style={{ display: "flex", alignItems: "center", gap: "14px", textAlign: "left" }}>
            <span style={{ fontSize: "28px" }}>☁️</span>
            <div>
              <div style={{ fontSize: "13px", fontWeight: "700", color: "#e6edf3" }}>Drag and drop file here</div>
              <div style={{ fontSize: "11px", color: "#8b949e", marginTop: "2px" }}>Limit 200MB per file · IFC</div>
            </div>
          </div>

          <label htmlFor="cloud-file-picker" className="btn-secondary" style={{ padding: "8px 20px", cursor: "pointer", fontSize: "13px" }}>
            Browse files
          </label>
        </div>

        {/* Selected file confirmation row (matches Streamlit layout when file is chosen) */}
        {selectedFile && (
          <div style={{ display: "grid", gridTemplateColumns: "3fr 1fr", gap: "12px", marginTop: "16px", alignItems: "center" }}>
            <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "8px", padding: "12px 16px", display: "flex", alignItems: "center", gap: "12px" }}>
              <span style={{ fontSize: "20px" }}>📄</span>
              <div>
                <div style={{ fontSize: "13px", fontWeight: "700", color: "#e6edf3" }}>{selectedFile.name}</div>
                <div style={{ fontSize: "11px", color: "#8b949e", marginTop: "2px" }}>
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB · IFC file
                </div>
              </div>
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <button 
                className="btn-primary" 
                onClick={uploadFile} 
                disabled={uploading}
                style={{ flex: 1, padding: "12px", fontSize: "13px", fontWeight: "700" }}
              >
                {uploading ? "Uploading..." : "⬆️ Upload Now"}
              </button>
              <button 
                className="btn-secondary" 
                onClick={() => setSelectedFile(null)} 
                disabled={uploading}
                style={{ padding: "12px 16px", fontSize: "13px" }}
              >
                ✕
              </button>
            </div>
          </div>
        )}
      </div>

      <hr style={{ border: "none", borderTop: "1px solid #30363d", margin: "24px 0" }} />

      {/* ── FILE LIBRARY HEADER ACTIONS ── */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "20px" }}>
        <button 
          className="btn-secondary" 
          onClick={fetchCloudFiles} 
          disabled={loading} 
          style={{ padding: "8px 24px", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}
        >
          🔄 Refresh
        </button>
      </div>

      {/* ── METRICS SECTION ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px", marginBottom: "24px" }}>
        <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "10px", padding: "14px 18px" }}>
          <div style={{ fontSize: "11px", color: "#8b949e", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.5px" }}>Total Files</div>
          <div style={{ fontSize: "28px", fontWeight: "800", color: "#e6edf3", marginTop: "6px" }}>{totalFiles}</div>
        </div>

        <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "10px", padding: "14px 18px" }}>
          <div style={{ fontSize: "11px", color: "#8b949e", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.5px" }}>Total Size</div>
          <div style={{ fontSize: "28px", fontWeight: "800", color: "#e6edf3", marginTop: "6px" }}>{totalSize} MB</div>
        </div>

        <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: "10px", padding: "14px 18px" }}>
          <div style={{ fontSize: "11px", color: "#8b949e", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.5px" }}>Bucket</div>
          <div style={{ fontSize: "20px", fontWeight: "800", color: "#e6edf3", marginTop: "12px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {bucketName}
          </div>
        </div>
      </div>

      <hr style={{ border: "none", borderTop: "1px solid #30363d", margin: "24px 0" }} />

      {/* ── FILE GRID TABLE LIST ── */}
      <div style={{ borderRadius: "8px", border: "1px solid #30363d", overflow: "hidden" }}>
        {/* Table header row */}
        <div style={{ 
          display: "grid", 
          gridTemplateColumns: "3fr 1.2fr 1.5fr 1fr 1fr 1fr", 
          gap: "12px", 
          padding: "12px 18px", 
          background: "#21262d", 
          fontSize: "11px", 
          fontWeight: "700", 
          color: "#8b949e", 
          letterSpacing: "1px",
          textTransform: "uppercase",
          alignItems: "center"
        }}>
          <div>File Name</div>
          <div>Size</div>
          <div>Uploaded</div>
          <div style={{ textAlign: "center" }}>Load</div>
          <div style={{ textAlign: "center" }}>Download</div>
          <div style={{ textAlign: "center" }}>Delete</div>
        </div>

        {/* Rows list */}
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#8b949e", background: "#0d1117" }}>
            Scanning Supabase bucket storage...
          </div>
        ) : (
          <div style={{ background: "#0d1117" }}>
            {files.map((file, idx) => {
              const fname = file.name || "unknown";
              const meta = file.metadata || {};
              const sizeBytes = meta.size || 0;
              const sizeStr = sizeBytes >= 1024 * 1024 
                ? `${(sizeBytes / (1024 * 1024)).toFixed(2)} MB`
                : `${(sizeBytes / 1024).toFixed(1)} KB`;
              const created = file.created_at 
                ? file.created_at.slice(0, 16).replace("T", " ") 
                : "—";

              return (
                <div key={idx} style={{ 
                  display: "grid", 
                  gridTemplateColumns: "3fr 1.2fr 1.5fr 1fr 1fr 1fr", 
                  gap: "12px", 
                  padding: "14px 18px", 
                  borderBottom: idx === files.length - 1 ? "none" : "1px solid #30363d", 
                  alignItems: "center",
                  color: "#e6edf3"
                }}>
                  <div style={{ fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={fname}>
                    {fname}
                  </div>
                  <div style={{ fontSize: "12px", color: "#8b949e" }}>{sizeStr}</div>
                  <div style={{ fontSize: "12px", color: "#8b949e" }}>{created}</div>
                  
                  {/* Load Action */}
                  <div style={{ display: "flex", justifyContent: "center" }}>
                    <button 
                      onClick={() => handleLoadModel(fname)}
                      disabled={loadingModel !== ""}
                      style={{ 
                        background: "#161b22", 
                        border: "1px solid #30363d", 
                        color: "#58a6ff", 
                        borderRadius: "6px", 
                        padding: "6px 12px", 
                        fontSize: "11px", 
                        cursor: "pointer",
                        fontWeight: "600"
                      }}
                    >
                      {loadingModel === fname ? "..." : "⚡"}
                    </button>
                  </div>

                  {/* Download Action */}
                  <div style={{ display: "flex", justifyContent: "center" }}>
                    <button 
                      onClick={() => handleDownloadFile(fname)}
                      style={{ 
                        background: "#161b22", 
                        border: "1px solid #30363d", 
                        color: "#e6edf3", 
                        borderRadius: "6px", 
                        padding: "6px 12px", 
                        fontSize: "11px", 
                        cursor: "pointer" 
                      }}
                    >
                      ⬇️
                    </button>
                  </div>

                  {/* Delete Action */}
                  <div style={{ display: "flex", justifyContent: "center" }}>
                    <button 
                      onClick={() => handleDelete(fname)}
                      style={{ 
                        background: "#161b22", 
                        border: "1px solid #30363d", 
                        color: "#ff6b6b", 
                        borderRadius: "6px", 
                        padding: "6px 12px", 
                        fontSize: "11px", 
                        cursor: "pointer" 
                      }}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              );
            })}

            {files.length === 0 && (
              <div style={{ padding: "40px", textAlign: "center", color: "#8b949e" }}>
                No files uploaded yet. Use the uploader above to add your first IFC file.
              </div>
            )}
          </div>
        )}

        {/* Footer row */}
        <div style={{ 
          padding: "10px 18px", 
          background: "#161b22", 
          borderTop: "1px solid #30363d", 
          fontSize: "11px", 
          color: "#8b949e" 
        }}>
          ☁️ {files.length} file(s) · bucket: {bucketName} · private (authenticated access only)
        </div>
      </div>
    </div>
  );
}
