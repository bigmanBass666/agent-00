# -*- coding: utf-8 -*-
"""
逐条判定脚本（对齐《评测脚手架》第五节判定规则）
================================================
规则自动判定 + 人工复核覆盖表（OVERRIDES），输出带 result 字段的 results.jsonl。

判定类别（老师定义）：
  correct        答案覆盖 expected 要点，且来源真实支持
  wrong          答案错误或与资料矛盾
  hallucinated   编造了资料中不存在的内容（最严重，单列统计）
  refuse_correct 应拒答而正确拒答
  refuse_wrong   不应拒答却拒答（漏答）或应拒答却未拒答/编造

用法: python judge_results.py
"""
import json

RESULTS = "evals/cookbook/results.jsonl"

# ---------------------------------------------------------------
# 人工复核覆盖表（自动规则判不准的样本，逐条给出理由）
# ---------------------------------------------------------------
OVERRIDES = {
    "i03": ("correct", "内容正确（西葫芦/菠菜/奶酪齐全），仅 ricotta 译为“奶油奶酪”，属术语译法差异"),
    "i04": ("wrong", "答案缺核心食材 egg white（蛋清），与题目所指菜品不符"),
    "i08": ("hallucinated", "原文 ground turkey，答案写成“鸡胸肉或牛肉末”，编造了资料中不存在的食材"),
    "i12": ("correct", "答案写“100千卡”=100 calories，关键词表未收录该译法导致漏判"),
    "i23": ("correct", "三文鱼/奶油奶酪等主料正确，caper 译为“腌渍凤尾鱼”属译法差异"),
    "i24": ("hallucinated", "原文 ground turkey / meat of choice，答案写成“火腿肉”，引入资料外食材"),
}


def judge(r):
    """按规则判定，未命中覆盖表时用规则"""
    rid = r["id"]
    if rid in OVERRIDES:
        return OVERRIDES[rid]

    if r["expected"] == "refuse":
        return ("refuse_correct", "阈值层或 LLM 层正确拒答") if r["actual_refused"] \
            else ("refuse_wrong", "应拒答但给出回答")

    # expected == answer
    if r["actual_refused"]:
        return ("refuse_wrong", "课内问题被误拒答")
    if r.get("keyword_hit"):
        return ("correct", "标准答案要素全覆盖且页码命中")
    return ("wrong", "标准答案要素未覆盖（需人工复核）")


def main():
    rows = [json.loads(l) for l in open(RESULTS, encoding="utf-8") if l.strip()]
    for r in rows:
        result, note = judge(r)
        r["result"] = result
        r["note"] = note

    with open(RESULTS, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    c = Counter(r["result"] for r in rows)
    print("判定完成：")
    for k in ["correct", "wrong", "hallucinated", "refuse_correct", "refuse_wrong"]:
        print(f"  {k}: {c[k]}")
    print("\n非通过项：")
    for r in rows:
        if r["result"] in ("wrong", "hallucinated", "refuse_wrong"):
            print(f"  {r['id']} [{r['result']}] {r['note']}")
    print(f"\n已写回: {RESULTS}")


if __name__ == "__main__":
    main()
