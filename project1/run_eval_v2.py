# -*- coding: utf-8 -*-
"""
自动化评测脚本（v2 架构 + 准确率/R6 判定）
跑 evals/cookbook/eval_set.jsonl 中的所有题目，输出逐条结果和统计。
支持断点续跑。
用法: python run_eval_v2.py [--fresh]
"""
import os
import re
import sys
import json
import time
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rag import load_kb, ask, REFUSE_SENTENCE

EVAL_SET = "evals/cookbook/eval_set.jsonl"
RESULTS_PATH = "evals/cookbook/results.jsonl"

CITATION_RE = re.compile(r"p\.(\d+)(?:\s*[-–~]\s*(\d+))?")


def keyword_hit(answer, keywords):
    """gold_keywords 命中数 / 总数。每项支持 "a|b" 的 OR 组（中英双语同义词）"""
    if not keywords:
        return None, 0
    ans = answer.lower()
    hit = sum(1 for k in keywords
              if any(alt.lower() in ans for alt in k.split("|")))
    return hit == len(keywords), hit


def cited_pages(answer):
    """从回答中抽取所有被引用的页码"""
    pages = set()
    for m in CITATION_RE.finditer(answer):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        pages.update(range(min(a, b), max(a, b) + 1))
    return pages


def page_hit(answer, gold_pages, tolerance=1):
    """答案引用的页码是否落在 gold_pages ± tolerance 内"""
    if not gold_pages:
        return None
    cited = cited_pages(answer)
    if not cited:
        return False
    for cp in cited:
        for gp in gold_pages:
            if abs(cp - gp) <= tolerance:
                return True
    return False


def longest_common_run(answer, context):
    """答案与检索上下文的最长连续公共子串长度（R6 抄原文检测代理指标）"""
    if not answer or not context:
        return 0
    # 去空白后比较，避免排版差异干扰
    a = re.sub(r"\s+", " ", answer)
    c = re.sub(r"\s+", " ", context)
    match = SequenceMatcher(None, a, c, autojunk=False).find_longest_match(
        0, len(a), 0, len(c))
    return match.size


def main():
    fresh = "--fresh" in sys.argv
    chunks, vectors = load_kb()
    with open(EVAL_SET, encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    results = []
    done_ids = set()
    if os.path.exists(RESULTS_PATH) and not fresh:
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
                      "top_score": 0.0, "sources": [], "context": ""}

        expected_refuse = q["expected"] == "refuse"
        actual_refuse = result["refused"]
        refusal_correct = (expected_refuse == actual_refuse)
        has_page_citation = "教材 p." in result["answer"]

        kw_ok, kw_hit_n = keyword_hit(result["answer"], q.get("gold_keywords"))
        p_ok = page_hit(result["answer"], q.get("gold_pages"))
        copy_len = longest_common_run(result["answer"], result.get("context", ""))

        record = {
            "id": q["id"], "question": q["question"], "type": q["type"],
            "expected": q["expected"], "actual_refused": actual_refuse,
            "refusal_correct": refusal_correct, "top_score": result["top_score"],
            "has_page_citation": has_page_citation,
            "gold_keywords": q.get("gold_keywords", []),
            "keyword_hit": kw_ok, "keyword_hit_n": kw_hit_n,
            "gold_pages": q.get("gold_pages", []), "page_hit": p_ok,
            "max_copy_len": copy_len,
            "sources": result["sources"], "answer": result["answer"],
        }
        results.append(record)

        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        status = "✓" if refusal_correct else "✗"
        extra = ""
        if kw_ok is not None:
            extra += f", 关键词{kw_hit_n}/{len(q['gold_keywords'])}"
        if p_ok is not None:
            extra += f", 页码{'✓' if p_ok else '✗'}"
        if copy_len >= 150:
            extra += f", ⚠抄原文{copy_len}字"
        print(f"  {status} 期望={'拒答' if expected_refuse else '回答'}, "
              f"实际={'拒答' if actual_refuse else '回答'}, "
              f"分数={result['top_score']:.4f}{extra}")
        if not refusal_correct:
            print(f"  [误判] 回答前100字: {result['answer'][:100]}")
        time.sleep(0.5)

    # ---------------- 统计 ----------------
    total = len(results)
    refusal_correct_count = sum(1 for r in results if r["refusal_correct"])
    expected_refuse = sum(1 for r in results if r["expected"] == "refuse")
    expected_answer = total - expected_refuse
    answer_correct = sum(1 for r in results if r["expected"] == "answer" and not r["actual_refused"])
    refuse_correct = sum(1 for r in results if r["expected"] == "refuse" and r["actual_refused"])
    citation_count = sum(1 for r in results if r["expected"] == "answer" and not r["actual_refused"] and r["has_page_citation"])

    answered = [r for r in results if r["expected"] == "answer" and not r["actual_refused"]
                and r.get("keyword_hit") is not None]
    kw_full = sum(1 for r in answered if r.get("keyword_hit"))
    kw_partial = sum(1 for r in answered if (r.get("keyword_hit_n") or 0) > 0)
    page_ok = sum(1 for r in answered if r.get("page_hit"))
    copy_violations = [r for r in answered if (r.get("max_copy_len") or 0) >= 150]

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
    if answered:
        print(f"\n答案准确率(关键词全覆盖): {kw_full}/{len(answered)} = {kw_full/len(answered)*100:.1f}%")
        print(f"答案准确率(关键词部分命中): {kw_partial}/{len(answered)} = {kw_partial/len(answered)*100:.1f}%")
        print(f"页码定位准确率: {page_ok}/{len(answered)} = {page_ok/len(answered)*100:.1f}%")
        print(f"R6 疑似抄原文(≥150字连续): {len(copy_violations)} 条 "
              f"{[r['id'] for r in copy_violations]}")
    in_scope_scores = [r["top_score"] for r in results if r["expected"] == "answer"]
    out_scope_scores = [r["top_score"] for r in results if r["expected"] == "refuse"]
    if in_scope_scores:
        print(f"\n课内题分数范围: {min(in_scope_scores):.4f} ~ {max(in_scope_scores):.4f}")
    if out_scope_scores:
        print(f"课外题分数范围: {min(out_scope_scores):.4f} ~ {max(out_scope_scores):.4f}")
    print(f"\n结果已保存: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
