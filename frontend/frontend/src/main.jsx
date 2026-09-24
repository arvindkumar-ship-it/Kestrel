// import React, { useEffect, useMemo, useState } from "react";
// import { createRoot } from "react-dom/client";
// import "./styles.css";

// const API = import.meta.env.VITE_API_BASE || "http://localhost:8010/api/v1";

// async function api(path, options = {}) {
//   const res = await fetch(`${API}${path}`, {
//     headers: { "Content-Type": "application/json", ...(options.headers || {}) },
//     ...options,
//   });
//   const text = await res.text();
//   let data;
//   try { data = text ? JSON.parse(text) : null; } catch { data = text; }
//   if (!res.ok) throw new Error(data?.detail || data?.message || `Request failed (${res.status})`);
//   return data;
// }

// function riskPct(v) {
//   const n = Number(v || 0);
//   return `${(n * 100).toFixed(1)}%`;
// }

// function riskLevel(v) {
//   const n = Number(v || 0);
//   if (n >= 0.8) return "critical";
//   if (n >= 0.5) return "elevated";
//   return "low";
// }

// function FlowNode({ icon, eyebrow, title, meta, tone = "" }) {
//   return (
//     <div className={`flow-node ${tone}`}>
//       <div className="flow-icon">{icon}</div>
//       <div className="flow-copy">
//         <span>{eyebrow}</span>
//         <strong>{title}</strong>
//         {meta && <small>{meta}</small>}
//       </div>
//     </div>
//   );
// }

// function AlertFlow({ alert }) {
//   const detail = alert.detail || {};
//   const level = riskLevel(alert.risk_score);
//   return (
//     <div className="alert-flow">
//       <div className="flow-line" />
//       <FlowNode
//         icon="◉"
//         eyebrow="ACTOR"
//         title={detail.actor_id || "unknown"}
//         meta="Observed identity"
//       />
//       <div className="flow-arrow">→</div>
//       <FlowNode
//         icon="□"
//         eyebrow="RESOURCE"
//         title={detail.resource_id || "unknown"}
//         meta={detail.resource_type || "accessed resource"}
//       />
//       <div className="flow-arrow">→</div>
//       <div className="signal-stack">
//         <div className="signal">
//           <span>Novelty</span>
//           <b>{Number(detail.novelty ?? 0).toFixed(2)}</b>
//         </div>
//         <div className="signal">
//           <span>Rate z-score</span>
//           <b>{Number(detail.rate_z ?? 0).toFixed(2)}</b>
//         </div>
//       </div>
//       <div className="flow-arrow">→</div>
//       <FlowNode
//         icon="↗"
//         eyebrow="RISK SCORE"
//         title={riskPct(alert.risk_score)}
//         meta="Threshold 80%"
//         tone={level}
//       />
//       <div className="flow-arrow">→</div>
//       <FlowNode
//         icon="!"
//         eyebrow="DECISION"
//         title="INSIDER ANOMALY"
//         meta="Alert generated"
//         tone="alert-node"
//       />
//     </div>
//   );
// }

// function AlertCard({ alert, selected, onSelect }) {
//   const detail = alert.detail || {};
//   const level = riskLevel(alert.risk_score);
//   return (
//     <button className={`alert-card ${selected ? "selected" : ""}`} onClick={onSelect}>
//       <div className={`severity-dot ${level}`} />
//       <div className="alert-main">
//         <div className="alert-top">
//           <div>
//             <span className="alert-type">insider_anomaly</span>
//             <span className={`risk-pill ${level}`}>{riskPct(alert.risk_score)}</span>
//           </div>
//           <span className="alert-id">ALERT #{alert.id}</span>
//         </div>
//         <div className="alert-sub">
//           <span><b>Actor</b> {detail.actor_id || "unknown"}</span>
//           <span><b>Resource</b> {detail.resource_id || "unknown"}</span>
//           <span><b>Novelty</b> {Number(detail.novelty ?? 0).toFixed(2)}</span>
//           <span><b>Rate z</b> {Number(detail.rate_z ?? 0).toFixed(2)}</span>
//         </div>
//       </div>
//       <span className="chevron">{selected ? "⌃" : "⌄"}</span>
//     </button>
//   );
// }

// function Alerts() {
//   const [alerts, setAlerts] = useState([]);
//   const [selected, setSelected] = useState(null);
//   const [error, setError] = useState("");

//   async function load() {
//     try {
//       const data = await api("/dashboard/alerts");
//       const next = Array.isArray(data) ? data : [];
//       setAlerts(next);
//       setError("");
//       if (!selected && next[0]) setSelected(next[0]);
//       else if (selected) {
//         const fresh = next.find(a => a.id === selected.id);
//         if (fresh) setSelected(fresh);
//       }
//     } catch (e) { setError(e.message); }
//   }

//   const [batchMsg, setBatchMsg] = useState("");
//   async function runBatch() {
//     setBatchMsg("running...");
//     try {
//       const r = await api("/batch/run", { method: "POST", body: "{}" });
//       setBatchMsg(`scored ${r.scored}, flagged ${r.flagged}`);
//       load();
//     } catch (e) { setBatchMsg(e.message); }
//   }

//   useEffect(() => {
//     load();
//     const t = setInterval(load, 3000);
//     return () => clearInterval(t);
//   }, []);

//   const stats = useMemo(() => {
//     const critical = alerts.filter(a => Number(a.risk_score) >= .8).length;
//     const actors = new Set(alerts.map(a => a.detail?.actor_id).filter(Boolean)).size;
//     return { total: alerts.length, critical, actors };
//   }, [alerts]);

//   return (
//     <section>
//       <div className="page-head">
//         <div>
//           <div className="eyebrow">REAL-TIME SECURITY MONITORING</div>
//           <h1>Alerts</h1>
//           <p>Behavior anomalies detected by the Kestrel risk engine.</p>
//         </div>
//         <div>
//           <div className="live-chip"><i /> LIVE · 3s refresh</div>
//           <button onClick={runBatch}>Run batch scan</button>
//           {batchMsg && <small> {batchMsg}</small>}
//         </div>
//       </div>

//       {error && <div className="error">{error}</div>}

//       <div className="stat-row">
//         <div className="stat"><span>Total alerts</span><b>{stats.total}</b></div>
//         <div className="stat"><span>Above threshold</span><b>{stats.critical}</b></div>
//         <div className="stat"><span>Actors involved</span><b>{stats.actors}</b></div>
//       </div>

//       {selected && (
//         <div className="threat-panel">
//           <div className="panel-head">
//             <div>
//               <span className="eyebrow">ALERT PATH</span>
//               <h2>How Kestrel reached this decision</h2>
//             </div>
//             <span className={`decision ${riskLevel(selected.risk_score)}`}>
//               {riskPct(selected.risk_score)} risk
//             </span>
//           </div>
//           <AlertFlow alert={selected} />
//           <div className="explain">
//             <span>WHY IT FIRED</span>
//             <p>
//               The actor accessed a resource with high novelty while the observed activity
//               contributed to the behavioral risk score crossing the <b>0.80</b> alert threshold.
//             </p>
//           </div>
//         </div>
//       )}

//       <div className="section-title">
//         <div><span className="eyebrow">DETECTION FEED</span><h2>Recent alerts</h2></div>
//         <span className="count">{alerts.length} records</span>
//       </div>

//       <div className="alert-list">
//         {alerts.length === 0 ? (
//           <div className="empty">No alerts yet. Submit an event to start the detection pipeline.</div>
//         ) : alerts.map(alert => (
//           <AlertCard
//             key={alert.id}
//             alert={alert}
//             selected={selected?.id === alert.id}
//             onSelect={() => setSelected(alert)}
//           />
//         ))}
//       </div>
//     </section>
//   );
// }

// function Overview() {
//   return (
//     <section>
//       <div className="page-head">
//         <div>
//           <div className="eyebrow">Kestrel SECURITY CONSOLE</div>
//           <h1>Overview</h1>
//           <p>Event-driven insider anomaly detection and response.</p>
//         </div>
//       </div>
//       <div className="overview-grid">
//         <div className="hero-card">
//           <div className="eyebrow">DETECTION PIPELINE</div>
//           <h2>From raw event to security decision.</h2>
//           <div className="pipeline">
//             {["Event", "Redis Stream", "Behavior Analysis", "Risk Engine", "Alert"].map((x, i) => (
//               <React.Fragment key={x}>
//                 <div className="pipeline-node"><b>{String(i + 1).padStart(2, "0")}</b>{x}</div>
//                 {i < 4 && <span>→</span>}
//               </React.Fragment>
//             ))}
//           </div>
//         </div>
//         <div className="side-card">
//           <span className="eyebrow">CURRENT MODE</span>
//           <strong>Detection active</strong>
//           <p>Responses are configured in safe dry-run mode.</p>
//           <div className="mode"><i /> Monitoring</div>
//         </div>
//       </div>
//     </section>
//   );
// }

// function EventForm() {
//   const [form, setForm] = useState({
//     actor_id: "demo-attacker",
//     resource_id: "demo-resource",
//     resource_type: "document",
//     action: "read",
//     source: "console",
//   });
//   const [msg, setMsg] = useState("");

//   const change = e => setForm({ ...form, [e.target.name]: e.target.value });
//   async function submit(e) {
//     e.preventDefault();
//     setMsg("");
//     try {
//       await api("/events", { method: "POST", body: JSON.stringify(form) });
//       setMsg("Event accepted by Kestrel.");
//     } catch (err) { setMsg(err.message); }
//   }

//   return (
//     <section>
//       <div className="page-head"><div><div className="eyebrow">EVENT INGESTION</div><h1>Send event</h1><p>Push a security event into the live detection pipeline.</p></div></div>
//       <form className="form-card" onSubmit={submit}>
//         {Object.keys(form).map(k => <label key={k}>{k.replace("_", " ")}<input name={k} value={form[k]} onChange={change}/></label>)}
//         <button className="primary">Submit event</button>
//         {msg && <div className="form-msg">{msg}</div>}
//       </form>
//     </section>
//   );
// }

// function Response() {
//   const [form, setForm] = useState({ session_id: "demo-attacker-session", reason: "Suspicious insider activity", actor: "security-admin" });
//   const [msg, setMsg] = useState("");
//   async function submit(e) {
//     e.preventDefault();
//     try {
//       const q = new URLSearchParams(form).toString();
//       const data = await api(`/response/revoke-session?${q}`, { method: "POST", body: "{}" });
//       setMsg(`${data.applied ? "Session revoked." : data.reason}`);
//     } catch (err) { setMsg(err.message); }
//   }
//   return (
//     <section>
//       <div className="page-head"><div><div className="eyebrow">SECURITY RESPONSE</div><h1>Session response</h1><p>Trigger the response workflow for a suspicious session.</p></div></div>
//       <form className="form-card" onSubmit={submit}>
//         {Object.keys(form).map(k => <label key={k}>{k.replace("_", " ")}<input name={k} value={form[k]} onChange={e => setForm({...form,[k]:e.target.value})}/></label>)}
//         <button className="danger">Request session revoke</button>
//         {msg && <div className="form-msg">{msg}</div>}
//         <div className="dry-note">Safe mode: autonomous response actions are currently disabled.</div>
//       </form>
//     </section>
//   );
// }

// function Health() {
//   const [state, setState] = useState({ live: "checking", ready: "checking" });
//   async function check() {
//     const get = async p => { try { await api(p); return "healthy"; } catch { return "offline"; } };
//     setState({ live: await get("/health/live"), ready: await get("/health/ready") });
//   }
//   useEffect(() => { check(); }, []);
//   return <div className="health"><span><i className={state.live}/> API live</span><span><i className={state.ready}/> DB/Redis ready</span></div>;
// }

// function App() {
//   const [page, setPage] = useState("alerts");
//   return (
//     <div className="app">
//       <aside>
//         <div className="brand"><div className="brand-mark">P8</div><div><b>Kestrel</b><span>Security Console</span></div></div>
//         <nav>
//           {[
//             ["overview","Overview"],
//             ["alerts","Alerts"],
//             ["events","Event intake"],
//             ["response","Response"],
//           ].map(([id,label]) => <button className={page===id?"active":""} onClick={()=>setPage(id)} key={id}>{label}</button>)}
//         </nav>
//         <div className="side-bottom"><Health /><span className="version">Kestrel · local environment</span></div>
//       </aside>
//       <main>
//         {page === "overview" && <Overview />}
//         {page === "alerts" && <Alerts />}
//         {page === "events" && <EventForm />}
//         {page === "response" && <Response />}
//       </main>
//     </div>
//   );
// }

// createRoot(document.getElementById("root")).render(<App />);







import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_API_BASE || "http://localhost:8010/api/v1";

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) throw new Error(data?.detail || data?.message || `Request failed (${res.status})`);
  return data;
}

function riskPct(v) {
  const n = Number(v || 0);
  return `${(n * 100).toFixed(1)}%`;
}

function riskLevel(v) {
  const n = Number(v || 0);
  if (n >= 0.8) return "critical";
  if (n >= 0.5) return "elevated";
  return "low";
}

function FlowNode({ icon, eyebrow, title, meta, tone = "" }) {
  return (
    <div className={`flow-node ${tone}`}>
      <div className="flow-icon">{icon}</div>
      <div className="flow-copy">
        <span>{eyebrow}</span>
        <strong>{title}</strong>
        {meta && <small>{meta}</small>}
      </div>
    </div>
  );
}

function AlertFlow({ alert }) {
  const detail = alert.detail || {};
  const level = riskLevel(alert.risk_score);
  return (
    <div className="alert-flow">
      <div className="flow-line" />
      <FlowNode
        icon="◉"
        eyebrow="ACTOR"
        title={detail.actor_id || "unknown"}
        meta="Observed identity"
      />
      <div className="flow-arrow">→</div>
      <FlowNode
        icon="□"
        eyebrow="RESOURCE"
        title={detail.resource_id || "unknown"}
        meta={detail.resource_type || "accessed resource"}
      />
      <div className="flow-arrow">→</div>
      <div className="signal-stack">
        <div className="signal">
          <span>Novelty</span>
          <b>{Number(detail.novelty ?? 0).toFixed(2)}</b>
        </div>
        <div className="signal">
          <span>Rate z-score</span>
          <b>{Number(detail.rate_z ?? 0).toFixed(2)}</b>
        </div>
      </div>
      <div className="flow-arrow">→</div>
      <FlowNode
        icon="↗"
        eyebrow="RISK SCORE"
        title={riskPct(alert.risk_score)}
        meta="Threshold 80%"
        tone={level}
      />
      <div className="flow-arrow">→</div>
      <FlowNode
        icon="!"
        eyebrow="DECISION"
        title="INSIDER ANOMALY"
        meta="Alert generated"
        tone="alert-node"
      />
    </div>
  );
}

function AlertCard({ alert, selected, onSelect }) {
  const detail = alert.detail || {};
  const level = riskLevel(alert.risk_score);
  return (
    <button className={`alert-card ${selected ? "selected" : ""}`} onClick={onSelect}>
      <div className={`severity-dot ${level}`} />
      <div className="alert-main">
        <div className="alert-top">
          <div>
            <span className="alert-type">insider_anomaly</span>
            <span className={`risk-pill ${level}`}>{riskPct(alert.risk_score)}</span>
          </div>
          <span className="alert-id">ALERT #{alert.id}</span>
        </div>
        <div className="alert-sub">
          <span><b>Actor</b> {detail.actor_id || "unknown"}</span>
          <span><b>Resource</b> {detail.resource_id || "unknown"}</span>
          <span><b>Novelty</b> {Number(detail.novelty ?? 0).toFixed(2)}</span>
          <span><b>Rate z</b> {Number(detail.rate_z ?? 0).toFixed(2)}</span>
        </div>
      </div>
      <span className="chevron">{selected ? "⌃" : "⌄"}</span>
    </button>
  );
}

function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      const data = await api("/dashboard/alerts");
      const next = Array.isArray(data) ? data : [];
      setAlerts(next);
      setError("");
      if (!selected && next[0]) setSelected(next[0]);
      else if (selected) {
        const fresh = next.find(a => a.id === selected.id);
        if (fresh) setSelected(fresh);
      }
    } catch (e) { setError(e.message); }
  }

  const [batchMsg, setBatchMsg] = useState("");
  async function runBatch() {
    setBatchMsg("running...");
    try {
      const r = await api("/batch/run", { method: "POST", body: "{}" });
      setBatchMsg(`scored ${r.scored}, flagged ${r.flagged}`);
      load();
    } catch (e) { setBatchMsg(e.message); }
  }

  const [demo, setDemo] = useState(false);
  async function toggleDemo() {
    try {
      const r = await api(`/demo/${demo ? "stop" : "start"}`, { method: "POST", body: "{}" });
      setDemo(r.running);
    } catch (e) { setBatchMsg(e.message); }
  }
  async function injectAnomaly() {
    try { await api("/demo/anomaly", { method: "POST", body: "{}" }); }
    catch (e) { setBatchMsg(e.message); }
  }

  useEffect(() => {
    api("/demo/status").then(r => setDemo(r.running)).catch(() => {});
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  const stats = useMemo(() => {
    const critical = alerts.filter(a => Number(a.risk_score) >= .8).length;
    const actors = new Set(alerts.map(a => a.detail?.actor_id).filter(Boolean)).size;
    return { total: alerts.length, critical, actors };
  }, [alerts]);

  return (
    <section>
      <div className="page-head">
        <div>
          <div className="eyebrow">REAL-TIME SECURITY MONITORING</div>
          <h1>Alerts</h1>
          <p>Behavior anomalies detected by the Kestrel risk engine.</p>
        </div>
        <div>
          <div className="live-chip"><i /> LIVE · 3s refresh</div>
          <button onClick={toggleDemo}>{demo ? "Stop live demo" : "Start live demo"}</button>
          <button onClick={injectAnomaly}>Inject anomaly</button>
          <button onClick={runBatch}>Run batch scan</button>
          {batchMsg && <small> {batchMsg}</small>}
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="stat-row">
        <div className="stat"><span>Total alerts</span><b>{stats.total}</b></div>
        <div className="stat"><span>Above threshold</span><b>{stats.critical}</b></div>
        <div className="stat"><span>Actors involved</span><b>{stats.actors}</b></div>
      </div>

      {selected && (
        <div className="threat-panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow">ALERT PATH</span>
              <h2>How Kestrel reached this decision</h2>
            </div>
            <span className={`decision ${riskLevel(selected.risk_score)}`}>
              {riskPct(selected.risk_score)} risk
            </span>
          </div>
          <AlertFlow alert={selected} />
          <div className="explain">
            <span>WHY IT FIRED</span>
            <p>
              The actor accessed a resource with high novelty while the observed activity
              contributed to the behavioral risk score crossing the <b>0.80</b> alert threshold.
            </p>
          </div>
        </div>
      )}

      <div className="section-title">
        <div><span className="eyebrow">DETECTION FEED</span><h2>Recent alerts</h2></div>
        <span className="count">{alerts.length} records</span>
      </div>

      <div className="alert-list">
        {alerts.length === 0 ? (
          <div className="empty">No alerts yet. Submit an event to start the detection pipeline.</div>
        ) : alerts.map(alert => (
          <AlertCard
            key={alert.id}
            alert={alert}
            selected={selected?.id === alert.id}
            onSelect={() => setSelected(alert)}
          />
        ))}
      </div>
    </section>
  );
}

function Overview() {
  return (
    <section>
      <div className="page-head">
        <div>
          <div className="eyebrow">Kestrel SECURITY CONSOLE</div>
          <h1>Overview</h1>
          <p>Event-driven insider anomaly detection and response.</p>
        </div>
      </div>
      <div className="overview-grid">
        <div className="hero-card">
          <div className="eyebrow">DETECTION PIPELINE</div>
          <h2>From raw event to security decision.</h2>
          <div className="pipeline">
            {["Event", "Redis Stream", "Behavior Analysis", "Risk Engine", "Alert"].map((x, i) => (
              <React.Fragment key={x}>
                <div className="pipeline-node"><b>{String(i + 1).padStart(2, "0")}</b>{x}</div>
                {i < 4 && <span>→</span>}
              </React.Fragment>
            ))}
          </div>
        </div>
        <div className="side-card">
          <span className="eyebrow">CURRENT MODE</span>
          <strong>Detection active</strong>
          <p>Responses are configured in safe dry-run mode.</p>
          <div className="mode"><i /> Monitoring</div>
        </div>
      </div>
    </section>
  );
}

function EventForm() {
  const [form, setForm] = useState({
    actor_id: "demo-attacker",
    resource_id: "demo-resource",
    resource_type: "document",
    action: "read",
    source: "console",
  });
  const [msg, setMsg] = useState("");

  const change = e => setForm({ ...form, [e.target.name]: e.target.value });
  async function submit(e) {
    e.preventDefault();
    setMsg("");
    try {
      await api("/events", { method: "POST", body: JSON.stringify(form) });
      setMsg("Event accepted by Kestrel.");
    } catch (err) { setMsg(err.message); }
  }

  return (
    <section>
      <div className="page-head"><div><div className="eyebrow">EVENT INGESTION</div><h1>Send event</h1><p>Push a security event into the live detection pipeline.</p></div></div>
      <form className="form-card" onSubmit={submit}>
        {Object.keys(form).map(k => <label key={k}>{k.replace("_", " ")}<input name={k} value={form[k]} onChange={change}/></label>)}
        <button className="primary">Submit event</button>
        {msg && <div className="form-msg">{msg}</div>}
      </form>
    </section>
  );
}

function Response() {
  const [form, setForm] = useState({ session_id: "demo-attacker-session", reason: "Suspicious insider activity", actor: "security-admin" });
  const [msg, setMsg] = useState("");
  async function submit(e) {
    e.preventDefault();
    try {
      const q = new URLSearchParams(form).toString();
      const data = await api(`/response/revoke-session?${q}`, { method: "POST", body: "{}" });
      setMsg(`${data.applied ? "Session revoked." : data.reason}`);
    } catch (err) { setMsg(err.message); }
  }
  return (
    <section>
      <div className="page-head"><div><div className="eyebrow">SECURITY RESPONSE</div><h1>Session response</h1><p>Trigger the response workflow for a suspicious session.</p></div></div>
      <form className="form-card" onSubmit={submit}>
        {Object.keys(form).map(k => <label key={k}>{k.replace("_", " ")}<input name={k} value={form[k]} onChange={e => setForm({...form,[k]:e.target.value})}/></label>)}
        <button className="danger">Request session revoke</button>
        {msg && <div className="form-msg">{msg}</div>}
        <div className="dry-note">Safe mode: autonomous response actions are currently disabled.</div>
      </form>
    </section>
  );
}

function Health() {
  const [state, setState] = useState({ live: "checking", ready: "checking" });
  async function check() {
    const get = async p => { try { await api(p); return "healthy"; } catch { return "offline"; } };
    setState({ live: await get("/health/live"), ready: await get("/health/ready") });
  }
  useEffect(() => { check(); }, []);
  return <div className="health"><span><i className={state.live}/> API live</span><span><i className={state.ready}/> DB/Redis ready</span></div>;
}

function App() {
  const [page, setPage] = useState("alerts");
  return (
    <div className="app">
      <aside>
        <div className="brand"><div className="brand-mark">P8</div><div><b>Kestrel</b><span>Security Console</span></div></div>
        <nav>
          {[
            ["overview","Overview"],
            ["alerts","Alerts"],
            ["events","Event intake"],
            ["response","Response"],
          ].map(([id,label]) => <button className={page===id?"active":""} onClick={()=>setPage(id)} key={id}>{label}</button>)}
        </nav>
        <div className="side-bottom"><Health /><span className="version">Kestrel · local environment</span></div>
      </aside>
      <main>
        {page === "overview" && <Overview />}
        {page === "alerts" && <Alerts />}
        {page === "events" && <EventForm />}
        {page === "response" && <Response />}
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);