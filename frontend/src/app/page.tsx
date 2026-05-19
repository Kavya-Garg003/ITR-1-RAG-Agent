"use client";
import { useEffect, useState, useRef } from "react";

// ── Animated counter ────────────────────────────────────────────────────────
function Counter({ to, suffix = "" }: { to: number; suffix?: string }) {
  const [val, setVal] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      let start = 0;
      const step = to / 60;
      const t = setInterval(() => {
        start = Math.min(start + step, to);
        setVal(Math.round(start));
        if (start >= to) clearInterval(t);
      }, 16);
      obs.disconnect();
    }, { threshold: 0.3 });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, [to]);
  return <div ref={ref}>{val}{suffix}</div>;
}

// ── Section heading ─────────────────────────────────────────────────────────
function SH({ label, title, sub }: { label: string; title: string; sub: string }) {
  return (
    <div className="text-center mb-16">
      <div className="inline-block text-xs font-bold tracking-[0.2em] text-blue-400 bg-blue-500/10
        border border-blue-500/20 rounded-full px-4 py-1.5 mb-4">{label}</div>
      <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">{title}</h2>
      <p className="text-slate-400 max-w-xl mx-auto">{sub}</p>
    </div>
  );
}

// ── Architecture SVG ────────────────────────────────────────────────────────
function ArchDiagram() {
  return (
    <div className="overflow-x-auto">
      <svg viewBox="0 0 800 520" className="w-full max-w-4xl mx-auto" style={{ minWidth: 600 }}>
        <defs>
          <linearGradient id="gBlue" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#6366f1" />
          </linearGradient>
          <linearGradient id="gGreen" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#10b981" />
            <stop offset="100%" stopColor="#059669" />
          </linearGradient>
          <linearGradient id="gAmber" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#d97706" />
          </linearGradient>
          <linearGradient id="gPurple" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#7c3aed" />
          </linearGradient>
          <linearGradient id="gTeal" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#14b8a6" />
            <stop offset="100%" stopColor="#0d9488" />
          </linearGradient>
          <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M2 2L8 5L2 8" fill="none" stroke="#64748b" strokeWidth="1.5" strokeLinecap="round"/>
          </marker>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {/* User */}
        <rect x="290" y="12" width="220" height="52" rx="10" fill="url(#gBlue)" opacity="0.9"/>
        <text x="400" y="33" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">👤 User (Browser)</text>
        <text x="400" y="52" textAnchor="middle" fill="#bfdbfe" fontSize="9">Upload docs · Ask questions · View ITR-1</text>

        {/* Arrow user → gateway */}
        <line x1="400" y1="64" x2="400" y2="94" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arr)" strokeDasharray="4 2"/>

        {/* API Gateway */}
        <rect x="250" y="94" width="300" height="52" rx="10" fill="url(#gPurple)" opacity="0.9"/>
        <text x="400" y="115" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">🔀 API Gateway — Node.js/Express :3001</text>
        <text x="400" y="133" textAnchor="middle" fill="#e9d5ff" fontSize="9">Auth · Rate limiting · File proxying · Routing</text>

        {/* Arrows gateway → 3 services */}
        <line x1="295" y1="146" x2="130" y2="186" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arr)"/>
        <line x1="400" y1="146" x2="400" y2="186" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arr)"/>
        <line x1="505" y1="146" x2="670" y2="186" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arr)"/>

        {/* Doc Parser */}
        <rect x="30" y="186" width="200" height="70" rx="10" fill="url(#gAmber)" opacity="0.9"/>
        <text x="130" y="207" textAnchor="middle" fill="white" fontSize="11" fontWeight="bold">📄 Doc Parser</text>
        <text x="130" y="222" textAnchor="middle" fill="#fef9c3" fontSize="8">Python · FastAPI :8002</text>
        <text x="130" y="236" textAnchor="middle" fill="#fef9c3" fontSize="8">Form 16 · Bank stmt · AIS</text>
        <text x="130" y="250" textAnchor="middle" fill="#fef9c3" fontSize="8">pdfplumber extraction</text>

        {/* RAG Service */}
        <rect x="300" y="186" width="200" height="70" rx="10" fill="url(#gTeal)" opacity="0.9"/>
        <text x="400" y="207" textAnchor="middle" fill="white" fontSize="11" fontWeight="bold">🔍 RAG Service</text>
        <text x="400" y="222" textAnchor="middle" fill="#ccfbf1" fontSize="8">Python · FastAPI :8001</text>
        <text x="400" y="236" textAnchor="middle" fill="#ccfbf1" fontSize="8">FAISS · MMR · Cross-encoder</text>
        <text x="400" y="250" textAnchor="middle" fill="#ccfbf1" fontSize="8">Groq LLM · Citations</text>

        {/* Agent Orchestrator */}
        <rect x="570" y="186" width="200" height="70" rx="10" fill="url(#gGreen)" opacity="0.9"/>
        <text x="670" y="207" textAnchor="middle" fill="white" fontSize="11" fontWeight="bold">🤖 Agent Orchestrator</text>
        <text x="670" y="222" textAnchor="middle" fill="#d1fae5" fontSize="8">Python · FastAPI :8000</text>
        <text x="670" y="236" textAnchor="middle" fill="#d1fae5" fontSize="8">LangGraph pipeline</text>
        <text x="670" y="250" textAnchor="middle" fill="#d1fae5" fontSize="8">5-node state machine</text>

        {/* Arrow: doc parser → agent */}
        <line x1="230" y1="230" x2="568" y2="230" stroke="#64748b" strokeWidth="1" strokeDasharray="4 2" markerEnd="url(#arr)"/>

        {/* Arrow: RAG → agent */}
        <line x1="500" y1="221" x2="568" y2="221" stroke="#64748b" strokeWidth="1" strokeDasharray="4 2" markerEnd="url(#arr)"/>

        {/* LangGraph pipeline box */}
        <rect x="30" y="290" width="740" height="150" rx="12" fill="none" stroke="#334155" strokeWidth="1.5" strokeDasharray="6 3"/>
        <text x="400" y="310" textAnchor="middle" fill="#94a3b8" fontSize="9" fontWeight="bold">LANGGRAPH AGENT PIPELINE</text>

        {/* 5 agent nodes */}
        {[
          { x: 60,  label: "fill_form",        color: "#f59e0b", icon: "📝" },
          { x: 210, label: "compare_regimes",  color: "#3b82f6", icon: "⚖️" },
          { x: 360, label: "validate",          color: "#ef4444", icon: "✅" },
          { x: 510, label: "score_confidence", color: "#8b5cf6", icon: "📊" },
          { x: 650, label: "explain",           color: "#10b981", icon: "💡" },
        ].map((node, i) => (
          <g key={i}>
            <rect x={node.x} y="318" width="120" height="90" rx="8"
              fill={node.color} fillOpacity="0.15" stroke={node.color} strokeWidth="1.5"/>
            <text x={node.x + 60} y="340" textAnchor="middle" fontSize="16">{node.icon}</text>
            <text x={node.x + 60} y="358" textAnchor="middle" fill="white" fontSize="8" fontWeight="bold">{node.label}</text>
            <text x={node.x + 60} y="372" textAnchor="middle" fill="#94a3b8" fontSize="7">
              {i === 0 ? "Map docs → fields" :
               i === 1 ? "Old vs new regime" :
               i === 2 ? "12 validation rules" :
               i === 3 ? "Confidence 0–1" : "Plain English why"}
            </text>
            {i < 4 && (
              <line x1={node.x + 120} y1="363" x2={node.x + 147} y2="363"
                stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arr)"/>
            )}
          </g>
        ))}

        {/* Arrow: agent → output */}
        <line x1="670" y1="256" x2="670" y2="292" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arr)"/>

        {/* Infrastructure bar */}
        <rect x="30" y="460" width="740" height="48" rx="10" fill="#1e293b" stroke="#334155" strokeWidth="1"/>
        <text x="400" y="480" textAnchor="middle" fill="#64748b" fontSize="9" fontWeight="bold">INFRASTRUCTURE</text>
        <text x="400" y="498" textAnchor="middle" fill="#475569" fontSize="8">
          Docker Compose · PostgreSQL :5432 · Redis :6379 · FAISS Vector Store
        </text>
      </svg>
    </div>
  );
}

// ── RAG Pipeline SVG ────────────────────────────────────────────────────────
function RAGPipeline() {
  const steps = [
    { icon: "❓", label: "User query",       sub: "Tax question" },
    { icon: "🔢", label: "Embed query",      sub: "BGE-small-en" },
    { icon: "🗄️", label: "FAISS search",     sub: "Top-60 candidates" },
    { icon: "🎯", label: "MMR filter",       sub: "Top-5 diverse" },
    { icon: "📐", label: "Rerank",           sub: "Cross-encoder" },
    { icon: "🤖", label: "LLM answer",      sub: "Groq llama-3.3-70b" },
    { icon: "📎", label: "Cite sources",     sub: "PDF + Web links" },
  ];
  return (
    <div className="flex items-center justify-center flex-wrap gap-2 py-4">
      {steps.map((s, i) => (
        <div key={i} className="flex items-center gap-2">
          <div className="flex flex-col items-center">
            <div className="w-14 h-14 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-2xl shadow-lg">
              {s.icon}
            </div>
            <div className="text-xs text-slate-300 font-medium mt-1 text-center w-20">{s.label}</div>
            <div className="text-[9px] text-slate-500 text-center w-20">{s.sub}</div>
          </div>
          {i < steps.length - 1 && (
            <div className="text-slate-600 text-lg mb-6">→</div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Tech stack grid ─────────────────────────────────────────────────────────
const STACK = [
  { cat: "Frontend",      items: ["Next.js 14", "React 18", "Tailwind CSS", "TypeScript"] },
  { cat: "API Gateway",   items: ["Node.js 20", "Express 4", "Multer", "JWT Auth"] },
  { cat: "AI Pipeline",   items: ["LangGraph", "LangChain", "Groq API", "llama-3.3-70b"] },
  { cat: "RAG",           items: ["FAISS", "BGE-small-en", "Cross-encoder", "MMR retrieval"] },
  { cat: "Doc Parsing",   items: ["pdfplumber", "PyMuPDF", "FastAPI", "Pydantic v2"] },
  { cat: "Infrastructure",items: ["Docker Compose", "PostgreSQL", "Redis", "Python 3.11"] },
];

// ── Feature cards ───────────────────────────────────────────────────────────
const FEATURES = [
  {
    icon: "📄",
    title: "Auto Form Filling",
    desc: "Upload Form 16 + bank statements. AI parses every field and fills all 40+ ITR-1 fields automatically with confidence scores and source citations.",
    color: "from-blue-500/20 to-indigo-500/10 border-blue-500/20",
  },
  {
    icon: "⚖️",
    title: "Regime Comparison",
    desc: "Statutory math computes exact tax under both old and new regime using AY 2024-25 slab rates. Recommends the better regime with rupee savings shown.",
    color: "from-purple-500/20 to-violet-500/10 border-purple-500/20",
  },
  {
    icon: "🔍",
    title: "Tax AI Chat",
    desc: "Ask any tax question. RAG retrieves from 6,700+ chunks of official CBDT documents, TRACES circulars, and IT Act sections. Every answer is cited.",
    color: "from-teal-500/20 to-cyan-500/10 border-teal-500/20",
  },
  {
    icon: "✅",
    title: "Validation Engine",
    desc: "12 cross-field validation rules catch errors before filing — 80C cap breach, HRA + 80GG conflict, income > ₹50L ITR-1 ineligibility, and more.",
    color: "from-green-500/20 to-emerald-500/10 border-green-500/20",
  },
  {
    icon: "📊",
    title: "Confidence Scoring",
    desc: "Every filled field gets a 0–100% confidence score. Fields below 60% are flagged for manual review. Source is shown for every value.",
    color: "from-amber-500/20 to-yellow-500/10 border-amber-500/20",
  },
  {
    icon: "📋",
    title: "Multi-format Export",
    desc: "Export the filled ITR-1 as JSON (for ITD utility import), Excel (for record keeping), or PDF audit trail showing how every field was filled.",
    color: "from-rose-500/20 to-pink-500/10 border-rose-500/20",
  },
];

// ── Main page ───────────────────────────────────────────────────────────────
export default function AboutPage() {
  const [activeTab, setActiveTab] = useState<"rag" | "agent">("agent");

  return (
    <div className="min-h-screen bg-[#0a0f1e] text-white">
      {/* ── Hero ─────────────────────────────────────────────────── */}
      <div className="relative overflow-hidden">
        {/* Gradient blobs */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-600/20 rounded-full blur-[120px]" />
        <div className="absolute top-20 right-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-[120px]" />

        <div className="relative max-w-5xl mx-auto px-6 pt-24 pb-20 text-center">
          <div className="inline-flex items-center gap-2 text-xs font-bold tracking-widest text-blue-400
            bg-blue-500/10 border border-blue-500/20 rounded-full px-5 py-2 mb-8">
            <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
            FINAL YEAR PROJECT · AI + ML · AY 2024-25
          </div>
          <h1 className="text-5xl md:text-7xl font-black mb-6 leading-tight">
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-400 to-teal-400">
              ITR-1 RAG Agent
            </span>
          </h1>
          <p className="text-xl md:text-2xl text-slate-300 mb-4 max-w-3xl mx-auto leading-relaxed">
            AI that reads your tax documents, fills your ITR-1 Sahaj form,
            and answers any tax question — grounded in official CBDT sources.
          </p>
          <p className="text-slate-500 mb-10 max-w-xl mx-auto">
            Multi-agentic LangGraph pipeline · RAG with FAISS · 6 microservices · 40+ ITR-1 fields auto-filled
          </p>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto mb-12">
            {[
              { n: 6,    s: "",   label: "Microservices" },
              { n: 6700, s: "+",  label: "RAG chunks" },
              { n: 40,   s: "+",  label: "ITR-1 fields" },
              { n: 5,    s: "",   label: "Agent nodes" },
            ].map((stat, i) => (
              <div key={i} className="bg-white/5 border border-white/10 rounded-2xl p-4">
                <div className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
                  <Counter to={stat.n} suffix={stat.s} />
                </div>
                <div className="text-xs text-slate-400 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>

          <div className="flex justify-center gap-4 flex-wrap">
            <a href="/upload" className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600
              rounded-full text-white font-bold hover:shadow-lg hover:shadow-blue-500/25
              transition-all transform hover:-translate-y-0.5">
              Try It Now →
            </a>
            <a href="/chat" className="px-8 py-3 bg-white/10 border border-white/20
              rounded-full text-white font-bold hover:bg-white/15 transition-all">
              Ask Tax AI
            </a>
          </div>
        </div>
      </div>

      {/* ── How it works ─────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 py-24">
        <SH label="USER FLOW" title="From documents to filed form in 4 steps"
          sub="Upload your Form 16 and bank statements. Everything else is automatic." />

        <div className="relative">
          {/* Connector line */}
          <div className="absolute top-8 left-[10%] right-[10%] h-px bg-gradient-to-r
            from-transparent via-slate-700 to-transparent hidden md:block" />

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { n: "01", icon: "📤", title: "Upload Documents", desc: "Form 16 PDF + bank statements. Drag and drop. Auto-detects document type.", color: "blue" },
              { n: "02", icon: "🔍", title: "AI Parses PDFs", desc: "pdfplumber extracts salary, TDS, HRA, interest income. 95%+ accuracy.", color: "purple" },
              { n: "03", icon: "🤖", title: "Agent Pipeline Runs", desc: "5 LangGraph nodes fill, compare regimes, validate, score, and explain.", color: "teal" },
              { n: "04", icon: "📋", title: "Review & Export", desc: "Edit any field, ask AI questions, download filled Excel/JSON/PDF.", color: "green" },
            ].map((step, i) => (
              <div key={i} className="relative">
                <div className={`w-16 h-16 rounded-2xl bg-${step.color}-500/20 border border-${step.color}-500/30
                  flex items-center justify-center text-2xl mx-auto mb-4 relative z-10 bg-[#0a0f1e]`}>
                  {step.icon}
                </div>
                <div className={`text-xs font-black text-${step.color}-400 text-center mb-2 tracking-widest`}>
                  STEP {step.n}
                </div>
                <h3 className="text-sm font-bold text-white text-center mb-2">{step.title}</h3>
                <p className="text-xs text-slate-400 text-center leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Architecture ─────────────────────────────────────────── */}
      <div className="bg-white/2 border-y border-white/5">
        <div className="max-w-5xl mx-auto px-6 py-24">
          <SH label="ARCHITECTURE" title="6 microservices. Each does one thing perfectly."
            sub="Python for ML, Node.js for API orchestration, Docker for everything." />
          <ArchDiagram />
        </div>
      </div>

      {/* ── Pipeline detail ────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 py-24">
        <SH label="INTERNALS" title="Two AI pipelines working together"
          sub="The agent pipeline fills your form. The RAG pipeline answers your questions." />

        {/* Tab switcher */}
        <div className="flex justify-center mb-8">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-1 flex gap-1">
            {(["agent", "rag"] as const).map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)}
                className={`px-6 py-2.5 rounded-lg text-sm font-bold transition-all
                  ${activeTab === tab
                    ? "bg-blue-600 text-white shadow"
                    : "text-slate-400 hover:text-white"}`}>
                {tab === "agent" ? "🤖 Agent Pipeline" : "🔍 RAG Pipeline"}
              </button>
            ))}
          </div>
        </div>

        {activeTab === "agent" && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8">
            <h3 className="text-lg font-bold text-white mb-2">LangGraph 5-Node State Machine</h3>
            <p className="text-slate-400 text-sm mb-8">Each node receives the full state dict and returns only what it changes. LangGraph handles routing.</p>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              {[
                { icon: "📝", name: "fill_form", color: "amber", detail: ["Maps Form 16 → all 40+ fields", "Assigns confidence 0–1", "Splits employee name", "Computes net salary", "Creates TDS entries"] },
                { icon: "⚖️", name: "compare_regimes", color: "blue", detail: ["Statutory slab math", "Old regime deductions", "New regime std ded", "Computes saving", "Recommends regime"] },
                { icon: "✅", name: "validate", color: "red", detail: ["80C family cap ₹1.5L", "HRA + 80GG conflict", "Income > ₹50L check", "TDS discrepancy", "Missing field flags"] },
                { icon: "📊", name: "score_confidence", color: "purple", detail: ["Aggregates all scores", "Marks critical fields", "Flags < 60% fields", "Audit trail entry", "Summary stats"] },
                { icon: "💡", name: "explain", color: "green", detail: ["87A rebate reason", "HRA 3-component calc", "Regime recommendation", "Refund calculation", "Plain English why"] },
              ].map((node, i) => (
                <div key={i} className={`bg-${node.color}-500/10 border border-${node.color}-500/20 rounded-xl p-4`}>
                  <div className="text-2xl mb-2">{node.icon}</div>
                  <div className={`text-xs font-black text-${node.color}-400 mb-3 font-mono`}>{node.name}()</div>
                  <ul className="space-y-1">
                    {node.detail.map((d, j) => (
                      <li key={j} className="text-[10px] text-slate-400 flex gap-1">
                        <span className="text-slate-600 shrink-0">·</span>{d}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "rag" && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8">
            <h3 className="text-lg font-bold text-white mb-2">RAG Pipeline — 6,700+ Chunks from Official Sources</h3>
            <p className="text-slate-400 text-sm mb-8">Web scraped + PDF ingested. MMR prevents redundant chunks. Cross-encoder improves precision.</p>
            <RAGPipeline />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
              {[
                { label: "CBDT ITR-1 Instructions", type: "PDF", icon: "📘" },
                { label: "e-Filing Portal FAQs", type: "Web", icon: "🌐" },
                { label: "CBDT Circular 03/2025", type: "PDF", icon: "📋" },
                { label: "Income Tax Act 1961", type: "PDF", icon: "⚖️" },
                { label: "ClearTax Guides", type: "Web", icon: "🌐" },
                { label: "Salaried Guide (Official)", type: "Web", icon: "🌐" },
                { label: "Validation Rules AY25-26", type: "PDF", icon: "📋" },
                { label: "IT Rules 2026", type: "PDF", icon: "📘" },
              ].map((src, i) => (
                <div key={i} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 flex gap-2 items-start">
                  <span>{src.icon}</span>
                  <div>
                    <div className="text-xs text-slate-300 leading-tight">{src.label}</div>
                    <div className={`text-[9px] font-bold mt-1 ${src.type === "PDF" ? "text-amber-400" : "text-teal-400"}`}>
                      {src.type}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Features ────────────────────────────────────────────────── */}
      <div className="bg-white/2 border-y border-white/5">
        <div className="max-w-5xl mx-auto px-6 py-24">
          <SH label="FEATURES" title="Everything you need to file ITR-1"
            sub="Two main features, six supporting capabilities." />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {FEATURES.map((f, i) => (
              <div key={i} className={`bg-gradient-to-br ${f.color} border rounded-2xl p-6`}>
                <div className="text-3xl mb-4">{f.icon}</div>
                <h3 className="text-base font-bold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Tech Stack ──────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 py-24">
        <SH label="TECH STACK" title="Every technology chosen deliberately"
          sub="Python for ML ecosystem. Node.js for async I/O. Free embeddings, free LLM." />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
          {STACK.map((cat, i) => (
            <div key={i} className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
              <div className="text-xs font-black text-slate-500 tracking-widest mb-3">{cat.cat}</div>
              <div className="flex flex-wrap gap-2">
                {cat.items.map((item, j) => (
                  <span key={j} className="text-xs bg-slate-800 border border-slate-700 text-slate-300
                    rounded-lg px-2.5 py-1 font-medium">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Key design decisions ─────────────────────────────────────── */}
      <div className="bg-white/2 border-y border-white/5">
        <div className="max-w-5xl mx-auto px-6 py-24">
          <SH label="DESIGN DECISIONS" title="Why every technical choice was made"
            sub="Interview-ready answers for every architectural decision." />
          <div className="space-y-3 max-w-3xl mx-auto">
            {[
              { q: "Why microservices?",             a: "Different scaling profiles — parser runs once per upload, RAG runs per query, agent runs per pipeline trigger. Independent deployment per AY update." },
              { q: "Why Python for ML services?",    a: "LangGraph, pdfplumber, FAISS, sentence-transformers — no equivalent in Node.js. Would lose 80% of the ML tooling." },
              { q: "Why Node.js for the gateway?",   a: "Event-driven non-blocking I/O is the correct tool for async orchestration of multiple Python microservices." },
              { q: "Why FAISS not Pinecone?",        a: "FAISS locally (zero cost, full control, fast). Pinecone for production scale (managed). Shows we understand the tradeoff." },
              { q: "Why MMR over similarity search?",a: "Prevents 5 near-identical chunks being returned. Balances relevance with diversity using λ=0.6." },
              { q: "Why Groq over OpenAI?",          a: "Free tier: 14,400 req/day, 500K tokens/day. llama-3.3-70b quality matches gpt-4o-mini for this domain. Fallback to OpenRouter if rate-limited." },
              { q: "How is it AY-updatable?",        a: "Versioned FAISS namespaces (AY2024-25.faiss, AY2025-26.faiss). New AY: ingest new CBDT PDFs + run embedder. Only RAG service redeploys." },
              { q: "How do you prevent hallucination?",a:"Answers grounded in retrieved FAISS chunks only. Confidence scoring flags uncertain fields. Validator catches tax rule violations." },
            ].map((item, i) => (
              <div key={i} className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 flex gap-4">
                <div className="text-blue-400 font-bold text-sm shrink-0 w-5">{i + 1}</div>
                <div>
                  <div className="text-sm font-bold text-white mb-1">{item.q}</div>
                  <div className="text-xs text-slate-400 leading-relaxed">{item.a}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── CTA ─────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 py-24 text-center">
        <h2 className="text-3xl font-black text-white mb-4">Ready to file your ITR-1?</h2>
        <p className="text-slate-400 mb-8">Upload your Form 16 and let AI do the rest.</p>
        <div className="flex justify-center gap-4 flex-wrap">
          <a href="/upload" className="px-10 py-4 bg-gradient-to-r from-blue-600 to-purple-600
            rounded-full text-white font-bold text-lg hover:shadow-xl hover:shadow-blue-500/30
            transition-all transform hover:-translate-y-1">
            Upload Form 16 →
          </a>
          <a href="/chat" className="px-10 py-4 bg-white/10 border border-white/20
            rounded-full text-white font-bold text-lg hover:bg-white/15 transition-all">
            Ask Tax Questions
          </a>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-white/5 py-8 text-center">
        <p className="text-slate-600 text-sm">
          ITR-1 RAG Agent · Final Year Project · RAG + Multi-Agentic AI · AY 2024-25
        </p>
      </div>
    </div>
  );
}
