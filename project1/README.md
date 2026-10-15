# agent-00 · 课程项目仓库

《专业素养培养》课程分组作业：某课程知识库的智能问答系统（RAG）。

## 项目概述

基于指定课程教材 PDF 构建知识库，实现带页码引用的智能问答。满足 R1~R6 行为约束：检索优先、禁止内部知识、页码引用、中英混排、如实拒答、不复制大段原文。

## 技术栈

| 环节 | 模型/工具 | 说明 |
|------|-----------|------|
| 向量化 | BAAI/bge-m3 | 1024 维，多语言，8192 token |
| 粗召回 | numpy 余弦相似度 | top-20 候选 |
| 精排 | BAAI/bge-reranker-v2-m3 | 交叉编码器，top-3 |
| 生成 | Qwen/Qwen3-8B | temperature=0.3 |
| 接口 | SiliconFlow | 全部免费层 |

技术选型：方案 B（向量检索）的轻量自研实现，未引入 LangChain 框架。

## 环境要求

- Python 3.8+
- 依赖：`requests`、`numpy`、`PyMuPDF`（fitz）

```bash
pip install requests numpy pymupdf
```

## 快速开始

```bash
cd project1

# 0. 配置 API key（创建 .env 文件）
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
│   ├── 测试报告_骨架.md         # 测试报告框架（待填数据）
│   └── PPT大纲_骨架.md          # 实施PPT大纲（待填内容）
└── evals/
    └── <教材名>/
        ├── eval_set.jsonl     # 评测集
        └── results.jsonl      # 评测结果
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
- **R5**：未覆盖内容如实拒答（固定句式 + 两层拒答：阈值层 + LLM层）
- **R6**：不超过 3 句连续原文引用

## 交付物清单

1. 知识库文件（kb_chunks.json + kb_vectors.npy，由 build_kb.py 生成）
2. 检索工具（rag.py）
3. 系统提示词（rag.py 中 SYSTEM_PROMPT）
4. 智能体配置与启动说明（本 README + config.py）
5. 测试报告（docs/测试报告_骨架.md 填充后导出）
6. 实施 PPT（docs/PPT大纲_骨架.md 填充后制作）
7. 小组分工说明（待组员确定后补充）

## API Key 安全

- API key 通过 `.env` 文件或环境变量 `SILICONFLOW_API_KEY` 加载
- `.env` 已被 `.gitignore` 排除，不会进入版本控制
- 仓库中不含任何明文 key
