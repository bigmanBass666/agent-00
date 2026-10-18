# -*- coding: utf-8 -*-
"""
RAG 问答系统（Phase 2）
======================
加载 build_kb.py 构建的知识库，回答问题并附带教材页码引用。
满足 R1~R6 行为约束。
用法: python rag.py
"""
import os
import json
import re
import time
import requests
import numpy as np
from config import (
    VECTORS_PATH, CHUNKS_PATH,
    RECALL_N, TOP_K, REFUSE_THRESHOLD, HYBRID_RECALL,
    EMBED_URL, RERANK_URL, LLM_URL,
    EMBED_MODEL, RERANK_MODEL, LLM_MODEL,
    TIMEOUT, HEADERS,
)

# -----------------------------------------------------------------
# 系统提示词（交付物 3）：从独立文本文件加载，便于单独评审与版本管理
# -----------------------------------------------------------------
_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "prompt", "system_prompt.txt")
if os.path.exists(_PROMPT_PATH):
    with open(_PROMPT_PATH, encoding="utf-8") as _f:
        SYSTEM_PROMPT = _f.read().strip()
else:
    SYSTEM_PROMPT = (
        "你是基于《The Anabolic Cookbook 2.0》回答问题的助手。严格遵守以下规则：\n"
        "1. 只能使用【资料】提供的内容作为事实依据，绝对禁止使用内部知识补充数字、用量、步骤或结论。\n"
        "2. 拒答判定分三种情况：\n"
        "   a) 【资料】与问题完全无关 → 只输出：根据教材内容未找到相关信息。\n"
        "   b) 【资料】只有部分相关内容 → 基于相关部分回答，并明确指出资料中未覆盖的部分，不得用常识补全。\n"
        "   c) 问题没有指明具体菜品、食谱或参数，无法确定回答哪一条（如“怎么做菜”“该吃什么”）"
        "→ 只输出：问题过于宽泛，请指明具体食谱或菜品。\n"
        "3. 每个事实性陈述后标注页码，格式【教材 p.XX】；跨页用【教材 p.XX-YY】。\n"
        "4. 用简洁中文回答，专业术语可在括号中保留英文原词（如 乳清蛋白(whey)），禁止中英拼接造词。\n"
        "5. 以转述为主：不得连续照抄资料原文超过 2 句，不得整段罗列原步骤，应概括要点。\n"
        "6. 必须紧扣提问中的具体对象作答，不得自行挑选一个菜谱代答；回答末尾用一句话点明来源章节。"
    )
REFUSE_SENTENCE = "根据教材内容未找到相关信息。"
VAGUE_SENTENCE = "问题过于宽泛"

STOPWORDS = {"the", "a", "an", "is", "are", "was", "do", "does", "did", "i",
             "how", "what", "which", "who", "when", "where", "why", "to", "in",
             "into", "of", "for", "and", "or", "with", "should", "my", "can", "could",
             "you", "your", "it", "this", "that", "on", "at", "be", "there", "me",
             "many", "much", "some", "any", "get", "make", "need", "want", "go",
             "goes", "use", "using", "used", "put", "recipe", "recipes"}
WORD_RE = re.compile(r"[a-z0-9]+")
LEXICAL_PASS = 0.85      # 词汇信号放行线：reranker 低分但实词几乎全覆盖时仍交 LLM 判断


def load_kb(verbose=True):
    vectors = np.load(VECTORS_PATH)
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)
    if verbose:
        print(f"知识库已加载: {len(chunks)} 个分块, 向量矩阵 {vectors.shape}")
    return chunks, vectors


def embed(text):
    resp = requests.post(EMBED_URL, headers=HEADERS,
                         json={"model": EMBED_MODEL, "input": text}, timeout=TIMEOUT)
    resp.raise_for_status()
    return np.array(resp.json()["data"][0]["embedding"], dtype=np.float32)


def lexical_recall(query, chunks):
    """IDF 加权词汇召回：实词命中越罕见越可信（救表格/短事实类查询）
    返回 [(score, chunk_index)]，score ∈ [0,1] 为 IDF 加权覆盖率。"""
    import math
    q_terms = set(WORD_RE.findall(query.lower())) - STOPWORDS
    if not q_terms:
        return []
    N = len(chunks)
    chunk_terms = [set(WORD_RE.findall(c["text"].lower())) for c in chunks]
    df = {t: sum(1 for ts in chunk_terms if t in ts) for t in q_terms}
    idf = {t: math.log((N + 1) / (df[t] + 1)) + 1 for t in q_terms}
    total = sum(idf.values())
    scored = []
    for i, ts in enumerate(chunk_terms):
        hit_w = sum(idf[t] for t in q_terms if t in ts)
        if hit_w:
            scored.append((hit_w / total, i))
    scored.sort(key=lambda x: -x[0])
    return scored


def retrieve(query, chunks, vectors):
    """两段式检索：embedding 粗召回 top-N (+IDF 词汇召回) → reranker 精排 top-k
    返回 (results, lexical_best_score)"""
    q_vec = embed(query)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    sims = (q_vec @ (vectors / norms).T).flatten()
    dense_idx = list(np.argsort(sims)[::-1][:RECALL_N])

    lex_scored = lexical_recall(query, chunks) if HYBRID_RECALL else []
    lex_best = lex_scored[0][0] if lex_scored else 0.0
    if HYBRID_RECALL:
        lex_idx = [i for _, i in lex_scored[:RECALL_N]]
        merged = list(dict.fromkeys(dense_idx + lex_idx))  # 顺序去重
    else:
        merged = dense_idx
    candidates = [chunks[i] for i in merged]

    if not candidates:
        return [], lex_best
    resp = requests.post(RERANK_URL, headers=HEADERS, json={
        "model": RERANK_MODEL, "query": query,
        "documents": [c["text"] for c in candidates],
        "top_n": min(TOP_K, len(candidates)), "return_documents": False,
    }, timeout=TIMEOUT)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return [(candidates[r["index"]], float(r["relevance_score"])) for r in results], lex_best


def llm_call(system_prompt, user_prompt, max_retries=3):
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
        "stream": False,
        "enable_thinking": False,
    }
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(LLM_URL, headers=HEADERS, json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"  [网络波动] {wait}s 后重试 ({attempt+1}/{max_retries})...")
                time.sleep(wait)
                continue
            raise


def knowledge_search(query, top_k=None):
    """检索工具/函数（交付物 2）
    查询本地知识库，返回带页码的片段列表。等效于框架中的 knowledge_search 工具。

    Args:
        query: 用户问题
        top_k: 返回条数，默认 config.TOP_K
    Returns:
        [{"text","page_start","page_end","chapter","score","citation"}, ...]
    """
    chunks, vectors = load_kb(verbose=False)
    results, lex_best = retrieve(query, chunks, vectors)
    if top_k:
        results = results[:top_k]
    out = []
    for c, s in results:
        page = f"p.{c['page_start']}" if c["page_start"] == c["page_end"] \
            else f"p.{c['page_start']}-{c['page_end']}"
        out.append({
            "text": c["text"],
            "page_start": c["page_start"],
            "page_end": c["page_end"],
            "chapter": c["chapter"],
            "score": round(float(s), 4),
            "citation": f"【教材 {page}】",
        })
    return out


def ask(query, chunks, vectors):
    retrieved, lex_best = retrieve(query, chunks, vectors)
    top_score = retrieved[0][1] if retrieved else 0.0
    print(f"  [检索] top_score={top_score:.4f}, lex={lex_best:.3f}, 召回{len(retrieved)}块")

    if top_score < REFUSE_THRESHOLD and lex_best < LEXICAL_PASS:
        return {"answer": REFUSE_SENTENCE, "refused": True,
                "top_score": top_score, "lex_best": lex_best,
                "sources": [], "hits": [], "context": ""}

    context_parts = []
    for chunk, score in retrieved:
        page_info = f"p.{chunk['page_start']}"
        if chunk["page_end"] != chunk["page_start"]:
            page_info = f"p.{chunk['page_start']}-{chunk['page_end']}"
        context_parts.append(
            f"【教材{page_info}｜章节：{chunk['chapter']}｜相关度={score:.4f}】\n{chunk['text']}")
    context = "\n\n".join(context_parts)
    user_prompt = f"【资料】\n{context}\n\n【问题】{query}\n\n【回答】"

    answer = llm_call(SYSTEM_PROMPT, user_prompt)
    stripped = answer.strip()
    refused = stripped.startswith(REFUSE_SENTENCE) or stripped.startswith(VAGUE_SENTENCE)

    return {"answer": answer, "refused": refused, "top_score": top_score,
            "lex_best": lex_best,
            "sources": [(c["page_start"], c["page_end"], c["chapter"]) for c, _ in retrieved],
            "hits": [{
                "page_start": c["page_start"], "page_end": c["page_end"],
                "chapter": c["chapter"], "score": round(float(s), 4),
                "snippet": c["text"][:320],
            } for c, s in retrieved],
            "context": context}


if __name__ == "__main__":
    chunks, vectors = load_kb()
    test_queries = [
        "How do I make protein French toast?",
        "What temperature should I bake egg bites at?",
        "How to make high protein lasagna?",
        "How do I write a Python program?",
    ]
    for q in test_queries:
        print(f"\n{'=' * 55}")
        print(f"问题: {q}")
        result = ask(q, chunks, vectors)
        print(f"  拒答: {result['refused']}")
        print(f"  来源: {result['sources']}")
        print(f"  回答: {result['answer']}")

    print(f"\n{'=' * 55}")
    print("【检索工具 knowledge_search 演示（交付物 2）】")
    for hit in knowledge_search("What temperature should I bake egg white bites at?"):
        print(f"  {hit['citation']} | {hit['chapter']} | score={hit['score']}")
