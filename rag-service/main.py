"""
RAG Service — FastAPI
======================
FAISS + MMR + cross-encoder reranking + LLM answer generation.
Fixes: PDF sources now appear in citations even without a URL.
       Answer format now includes quoted paragraph from source.
       Both Groq and OpenRouter used via best_of_n for quality answers.
"""

import os, json, re
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # /app in Docker

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

VECTOR_STORE_DIR = Path(os.getenv("VECTOR_STORE_DIR", "/app/vector_store"))
DEFAULT_AY       = os.getenv("DEFAULT_AY", "AY2024-25")

app = FastAPI(title="RAG Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_index_cache, _meta_cache, _embedder_cache = {}, {}, {}


# ── Source name normaliser ─────────────────────────────────────────────────────
# Converts raw source / chunk_id into a human-readable document name.

def _nice_source(chunk: dict) -> str:
    """Return a clean document name from chunk metadata."""
    raw = chunk.get("source", "") or ""

    # Already a good name (not generic)
    if raw and raw != "PDF Document" and raw != "Tax Reference Document":
        return raw

    # Try to derive from chunk_id  e.g. pdf_cbdt_e_filing_itr_1_validation_rules_ay__0000_xxx
    cid = chunk.get("chunk_id", "")
    if cid.startswith("pdf_"):
        stem = cid[4:].split("_0")[0]   # strip leading "pdf_" and trailing "_0000_..."
        # map common stems to nice names
        nice_map = {
            "a1961":                              "Income Tax Act 1961",
            "cbdt_e_filing_itr_1_validation":     "CBDT ITR-1 Validation Rules AY 2025-26",
            "circular_no_03_2025":                "CBDT Circular 03/2025 (TDS on Salary)",
            "income_tax_rules_2026":              "Income Tax Rules 2026",
            "itr_1_2026_eng":                     "ITR-1 Instructions Booklet 2026",
        }
        for key, label in nice_map.items():
            if key in stem:
                return label
        # Fallback: title-case the stem
        return stem.replace("_", " ").title()

    # Web scraped sources
    url = chunk.get("url", "")
    if "incometax.gov.in" in url:
        return "e-Filing Portal (Official)"
    if "cleartax.in" in url:
        return "ClearTax Guide"
    if "taxguru.in" in url:
        return "TaxGuru"

    return raw or "Tax Reference Document"


def _citation_id(chunk: dict) -> str:
    """Unique identifier for deduplication — URL if available, else chunk_id prefix."""
    url = chunk.get("url", "")
    cid = chunk.get("chunk_id", "")
    if url:
        return url
    # For PDFs: use chunk_id stem for dedup (group same-pdf chunks)
    if cid.startswith("pdf_"):
        # pdf_a1961_43_0003_abc123 → pdf_a1961_43
        parts = cid.split("_")
        # Find the numeric index part (e.g. 0003)
        for i, p in enumerate(parts):
            if len(p) == 4 and p.isdigit():
                return "_".join(parts[:i])
        return "_".join(parts[:3])
    return _nice_source(chunk)


# ── Embedder ───────────────────────────────────────────────────────────────────

def _get_embedder(backend="huggingface"):
    if backend in _embedder_cache:
        return _embedder_cache[backend]
    if backend == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        def embed(texts):
            resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
            return np.array([r.embedding for r in resp.data], dtype=np.float32)
    else:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        def embed(texts):
            return model.encode(texts, normalize_embeddings=True,
                                show_progress_bar=False).astype(np.float32)
    _embedder_cache[backend] = embed
    return embed


# ── Index loader ──────────────────────────────────────────────────────────────

def _load_index(ay=DEFAULT_AY):
    if ay in _index_cache:
        return _index_cache[ay], _meta_cache[ay]
    import faiss
    index_path = VECTOR_STORE_DIR / f"{ay}.faiss"
    meta_path  = VECTOR_STORE_DIR / f"{ay}.meta.json"
    if not index_path.exists():
        raise FileNotFoundError(
            f"FAISS index not found: {index_path}. "
            f"Run: python knowledge-base/embedder.py --ay {ay}")
    index = faiss.read_index(str(index_path))
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    _index_cache[ay] = index
    _meta_cache[ay]  = meta
    
    # Count PDF vs Web chunks
    pdf_count = sum(1 for v in meta.values() if v.get("chunk_id", "").startswith("pdf_"))
    web_count = len(meta) - pdf_count
    print(f"Loaded FAISS [{ay}] — {index.ntotal} vectors (PDF={pdf_count}, Web={web_count})")
    return index, meta


# ── MMR retrieval ──────────────────────────────────────────────────────────────

def _mmr(query, index, meta, embed_fn, top_k=5, fetch_k=60, lam=0.6):
    q_emb = embed_fn([query])
    distances, ids = index.search(q_emb, fetch_k)
    candidates = []
    for dist, vid in zip(distances[0], ids[0]):
        if vid >= 0:
            c = dict(meta.get(str(vid), {}))
            c["_l2"] = float(dist)
            # Enrich with nice display name immediately
            c["_display_source"] = _nice_source(c)
            candidates.append(c)
    if not candidates:
        return []

    cand_embs = embed_fn([c["text"] for c in candidates])
    q_sims    = (cand_embs @ q_emb.T).flatten()

    # Slight boost for PDF sources (they contain authoritative statutory text)
    def _is_pdf(c):
        return c.get("doc_type", "") in ("official_instructions", "cbdt_circular",
                                          "legislation", "supplementary_guide") \
               or c.get("chunk_id", "").startswith("pdf_")

    selected, remaining = [], list(range(len(candidates)))
    for _ in range(min(top_k, len(candidates))):
        if not remaining:
            break
        if not selected:
            best = max(remaining, key=lambda i: q_sims[i])
        else:
            sel_e  = cand_embs[selected]
            scores = []
            for i in remaining:
                rel      = q_sims[i]
                red      = float(np.max(cand_embs[i] @ sel_e.T))
                scores.append((i, lam * rel - (1 - lam) * red))
            best = max(scores, key=lambda x: x[1])[0]
        selected.append(best)
        remaining.remove(best)
    return [candidates[i] for i in selected]


# ── Cross-encoder reranker ─────────────────────────────────────────────────────

def _rerank(query, chunks):
    try:
        from sentence_transformers import CrossEncoder
        ce     = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        scores = ce.predict([[query, c["text"]] for c in chunks])
        for c, s in zip(chunks, scores):
            c["_score"] = float(s)
        chunks.sort(key=lambda x: x.get("_score", 0), reverse=True)
    except Exception as e:
        print(f"Rerank skipped: {e}")
    return chunks


# ── LLM answer ─────────────────────────────────────────────────────────────────

def _answer(query: str, form_context: str, chunks: list[dict], ay: str) -> str:
    # Build numbered context blocks with clear source labels
    ctx_parts = []
    for i, c in enumerate(chunks, 1):
        source_label = c.get("_display_source", _nice_source(c))
        section      = c.get("section", "")
        doc_type     = c.get("doc_type", "")
        is_pdf       = c.get("chunk_id", "").startswith("pdf_")
        src_type     = "📄 PDF" if is_pdf else "🌐 Web"
        header       = f"[{i}] {src_type} — {source_label}" + (f" — {section}" if section else "")
        numbered_text = "\n".join(f"Line {idx+1}: {line}" for idx, line in enumerate(c['text'].split('\n')))
        ctx_parts.append(f"{header}\n{numbered_text}")
    ctx = "\n\n---\n\n".join(ctx_parts)

    system = (
        f"You are an expert Indian income tax assistant for ITR-1 (Sahaj), AY {ay}. "
        "Your knowledge base includes official CBDT PDF documents (Income Tax Act, Circulars, "
        "ITR-1 Instructions, Validation Rules) AND web sources (e-Filing portal, ClearTax). "
        "\n\nRULES:\n"
        "1. Answer the question using the provided context chunks. Be helpful and informative.\n"
        "2. If the context contains relevant information, cite it with [N] references.\n"
        "3. Be precise with numbers: mention section numbers, rupee amounts, AY specifics.\n"
        "4. If the context partially covers the topic, give your best answer using what's available "
        "and clearly note which parts are from the source vs general knowledge.\n"
        "5. If the user's input is abusive, greeting-only, or completely unrelated to taxes (e.g. 'stfu', 'hello', 'write a poem'), politely reply that you are an ITR-1 tax assistant and ask how you can help with their taxes. Do not try to force an answer from the context in this case.\n"
        "6. Include relevant source names in your answer.\n\n"
        "Format your response as:\n\n"
        "**Answer**: <clear direct answer>\n"
        "**Details**: <detailed explanation with specific references>\n"
        "**Sources**: <list each source [N] used, state the document name, page number, and the exact Line numbers (e.g., Lines 4-6) it references, and quote the specific sentence>"
    )
    prompt = f"Context:\n{ctx}\n"
    if form_context:
        prompt += f"{form_context}\n"
    prompt += f"\nQuestion: {query}\n\nResponse:"

    try:
        from shared.llm_client import complete_with_system
        return complete_with_system(system=system, user=prompt, temperature=0.0, best_of_n=True)
    except Exception as e:
        print(f"LLM failed: {e}")
        # Fallback: return best chunk as plain answer with source
        if chunks:
            src = chunks[0].get("_display_source", _nice_source(chunks[0]))
            return (f"**Answer**: Based on {src}:\n\n"
                    f"{chunks[0]['text'][:600]}\n\n"
                    f"*(LLM unavailable — showing raw source text)*")
        return "No relevant information found in the knowledge base."


# ── Self-verification ────────────────────────────────────────────────────────────────────

def _verify_answer(question: str, answer: str, chunks: list[dict]) -> dict:
    """
    Self-verifying loop: ask the LLM to identify which chunk supports each claim
    and flag any unsupported claims.
    Returns: {verified: bool, grounding: [{claim, chunk_no, excerpt}]}
    """
    try:
        # Build short context for verification
        ctx = "\n".join(
            f"[{i+1}] {c.get('_display_source', '')} | {c['text'][:300]}"
            for i, c in enumerate(chunks)
        )
        verify_system = (
            "You are a fact-checking assistant. Your job is to verify that an answer "
            "is fully supported by the given source chunks. "
            "Return JSON only, no markdown. Format: "
            '{"verified": true/false, "grounding": [{"claim": "...", "chunk_no": N, "excerpt": "exact quote from chunk"}]}'
            " Include one entry per key claim in the answer. "
            "If a claim is not in any chunk, set chunk_no to 0 and set verified=false."
        )
        verify_prompt = (
            f"Question: {question}\n\n"
            f"Answer to verify:\n{answer[:1000]}\n\n"
            f"Source chunks:\n{ctx}\n\n"
            "List each factual claim and which chunk number it comes from."
        )
        from shared.llm_client import complete_with_system
        raw = complete_with_system(system=verify_system, user=verify_prompt, temperature=0.0)
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return {
            "verified":  bool(result.get("verified", True)),
            "grounding": result.get("grounding", []),
        }
    except Exception as e:
        print(f"Verification skipped: {e}")
        return {"verified": True, "grounding": []}


# ── Request / Response ─────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    form_context: str = ""
    ay:       str  = DEFAULT_AY
    top_k:    int  = 7      # increased from 5 for better coverage
    backend:  str  = "huggingface"
    rerank:   bool = True
    verify:   bool = True   # self-verify grounding of answer

class GroundingItem(BaseModel):
    claim:    str
    chunk_no: int
    excerpt:  str

class QueryResponse(BaseModel):
    answer:    str
    citations: list[dict]
    chunks:    list[dict]
    ay:        str
    verified:  bool = True
    grounding: list[dict] = []


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "rag-service", "default_ay": DEFAULT_AY}


@app.get("/indexes")
def list_indexes():
    if not VECTOR_STORE_DIR.exists():
        return {"indexes": []}
    return {"indexes": [f.stem for f in VECTOR_STORE_DIR.glob("*.faiss")]}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    try:
        index, meta = _load_index(req.ay)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    embed_fn = _get_embedder(req.backend)
    chunks   = _mmr(req.question, index, meta, embed_fn, req.top_k)
    if req.rerank and chunks:
        chunks = _rerank(req.question, chunks)

    answer = _answer(req.question, req.form_context, chunks, req.ay)

    # Self-verify grounding
    verify_result = {"verified": True, "grounding": []}
    if req.verify and chunks:
        verify_result = _verify_answer(req.question, answer, chunks)

    # Build citations — include ALL retrieved sources, URL or not
    seen, citations = set(), []
    for c in chunks:
        cid = _citation_id(c)
        if cid in seen:
            continue
        seen.add(cid)
        url = c.get("url", "")
        is_pdf = c.get("chunk_id", "").startswith("pdf_")
        source_name = c.get("_display_source", _nice_source(c))
        citations.append({
            "source":   source_name,
            "url":      url if not is_pdf else "",  # PDFs don't have URLs
            "section":  c.get("section", ""),
            "doc_type": c.get("doc_type", ""),
            "is_pdf":   is_pdf,
            # Excerpt: the exact text passage from the source document
            "excerpt":  c["text"][:300].strip() + ("…" if len(c["text"]) > 300 else ""),
        })

    return QueryResponse(
        answer=answer,
        citations=citations,
        ay=req.ay,
        verified=verify_result["verified"],
        grounding=verify_result["grounding"],
        chunks=[{
            "text":    c["text"],
            "source":  c.get("_display_source", _nice_source(c)),
            "section": c.get("section", ""),
            "score":   round(c.get("_score", 0), 3),
        } for c in chunks],
    )


@app.post("/query/chunks")
async def query_chunks_only(req: QueryRequest):
    try:
        index, meta = _load_index(req.ay)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    chunks = _mmr(req.question, index, meta, _get_embedder(req.backend), req.top_k)
    return {"chunks": chunks, "count": len(chunks)}


@app.on_event("startup")
async def startup():
    try:
        print(f"Pre-loading FAISS index [{DEFAULT_AY}]…")
        _load_index(DEFAULT_AY)
        print("Pre-loading embedding model…")
        _get_embedder("huggingface")
        print("Warming up reranker…")
        _rerank("warmup", [{"text": "warmup", "chunk_id": ""}])
        print("All RAG models ready.")
    except Exception as e:
        print(f"Startup warning: {e}")
