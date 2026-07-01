"""Vérification end-to-end : analyse complète + capture de tous les onglets."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.environ.get("APP_URL", "http://127.0.0.1:8503")
OUT = Path(__file__).resolve().parents[1] / "screenshots_verify"
OUT.mkdir(exist_ok=True)
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
DESC = ("Un film de science-fiction philosophique sur le temps, la mémoire et la nature "
        "de la réalité, visuellement spectaculaire et contemplatif.")

with sync_playwright() as p:
    kw = {"headless": True}
    if Path(CHROME).exists():
        kw["executable_path"] = CHROME
    b = p.chromium.launch(**kw)
    pg = b.new_page(viewport={"width": 1280, "height": 1700})
    pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_selector("textarea", state="visible", timeout=90000)
    pg.locator("textarea").first.fill(DESC)
    pg.wait_for_timeout(600)
    pg.get_by_role("button", name="Analyser mes Préférences").click()
    print("analyse lancée (SBERT + Gemini)...")
    pg.get_by_role("tab", name="Top 3 Films").wait_for(state="visible", timeout=240000)
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(4000)
    tabs = [("Top 3 Films", "v_top3"), ("Visualisations", "v_visu"),
            ("Profil Cinéphile", "v_profil"), ("Plan de Découverte", "v_plan"),
            ("Statistiques", "v_stats")]
    for label, fname in tabs:
        try:
            pg.get_by_role("tab", name=label).click()
            pg.wait_for_timeout(2800)
            pg.evaluate("window.scrollTo(0,0)")
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(OUT / f"{fname}.png"), full_page=True)
            print("capture", fname)
        except Exception as e:
            print(label, "KO", e)
    b.close()
print("OK")
