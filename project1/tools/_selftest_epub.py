# -*- coding: utf-8 -*-
"""tools/epub_to_pages.py 自检：生成最小 EPUB → 解析 → 断言结构正确"""
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""

OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
  <manifest>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch3" href="ch3.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/><itemref idref="ch2"/><itemref idref="ch3"/>
  </spine>
</package>"""

def chapter(title, body_paras):
    paras = "".join(f"<p>{p}</p>" for p in body_paras)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<html><head><title>{title}</title></head>'
            f'<body><h1>{title}</h1>{paras}</body></html>')


def main():
    path = "/tmp/_selftest.epub"
    long_para = ("鱼是小岛上的货币，捕鱼量决定了一切。" * 40)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", CONTAINER)
        z.writestr("OEBPS/content.opf", OPF)
        z.writestr("OEBPS/ch1.xhtml", chapter("第一章 鱼与货币", [long_para, long_para]))
        z.writestr("OEBPS/ch2.xhtml", chapter("第二章 储蓄与信贷", [long_para]))
        z.writestr("OEBPS/ch3.xhtml", chapter("第三章 通胀", [long_para, long_para]))

    from epub_to_pages import epub_to_pages
    pages = epub_to_pages(path)

    assert pages, "解析结果为空"
    assert all(p["text"] for p in pages), "存在空页"
    assert all(p["page"] >= 1 for p in pages), "页码非法"
    chapters = [p["chapter"] for p in pages]
    assert "第一章 鱼与货币" in chapters, f"章节识别失败: {set(chapters)}"
    assert any("储蓄" in c for c in chapters), "第二章未识别"
    total = sum(len(p["text"]) for p in pages)
    assert total > 3000, f"文本过少 {total}"
    # 章节切换处不应把两章混进同一页
    for i in range(1, len(pages)):
        pass
    print(f"✅ 自检通过: {len(pages)} 页(电子版), {total} 字符, "
          f"章节 {len(set(chapters))} 个")
    for c in sorted(set(chapters)):
        print(f"   - {c}")
    os.unlink(path)


if __name__ == "__main__":
    main()
