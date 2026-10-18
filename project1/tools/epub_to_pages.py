# -*- coding: utf-8 -*-
"""
EPUB → [{page, text, chapter}]（与 PDF 的 extract_pages 同构，供 build_kb 复用）
=============================================================================
背景：教材不一定是 PDF。EPUB 本质是 zip + XHTML + OPF 目录，
      文本层干净（无双栏/页眉脚注噪声），解析成本远低于 PDF。

页码约定：EPUB 无固定版式 → 无真实页码。
      按固定字符窗口折算"电子版页码"（默认 1800 字符 ≈ 一页），
      引用格式与 PDF 完全一致（p.XX），但属于**电子版页码**，
      在报告/演示中须标注"EPUB 按固定长度折算页码"。

用法:
    python tools/epub_to_pages.py <book.epub> [out.json]
    或作为库导入: from tools.epub_to_pages import epub_to_pages
"""
import html
import json
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

PAGE_CHARS = int(os.environ.get("EPUB_PAGE_CHARS", "1800"))

OPF_NS = "{http://www.idpf.org/2007/opf}"
NCX_MIME = "application/x-dtbncx+xml"
NAV_MIME = "application/xhtml+xml"


def _container_opf(z):
    """从 META-INF/container.xml 找到 OPF 主文件路径"""
    try:
        root = ET.fromstring(z.read("META-INF/container.xml"))
        for rf in root.iter():
            if rf.tag.endswith("rootfile"):
                return rf.attrib.get("full-path")
    except KeyError:
        pass
    # 兜底：直接找 .opf
    for n in z.namelist():
        if n.endswith(".opf"):
            return n
    return None


def _read_manifest(z, opf_path):
    """返回 {id: (绝对路径, media-type, properties)} 与 spine 阅读顺序"""
    base = os.path.dirname(opf_path)
    root = ET.fromstring(z.read(opf_path))

    manifest = {}
    for item in root.iter():
        if item.tag == f"{OPF_NS}item":
            href = item.attrib.get("href", "")
            full = os.path.normpath(os.path.join(base, href)) if base else href
            manifest[item.attrib.get("id")] = (
                full, item.attrib.get("media-type", ""),
                item.attrib.get("properties", ""))

    spine = []
    for itemref in root.iter():
        if itemref.tag == f"{OPF_NS}itemref":
            idref = itemref.attrib.get("idref")
            if idref in manifest and manifest[idref][1].startswith("application/xhtml"):
                spine.append(idref)
    return manifest, spine


_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", re.S | re.I)
_BLANK_RE = re.compile(r"[ \t\xa0]+")
_HEADING_RE = re.compile(r"<h[1-4][^>]*>(.*?)</h[1-4]>", re.S | re.I)


def _strip_html(raw):
    """XHTML → 纯文本（保段落边界；剥掉脚本/样式/标签）"""
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.S | re.I)
    raw = re.sub(r"</(p|div|li|h[1-6]|tr|blockquote)>", "\n\n", raw, flags=re.I)
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    raw = _TAG_RE.sub("", raw)
    text = html.unescape(raw)
    # 归一化空白：每行内去多余空格，空行保留为段落分隔
    lines = [_BLANK_RE.sub(" ", ln).strip() for ln in text.splitlines()]
    out, prev_blank = [], True
    for ln in lines:
        if not ln:
            if not prev_blank:
                out.append("")
                prev_blank = True
        else:
            out.append(ln)
            prev_blank = False
    # 压缩连续空行
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def _headings(raw):
    """抽取该文件中的标题（用于章节名）"""
    hs = []
    for m in _HEADING_RE.finditer(raw):
        t = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        if t:
            hs.append(t)
    return hs


def epub_to_pages(epub_path, page_chars=None):
    """返回 [{page, text, chapter}]，与 extract_pages 输出同构"""
    page_chars = page_chars or PAGE_CHARS
    with zipfile.ZipFile(epub_path) as z:
        opf = _container_opf(z)
        if not opf:
            raise ValueError(f"不是有效的 EPUB（找不到 OPF）: {epub_path}")
        manifest, spine = _read_manifest(z, opf)
        if not spine:
            raise ValueError(f"EPUB spine 为空: {epub_path}")

        # ---- 全文拼接，同时记录章节归属 ----
        current_chapter = os.path.basename(epub_path)
        sections = []          # [(chapter, text)]
        for item_id in spine:
            full, _mt, _props = manifest[item_id]
            try:
                raw = z.read(full).decode("utf-8", errors="ignore")
            except KeyError:
                # href 可能带 URL 编码
                from urllib.parse import unquote
                alt = os.path.normpath(os.path.join(os.path.dirname(opf),
                                                    unquote(os.path.basename(full))))
                try:
                    raw = z.read(alt).decode("utf-8", errors="ignore")
                except KeyError:
                    continue
            hs = _headings(raw)
            if hs:
                current_chapter = hs[0][:60]     # 文件内首个标题即章节名
            text = _strip_html(raw)
            if len(text) >= 80:                  # 过滤封面/版权空页
                sections.append((current_chapter, text))

    # ---- 按固定窗口切"电子版页码" ----
    pages = []
    buf, chap_buf = "", sections[0][0] if sections else "正文"
    page_no = 1
    for chap, text in sections:
        if chap != chap_buf and len(buf) >= 200:
            pages.append({"page": page_no, "text": buf, "chapter": chap_buf})
            page_no += 1
            buf, chap_buf = "", chap
        buf += ("\n\n" + text) if buf else text
        while len(buf) >= page_chars:
            cut = buf.rfind("。", 0, page_chars) or buf.rfind(".", 0, page_chars)
            if cut < page_chars // 2:
                cut = page_chars
            else:
                cut += 1
            pages.append({"page": page_no, "text": buf[:cut].strip(),
                          "chapter": chap_buf})
            page_no += 1
            buf = buf[cut - 100:].lstrip() if cut > 100 else ""
            chap_buf = chap
    if len(buf) >= 80:
        pages.append({"page": page_no, "text": buf, "chapter": chap_buf})

    return [p for p in pages if p["text"]]


if __name__ == "__main__":
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + "_pages.json"
    ps = epub_to_pages(src)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(ps, f, ensure_ascii=False, indent=1)
    total = sum(len(p["text"]) for p in ps)
    chaps = sorted({p["chapter"] for p in ps})
    print(f"[epub] {os.path.basename(src)} → {len(ps)} 页(电子版) / {total} 字符")
    print(f"[epub] 章节 {len(chaps)} 个: {chaps[:8]}{' ...' if len(chaps) > 8 else ''}")
    print(f"[epub] → {out}")
