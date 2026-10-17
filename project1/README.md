# agent-00 · 课程项目仓库

《专业素养培养》课程分组作业：某课程知识库的智能问答系统（RAG）。

## 项目概述

基于指定课程教材 PDF 构建知识库，实现带页码引用的智能问答。满足 R1~R6 行为约束：检索优先、禁止内部知识、页码引用、中英混排、如实拒答、不复制大段原文。

## 技术栈

| 环节 | 模型/工具 | 说明 |
|------|-----------|------|
| 向量化 | BAAI/bge-m3 | 1024 维，多语言，8192 token |
| 粗召回 | numpy 余弦相似度 + IDF 加权词汇召回 | 两路各 top-20，合并去重 |
| 精排 | BAAI/bge-reranker-v2-m3 | 交叉编码器，top-3 |
| 生成 | Qwen/Qwen3-8B | temperature=0.3 |
| 接口 | SiliconFlow | 全部免费层 |

技术选型：方案 B（向量检索）的轻量自研实现，未引入 LangChain 框架。

**教材说明**：本书 205 页、209 条书签、142 个可解析章节，满足作业文档"PDF ≥100 页 + 清晰章节结构"的全部硬性条件；章节粒度均匀，适合验证"按章节语义分块"。系统与教材完全解耦，换书只需改 `config.py` 的 `PDF_PATH` 并重跑构建脚本（详见 `设计文档.md` 第〇节）。

## 环境要求

- Python 3.8+
- 依赖：`requests`、`numpy`、`PyMuPDF`（fitz）

```bash
pip install requests numpy pymupdf
```

## 快速开始

```bash
cd project1

# 0. 零依赖验证（无需 API key、无需教材 PDF）：
#    直接查看 50 条真实运行留痕，含课内/课外/诱导/失败四类样本
python demo_offline.py

# 1. 配置 API key（创建 .env 文件）
echo "SILICONFLOW_API_KEY=你的key" > .env

# 1. 放入教材 PDF（默认文件名 textbook.pdf，可在 config.py 修改）
# 2. 构建知识库（PDF → 分块 → 向量化）
python build_kb.py

# 3. 校验知识库
python validate_kb.py

# 4. 运行问答演示
python rag.py

# 5. 跑评测（需先准备 evals/<教材>/eval_set.jsonl）
python run_eval_v2.py

# 6. 校准拒答阈值（基于评测结果）
python calibrate_threshold.py
```

## 目录结构

```
project1/
├── config.py                  # 全局配置（路径、分块、检索、模型参数）
├── build_kb.py                # 知识库构建：PDF提取 → 分块 → bge-m3向量化
├── rag.py                     # 问答系统：两段式检索 + R1~R6 + 页码引用
├── validate_kb.py             # 知识库自动校验
├── run_eval_v2.py             # 自动化评测（支持断点续跑）
├── calibrate_threshold.py     # 阈值自动校准
├── .env.example               # API key 配置模板
├── .gitignore                 # 排除 .env、*.pdf、*.npy 等
├── docs/
│   ├── 测试报告.md             # 测试报告（已填充实测数据）
│   └── PPT大纲.md              # 答辩 PPT 大纲（18 页，内容已完成）
└── evals/
    └── cookbook/
        ├── eval_set.jsonl      # 评测集（50 条，含 gold_pages/gold_keywords）
        ├── results.jsonl       # 最终评测结果（逐条）
        ├── results_round1.jsonl  # 第 1 轮（基线）
        └── results_round2.jsonl  # 第 2 轮（混合召回 + Prompt 重写）
```

## 换教材流程

1. 将新 PDF 放入 project1/ 目录
2. 修改 `config.py` 中 `PDF_PATH` 指向新文件
3. 运行 `python build_kb.py` 重建知识库
4. 运行 `python validate_kb.py` 校验
5. 准备新评测集，运行 `python run_eval_v2.py`
6. 运行 `python calibrate_threshold.py` 校准阈值

## 行为约束（R1~R6）

- **R1**：回答前必须先检索知识库（代码层面强制）
- **R2**：只能使用教材内容，禁止模型内部知识（System Prompt + 资料隔离）
- **R3**：每个事实附页码引用【教材 p.XX】（分块记录页码 + Prompt 要求 + 自动检查）
- **R4**：简单中文解释，关键术语保留英文
- **R5**：未覆盖内容如实拒答（固定句式 + 三层防线：阈值层 + 词汇放行通道 + LLM 层）
- **R6**：不超过 3 句连续原文引用

## 交付物清单（对齐 v2 作业文档第七节 7 项）

| # | 交付物 | 文件 |
|---|--------|------|
| 1 | 知识库（数据库文件 + 构建脚本） | `kb_chunks.json` + `kb_vectors.npy`（由 `build_kb.py` 生成） |
| 2 | 检索工具/函数（源码 + 调用说明） | `rag.py` 的 `knowledge_search()`，调用说明见下方 |
| 3 | 系统提示词（文本文件 + 设计说明） | `prompt/system_prompt.txt` + `docs/提示词设计说明.md` |
| 4 | 智能体配置与启动说明 | `config.py` + 本 README |
| 5 | 测试报告（DOCX） | `docs/测试报告.docx`（源：`docs/测试报告.md`） |
| 6 | 实施过程 PPT（PPTX） | `docs/智能问答系统_实施过程.pptx` |
| 7 | 小组分工说明（DOCX） | `docs/小组分工说明.docx` |

### 检索工具调用说明

```python
from rag import knowledge_search

hits = knowledge_search("What temperature should I bake egg white bites at?")
# 返回：
# [{"text": "...", "page_start": 27, "page_end": 27, "chapter": "Egg White Bites",
#   "score": 0.9528, "citation": "【教材 p.27】"}, ...]
```

## 实测指标（50 题评测集，严格口径，2026-10-18）

| 指标 | 数值 | 达标线 |
|------|------|--------|
| **准确率** | **89.7%（26/29）** | ≥70% ✅ |
| **拒答正确率** | **85.7%（18/21）** | ≥70% ✅ |
| 课内题回答率 | 96.7%（29/30） | — |
| 页码引用覆盖率 | 100%（29/29） | — |
| 页码定位准确率 | 93.1%（27/29） | — |
| 幻觉条数 | 2 | <3 ✅ |

- 评测集配比：课内 30 / 课外 10 / 诱导 5 / 模糊 5 = 60% / 20% / 10% / 10%（全部满足脚手架硬性要求）
- 答辩 holdout：`evals/cookbook/holdout.jsonl`（5 条，含 1 条库外陷阱题，不参与调优）
- 逐条判定：`judge_results.py` 生成 `result` 字段；统计：`evals/project1/eval_stats.py`

## 已完成的拓展挑战（v2 第十一节，每项 +2~5 分）

| 拓展项 | 实现 |
|--------|------|
| 混合检索（全文 + 向量融合排序） | `rag.py` `lexical_recall()`：embedding 余弦 + IDF 加权词汇召回双路合并去重 |
| 检索结果重排序（cross-encoder） | `rag.py` `retrieve()`：bge-reranker-v2-m3 交叉编码器对初检 top-40 二次排序取 top-3 |

## API Key 安全

- API key 通过 `.env` 文件或环境变量 `SILICONFLOW_API_KEY` 加载
- `.env` 已被 `.gitignore` 排除，不会进入版本控制
- 仓库中不含任何明文 key
