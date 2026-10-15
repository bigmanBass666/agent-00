# -*- coding: utf-8 -*-
"""
阈值自动校准
============
基于评测结果的 top_score，扫描 0.1~0.9 阈值，
输出每个阈值的拒答率/准确率/误拒答率，推荐最优值。
用法: python calibrate_threshold.py
"""
import json
import os

RESULTS_PATH = "evals/cookbook/results.jsonl"


def load_results():
    results = []
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    return results


def evaluate_threshold(results, threshold):
    """计算给定阈值下的各项指标"""
    total = len(results)
    correct = 0
    false_refuse = 0
    false_answer = 0
    in_scope = 0
    out_scope = 0

    for r in results:
        expected_refuse = r["expected"] == "refuse"
        top_score = r["top_score"]

        if top_score < threshold:
            final_refused = True
        else:
            final_refused = r["actual_refused"]

        if expected_refuse:
            out_scope += 1
            if final_refused:
                correct += 1
            else:
                false_answer += 1
        else:
            in_scope += 1
            if not final_refused:
                correct += 1
            else:
                false_refuse += 1

    return {
        "threshold": threshold,
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0,
        "in_scope": in_scope,
        "out_scope": out_scope,
        "false_refuse": false_refuse,
        "false_answer": false_answer,
        "in_scope_answer_rate": (in_scope - false_refuse) / in_scope if in_scope else 0,
        "out_scope_refuse_rate": (out_scope - false_answer) / out_scope if out_scope else 0,
    }


if __name__ == "__main__":
    results = load_results()
    if not results:
        print(f"未找到评测结果: {RESULTS_PATH}")
        print("请先运行 python run_eval_v2.py")
        exit(1)

    print(f"加载 {len(results)} 条评测结果")
    print("=" * 70)
    print(f"{'阈值':>6} {'总正确率':>8} {'课内回答率':>10} {'课外拒答率':>10} {'误拒答':>6} {'误回答':>6}")
    print("-" * 70)

    best = None
    for t in [i / 10 for i in range(1, 10)]:
        m = evaluate_threshold(results, t)
        print(f"{m['threshold']:>6.1f} {m['accuracy']:>8.1%} "
              f"{m['in_scope_answer_rate']:>10.1%} "
              f"{m['out_scope_refuse_rate']:>10.1%} "
              f"{m['false_refuse']:>6} {m['false_answer']:>6}")
        if best is None or m["accuracy"] > best["accuracy"]:
            best = m

    print("=" * 70)
    print(f"\n推荐阈值: {best['threshold']:.1f}")
    print(f"  总正确率: {best['accuracy']:.1%} ({best['correct']}/{best['total']})")
    print(f"  课内题回答率: {best['in_scope_answer_rate']:.1%} (误拒答 {best['false_refuse']} 条)")
    print(f"  课外题拒答率: {best['out_scope_refuse_rate']:.1%} (误回答 {best['false_answer']} 条)")
    print(f"\n请将 config.py 中的 REFUSE_THRESHOLD 改为 {best['threshold']:.1f}")
