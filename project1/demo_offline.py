# -*- coding: utf-8 -*-
"""
离线演示（不需要 API key、不需要教材 PDF）
==========================================
读取评测留痕 results.jsonl，展示一次完整问答的输入/输出/判定，
用于评审快速验证系统行为。

用法: python demo_offline.py
"""
import json
import os

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "evals", "cookbook", "results.jsonl")


def show(rid, rows):
    r = next((x for x in rows if x["id"] == rid), None)
    if not r:
        return
    print("=" * 66)
    print(f"[{r['id']}] {r['type']} | 判定: {r.get('result', '-')}")
    print(f"问题: {r['question']}")
    print(f"检索: top_score={r['top_score']:.4f} | 来源={r['sources']}")
    print(f"回答: {r['answer'][:500]}")
    if r.get("note"):
        print(f"备注: {r['note']}")


def main():
    if not os.path.exists(RESULTS):
        print("未找到 results.jsonl，请先运行 python run_eval_v2.py")
        return
    rows = [json.loads(l) for l in open(RESULTS, encoding="utf-8") if l.strip()]

    print(f"评测留痕：{len(rows)} 条（数据来源：{os.path.relpath(RESULTS)}）\n")
    print("下面展示 4 类典型行为，均为真实运行结果，未经修改。\n")

    # 选一条课内正确、一条课外拒答、一条诱导拒答、一条失败案例
    picks = []
    for cond in [
        lambda r: r["type"] == "in_scope" and r.get("result") == "correct",
        lambda r: r["type"] == "out_of_scope" and r.get("result") == "refuse_correct",
        lambda r: r["type"] == "adversarial" and r.get("result") == "refuse_correct",
        lambda r: r.get("result") in ("hallucinated", "wrong"),
    ]:
        for r in rows:
            if cond(r):
                picks.append(r["id"])
                break

    for rid in picks:
        show(rid, rows)

    from collections import Counter
    c = Counter(r.get("result") for r in rows)
    print("=" * 66)
    print("判定分布:", dict(c))
    print("统计口径见 evals/project1/eval_stats.py")


if __name__ == "__main__":
    main()
