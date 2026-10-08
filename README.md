# agent-00 · 课程项目仓库

《专业素养培养》课程项目仓库。当前进行项目一：课程知识问答智能体（RAG）。

## 项目一：课程知识问答智能体（RAG）

基于《操作系统》课程资料的问答智能体，支持资料内问答 + 库外问题拒答。

### 技术栈
- **Embedding**：BAAI/bge-m3（1024 维，SiliconFlow 免费）
- **精排**：BAAI/bge-reranker-v2-m3（SiliconFlow 免费）
- **LLM**：Qwen/Qwen3-8B（SiliconFlow 免费，需实名认证）
- **检索架构**：两段式 —— embedding 粗召回 top-20 → reranker 精排 top-3
- **拒答机制**：双层 —— 前置阈值（reranker 分数 < 0.5）+ LLM 层判断

### 环境要求
- Python 3.8+
- 依赖：`requests`、`numpy`

### 快速开始
```bash
pip install requests numpy
cd project1
python 12_最小RAG骨架.py   # 端到端问答演示（4 道题）
python run_eval.py          # 完整评测（25 条题 + 统计）
```

### 目录结构
```
project1/
├── 12_最小RAG骨架.py      # 主程序（RAG 全链路）
├── run_eval.py            # 评测脚本
├── 设计文档.md             # 设计与复盘文档
├── corpus/
│   └── os_ch1.txt         # 样例语料（进程 3 小节）
└── evals/project1/
    ├── eval_set.jsonl     # 评测集（25 条）
    └── results.jsonl      # 评测结果
```

### 三件套提交物
1. **可运行系统**：`project1/12_最小RAG骨架.py`
2. **设计/复盘文档**：`project1/设计文档.md`
3. **评测数据**：`project1/evals/project1/`

### 首轮评测指标
- 拒答正确率：100%（≥70% 达标）
- 答案准确率：100%（≥70% 达标）
- 幻觉条数：0
