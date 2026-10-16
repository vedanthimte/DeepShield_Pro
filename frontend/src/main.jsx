import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { ShieldCheck, Upload, ScanSearch, FileVideo, Image as ImageIcon, AlertTriangle, CheckCircle2, CircleHelp, LoaderCircle, Download } from "lucide-react";
import "./style.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
function App() {
  const [mode, setMode] = useState("image");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [health, setHealth] = useState(null);

  React.useEffect(() => {
    fetch(`${API}/api/health`).then(r => r.json()).then(setHealth).catch(() => setHealth({status:"offline"}));
  }, []);

  function chooseMode(next) {
    setMode(next); setFile(null); setResult(null); setError("");
  }
  async function analyze(e) {
    e.preventDefault();
    if (!file) return;
    setBusy(true); setError(""); setResult(null);
    try {
      const form = new FormData(); form.append("file", file);
      const response = await fetch(`${API}/api/analyze/${mode}`, {method:"POST", body:form});
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Analysis failed.");
      setResult(body);
    } catch (err) {
      setError(`${err.message}. Confirm that the backend is running at ${API}.`);
    } finally { setBusy(false); }
  }
  function downloadReport() {
    const blob = new Blob([JSON.stringify(result, null, 2)], {type:"application/json"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "deepshield-report.json"; a.click();
    URL.revokeObjectURL(url);
  }
  const prediction = result?.prediction;
  const verdict = prediction?.verdict || result?.verdict;
  const fakeScore = prediction?.fake_score ?? result?.average_fake_score;
  // const scorePct = typeof fakeScore === "number" ? Math.round(fakeScore * 100) : null;
  const scorePct = typeof fakeScore === "number"
  ? fakeScore * 100
  : null;
  const scoreLabel = scorePct !== null
  ? `${scorePct.toFixed(2)}%`
  : "—";
  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-icon"><ShieldCheck size={25}/></div><div><b>DeepShield</b><span>MEDIA AUTHENTICITY LAB</span></div></div>
      <div className={`api-status ${health?.status === "ok" ? "online" : ""}`}><span className="dot"/>{health?.status === "ok" ? "API connected" : "API not connected"}</div>
    </header>
    <main>
      <section className="hero">
        <div className="eyebrow"><span className="pulse"/> LOCAL AI FORENSICS</div>
        <h1>Look closer.<br/><em>Question the pixels.</em></h1>
        <p>Screen images for AI-generated patterns and sample video frames for potential manipulation indicators. Results are evidence signals—not proof.</p>
        <div className="model-pill"><span className="mini-dot"/> CommunityForensics · ViT-Small · 2.7M training samples</div>
      </section>
      <section className="workspace">
        <div className="panel upload-panel">
          <div className="panel-heading"><div><span className="step">01</span><h2>Submit media</h2></div><span className="quiet">LOCAL INFERENCE</span></div>
          <div className="mode-switch">
            <button className={mode==="image"?"selected":""} onClick={()=>chooseMode("image")}><ImageIcon size={17}/> Image</button>
            <button className={mode==="video"?"selected":""} onClick={()=>chooseMode("video")}><FileVideo size={17}/> Video frames</button>
          </div>
          <form onSubmit={analyze}>
            <label className="dropzone">
              <input type="file" accept={mode==="image"?"image/jpeg,image/png,image/webp,image/bmp":"video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm"} onChange={e=>{setFile(e.target.files?.[0]||null);setResult(null);setError("");}}/>
              <div className="upload-symbol"><Upload size={23}/></div>
              <strong>{file ? file.name : `Choose ${mode==="image"?"an image":"a video"}`}</strong>
              <span>{file ? `${(file.size/1024/1024).toFixed(2)} MB` : mode==="image" ? "JPG · PNG · WEBP · up to 15 MB" : "MP4 · MOV · AVI · MKV · WEBM · up to 100 MB"}</span>
              <small>Click to browse files</small>
            </label>
            {file && <div className="file-row"><span>{mode==="image"?"IMAGE FILE":"VIDEO FILE"}</span><button type="button" className="text-button" onClick={()=>setFile(null)}>Remove</button></div>}
            <button className="analyze-btn" type="submit" disabled={!file||busy}>
              {busy ? <><LoaderCircle className="spin" size={18}/> Analyzing media…</> : <><ScanSearch size={18}/> Analyze {mode==="image"?"image":"video frames"}</>}
            </button>
          </form>
          {error && <div className="error"><AlertTriangle size={18}/><span>{error}</span></div>}
          <div className="privacy-note"><ShieldCheck size={17}/><span>Files are processed by your local backend and are not saved by the app after analysis.</span></div>
        </div>
        <div className="panel result-panel">
          <div className="panel-heading"><div><span className="step">02</span><h2>Analysis report</h2></div>{result && <button className="icon-button" onClick={downloadReport} title="Download JSON report"><Download size={17}/></button>}</div>
          {!result && !busy && <div className="empty-state"><div className="radar"><div/><div/><ScanSearch size={27}/></div><h3>Awaiting evidence</h3><p>Choose a file and start an analysis. Model outputs and frame-level signals will appear here.</p><div className="empty-meta"><span><CheckCircle2 size={14}/> Model-backed inference</span><span><CircleHelp size={14}/> Uncertainty-aware</span></div></div>}
          {busy && <div className="loading-state"><LoaderCircle className="spin" size={36}/><h3>Running model inference</h3><p>The first request downloads model weights and may take several minutes.</p></div>}
          {result && <div className="report">
            <div className={`verdict ${verdict?.toLowerCase().includes("likely real")||verdict?.toLowerCase().includes("no strong")?"real":verdict?.toLowerCase().includes("inconclusive")?"uncertain":"fake"}`}>
              <span className="verdict-icon">{verdict?.toLowerCase().includes("inconclusive")?<CircleHelp/>:verdict?.toLowerCase().includes("likely real")||verdict?.toLowerCase().includes("no strong")?<CheckCircle2/>:<AlertTriangle/>}</span>
              <div><small>MODEL ASSESSMENT</small><h3>{verdict}</h3><p>{mode==="video"?"Sampled frame screening":"AI-generated image screening"}</p></div>
            </div>
            <div className="score-head"><span>AI/manipulation score</span><b>{scoreLabel}</b></div>
            <div className="score-track"><div style={{width:`${scorePct}%`}}/></div>
            <div className="score-labels"><span>Lower model score</span><span>Higher model score</span></div>
            <div className="stats">
              <div><span>MODEL</span><b>CommunityForensics</b></div>
              <div><span>SHA-256</span><b className="hash">{result.sha256?.slice(0,18)}…</b></div>
              {result.width && <div><span>DIMENSIONS</span><b>{result.width} × {result.height}</b></div>}
              {result.sampled_frames && <div><span>FRAMES SAMPLED</span><b>{result.sampled_frames}</b></div>}
            </div>
            {result.frames && <div className="frames"><h4>Frame-level results</h4>{result.frames.map((f,i)=><div className="frame-row" key={i}><span>Frame {f.frame_index}{f.timestamp_seconds!=null?` · ${f.timestamp_seconds}s`:""}</span><b>{Math.round(f.prediction.fake_score*100)}%</b><span>{f.prediction.verdict}</span></div>)}</div>}
            <div className="disclaimer"><AlertTriangle size={16}/><span>{result.note || prediction?.note}</span></div>
            <button className="download-btn" onClick={downloadReport}><Download size={17}/> Download JSON report</button>
          </div>}
        </div>
      </section>
      <section className="bottom-grid">
        <div className="info-card"><span className="info-number">01</span><h3>What it can do</h3><p>Use a pretrained image detector and analyze a small set of frames distributed across a video. Keep reports with the file hash for traceability.</p></div>
        <div className="info-card"><span className="info-number">02</span><h3>What it cannot prove</h3><p>Image detectors can misclassify genuine photos. This model is not validated as a dedicated face-swap or temporal video detector. Confirm important cases independently.</p></div>
        <div className="info-card"><span className="info-number">03</span><h3>Built for iteration</h3><p>Use a labeled test set of phone photos, social-media images, and current generators to measure false positives before changing thresholds.</p></div>
      </section>
      <footer><span>DEEPSHIELD <i>·</i> LOCAL PROTOTYPE</span><span>Model: buildborderless/CommunityForensics-DeepfakeDet-ViT</span></footer>
    </main>
  </div>;
}
createRoot(document.getElementById("root")).render(<App/>);
