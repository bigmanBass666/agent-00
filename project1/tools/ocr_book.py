# -*- coding: utf-8 -*-
"""
扫描版 PDF → 带页码的纯文本（tesseract OCR，多进程）
=====================================================
用途：教材是扫描件（无文本层）时，先把书 OCR 成带 [PAGE n] 标记的 txt，
      再交给 build_kb.py 建库（build_kb 支持 --txt 输入）。

用法:
    python tools/ocr_book.py <src.pdf> <out.txt> <out_pages.json>
环境变量:
    OCR_DPI=200   渲染精度（默认 200，学术书 200-250 足够）
    OCR_WORKERS=3 并行进程数
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool

import pymupdf

DPI = int(os.environ.get("OCR_DPI", "200"))
WORKERS = int(os.environ.get("OCR_WORKERS", "3"))

SRC = os.path.abspath(sys.argv[1])
OUT_TXT = os.path.abspath(sys.argv[2])
OUT_JSON = os.path.abspath(sys.argv[3])


def ocr_one(i):
    """OCR 第 i 页，返回 (页码0基, 文本)"""
    doc = pymupdf.open(SRC)
    try:
        pix = doc[i].get_pixmap(dpi=DPI)
        png = pix.tobytes("png")
    finally:
        doc.close()
    fd, fn = tempfile.mkstemp(suffix=".png")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(png)
        r = subprocess.run(
            ["tesseract", fn, "stdout", "-l", "chi_sim", "--psm", "3"],
            capture_output=True, text=True,
        )
        return i, r.stdout
    finally:
        os.unlink(fn)


_PAGE_NO = re.compile(r"^\s*[-—–]?\s*\d{1,4}\s*[-—–]?\s*$")
_CJK = re.compile(r"[\u4e00-\u9fff]")


def clean(text):
    """去页码行、去 OCR 常见噪声、合并被硬换行切开的段落"""
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            lines.append("")           # 保留空行作为段落边界
            continue
        if _PAGE_NO.match(s):          # 纯页码
            continue
        if len(s) <= 2 and not _CJK.search(s):   # 单字符噪声
            continue
        lines.append(s)
    # 合并：上一行不以句末标点结尾 + 本行不以缩进/短句开头 → 视为同一段
    merged = []
    for s in lines:
        if not s:
            if merged and merged[-1] != "":
                merged.append("")
            continue
        if (merged and merged[-1] and not _ENDS.search(merged[-1])
                and len(merged[-1]) > 12 and len(s) > 12):
            merged[-1] += s
        else:
            merged.append(s)
    return "\n".join(merged)


_ENDS = re.compile(r"[。！？；：”’」』)】…]$")

_CHAPTER = re.compile(r"^第\s*[一二三四五六七八九十百零0-9]+\s*章[\s　:：]*(.{0,40})$")


def main():
    doc = pymupdf.open(SRC)
    n = doc.page_count
    doc.close()
    print(f"[ocr] {os.path.basename(SRC)} 共 {n} 页，DPI={DPI}，并行 {WORKERS}", flush=True)

    t0 = time.time()
    pages = [None] * n
    done = 0
    with Pool(WORKERS) as pool:
        for i, text in pool.imap_unordered(ocr_one, range(n), chunksize=1):
            pages[i] = clean(text)
            done += 1
            if done % 20 == 0 or done == n:
                el = time.time() - t0
                print(f"[ocr] {done}/{n} 页  已用 {el:.0f}s  预计剩余 {el/done*(n-done):.0f}s", flush=True)

    # 章节识别：扫到 "第X章 标题" 就切换当前章节
    records = []
    chapter = "前言"
    for i, text in enumerate(pages):
        text = text or ""
        for ln in text.splitlines():
            m = _CHAPTER.match(ln.strip())
            if m and len(ln.strip()) <= 40:
                chapter = ln.strip()
                break
        records.append({"page": i + 1, "text": text, "chapter": chapter})

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(f"\n\n[PAGE {r['page']}]\n{r['text']}")

    print(f"[ocr] 完成：{n} 页，用时 {(time.time()-t0)/60:.1f} 分钟 → {OUT_TXT}", flush=True)


if __name__ == "__main__":
    main()
