# -*- coding: utf-8 -*-
"""
知识库构建脚本（Phase 1）
=========================
输入: config.PDF_PATH
输出: kb_vectors.npy (N, 1024) + kb_chunks.json
用法: python build_kb.py
"""
import re
import os
import json
import requests
import numpy as np
import fitz  # PyMuPDF
from config import (
    PDF_PATH, VECTORS_PATH, CHUNKS_PATH,
    CHUNK_CHARS, CHUNK_OVERLAP, MIN_CHUNK_CHARS, CHUNK_TARGET_MIN,
    EMBED_URL, EMBED_MODEL, BATCH_SIZE, TIMEOUT, HEADERS,
)


def extract_pages(pdf_path):
    """提取每页文字，用书签(TOC)标注章节归属"""
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
    """按字符数分块，记录 page_start/page_end/chapter"""
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

        if current_chapter != p["chapter"] and len(current_text) >= CHUNK_TARGET_MIN:
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


def extract_table_chunks(pdf_path):
    """把 PDF 表格抽成结构化句子块（解决 get_text() 把表格压平、行列关系丢失的问题）

    转换规则：
      - 2 列表     → "A = B"（单位换算表）
      - 首列为 Page → "菜名 (p.XX): 列=值, ..."（营养数据表）
      - 其他       → "名称: 列=值, ..."（蔬果份量表）
    """
    doc = fitz.open(pdf_path)
    out = []
    for pno in range(1, len(doc) + 1):
        page = doc[pno - 1]
        try:
            tabs = page.find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            rows = [[("" if c is None else str(c).replace("\n", " ").strip()) for c in r]
                    for r in t.extract()]
            if len(rows) < 2:
                continue
            header = rows[0]
            # 过滤低价值元信息表（准备时间/难度/素食标记），只保留真正的数据表
            h0 = re.sub(r"\s+", "", header[0]).upper() if header else ""
            if "PREPTIME" in h0 or "DIFFICULTY" in h0:
                continue
            lines = []
            if len(header) == 2:
                for r in rows[1:]:
                    if r[0] and r[1]:
                        lines.append(f"{r[0]} = {r[1]}")
                title = f"【换算/对照表 p.{pno}｜{header[0]} / {header[1]}】"
            elif header and header[0].lower() == "page" and len(header) >= 3:
                for r in rows[1:]:
                    if not any(r):
                        continue
                    name = r[1] if len(r) > 1 else r[0]
                    pairs = [f"{h}={v}" for h, v in zip(header[2:], r[2:]) if v]
                    if pairs:
                        lines.append(f"{name} (p.{r[0]}): " + ", ".join(pairs))
                title = f"【营养数据表 p.{pno}｜列：{' / '.join(header)}】"
            else:
                for r in rows[1:]:
                    if not any(r):
                        continue
                    pairs = [f"{h}={v}" for h, v in zip(header[1:], r[1:]) if v]
                    if pairs:
                        lines.append(f"{r[0]}: " + ", ".join(pairs))
                title = f"【数据表 p.{pno}｜列：{' / '.join(header)}】"
            if not lines:
                continue
            out.append({
                "text": title + "\n" + "\n".join(lines),
                "page_start": pno, "page_end": pno,
                "chapter": f"表格数据 - {header[0]}",
            })
    doc.close()
    return out


def embed_batch(texts):
    """批量向量化（bge-m3）"""
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
    print(f"Step 1: 提取 PDF 页面文字 ({PDF_PATH})...")
    pages = extract_pages(PDF_PATH)
    text_pages = [p for p in pages if p["text"]]
    print(f"  共 {len(pages)} 页，其中 {len(text_pages)} 页有文字")

    print("\nStep 2: 分块...")
    chunks = build_chunks(pages)
    print(f"  正文分块: {len(chunks)} 块")
    if os.environ.get("USE_TABLE_CHUNKS", "1") != "0":
        table_chunks = extract_table_chunks(PDF_PATH)
        print(f"  表格结构化: {len(table_chunks)} 个表格块（解决表格压平问题）")
        chunks = chunks + table_chunks
        chunks.sort(key=lambda c: (c["page_start"], 0 if "表格" not in c["chapter"] else 1))
        for i, c in enumerate(chunks):
            c["chunk_id"] = i
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
    print(f"  向量: {VECTORS_PATH}")
    print(f"  元数据: {CHUNKS_PATH}")
    print("\n知识库构建完成！")
