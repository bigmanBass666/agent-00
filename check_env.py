# -*- coding: utf-8 -*-
"""环境自检脚本（课程仓库模板要求）
================================
用法：python check_env.py
预期：全部通过时输出 ALL CHECKS PASSED

检查项：
  1. Python 版本 ≥ 3.10
  2. 依赖可导入：requests / numpy / pymupdf
  3. API key 已配置（环境变量或 project1/.env）
  4. 知识库成品文件存在（交付物 1：kb_chunks.json + kb_vectors.npy）
  5. 教材 PDF 是否存在（可选——版权材料不入库，缺失不判失败）
  6. 评测数据落点存在（evals/project1/）
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(ROOT, "project1")

ok = True


def check(name, cond, detail=""):
    global ok
    mark = "PASS" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def main():
    # 1. Python 版本
    check("Python >= 3.10", sys.version_info >= (3, 10),
          f"当前 {sys.version.split()[0]}")

    # 2. 依赖
    for mod in ("requests", "numpy", "pymupdf"):
        try:
            __import__(mod)
            check(f"依赖 {mod}", True)
        except ImportError:
            check(f"依赖 {mod}", False, "请 pip install -r project1/requirements.txt")

    # 3. API key
    key = os.environ.get("SILICONFLOW_API_KEY", "")
    if not key:
        env = os.path.join(PROJ, ".env")
        if os.path.exists(env):
            with open(env, encoding="utf-8") as f:
                key = next((ln.split("=", 1)[1].strip().strip('"\'')
                            for ln in f if ln.startswith("SILICONFLOW_API_KEY=")), "")
    check("API key 已配置", bool(key), "环境变量或 project1/.env（不入库）")

    # 4. 知识库成品文件（交付物 1，必须入库）
    for f in ("kb_chunks.json", "kb_vectors.npy"):
        p = os.path.join(PROJ, f)
        size = os.path.getsize(p) // 1024 if os.path.exists(p) else 0
        check(f"知识库文件 {f}", os.path.exists(p), f"{size}K")

    # 5. 教材 PDF（可选）
    pdf = os.path.join(PROJ, "textbook.pdf")
    print(f"[INFO] 教材 PDF {'存在' if os.path.exists(pdf) else '缺失（版权材料不入库，可跳过）'}")

    # 6. 评测数据落点
    check("评测数据目录 evals/project1/", os.path.isdir(os.path.join(ROOT, "evals", "project1")))

    print()
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
