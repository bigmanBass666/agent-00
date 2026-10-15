# -*- coding: utf-8 -*-
"""
知识库校验脚本
==============
建库后运行，检查块数、章节覆盖率、页码完整性、检索可用性。
用法: python validate_kb.py
"""
import os
import json
import numpy as np
from config import VECTORS_PATH, CHUNKS_PATH, EMBED_URL, EMBED_MODEL, TIMEOUT, HEADERS
import requests


def check_files():
    """检查知识库文件是否存在且格式正确"""
    errors = []
    if not os.path.exists(VECTORS_PATH):
        errors.append(f"缺少向量文件: {VECTORS_PATH}")
    if not os.path.exists(CHUNKS_PATH):
        errors.append(f"缺少元数据文件: {CHUNKS_PATH}")
    return errors


def check_consistency(chunks, vectors):
    """检查向量数与块数一致"""
    errors = []
    if len(chunks) != vectors.shape[0]:
        errors.append(f"块数({len(chunks)})与向量数({vectors.shape[0]})不一致")
    if vectors.shape[1] != 1024:
        errors.append(f"向量维度异常: {vectors.shape[1]} (预期 1024)")
    return errors


def check_metadata(chunks):
    """检查每个块的元数据完整性"""
    errors = []
    warnings = []
    missing_page = 0
    missing_chapter = 0
    too_short = 0
    for c in chunks:
        if "page_start" not in c or "page_end" not in c:
            missing_page += 1
        if "chapter" not in c or not c["chapter"]:
            missing_chapter += 1
        if len(c.get("text", "")) < 100:
            too_short += 1
    if missing_page:
        errors.append(f"{missing_page} 个块缺少页码信息")
    if missing_chapter:
        errors.append(f"{missing_chapter} 个块缺少章节信息")
    if too_short:
        warnings.append(f"{too_short} 个块过短(<100字符)")
    return errors, warnings


def check_chapter_coverage(chunks):
    """统计章节覆盖率"""
    chapters = {}
    for c in chunks:
        ch = c.get("chapter", "未知")
        chapters[ch] = chapters.get(ch, 0) + 1
    total = len(chunks)
    multi_chunk = sum(1 for v in chapters.values() if v >= 2)
    return {
        "总章节数": len(chapters),
        "总分块数": total,
        "含多个分块的章节数": multi_chunk,
        "单块章节数": len(chapters) - multi_chunk,
    }


def retrieval_smoke_test(chunks, vectors, n_tests=3):
    """用几个块的原文做检索测试，验证能检索回自身"""
    import random
    random.seed(42)
    test_indices = random.sample(range(len(chunks)), min(n_tests, len(chunks)))
    results = []
    for idx in test_indices:
        query = chunks[idx]["text"][:200]
        q_vec = _embed(query)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        sims = (q_vec @ (vectors / norms).T).flatten()
        top_idx = int(np.argmax(sims))
        top_sim = float(sims[top_idx])
        recovered = top_idx == idx
        results.append({
            "query_chunk": idx,
            "top1_chunk": top_idx,
            "top1_score": top_sim,
            "self_recovered": recovered,
        })
    return results


def _embed(text):
    resp = requests.post(EMBED_URL, headers=HEADERS,
                         json={"model": EMBED_MODEL, "input": text}, timeout=TIMEOUT)
    resp.raise_for_status()
    return np.array(resp.json()["data"][0]["embedding"], dtype=np.float32)


if __name__ == "__main__":
    print("=" * 55)
    print("知识库校验")
    print("=" * 55)

    all_errors = []
    all_warnings = []

    print("\n[1/4] 文件检查...")
    errors = check_files()
    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        all_errors.extend(errors)
    else:
        print("  ✓ 向量文件和元数据文件都存在")

    if all_errors:
        print("\n校验失败：缺少必要文件，无法继续。")
        exit(1)

    vectors = np.load(VECTORS_PATH)
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)

    print("\n[2/4] 一致性检查...")
    errors = check_consistency(chunks, vectors)
    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        all_errors.extend(errors)
    else:
        print(f"  ✓ 块数={len(chunks)}, 向量矩阵={vectors.shape}, 一致")

    print("\n[3/4] 元数据检查...")
    errors, warnings = check_metadata(chunks)
    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        all_errors.extend(errors)
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")
        all_warnings.extend(w)
    if not errors and not warnings:
        print("  ✓ 所有块的页码和章节信息完整")

    coverage = check_chapter_coverage(chunks)
    print(f"  章节覆盖: {coverage['总章节数']} 个章节, {coverage['总分块数']} 个分块")
    print(f"  含多块的章节: {coverage['含多个分块的章节数']}, 单块章节: {coverage['单块章节数']}")

    print("\n[4/4] 检索冒烟测试...")
    try:
        results = retrieval_smoke_test(chunks, vectors)
        recovered = sum(1 for r in results if r["self_recovered"])
        print(f"  自检索命中率: {recovered}/{len(results)}")
        for r in results:
            status = "✓" if r["self_recovered"] else "✗"
            print(f"  {status} 查询块{r['query_chunk']} → top1块{r['top1_chunk']} (score={r['top1_score']:.4f})")
        if recovered < len(results):
            all_warnings.append(f"自检索命中率 {recovered}/{len(results)}，可能分块质量有问题")
    except Exception as e:
        print(f"  ⚠ 检索测试失败: {e}")
        all_warnings.append(f"检索测试失败: {e}")

    print("\n" + "=" * 55)
    if all_errors:
        print(f"校验结果: 失败 ({len(all_errors)} 个错误)")
        for e in all_errors:
            print(f"  ✗ {e}")
        exit(1)
    elif all_warnings:
        print(f"校验结果: 通过 ({len(all_warnings)} 个警告)")
        for w in all_warnings:
            print(f"  ⚠ {w}")
    else:
        print("校验结果: 全部通过 ✓")
