# agent-00 · 课程项目仓库

《专业素养培养》课程项目仓库。当前进行项目一：课程知识问答智能体（RAG）。

## 项目一：课程知识问答智能体（RAG）

基于《操作系统》课程资料的问答智能体，支持资料内问答 + 库外问题拒答。

### 技术栈
- **Embedding**：BAAI/bge-m3（1024 维，SiliconFlow 免费）
- **精排**：BAAI/bge-reranker-v2-m3（SiliconFlow 免费）
- **LLM**：Qwen/Qwen3-8B（SiliconFlow 免费，需实名认证）
- **检索架构**：两段式 + 混合召回 —— embedding 余弦 + IDF 词汇召回各 top-20 → reranker 精排 top-3
- **拒答机制**：三层 —— 阈值（reranker < 0.3 且词汇分 < 0.85）+ 词汇放行通道 + LLM 层判断

### 环境要求
- Python 3.8+
- 依赖：`requests`、`numpy`、`PyMuPDF`

### 快速开始
```bash
pip install requests numpy pymupdf
cd project1
echo "SILICONFLOW_API_KEY=你的key" > .env
python build_kb.py            # 建知识库（PDF → 159 块 → 向量化）
python validate_kb.py         # 校验
python rag.py                 # 端到端问答演示（4 道题 + 检索工具演示）
python run_eval_v2.py --fresh # 完整评测（50 题）
python judge_results.py       # 逐条判定（correct/wrong/hallucinated/refuse_*）
cd ../evals/project1 && python eval_stats.py   # 课程口径统计
```

### 目录结构
```
agent-00/
├── materials/                      # 课程发放材料（含 16_分组作业_v2_正式版.md）
├── evals/project1/                 # 评测数据（课程脚手架要求的落点）
│   ├── eval_set.jsonl              # 50 条评测集
│   ├── results.jsonl               # 逐条结果 + result 判定
│   ├── holdout.jsonl               # 5 条答辩现场抽问题
│   └── eval_stats.py               # 课程指定统计脚本
└── project1/
    ├── config.py                   # 全局配置
    ├── build_kb.py                 # 知识库构建
    ├── rag.py                      # 问答系统 + knowledge_search 工具
    ├── validate_kb.py              # 知识库校验
    ├── run_eval_v2.py              # 自动化评测
    ├── judge_results.py            # 逐条判定（含人工复核表）
    ├── calibrate_threshold.py      # 阈值校准
    ├── 设计文档.md                  # 设计与复盘
    ├── prompt/system_prompt.txt    # 系统提示词（独立交付物）
    ├── docs/
    │   ├── 测试报告.md / .docx      # 测试报告（DOCX 交付）
    │   ├── 提示词设计说明.md         # 提示词 rationale
    │   ├── 小组分工说明.md / .docx   # 分工说明（DOCX 交付）
    │   └── PPT大纲.md / .pptx       # 实施过程 PPT
    └── evals/cookbook/             # 评测快照与 A/B 记录
```

### 交付物（对齐 v2 作业文档 7 项）
| # | 交付物 | 文件 |
|---|--------|------|
| 1 | 知识库 + 构建脚本 | `kb_chunks.json` + `kb_vectors.npy` + `build_kb.py` |
| 2 | 检索工具 | `rag.py` 的 `knowledge_search()` |
| 3 | 系统提示词 | `prompt/system_prompt.txt` + `docs/提示词设计说明.md` |
| 4 | 智能体配置 | `config.py` + README |
| 5 | 测试报告（DOCX） | `docs/测试报告.docx` |
| 6 | 实施 PPT（PPTX） | `docs/智能问答系统_实施过程.pptx`（大纲已定稿，PPTX 待生成） |
| 7 | 小组分工说明（DOCX） | `docs/小组分工说明.docx` |

### 实测指标（50 题，严格口径，2026-10-18）
- 准确率：**89.7%**（26/29，达标线 ≥70%）
- 拒答正确率：**90.5%**（19/21，达标线 ≥70%）
- 课内题回答率：96.7%（29/30）
- 页码引用覆盖率：**100%**（29/29），页码定位 96.6%
- 幻觉条数：2（达标线 <3）
- 四轮迭代：87.5% → 87.5% → 93.8% → 90.5%（口径不同，详见设计文档）
- 已完成拓展挑战 3 项：混合检索、cross-encoder 重排序、两组对比实验
