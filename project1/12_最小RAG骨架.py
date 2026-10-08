# -*- coding: utf-8 -*-
"""
最小 RAG 骨架（项目一 · 已补全 TODO 1-6）
============================================
说明：本版本已补完全部 6 处 TODO，可直接运行 `python 12_最小RAG骨架.py`
完成一次端到端问答。embedding 和 LLM 当前使用占位实现（哈希假向量 + 模拟回答），
接入课程统一接口后只需替换 embed() 和 answer() 两个函数内部。
配套语料见 corpus/os_ch1.txt。
"""

import re
import numpy as np

# ---------------------------------------------------------------
# 配置区（可按需调整，调整需在设计文档中说明理由）
# ---------------------------------------------------------------
CHUNK_SIZE = 500          # 分块大小（字）
CHUNK_OVERLAP = 50        # 块间重叠
TOP_K = 3                 # 检索返回的分块数
REFUSE_THRESHOLD = 0.35   # 拒答阈值：最高相似度低于此值则拒答
DOCS_PATH = "corpus/os_ch1.txt"


# ---------------------------------------------------------------
# TODO 1（卡 7）：实现分块器
# 策略：按【x.x】标题切优先于硬切；单块超过 CHUNK_SIZE 时硬切并保留重叠。
# 返回: List[dict]，每个元素 {"chunk_id": int, "text": str, "source": str}
# ---------------------------------------------------------------
def load_and_chunk(path: str):
    with open(path, encoding="utf-8") as f:
        text = f.read()

    # 按【数字.数字】标题切分（前瞻断言，保留标题在每段开头）
    sections = re.split(r"(?=【\d+\.\d+)", text)
    chunks = []
    chunk_id = 0

    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        # 提取标题作为来源标记
        header_match = re.match(r"(【[^】]+】)", sec)
        source = header_match.group(1) if header_match else "未知章节"

        # 段落不超过块大小 → 整块作为一个 chunk
        if len(sec) <= CHUNK_SIZE:
            chunks.append({"chunk_id": chunk_id, "text": sec, "source": source})
            chunk_id += 1
            continue

        # 段落过长 → 硬切 + 重叠，防止句子被切断在边界
        start = 0
        while start < len(sec):
            end = min(start + CHUNK_SIZE, len(sec))
            piece = sec[start:end].strip()
            if piece:
                chunks.append({"chunk_id": chunk_id, "text": piece, "source": source})
                chunk_id += 1
            if end >= len(sec):
                break
            start = end - CHUNK_OVERLAP

    return chunks


# ---------------------------------------------------------------
# 工具函数：稳定哈希（不依赖 Python 随机化 hash，保证每次运行向量一致）
# ---------------------------------------------------------------
def _stable_hash(s: str) -> int:
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h


# ---------------------------------------------------------------
# TODO 2（卡 4）：实现 embedding
# 当前实现：字符 n-gram 哈希占位向量（仅调试用，效果差，必须在文档中声明）。
# 接入课程统一 embedding 接口后，替换本函数内部即可，返回值形状不变。
# 返回: np.ndarray, shape (dim,)
# ---------------------------------------------------------------
EMBED_DIM = 256


def embed(text: str) -> np.ndarray:
    vec = np.zeros(EMBED_DIM, dtype=np.float32)
    text = text.lower()
    # 多粒度 n-gram（2/3/4 字符），捕捉中文词组信息
    for n in (2, 3, 4):
        for i in range(len(text) - n + 1):
            gram = text[i:i + n]
            idx = _stable_hash(gram) % EMBED_DIM
            vec[idx] += 1.0
    # L2 归一化，使点积等于余弦相似度
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


# ---------------------------------------------------------------
# TODO 3（卡 5）：实现检索
# 对全部分块向量计算余弦相似度（向量已归一化，点积即余弦），返回 top_k。
# 几千规模用 numpy 暴力即可，无需向量数据库。
# ---------------------------------------------------------------
def retrieve(query: str, chunks, top_k=TOP_K):
    if not chunks:
        return []
    q_vec = embed(query)
    chunk_vecs = np.array([embed(c["text"]) for c in chunks])
    scores = chunk_vecs @ q_vec  # 归一化后点积 = 余弦相似度
    scored = list(zip(chunks, scores))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


# ---------------------------------------------------------------
# TODO 4（卡 3 + 卡 8）：组装 Prompt 并调用 LLM
# 当前实现：模拟 LLM（无 API 时占位）。接入真实接口后替换 mock_llm() 调用。
# 返回: str
# ---------------------------------------------------------------
SYSTEM_PROMPT = (
    "你是课程助教。你只能依据【资料】回答，不得编造。"
    "若资料不足以回答，必须只输出：课程资料中未找到相关内容。"
    "回答末尾注明来源段落编号。"
)
REFUSE_SENTENCE = "课程资料中未找到相关内容。"


def mock_llm(prompt: str) -> str:
    """模拟 LLM 输出（占位，仅用于无 API 时跑通链路）。
    接入课程统一 LLM 接口后，删除本函数并在 answer() 中直接调用接口。"""
    return (
        "[模拟回答] 已依据检索到的资料生成回答。\n"
        "（接入真实 LLM 接口后，此处将返回基于资料的实际生成内容。）"
    )


def answer(query: str, retrieved) -> str:
    if not retrieved:
        return REFUSE_SENTENCE
    # 将 retrieved 中的 chunk 文本拼入 Prompt 的【资料】部分
    context_parts = []
    for chunk, score in retrieved:
        context_parts.append(
            f"【资料 {chunk['chunk_id']}｜来源：{chunk['source']}｜相似度={score:.3f}】\n{chunk['text']}"
        )
    context = "\n\n".join(context_parts)
    prompt = f"{SYSTEM_PROMPT}\n\n【资料】\n{context}\n\n【问题】{query}\n\n【回答】"

    # TODO: 替换为课程统一 LLM 接口调用（勿用个人 key）
    return mock_llm(prompt)


# ---------------------------------------------------------------
# TODO 5（卡 8）：拒答判定
# 若 top-1 相似度 < REFUSE_THRESHOLD，直接拒答，不调用 LLM。
# 为什么放在 LLM 之前？省 token + 防止模型在低相关资料上"认真地编造"。
# ---------------------------------------------------------------
def rag_query(query: str, chunks) -> dict:
    retrieved = retrieve(query, chunks)
    top_score = float(retrieved[0][1]) if retrieved else 0.0

    if top_score < REFUSE_THRESHOLD:
        return {
            "query": query,
            "answer": REFUSE_SENTENCE,
            "refused": True,
            "sources": [],
            "top_score": top_score,
        }

    ans = answer(query, retrieved)
    return {
        "query": query,
        "answer": ans,
        "refused": False,
        "sources": [c["chunk_id"] for c, _ in retrieved],
        "top_score": top_score,
    }


# ---------------------------------------------------------------
# TODO 6：主流程
# 运行后输出一次完整问答（含来源与是否拒答），并附带库外问题测试拒答。
# ---------------------------------------------------------------
if __name__ == "__main__":
    chunks = load_and_chunk(DOCS_PATH)
    print(f"共加载 {len(chunks)} 个分块")
    for c in chunks:
        print(f"  chunk {c['chunk_id']}: {c['source']}（{len(c['text'])} 字）")

    test_queries = [
        "什么是进程？进程和程序有什么区别？",   # 课内题
        "进程有哪几种状态？",                    # 课内题
        "明天天气怎么样？",                      # 库外题 → 应拒答
        "帮我写一段 Python 排序代码",            # 库外题 → 应拒答
    ]

    for q in test_queries:
        print(f"\n{'=' * 55}")
        print(f"问题: {q}")
        result = rag_query(q, chunks)
        print(f"  top_score : {result['top_score']:.4f}（阈值 {REFUSE_THRESHOLD}）")
        print(f"  refused   : {result['refused']}")
        print(f"  sources   : {result['sources']}")
        print(f"  回答      : {result['answer']}")
