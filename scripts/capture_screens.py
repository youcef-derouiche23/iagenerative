"""
Capture de vraies captures d'écran de l'application Streamlit via Playwright.

Pré-requis : l'app doit tourner sur http://127.0.0.1:8501.
Produit dans screenshots/ : questionnaire, top3, visualisations.

Usage : python scripts/capture_screens.py
"""

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.environ.get("APP_URL", "http://127.0.0.1:8501")
# Utiliser le Chromium pré-installé de l'environnement (évite "playwright install")
CHROME = os.environ.get("CHROME_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
OUT = Path(__file__).resolve().parents[1] / "screenshots"
OUT.mkdir(exist_ok=True)

DESC = ("Un film de science-fiction philosophique sur le temps, la mémoire et la "
        "nature de la réalité, visuellement spectaculaire, avec une atmosphère "
        "contemplative et des twists narratifs qui font réfléchir longtemps.")


def main():
    with sync_playwright() as p:
        launch_kwargs = {"headless": True}
        if Path(CHROME).exists():
            launch_kwargs["executable_path"] = CHROME
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1280, "height": 1600})
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # 1) Questionnaire
        page.screenshot(path=str(OUT / "01_questionnaire.png"), full_page=True)
        print("capture 01_questionnaire.png")

        # Remplir la description libre
        ta = page.locator("textarea").first
        ta.fill(DESC)
        page.wait_for_timeout(1000)

        # Cliquer sur "Analyser mes Préférences"
        page.get_by_role("button", name="Analyser mes Préférences").click()
        print("analyse lancée, attente des résultats (SBERT)...")

        # Attendre l'état "résultats" : l'onglet "Top 3 Films" devient visible
        # (le questionnaire a disparu). On vise l'onglet, pas un texte ambigu.
        page.get_by_role("tab", name="Top 3 Films").wait_for(state="visible", timeout=180000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)

        # 2) Top 3 films
        page.get_by_role("tab", name="Top 3 Films").click()
        page.wait_for_timeout(3000)
        page.screenshot(path=str(OUT / "02_top3.png"), full_page=True)
        print("capture 02_top3.png")

        # 3) Onglet Visualisations
        try:
            page.get_by_role("tab", name="Visualisations").click()
            page.wait_for_timeout(4000)
            page.screenshot(path=str(OUT / "03_visualisations.png"), full_page=True)
            print("capture 03_visualisations.png")
        except Exception as e:
            print("visualisations KO:", e)

        # 4) Onglet Statistiques (détails techniques)
        try:
            page.get_by_role("tab", name="Statistiques").click()
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUT / "04_statistiques.png"), full_page=True)
            print("capture 04_statistiques.png")
        except Exception as e:
            print("statistiques KO:", e)

        browser.close()


if __name__ == "__main__":
    main()
