# -*- coding: utf-8 -*-
"""
最小 RAG 骨架（项目一 · 真实 API 版）
====================================
embedding : BAAI/bge-m3（SiliconFlow，1024 维，免费）
精排      : BAAI/bge-reranker-v2-m3（SiliconFlow，免费）
LLM       : Qwen/Qwen3-8B（SiliconFlow，免费，需实名认证）
检索架构  : 两段式 —— embedding 粗召回 top-N → reranker 精排 top-k
配套语料  : corpus/os_ch1.txt
运行      : python 12_最小RAG骨架.py
"""

import re
import time
import requests
import numpy as np

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3
RECALL_N = 20
REFUSE_THRESHOLD = 0.5
DOCS_PATH = "corpus/os_ch1.txt"

API_KEY = "sk-fsaaxrhrfijelnmwjvpifugzoiahnjygylgemmcroxdmxaqw"
EMBED_URL = "https://api.siliconflow.cn/v1/embeddings"
RERANK_URL = "https://api.siliconflow.cn/v1/rerank"
LLM_URL = "https://api.siliconflow.cn/v1/chat/completions"
EMBED_MODEL = "BAAI/bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
LLM_MODEL = "Qwen/Qwen3-8B"
TIMEOUT = 30
BATCH_SIZE = 32
USE_MOCK_LLM = False

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

SYSTEM_PROMPT = (
    "你是课程助教。请依据【资料】回答问题，答案必须来自资料内容。"
    "只有当资料中完全没有相关信息时，才输出且仅输出：课程资料中未找到相关内容。"
    "回答末尾注明来源段落编号。"
)
REFUSE_SENTENCE = "课程资料中未找到相关内容。"


def load_and_chunk(path: str):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    sections = re.split(r"(?=【\d+\.\d+)", text)
    chunks = []
    chunk_id = 0
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        header_match = re.match(r"(【[^】]+】)", sec)
        source = header_match.group(1) if header_match else "未知章节"
        if len(sec) <= CHUNK_SIZE:
            chunks.append({"chunk_id": chunk_id, "text": sec, "source": source})
            chunk_id += 1
            continue
        start = 0
        while start < len(sec):
            end = min(start + CHUNK_SIZE, len(sec))
            piece = sec[start:end].strip()
            if piece:
                chunks.append({"chunk_id": chunk_id, "text": piece, "source": source})
                chunk_id += 1
            if end >= len(sec):
                break
            start = end - CHUNK_OVERLAP
    return chunks


def embed(text: str) -> np.ndarray:
    resp = requests.post(EMBED_URL, headers=HEADERS,
                         json={"model": EMBED_MODEL, "input": text}, timeout=TIMEOUT)
    resp.raise_for_status()
    return np.array(resp.json()["data"][0]["embedding"], dtype=np.float32)


def embed_documents(texts: list) -> np.ndarray:
    all_vecs = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        resp = requests.post(EMBED_URL, headers=HEADERS,
                             json={"model": EMBED_MODEL, "input": batch}, timeout=TIMEOUT)
        resp.raise_for_status()
        sorted_data = sorted(resp.json()["data"], key=lambda x: x["index"])
        all_vecs.extend([item["embedding"] for item in sorted_data])
    return np.array(all_vecs, dtype=np.float32)


def rerank(query: str, docs: list, top_k: int = TOP_K) -> list:
    if not docs:
        return []
    resp = requests.post(RERANK_URL, headers=HEADERS, json={
        "model": RERANK_MODEL, "query": query, "documents": docs,
        "top_n": min(top_k, len(docs)), "return_documents": False,
    }, timeout=TIMEOUT)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return [(item["index"], float(item["relevance_score"])) for item in results]


def retrieve(query: str, chunks: list, chunk_embeddings: np.ndarray,
             top_k: int = TOP_K, recall_n: int = RECALL_N) -> list:
    if not chunks:
        return []
    q_vec = embed(query)
    norms = np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    sims = (q_vec @ (chunk_embeddings / norms).T).flatten()
    recall_n = min(recall_n, len(chunks))
    top_n_idx = np.argsort(sims)[::-1][:recall_n]
    candidates = [chunks[i] for i in top_n_idx]
    candidate_texts = [c["text"] for c in candidates]
    reranked = rerank(query, candidate_texts, top_k=top_k)
    return [(candidates[idx], score) for idx, score in reranked]


def llm_call(system_prompt: str, user_prompt: str, max_retries: int = 2) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "top_p": 0.7,
        "max_tokens": 1024,
        "stream": False,
        "enable_thinking": False,
    }
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(LLM_URL, headers=HEADERS, json=payload, timeout=TIMEOUT)
            if resp.status_code == 429:
                if attempt < max_retries:
                    wait = 2 ** attempt
                    print(f"  [429 限流] {wait}s 后重试...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < max_retries:
                time.sleep(1)
                continue
            raise RuntimeError(f"LLM 调用失败: {e}")
    raise RuntimeError("LLM 重试次数已耗尽")


def mock_llm(prompt: str) -> str:
    return ("[模拟回答] 已依据检索到的资料生成回答。\n"
            "（接入真实 LLM 接口后，此处将返回基于资料的实际生成内容。）")


def answer(query: str, retrieved: list) -> str:
    if not retrieved:
        return REFUSE_SENTENCE
    context_parts = []
    for chunk, score in retrieved:
        context_parts.append(
            f"【资料 {chunk['chunk_id']}｜来源：{chunk['source']}｜相关度={score:.4f}】\n{chunk['text']}")
    context = "\n\n".join(context_parts)
    user_prompt = f"【资料】\n{context}\n\n【问题】{query}\n\n【回答】"
    if USE_MOCK_LLM:
        return mock_llm(user_prompt)
    return llm_call(SYSTEM_PROMPT, user_prompt)


def rag_query(query: str, chunks: list, chunk_embeddings: np.ndarray) -> dict:
    retrieved = retrieve(query, chunks, chunk_embeddings)
    top_score = float(retrieved[0][1]) if retrieved else 0.0
    if top_score < REFUSE_THRESHOLD:
        return {"query": query, "answer": REFUSE_SENTENCE,
                "refused": True, "sources": [], "top_score": top_score}
    ans = answer(query, retrieved)
    llm_refused = ans.strip().startswith(REFUSE_SENTENCE)
    return {"query": query, "answer": ans, "refused": llm_refused,
            "sources": [c["chunk_id"] for c, _ in retrieved], "top_score": top_score}


if __name__ == "__main__":
    chunks = load_and_chunk(DOCS_PATH)
    print(f"共加载 {len(chunks)} 个分块，正在预计算语料 embedding...")
    chunk_embeddings = embed_documents([c["text"] for c in chunks])
    print(f"embedding 矩阵形状: {chunk_embeddings.shape}")
    for c in chunks:
        print(f"  chunk {c['chunk_id']}: {c['source']}（{len(c['text'])} 字）")
    test_queries = [
        "什么是进程？进程和程序有什么区别？",
        "进程有哪几种状态？",
        "进程和线程有什么区别？",
        "明天天气怎么样？",
    ]
    for q in test_queries:
        print(f"\n{'=' * 55}")
        print(f"问题: {q}")
        result = rag_query(q, chunks, chunk_embeddings)
        print(f"  top_score : {result['top_score']:.4f}（阈值 {REFUSE_THRESHOLD}）")
        print(f"  refused   : {result['refused']}")
        print(f"  sources   : {result['sources']}")
        print(f"  回答      : {result['answer']}")
