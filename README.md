# agent-00 · 课程项目仓库

《专业素养培养》课程项目仓库。当前进行**项目一：课程知识问答智能体（RAG）**。

## 一句话

基于指定课程教材 PDF 构建知识库，实现**带页码引用**的问答：只查教材、逐句给出处、检索不到如实说明、答不上自动转人工。

## 文档导航（找什么看这里）

| 要找什么 | 去哪 |
|---|---|
| **条款对照 / 状态 / 待办 / 指标口径** | [`REQUIREMENTS.md`](REQUIREMENTS.md)（唯一执行基准） |
| 设计依据（分块/Prompt/拒答/教材与技术栈归类） | `project1/设计文档.md` |
| 决策过程与自我推翻（时间线留痕） | `project1/docs/决策日志.md` |
| 会议决策 / 分工 / 风险 | `minutes/2026-09-20.md` `2026-10-12.md` `2026-10-18.md` |
| 测试报告与失败案例 | `project1/docs/测试报告.md` |
| 答辩演示与问答库 | `project1/docs/答辩演示脚本.md` |
| 老师发放材料（原件，只读） | `materials/` |

## 技术栈

| 组件 | 选型 | 说明 |
|---|---|---|
| Embedding | `BAAI/bge-m3`（1024 维） | 多语言，建库与查询同源（向量空间一致） |
| 精排 | `BAAI/bge-reranker-v2-m3` | cross-encoder，40 候选 → 3 |
| LLM | `Qwen/Qwen3-8B` | 生成用，不参与向量计算（标准 RAG 架构） |
| 接口 | SiliconFlow 免费层 | key 走 `.env`，不入库 |
| 检索 | 两段式 + 混合召回 | 余弦 top-20 + IDF 词汇 top-20 → reranker 精排 |
| 拒答 | 双层 | 阈值（reranker < 0.3 且词汇 < 0.85）+ LLM 判断 |
| 转人工 | 自动工单 | 拒答 → tickets.jsonl → `/handoff` 工作台 |

## 快速开始

```bash
pip install requests numpy pymupdf
cd project1
echo "SILICONFLOW_API_KEY=你的key" > .env

python build_kb.py            # PDF → 分块 → 向量化
python validate_kb.py         # 知识库校验
python rag.py                 # 端到端问答演示
python webui.py               # Web UI（http://127.0.0.1:8000，含 /handoff）
python run_eval_v2.py --fresh # 完整评测

# 评审 30 秒验证（无需 API key、无需教材 PDF）
python demo_offline.py        # 4 类典型样本 + 判定分布
```

换教材：`BOOK_PATH=新书.pdf python build_kb.py`（支持 `.pdf`/`.epub`，多书并存用 `KB_VECTORS`/`KB_CHUNKS` 环境变量隔离）。

## 目录结构

```
agent-00/
├── README.md                  ← 本文件（导航）
├── REQUIREMENTS.md            ← 唯一执行基准（条款对照/状态/口径）
├── materials/                 ← 老师发放材料（10 份，只读）
├── minutes/                   ← 会议纪要（合规要求，每课一份）
├── evals/project1/            ← 评测数据落点（课程脚手架要求）
│   ├── eval_set.jsonl         # 50 条评测集（60/20/10/10）
│   ├── results.jsonl          # 逐条结果 + 五类判定
│   ├── holdout.jsonl          # 5 条答辩现场抽问题
│   ├── eval_stats.py          # 课程指定统计脚本（对外指标口径）
│   └── summary.md
└── project1/
    ├── config.py / build_kb.py / rag.py / validate_kb.py
    ├── run_eval_v2.py / judge_results.py / calibrate_threshold.py
    ├── demo_offline.py        # 零依赖验证入口
    ├── webui.py               # Web UI + 人工工作台
    ├── 设计文档.md             # 分块策略 / Prompt / 拒答机制 / 失败案例 / 归类说明
    ├── prompt/system_prompt.txt   # 系统提示词（交付物 3）
    ├── docs/
    │   ├── 测试报告.md          # 交付物 5（定稿后转 Office）
    │   ├── 提示词设计说明.md     # 提示词 rationale
    │   ├── 小组分工说明.md       # 交付物 7（定稿后转 Office）
    │   ├── PPT大纲.md          # 交付物 6（定稿后转 PPTX）
    │   ├── 对比实验_混合召回.md  # A/B 记录
    │   ├── 对比实验_分块粒度.md  # A/B 记录
    │   ├── 决策日志.md          # 决策与自我推翻（时间线）
    │   └── 答辩演示脚本.md       # 演示脚本 + Q&A 库
    ├── evals/cookbook/        # 主线评测快照与 A/B 结果
    └── evals/atomic/          # 换书验证（《原子习惯》中文库）
```

## 交付物与指标

全部见 [`REQUIREMENTS.md`](REQUIREMENTS.md)（含任务书三件套、v2 七项交付物、两套评分口径、过关硬性条件）。

> **指标口径提醒**：对外（报告/PPT/答辩）一律用课程口径 `evals/project1/eval_stats.py` 的数字；`run_eval_v2.py` 的自动口径仅供内部迭代参考，两者不要混用。
