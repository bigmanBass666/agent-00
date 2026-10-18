# -*- coding: utf-8 -*-
"""Web UI 自动化验证 + 截图"""
import sys
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8000"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900},
                                device_scale_factor=2)
        page.goto(URL, wait_until="networkidle")
        page.screenshot(path="/tmp/ui_00_empty.png", full_page=True)
        print("[1] 空态截图完成")

        # 课内题
        page.fill("#q", "How many tablespoons are in one cup?")
        page.click("#send")
        page.wait_for_selector(".answer.show", timeout=90000)
        page.wait_for_timeout(500)
        page.screenshot(path="/tmp/ui_01_answer.png", full_page=True)
        body = page.inner_text("#body")
        assert "8" in body and "p.14" in body, f"课内题校验失败: {body[:120]}"
        hits = page.query_selector_all(".hit")
        print(f"[2] 课内题通过，检索片段 {len(hits)} 个")

        # 课外题（拒答）
        page.fill("#q", "What is the capital of France?")
        page.click("#send")
        page.wait_for_selector(".refused", timeout=90000)
        page.wait_for_timeout(400)
        page.screenshot(path="/tmp/ui_02_refuse.png", full_page=True)
        print("[3] 拒答态通过")

        # 移动端视口
        page.set_viewport_size({"width": 390, "height": 844})
        page.fill("#q", "How do I make protein French toast?")
        page.click("#send")
        page.wait_for_selector(".answer.show", timeout=90000)
        page.wait_for_timeout(500)
        page.screenshot(path="/tmp/ui_03_mobile.png", full_page=True)
        print("[4] 移动端截图完成")

        browser.close()
        print("全部通过")


if __name__ == "__main__":
    sys.exit(main())
