import json, sys
from collections import Counter

rows = [json.loads(l) for l in open("results.jsonl", encoding="utf-8")]
c = Counter(r["result"] for r in rows)

answered = c["correct"] + c["wrong"] + c["hallucinated"]
acc = c["correct"] / answered if answered else 0
refuse_total = c["refuse_correct"] + c["refuse_wrong"]
refuse_rate = c["refuse_correct"] / refuse_total if refuse_total else 0

print(f"总条数: {len(rows)}")
print(f"准确率: {acc:.1%}  (correct={c['correct']}, wrong={c['wrong']}, hallucinated={c['hallucinated']})")
print(f"拒答正确率: {refuse_rate:.1%}  (拒对={c['refuse_correct']}, 拒错={c['refuse_wrong']})")
print("达标判定:", "PASS" if (refuse_rate >= 0.7 and len(rows) >= 20) else "FAIL")

# 题型配比自检（《评测脚手架》硬性要求）
from collections import Counter as C2
types = C2(r["type"] for r in rows)
n = len(rows)
print("\n题型配比:")
for t, low in [("in_scope", 0.60), ("out_of_scope", 0.20), ("adversarial", 0.10), ("vague", 0.10)]:
    print(f"  {t}: {types[t]}/{n} = {types[t]/n:.0%} (要求≥{low:.0%})",
          "OK" if types[t]/n >= low else "FAIL")

# 幻觉清单（≥3 条须逐条归因）
hal = [r for r in rows if r["result"] == "hallucinated"]
print(f"\n幻觉条数: {len(hal)}")
for r in hal:
    print(f"  {r['id']}: {r['note']}")
