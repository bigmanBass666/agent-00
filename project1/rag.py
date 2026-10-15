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
import time
import requests
import numpy as np

VECTORS_PATH = "kb_vectors.npy"
CHUNKS_PATH = "kb_chunks.json"
RECALL_N = 20
TOP_K = 3
REFUSE_THRESHOLD = 0.3

EMBED_URL = "https://api.siliconflow.cn/v1/embeddings"
RERANK_URL = "https://api.siliconflow.cn/v1/rerank"
LLM_URL = "https://api.siliconflow.cn/v1/chat/completions"
EMBED_MODEL = "BAAI/bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
LLM_MODEL = "Qwen/Qwen3-8B"
TIMEOUT = 60


def load_api_key():
    key = os.environ.get("SILICONFLOW_API_KEY")
    if key:
        return key.strip()
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("SILICONFLOW_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("未找到 API key，请检查 .env 文件")


API_KEY = load_api_key()
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

SYSTEM_PROMPT = (
    "你是一个基于教材回答问题的课程助教。你必须严格遵守以下规则：\n"
    "1. 只能使用【资料】中提供的教材内容作为事实依据，绝对禁止使用你自己的内部知识。\n"
    "2. 资料中没有相关信息时，只输出：根据教材内容未找到相关信息。不要编造或推测。\n"
    "3. 每个事实性陈述后面必须标注教材页码，格式为【教材 p.XX】。如果一个陈述来自多页，标注【教材 p.XX-YY】。\n"
    "4. 用简单的中文解释，但保留关键术语的英文原文（例如：protein, macros, anabolic）。\n"
    "5. 不要大段复制教材原文，只能用短句引用和自己的话转述。连续引用不超过3个句子。\n"
    "6. 回答末尾用一句话总结来源章节。"
)
REFUSE_SENTENCE = "根据教材内容未找到相关信息。"


def load_kb():
    vectors = np.load(VECTORS_PATH)
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"知识库已加载: {len(chunks)} 个分块, 向量矩阵 {vectors.shape}")
    return chunks, vectors


def embed(text):
    resp = requests.post(EMBED_URL, headers=HEADERS,
                         json={"model": EMBED_MODEL, "input": text}, timeout=TIMEOUT)
    resp.raise_for_status()
    return np.array(resp.json()["data"][0]["embedding"], dtype=np.float32)


def retrieve(query, chunks, vectors):
    q_vec = embed(query)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    sims = (q_vec @ (vectors / norms).T).flatten()
    top_n_idx = np.argsort(sims)[::-1][:RECALL_N]
    candidates = [chunks[i] for i in top_n_idx]
    if not candidates:
        return []
    resp = requests.post(RERANK_URL, headers=HEADERS, json={
        "model": RERANK_MODEL, "query": query,
        "documents": [c["text"] for c in candidates],
        "top_n": min(TOP_K, len(candidates)), "return_documents": False,
    }, timeout=TIMEOUT)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return [(candidates[r["index"]], float(r["relevance_score"])) for r in results]


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


def ask(query, chunks, vectors):
    retrieved = retrieve(query, chunks, vectors)
    top_score = retrieved[0][1] if retrieved else 0.0
    print(f"  [检索] top_score={top_score:.4f}, 召回{len(retrieved)}块")
    if top_score < REFUSE_THRESHOLD:
        return {"answer": REFUSE_SENTENCE, "refused": True,
                "top_score": top_score, "sources": []}
    context_parts = []
    for chunk, score in retrieved:
        page_info = f"p.{chunk['page_start']}"
        if chunk["page_end"] != chunk["page_start"]:
            page_info = f"p.{chunk['page_start']}-{chunk['page_end']}"
        context_parts.append(
            f"【教材{page_info}｜章节：{chunk['chapter']}｜相关度={score:.4f}】\n{chunk['text'][:2000]}")
    context = "\n\n".join(context_parts)
    user_prompt = f"【资料】\n{context}\n\n【问题】{query}\n\n【回答】"
    answer = llm_call(SYSTEM_PROMPT, user_prompt)
    refused = answer.strip().startswith(REFUSE_SENTENCE)
    return {"answer": answer, "refused": refused, "top_score": top_score,
            "sources": [(c["page_start"], c["page_end"], c["chapter"]) for c, _ in retrieved]}


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
