# 交付索引

> 课程：专业素养培养（2026-2027 学年第 1 学期）
> 项目：某课程知识库的智能问答系统（分组实践作业）
> 小组：刘家暄、傅卓凝、陈涵飞、陈芝聪
> 提交日期：2026-10-18

本文件把作业文档第七节要求的 **7 项交付物**逐一对应到仓库路径，便于评审核对。

---

## 一、7 项交付物对照

| # | 交付物 | 要求 | 本仓库位置 |
|---|--------|------|-----------|
| 1 | 知识库 + 构建脚本 | 数据库文件 + 可独立运行的构建脚本 | `project1/kb_chunks.json`、`project1/kb_vectors.npy`、`project1/build_kb.py` |
| 2 | 检索工具/函数 | 源码 + 调用说明 | `project1/rag.py` → `knowledge_search()`；调用说明见 `project1/README.md`「检索工具调用说明」 |
| 3 | 系统提示词 | 文本文件 + 设计说明 | `project1/prompt/system_prompt.txt` + `project1/docs/提示词设计说明.md` |
| 4 | 智能体配置 | 配置文件 + 启动说明 | `project1/config.py` + `project1/README.md` |
| 5 | 测试报告 | PDF / DOCX | `project1/docs/测试报告.docx`（源文件 `.md` 同目录） |
| 6 | 实施过程 PPT | PPTX，15~20 页 | `project1/docs/智能问答系统_实施过程.pptx`（18 页大纲已定稿：`docs/PPT大纲.md`） |
| 7 | 小组分工说明 | PDF / DOCX | `project1/docs/小组分工说明.docx`（源文件 `.md` 同目录） |

---

## 二、评审 30 秒验证路径（无需 API key、无需教材 PDF）

```bash
cd project1
python demo_offline.py
```

输出 50 条真实运行留痕中的 4 类典型样本（课内答对 / 课外拒答 / 诱导拒答 / 失败案例），并给出判定分布。

---

## 三、完整复现（需要 API key + 教材 PDF）

```bash
pip install requests numpy pymupdf
cd project1
echo "SILICONFLOW_API_KEY=你的key" > .env

python build_kb.py            # PDF → 159 块 → 向量化（约 2 分钟）
python validate_kb.py         # 知识库校验
python rag.py                 # 端到端演示（4 题 + 检索工具演示）
python run_eval_v2.py --fresh # 50 题评测（约 8 分钟）
python judge_results.py       # 逐条判定
cd ../evals/project1 && python eval_stats.py   # 课程口径统计
```

**说明**：教材 PDF 与 API key 不入仓库（版权 / 密钥安全），`.gitignore` 已排除。教材为 The Anabolic Cookbook 2.0（205 页），可在项目 README「换教材流程」中替换为任意 PDF。

---

## 四、核心指标（50 题实测）

| 指标 | 数值 | 达标线 |
|------|------|--------|
| 准确率 | 89.7%（26/29） | ≥70% |
| 拒答正确率 | 85.7%（18/21） | ≥70% |
| 页码引用覆盖率 | 100%（29/29） | — |
| 幻觉条数 | 2 | <3 |

评测集配比：课内 30 / 课外 10 / 诱导 5 / 模糊 5（60/20/10/10，满足脚手架硬性要求）；另设 5 条 holdout 供答辩现场抽问（实测 5/5 通过）。

---

## 五、R1~R6 合规性速查

| 约束 | 实现位置 | 验证方式 |
|------|---------|---------|
| R1 先检索再回答 | `rag.py` `ask()`：`retrieve()` → 阈值 → `llm_call()` | 代码顺序不可绕过；日志打印检索分数 |
| R2 只用教材 | `prompt/system_prompt.txt` 第 1 条 + 资料隔离 | 10 道课外题 100% 拒答；2 例实体替换已归因 |
| R3 页码引用 | 分块元数据 + Prompt 第 3 条 + 自动解析 | 覆盖率 100%，定位准确率 93.1% |
| R4 中文 + 术语英文 | Prompt 第 4 条（禁中英拼接） | 人工检查通过 |
| R5 如实拒答 | 三档拒答 Prompt + 三层防线 | 拒答正确率 85.7% |
| R6 不抄原文 | Prompt 第 5 条 + 最长公共子串检测 | 50 题 0 条违规 |

---

## 六、拓展挑战完成情况（v2 第十一节）

| 拓展项 | 状态 | 位置 |
|--------|------|------|
| 混合检索（全文 + 向量融合） | ✅ | `rag.py` `lexical_recall()` |
| 检索结果重排序（cross-encoder） | ✅ | `rag.py` `retrieve()` + bge-reranker-v2-m3 |
| 对比实验（同一教材对比检索质量） | ✅ | `project1/docs/对比实验_混合召回.md` |

---

## 七、目录总览

```
agent-00/
├── DELIVERY.md                    ← 本文件
├── README.md                      ← 项目总览
├── materials/                     ← 课程发放材料（含 v2 正式版作业要求）
├── evals/project1/                ← 评测数据（脚手架要求落点）
│   ├── eval_set.jsonl             ← 50 条评测集
│   ├── results.jsonl              ← 逐条结果 + result 判定
│   ├── holdout.jsonl              ← 5 条答辩抽问题
│   ├── eval_stats.py              ← 课程指定统计脚本
│   └── summary.md                 ← 统计摘要
└── project1/
    ├── config.py / build_kb.py / rag.py / validate_kb.py
    ├── run_eval_v2.py / judge_results.py / calibrate_threshold.py
    ├── demo_offline.py            ← 零依赖验证入口
    ├── 设计文档.md                 ← 设计与复盘（含分块/Prompt/拒答/三轮A/B/失败案例）
    ├── prompt/system_prompt.txt   ← 系统提示词（交付物 3）
    ├── docs/
    │   ├── 测试报告.md / .docx      ← 交付物 5
    │   ├── 提示词设计说明.md
    │   ├── 小组分工说明.md / .docx   ← 交付物 7
    │   ├── PPT大纲.md / .pptx       ← 交付物 6
    │   ├── 对比实验_混合召回.md
    │   └── 答辩演示脚本.md
    └── evals/cookbook/            ← 评测快照与 A/B 记录
```
