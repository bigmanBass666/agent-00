# -*- coding: utf-8 -*-
"""
项目一评测脚本
==============
用法: python run_eval.py
功能: 加载 eval_set.jsonl，逐条调用 RAG，自动判定拒答正确性，输出 results.jsonl 和统计。
注意: 当前 LLM 为模拟输出，答案质量（correct/wrong/hallucinated）暂标记为 pending，
      接入真实 LLM 后需人工或自动复核答案内容。
"""

import json
import os
import importlib.util
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAG_PATH = os.path.join(SCRIPT_DIR, "12_最小RAG骨架.py")
spec = importlib.util.spec_from_file_location("rag_skeleton", RAG_PATH)
rag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rag)

EVAL_SET_PATH = os.path.join(SCRIPT_DIR, "evals", "project1", "eval_set.jsonl")
RESULTS_PATH = os.path.join(SCRIPT_DIR, "evals", "project1", "results.jsonl")


def load_eval_set(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def judge_refusal(item, refused):
    expected_refuse = item["expected"].startswith("应拒答")
    if expected_refuse and refused:
        return "refuse_correct"
    if expected_refuse and not refused:
        return "refuse_wrong"
    if not expected_refuse and refused:
        return "refuse_wrong"
    return "pending_llm"


def main():
    print("加载语料并预计算 embedding...")
    chunks = rag.load_and_chunk(rag.DOCS_PATH)
    chunk_embeddings = rag.embed_documents([c["text"] for c in chunks])
    print(f"  共 {len(chunks)} 个分块，embedding 形状 {chunk_embeddings.shape}\n")

    eval_set = load_eval_set(EVAL_SET_PATH)
    print(f"评测集共 {len(eval_set)} 条，开始逐条评测...\n")

    results = []
    for item in eval_set:
        qid = item["id"]
        question = item["question"]
        qtype = item["type"]

        result = rag.rag_query(question, chunks, chunk_embeddings)
        refused = result["refused"]
        answer = result["answer"]
        sources = result["sources"]
        top_score = result["top_score"]

        judgment = judge_refusal(item, refused)

        record = {
            "id": qid,
            "question": question,
            "type": qtype,
            "answer": answer,
            "refused": refused,
            "sources": sources,
            "top_score": round(top_score, 4),
            "result": judgment,
            "expected": item["expected"],
        }
        results.append(record)

        status = "OK" if judgment == "refuse_correct" else ("FAIL" if judgment == "refuse_wrong" else "PEND")
        print(f"  [{status}] {qid} ({qtype:13s}) refused={str(refused):5s} score={top_score:.4f} | {question[:30]}")

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n结果已保存到 {RESULTS_PATH}")

    c = Counter(r["result"] for r in results)
    total = len(results)
    refuse_total = c["refuse_correct"] + c["refuse_wrong"]
    refuse_rate = c["refuse_correct"] / refuse_total if refuse_total else 0
    pending = c.get("pending_llm", 0)

    print(f"\n{'=' * 50}")
    print(f"评测统计（共 {total} 条）")
    print(f"  拒答正确 (refuse_correct): {c['refuse_correct']}")
    print(f"  拒答错误 (refuse_wrong)  : {c['refuse_wrong']}")
    print(f"  已作答待LLM复核 (pending) : {pending}")
    print(f"  ─────────────────────────────")
    print(f"  拒答正确率: {refuse_rate:.1%} （硬性达标线 ≥70%）")
    print(f"  达标判定: {'PASS' if refuse_rate >= 0.7 else 'FAIL'}")
    print(f"  注: 答案准确率需接入真实 LLM 后复核 pending 条目")
    print(f"{'=' * 50}")

    refuse_wrong_items = [r for r in results if r["result"] == "refuse_wrong"]
    if refuse_wrong_items:
        print(f"\n拒答错误条目（需归因）:")
        for r in refuse_wrong_items:
            reason = "应答却拒答" if not r["refused"] else "应拒却作答"
            print(f"  {r['id']} [{r['type']}] {reason}: {r['question']} (score={r['top_score']})")


if __name__ == "__main__":
    main()
