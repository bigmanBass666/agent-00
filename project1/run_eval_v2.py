# -*- coding: utf-8 -*-
"""
自动化评测脚本（v2 架构）
跑 evals/cookbook/eval_set.jsonl 中的所有题目，输出逐条结果和统计。
支持断点续跑。
用法: python run_eval_v2.py
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rag import load_kb, ask, REFUSE_SENTENCE

EVAL_SET = "evals/cookbook/eval_set.jsonl"
RESULTS_PATH = "evals/cookbook/results.jsonl"


def main():
    chunks, vectors = load_kb()
    with open(EVAL_SET, encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    results = []
    done_ids = set()
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    results.append(r)
                    done_ids.add(r["id"])
        print(f"已加载 {len(results)} 条已有结果，跳过已完成题目")

    print(f"评测集: {len(questions)} 道题")
    print("=" * 60)

    for i, q in enumerate(questions):
        if q["id"] in done_ids:
            print(f"\n[{i+1}/{len(questions)}] {q['id']} 跳过（已有结果）")
            continue
        print(f"\n[{i+1}/{len(questions)}] {q['id']} ({q['type']})")
        print(f"  问题: {q['question']}")
        try:
            result = ask(q["question"], chunks, vectors)
        except Exception as e:
            print(f"  [错误] {e}")
            result = {"answer": f"[ERROR] {e}", "refused": False,
                      "top_score": 0.0, "sources": []}

        expected_refuse = q["expected"] == "refuse"
        actual_refuse = result["refused"]
        refusal_correct = (expected_refuse == actual_refuse)
        has_page_citation = "【教材 p." in result["answer"] or "教材 p." in result["answer"]

        record = {
            "id": q["id"], "question": q["question"], "type": q["type"],
            "expected": q["expected"], "actual_refused": actual_refuse,
            "refusal_correct": refusal_correct, "top_score": result["top_score"],
            "has_page_citation": has_page_citation,
            "sources": result["sources"], "answer": result["answer"],
        }
        results.append(record)

        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        status = "✓" if refusal_correct else "✗"
        print(f"  {status} 期望={'拒答' if expected_refuse else '回答'}, 实际={'拒答' if actual_refuse else '回答'}, 分数={result['top_score']:.4f}")
        if not refusal_correct:
            print(f"  [误判] 回答前100字: {result['answer'][:100]}")
        time.sleep(0.5)

    total = len(results)
    refusal_correct_count = sum(1 for r in results if r["refusal_correct"])
    expected_refuse = sum(1 for r in results if r["expected"] == "refuse")
    expected_answer = total - expected_refuse
    answer_correct = sum(1 for r in results if r["expected"] == "answer" and not r["actual_refused"])
    refuse_correct = sum(1 for r in results if r["expected"] == "refuse" and r["actual_refused"])
    citation_count = sum(1 for r in results if r["expected"] == "answer" and not r["actual_refused"] and r["has_page_citation"])

    print("\n" + "=" * 60)
    print("评测统计")
    print("=" * 60)
    print(f"总题数: {total}")
    print(f"  课内题(应回答): {expected_answer}, 实际回答: {answer_correct}, 误拒答: {expected_answer - answer_correct}")
    print(f"  课外题(应拒答): {expected_refuse}, 实际拒答: {refuse_correct}, 误回答: {expected_refuse - refuse_correct}")
    print(f"\n拒答正确率: {refusal_correct_count}/{total} = {refusal_correct_count/total*100:.1f}%")
    if expected_answer > 0:
        print(f"课内题回答率: {answer_correct}/{expected_answer} = {answer_correct/expected_answer*100:.1f}%")
    if expected_refuse > 0:
        print(f"课外题拒答率: {refuse_correct}/{expected_refuse} = {refuse_correct/expected_refuse*100:.1f}%")
    if answer_correct > 0:
        print(f"页码引用覆盖率: {citation_count}/{answer_correct} = {citation_count/answer_correct*100:.1f}%")
    in_scope_scores = [r["top_score"] for r in results if r["expected"] == "answer"]
    out_scope_scores = [r["top_score"] for r in results if r["expected"] == "refuse"]
    if in_scope_scores:
        print(f"\n课内题分数范围: {min(in_scope_scores):.4f} ~ {max(in_scope_scores):.4f}")
    if out_scope_scores:
        print(f"课外题分数范围: {min(out_scope_scores):.4f} ~ {max(out_scope_scores):.4f}")
    print(f"\n结果已保存: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
