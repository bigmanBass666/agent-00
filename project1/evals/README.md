# evals/ 目录说明（内部迭代快照，非对外口径）

> ⚠️ **对外指标以仓库根目录 `evals/project1/summary.md` 为准**（课程脚手架 `eval_stats.py` 五类判定）：
> 准确率 **89.7%**、拒答正确率 **90.5%**、页码引用 100%、页码定位 96.6%、幻觉 2 条。

本目录是**内部迭代过程的原始快照**（`run_eval_v2.py` 自动判定口径），用于：
1. 复现每一轮的 A/B 对比
2. 保留历史（课程要求"每轮改进必须留 A/B 记录"）
3. 换书验证的原始数据

## 文件清单

| 文件 | 内容 |
|---|---|
| `cookbook/results.jsonl` | 主线最新一次自动评测结果（内部口径，**非对外指标**） |
| `cookbook/results_round1.jsonl` / `round2` / `round3_32q` | 三轮迭代的历史快照 |
| `cookbook/results_ab_dense_only.jsonl` | A/B：纯向量 vs 混合召回（纯向量组） |
| `cookbook/results_ab_chunk_merge.jsonl` | A/B：章节切 vs 合并切（合并组） |
| `cookbook/results_ab_table_*.jsonl` | A/B：表格结构化前后 |
| `cookbook/results_before_translate.jsonl` | 查询翻译层上线前的基线（用于对比 25%→0%） |
| `cookbook/eval_set.jsonl` / `eval_set_v0_original_25.jsonl` | 50 题评测集 + 原始 25 题版本（保留原始版，课程要求"不得删改评测集题目，修订须保留原版"） |
| `cookbook/holdout.jsonl` | 5 条答辩现场抽问题（不参与调优） |
| `atomic/` | 换书验证：《原子习惯》中文库（58 块）+ 30 题题集 + 5 次评测 + API 波动备份 |

## 两套口径为什么不同

| 口径 | 出处 | 判定方式 | 典型数字 |
|---|---|---|---|
| **课程口径**（对外） | `evals/project1/` | `eval_stats.py` 五类判定（correct/wrong/hallucinated/refuse_*） | 89.7% / 90.5% |
| 内部自动口径 | 本目录 | `run_eval_v2.py` 的 refusal_correct 等字段 | 96%（±4pp 波动） |

差异原因：课程口径把"误拒答"计入 `refuse_wrong`（更严格），内部口径只统计 `refused` 布尔值。**答辩/报告一律引用课程口径。**
