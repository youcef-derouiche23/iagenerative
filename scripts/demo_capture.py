"""Capture live d'une démo (requête personnalisée) — pour montrer l'app en action."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8501"
OUT = Path(__file__).resolve().parents[1] / "screenshots_demo"
OUT.mkdir(exist_ok=True)
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

DESC = ("Je cherche un film d'animation japonais poétique et émouvant, sur "
        "l'enfance et le passage du temps, avec une atmosphère contemplative "
        "et de magnifiques paysages.")

with sync_playwright() as p:
    kw = {"headless": True}
    if Path(CHROME).exists():
        kw["executable_path"] = CHROME
    b = p.chromium.launch(**kw)
    page = b.new_page(viewport={"width": 1280, "height": 1700})
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    page.screenshot(path=str(OUT / "debug_initial.png"))
    page.wait_for_selector("textarea", state="visible", timeout=90000)
    page.locator("textarea").first.fill(DESC)
    page.wait_for_timeout(800)
    page.get_by_role("button", name="Analyser mes Préférences").click()
    print("analyse lancee...")
    page.get_by_role("tab", name="Top 3 Films").wait_for(state="visible", timeout=180000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(4000)
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(800)
    page.get_by_role("tab", name="Top 3 Films").click()
    page.wait_for_timeout(2500)
    page.screenshot(path=str(OUT / "demo_top3.png"), full_page=True)
    print("demo_top3.png")
    page.get_by_role("tab", name="Visualisations").click()
    page.wait_for_timeout(3500)
    page.screenshot(path=str(OUT / "demo_visu.png"), full_page=True)
    print("demo_visu.png")
    b.close()
