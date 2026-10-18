# -*- coding: utf-8 -*-
"""
Web UI（交付物 2 的可视化封装 / 拓展挑战：可视化界面）
=====================================================
零依赖：只用 Python 内置 http.server，不引入 Flask/FastAPI。
用法:
    python webui.py            # 默认 http://127.0.0.1:8000
    python webui.py 8080       # 指定端口
"""
import json
import os
import re
import sys

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rag import load_kb, ask  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webui")
CHUNKS, VECTORS = load_kb(verbose=False)


def clean_snippet(text):
    """去除 PDF 提取噪音：页码+书名连写、全大写页眉等"""
    if not text:
        return text
    # 格式1: 字母间带空格的页眉，如 "T H E U L T I M A T E ... 2 . 0"
    # 只匹配"单字符+空白"的重复模式，遇到正常单词（大写后接小写）自动停止
    text = re.sub(r"\d*\s*(?:[A-Z]\s+){6,}(?:[A-Z0-9]\s+|\.\s+)*", " ", text)
    # 格式2: 页码+全大写无空格连写，如 "37THEULTIMATEANABOLICCOOKBOOK2.0"
    text = re.sub(r"\d+[A-Z]{8,}[A-Z0-9.]*", " ", text)
    # 格式3: 独立全大写连写串（8+ 大写字母）
    text = re.sub(r"(?<![A-Z])[A-Z]{8,}(?![A-Z])", " ", text)
    # 清理多余空白
    text = re.sub(r"\s+", " ", text).strip()
    return text


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---------- 转人工工单（老师原话：答不上来就自动转人工，人在旁边休息）----------
    TICKET_PATH = os.path.join(ROOT, "tickets.jsonl")

    @classmethod
    def _read_tickets(cls):
        if not os.path.exists(cls.TICKET_PATH):
            return []
        rows = []
        with open(cls.TICKET_PATH, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    rows.append(json.loads(ln))
        return rows

    @classmethod
    def _new_ticket(cls, question):
        from datetime import datetime as _dt
        rows = cls._read_tickets()
        now = _dt.now()
        day = now.strftime("%Y%m%d")
        seq = sum(1 for r in rows if r.get("id", "").startswith(f"T{day}-")) + 1
        ticket = {
            "id": f"T{day}-{seq:03d}",
            "question": question,
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pending",
        }
        with open(cls.TICKET_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(ticket, ensure_ascii=False) + "\n")
        return ticket

    @classmethod
    def _resolve_ticket(cls, ticket_id):
        rows = cls._read_tickets()
        hit = False
        for r in rows:
            if r.get("id") == ticket_id:
                r["status"] = "resolved"
                hit = True
        if hit:
            with open(cls.TICKET_PATH, "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return hit

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            path = os.path.join(ROOT, "index.html")
            if not os.path.exists(path):
                self._send(500, json.dumps({"error": "webui/index.html 缺失"}))
                return
            self._send(200, open(path, "rb").read(), "text/html; charset=utf-8")
        elif self.path == "/api/info":           # 前端动态显示块数/向量维度
            self._send(200, json.dumps({
                "chunk_count": len(CHUNKS),
                "vector_dim": VECTORS.shape[1] if VECTORS is not None else 0,
            }, ensure_ascii=False))
        elif self.path == "/handoff":            # 人工工作台：接 AI 答不上来的单
            path = os.path.join(ROOT, "handoff.html")
            if not os.path.exists(path):
                self._send(500, json.dumps({"error": "webui/handoff.html 缺失"}))
                return
            self._send(200, open(path, "rb").read(), "text/html; charset=utf-8")
        elif self.path == "/api/tickets":        # 工单队列（倒序，新单在前）
            self._send(200, json.dumps(self._read_tickets()[::-1],
                                       ensure_ascii=False))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path == "/api/tickets/resolve":  # 人工标记已处理
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n) or b"{}")
            ok = self._resolve_ticket((payload.get("id") or "").strip())
            self._send(200, json.dumps({"ok": ok}))
            return
        if self.path != "/api/ask":
            self._send(404, json.dumps({"error": "not found"}))
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n) or b"{}")
            question = (payload.get("question") or "").strip()
            if not question:
                self._send(400, json.dumps({"error": "问题为空"}, ensure_ascii=False))
                return
            result = ask(question, CHUNKS, VECTORS)
            # 拒答 = 系统答不了 → 自动生成工单转人工（核心要求之一）
            if result.get("refused"):
                result["ticket"] = self._new_ticket(question)
            # context 体积大，不回传给前端
            result.pop("context", None)
            # 清洗来源片段中的 PDF 提取噪音
            for hit in result.get("hits", []):
                hit["snippet"] = clean_snippet(hit.get("snippet", ""))
            self._send(200, json.dumps(result, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))

    def log_message(self, *args):  # 静默访问日志
        pass


def main():
    # 云平台会注入 PORT；本地默认 8000
    port = int(os.environ.get("PORT",
                              sys.argv[1] if len(sys.argv) > 1 else 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("=" * 52)
    print("  知识库问答系统 · Web UI")
    print(f"  知识库: {len(CHUNKS)} 块")
    print(f"  监听: http://{host}:{port}")
    print("  Ctrl+C 退出")
    print("=" * 52)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
