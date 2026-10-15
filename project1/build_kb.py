# -*- coding: utf-8 -*-
"""
知识库构建脚本（Phase 1）
=========================
输入: textbook.pdf
输出: kb_vectors.npy  (N, 1024) 向量矩阵
      kb_chunks.json   每个 chunk 的元数据

用法: python build_kb.py
"""
import os
import re
import json
import numpy as np
import fitz  # PyMuPDF

PDF_PATH = "textbook.pdf"
VECTORS_PATH = "kb_vectors.npy"
CHUNKS_PATH = "kb_chunks.json"

CHUNK_CHARS = 3500
CHUNK_OVERLAP = 300
MIN_CHUNK_CHARS = 200

EMBED_URL = "https://api.siliconflow.cn/v1/embeddings"
EMBED_MODEL = "BAAI/bge-m3"
BATCH_SIZE = 32
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


def extract_pages(pdf_path):
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    page_chapter = {}
    for level, title, page in toc:
        page_chapter[page] = title.strip()
    current_chapter = "前言/目录"
    pages = []
    for i in range(1, len(doc) + 1):
        if i in page_chapter:
            current_chapter = page_chapter[i]
        text = doc[i - 1].get_text().strip()
        text = re.sub(r"Copyright.*?\d{4}.*?\n", "", text)
        text = re.sub(r"www\.\w+\.\w+", "", text)
        text = re.sub(r"Back to Table of Contents", "", text)
        text = text.strip()
        pages.append({"page": i, "text": text, "chapter": current_chapter})
    doc.close()
    return pages


def build_chunks(pages):
    chunks = []
    current_text = ""
    current_start_page = None
    current_chapter = None
    for p in pages:
        if not p["text"]:
            continue
        if current_start_page is None:
            current_start_page = p["page"]
            current_chapter = p["chapter"]
        if current_chapter != p["chapter"] and len(current_text) > MIN_CHUNK_CHARS:
            chunks.append(_make_chunk(current_text, current_start_page, p["page"] - 1, current_chapter))
            current_text = ""
            current_start_page = p["page"]
            current_chapter = p["chapter"]
        current_text += "\n" + p["text"]
        while len(current_text) >= CHUNK_CHARS:
            split_at = CHUNK_CHARS
            for nl in range(CHUNK_CHARS, max(CHUNK_CHARS - 200, 0), -1):
                if nl < len(current_text) and current_text[nl] in ".\n":
                    split_at = nl + 1
                    break
            piece = current_text[:split_at].strip()
            if piece:
                chunks.append(_make_chunk(piece, current_start_page, p["page"], current_chapter))
            current_text = current_text[split_at - CHUNK_OVERLAP:].strip()
            current_start_page = p["page"]
    if current_text and len(current_text) > MIN_CHUNK_CHARS:
        last_page = pages[-1]["page"]
        chunks.append(_make_chunk(current_text, current_start_page, last_page, current_chapter))
    for i, c in enumerate(chunks):
        c["chunk_id"] = i
    return chunks


def _make_chunk(text, page_start, page_end, chapter):
    return {"text": text, "page_start": page_start, "page_end": page_end, "chapter": chapter}


def embed_batch(texts):
    import requests
    all_vecs = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        resp = requests.post(EMBED_URL, headers=HEADERS,
                             json={"model": EMBED_MODEL, "input": batch}, timeout=TIMEOUT)
        resp.raise_for_status()
        sorted_data = sorted(resp.json()["data"], key=lambda x: x["index"])
        all_vecs.extend([item["embedding"] for item in sorted_data])
        print(f"  已嵌入 {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")
    return np.array(all_vecs, dtype=np.float32)


if __name__ == "__main__":
    print("=" * 55)
    print("Step 1: 提取 PDF 页面文字...")
    pages = extract_pages(PDF_PATH)
    text_pages = [p for p in pages if p["text"]]
    print(f"  共 {len(pages)} 页，其中 {len(text_pages)} 页有文字")
    print("\nStep 2: 分块...")
    chunks = build_chunks(pages)
    print(f"  共 {len(chunks)} 个分块")
    chapters = set(c["chapter"] for c in chunks)
    print(f"  覆盖 {len(chapters)} 个章节")
    avg_len = sum(len(c["text"]) for c in chunks) / len(chunks)
    print(f"  平均块长: {avg_len:.0f} 字符")
    print("\nStep 3: bge-m3 向量化...")
    texts = [c["text"] for c in chunks]
    vectors = embed_batch(texts)
    print(f"  向量矩阵: {vectors.shape}")
    print("\nStep 4: 保存...")
    np.save(VECTORS_PATH, vectors)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"  向量已保存: {VECTORS_PATH}")
    print(f"  元数据已保存: {CHUNKS_PATH}")
    print("\n知识库构建完成！")
