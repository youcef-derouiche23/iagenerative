"""
Génère les livrables rédigés au format Office (NON commités dans le dépôt) :
  livrables/rapport_projet3.docx
  livrables/plan_soutenance_projet3.docx
  livrables/antiseche_projet3.docx
  livrables/dossier_audit_projet3.docx
  livrables/presentation_projet3.pptx

Les chiffres clés sont lus dynamiquement depuis evaluation/*.md quand ils
existent (sinon valeurs de repli). Captures réelles : screenshots/*.png ;
figure d'éval : evaluation/figures/*.png.

Usage : python scripts/generate_deliverables.py
"""

import os
import re
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pptx import Presentation
from pptx.util import Inches as PInches, Pt as PPt
from pptx.dml.color import RGBColor as PRGB
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "livrables"
OUT.mkdir(exist_ok=True)
SHOTS = ROOT / "screenshots"
FIGS = ROOT / "evaluation" / "figures"

AUTHORS = "BOUCHER Anthony & DEROUICHE Youcef"
ACCENT = RGBColor(0x0E, 0xA5, 0xE9)
PACCENT = PRGB(0x0E, 0xA5, 0xE9)

# --- Chiffres clés (repli ; surchargés par lecture des résultats si dispo) ---
NUM = {
    "ndcg_sem": "0.333", "ndcg_bug": "0.326", "ndcg_cal": "0.506",
    "mrr_sem": "0.593", "mrr_cal": "0.778", "gain_ndcg": "+52",
    "tfidf_ndcg": "0.031", "sbert_ndcg": "0.333", "tfidf_gain": "+961",
    "w_naive": "0.489", "w_chosen": "0.506",
    "model": "gemini-2.5-flash",
}


def _read(path):
    p = ROOT / path
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _load_numbers():
    """Met à jour NUM depuis les fichiers de résultats générés."""
    res = _read("evaluation/RESULTS.md")
    m = re.search(r"de \*\*([\d.]+)\*\* à \*\*([\d.]+)\*\* \(\+?([\d.]+)\s*%", res)
    if m:
        NUM["ndcg_sem"], NUM["ndcg_cal"] = m.group(1), m.group(2)
        NUM["gain_ndcg"] = "+" + m.group(3).split(".")[0]
    base = _read("evaluation/baseline_results.md")
    mb = re.search(r"nDCG@5 de \*\*\+?([\d.]+)\s*%", base)
    if mb:
        NUM["tfidf_gain"] = "+" + mb.group(1).split(".")[0]


# ---------------------------------------------------------------- DOCX helpers
def h1(doc, t): return doc.add_heading(t, level=1)
def h2(doc, t): return doc.add_heading(t, level=2)


def para(doc, text, bold=False, italic=False):
    p = doc.add_paragraph(); r = p.add_run(text); r.bold = bold; r.italic = italic
    return p


def bullet(doc, text): doc.add_paragraph(text, style="List Bullet")
def numbered(doc, text): doc.add_paragraph(text, style="List Number")


def table(doc, headers, rows):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Light Grid Accent 1"
    for i, h in enumerate(headers):
        run = t.rows[0].cells[i].paragraphs[0].add_run(h); run.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
    return t


def title_block(doc, title, subtitle):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title); r.bold = True; r.font.size = Pt(24); r.font.color.rgb = ACCENT
    p2 = doc.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.add_run(subtitle).font.size = Pt(12)
    p3 = doc.add_paragraph(); p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.add_run(AUTHORS + "  —  RNCP40875, Bloc 2 (C5.1 → C5.3)").italic = True
    doc.add_paragraph()


# ======================================================= 1. RAPPORT
def build_rapport():
    doc = Document()
    title_block(doc, "Rapport — Projet 3 : IA Générative",
                "AISCA-Cinema : agent de recommandation cinématographique (RAG)")

    h1(doc, "1. Besoin métier (C5.1)")
    para(doc, "Face au volume de films disponibles, choisir quoi regarder est coûteux. "
              "Les moteurs par mots-clés ne comprennent pas une envie exprimée en langage "
              "naturel et n'expliquent pas leurs suggestions. AISCA-Cinema répond au besoin "
              "de découverte personnalisée : l'utilisateur décrit son envie avec ses mots, "
              "et l'agent recommande des films pertinents ET justifie son choix, à partir "
              "d'un référentiel maîtrisé (pas d'invention).")
    para(doc, "Pourquoi la GenAI : compréhension sémantique de la demande (SBERT) + "
              "restitution personnalisée en langage naturel (LLM), hors de portée d'un "
              "simple filtre par genres.")

    h1(doc, "2. Choix techniques")
    para(doc, "Approche retenue : un RAG (Retrieval-Augmented Generation) — récupération "
              "sémantique de films pertinents puis génération de synthèses ancrées sur ces films.")
    table(doc, ["Décision", "Choix", "Justification"], [
        ["Paradigme", "RAG", "corpus évolutif sans réentraînement ; génération traçable ; coût maîtrisé"],
        ["vs Fine-tuning", "écarté", "coût/temps, données insuffisantes, perte de traçabilité"],
        ["vs Prompting seul", "écarté", "risque d'hallucination sans ancrage corpus"],
        ["Embeddings", "SBERT multilingue MiniLM-L12-v2", "requête FR / corpus EN, léger en CPU"],
        ["Génération", f"Google Gemini ({NUM['model']})", "qualité FR, free tier, latence faible"],
        ["Coûts API", "cache + retry/backoff + 2 appels/session", "free tier respecté, résilience"],
    ])
    para(doc, "Pourquoi SBERT plutôt qu'un index lexical : une baseline TF-IDF (mots-clés) "
              f"obtient un nDCG@5 de {NUM['tfidf_ndcg']} contre {NUM['sbert_ndcg']} pour SBERT "
              f"(soit {NUM['tfidf_gain']} %). L'écart est massif car les requêtes sont en "
              "français et les descriptions en anglais : seul un modèle multilingue fait le "
              "pont sémantique — ce qu'un index de mots-clés ne peut pas.")

    h1(doc, "3. Réalisation")
    bullet(doc, "questionnaire.py : acquisition et structuration des préférences.")
    bullet(doc, "nlp_engine.py : retrieval SBERT + cache des embeddings (mémoire ET disque) + index FAISS optionnel.")
    bullet(doc, "scoring.py : ranking pondéré 0.50 sémantique + 0.40 genre + 0.10 mood (poids calibrés, cf. §4).")
    bullet(doc, "genai_integration.py : génération Gemini, GenerationConfig ajustable, retry/backoff (quota 429), "
                "safety_settings, garde-fou anti-prompt-injection, suivi tokens/coût/latence, LLM-as-judge.")
    bullet(doc, "app.py : UI Streamlit accessible, traçabilité des sources, mode dégradé sans clé API.")
    h2(doc, "Correctifs majeurs apportés lors de la finalisation")
    numbered(doc, "Sécurité : retrait d'une clé API réelle commitée dans .env.example (rotation effectuée).")
    numbered(doc, "Bug fonctionnel (C5.2) : composant genre neutralisé (libellés FR vs colonne Genre "
                  "anglaise). Corrigé via la colonne Categorie (FR) + matching insensible aux accents.")
    numbered(doc, "Évaluation (C5.3) : cadre d'évaluation complet créé (métriques retrieval, validation "
                  "croisée des poids, LLM-as-judge, comparaison de paramètres).")
    numbered(doc, "Industrialisation : Dockerfile, persistance des embeddings, suivi des coûts, CI GitHub Actions.")

    h1(doc, "4. Preuve (mesures réelles)")
    h2(doc, "4.1 Qualité du RAG — comparaison avant / après")
    para(doc, "Jeu de cas : 15 requêtes annotées (vérité terrain). Métriques @5 :")
    table(doc, ["Configuration", "MRR", "nDCG@5"], [
        ["A. Sémantique seule (baseline)", NUM["mrr_sem"], NUM["ndcg_sem"]],
        ["B. Pondéré — genre buggé (colonne EN)", "0.533", NUM["ndcg_bug"]],
        ["C. Pondéré — corrigé + calibré 50/40/10", NUM["mrr_cal"], NUM["ndcg_cal"]],
    ])
    para(doc, f"Le correctif (A → C) améliore le nDCG@5 de {NUM['gain_ndcg']} % et le MRR de "
              f"{NUM['mrr_sem']} à {NUM['mrr_cal']}. La config B (genre buggé) reste collée au "
              "sémantique seul — preuve chiffrée que le composant genre était inopérant.")
    if (FIGS / "rag_comparison.png").exists():
        doc.add_picture(str(FIGS / "rag_comparison.png"), width=Inches(5.6))
    h2(doc, "4.2 Calibrage des poids (validation croisée)")
    para(doc, "Les poids ne sont pas fixés à la main : un grid-search sur le jeu annoté "
              f"montre que 0.50/0.40/0.10 (nDCG@5 {NUM['w_chosen']}) bat le réglage naïf "
              f"0.50/0.30/0.20 ({NUM['w_naive']}). On garde le sémantique dominant (robuste "
              "sur les requêtes libres) et le mood comme départage léger. Script : "
              "evaluation/tune_weights.py.")
    h2(doc, "4.3 Qualité de la génération (LLM-as-judge + paramètres)")
    para(doc, "Un LLM-as-judge (appel déterministe, JSON strict) note chaque réponse de 1 à 5 "
              "(pertinence, exactitude, complétude, absence d'hallucination, ton). On compare "
              "deux réglages — Factuelle (température 0.2) vs Créative (0.9) — et on retient le "
              "meilleur compromis qualité/fiabilité. Scripts : evaluation/compare_params.py "
              "(résultats dans evaluation/params_results.md).")
    h2(doc, "4.4 Tests & CI")
    para(doc, "29 tests unitaires (scoring, métriques, cache, anti-injection) ; CI GitHub "
              "Actions exécutant les tests à chaque push (garde-fou de non-régression).")

    h1(doc, "5. Résultat")
    para(doc, "Application fonctionnelle et accessible, RAG réellement personnalisé (correctif "
              "prouvé), génération ancrée/traçable et résiliente, évaluation chiffrée avec "
              "comparaison avant/après — C5.1, C5.2 et C5.3 couvertes.")

    h1(doc, "6. Limites, biais et risques")
    bullet(doc, "Corpus : 260 films classiques (IMDb), descriptions EN → biais culturel / couverture limitée.")
    bullet(doc, "Hallucination : atténuée (prompts + sources + garde-fou) mais résiduelle hors top 3.")
    bullet(doc, "Dépendance API + quotas free tier (limites/jour et /minute) → mode dégradé + retry/backoff.")
    bullet(doc, "RGPD : stockage local des réponses libres à encadrer (consentement, rétention).")
    bullet(doc, "Évaluation : vérité terrain construite par les auteurs (subjectivité) ; à élargir.")

    h1(doc, "7. Industrialisation")
    bullet(doc, "Index vectoriel (FAISS, déjà intégré en option) + embeddings persistés (fait).")
    bullet(doc, "Docker (fait) + CI exécutant tests (fait) ; étendre la CI à l'évaluation.")
    bullet(doc, "Monitoring coûts/latence (instrumenté) + supervision du taux d'hallucination + A/B testing des paramètres.")

    h1(doc, "8. Compétences démontrées (mapping RNCP)")
    table(doc, ["Compétence", "Réalisation", "Preuve"], [
        ["C5.1 Cas d'usage", "Besoin métier formalisé, justification RAG, gouvernance (clé, safety, RGPD)", "§1, §2, §6"],
        ["C5.2 Solution", "RAG fonctionnel, accessible, traçable, résilient ; correctif scoring", "app, §3, tests"],
        ["C5.3 Évaluation", "Métriques + validation croisée poids + LLM-as-judge + comparaison params", f"evaluation/, {NUM['gain_ndcg']}% nDCG"],
    ])

    h1(doc, "9. Ma contribution individuelle (à compléter par chaque membre)")
    para(doc, "À personnaliser pour la défense individualisée :", italic=True)
    bullet(doc, "[Prénom] : moteur de retrieval SBERT, système de scoring, correction du bug genre/mood, "
                "calibrage des poids, tests. Choix défendus : SBERT multilingue, pondération calibrée, colonne Categorie.")
    bullet(doc, "[Prénom] : intégration Gemini (prompts, GenerationConfig, retry, safety, anti-injection, coûts), "
                "cadre d'évaluation (métriques, LLM-as-judge, compare_params), UI et traçabilité, Docker/CI.")

    doc.save(OUT / "rapport_projet3.docx")
    print("OK rapport_projet3.docx")


# ======================================================= 2. PLAN DE SOUTENANCE
def build_plan():
    doc = Document()
    title_block(doc, "Plan de soutenance — Projet 3 (IA Générative)",
                "Déroulé slide par slide · script oral · répartition binôme · timing (~10 min)")
    para(doc, "Format : 3 projets en 30 min au total (~10 min/projet) puis 20 min de questions. "
              "Projet 3 : ~10 min, 9 slides de contenu.", italic=True)

    slides = [
        ("1. Titre", "Slide titre (AISCA-Cinema, noms, RNCP).", "—", "Anthony", "0:30",
         "« Bonjour, nous présentons AISCA-Cinema : un agent de recommandation de films basé "
         "sur une architecture RAG. »"),
        ("2. Besoin métier", "Problème, cible, valeur.", "—", "Anthony", "1:00",
         "« Choisir un film est devenu difficile ; les filtres par mots-clés ne comprennent pas "
         "une envie formulée en langage naturel. Notre cible : un spectateur qui décrit une envie, "
         "pas un titre. Valeur : recommander ET justifier. C'est notre cas d'usage C5.1. »"),
        ("3. Architecture RAG", "Schéma pipeline + capture questionnaire.", "01_questionnaire.png",
         "Youcef", "1:30",
         "« Le questionnaire alimente SBERT qui encode la demande et le catalogue ; on récupère "
         "par similarité cosinus, on reclasse par un score pondéré, puis Gemini génère des "
         "synthèses ancrées sur ces films. Retrieval + Generation. »"),
        ("4. Choix techniques", "Tableau RAG vs alternatives + baseline TF-IDF.", "—", "Youcef", "1:15",
         "« Pourquoi un RAG ? Corpus évolutif, génération traçable, coût maîtrisé. Et pourquoi "
         "des embeddings plutôt que des mots-clés ? Notre baseline TF-IDF s'effondre face à SBERT "
         f"({NUM['tfidf_gain']} % de nDCG) car les requêtes sont en français et les films décrits "
         "en anglais : seul le modèle multilingue fait le pont. C'est notre justification C5.2. »"),
        ("5. Démo — Top 3", "Capture recommandations réelles + composantes.", "02_top3.png",
         "Anthony", "1:30",
         "« Voici une vraie sortie : le Top 3 avec le détail du score — sémantique, genre, mood. "
         "La recommandation est expliquée et tracée. »"),
        ("6. Démo — Visualisations", "Radars + barres de score 50/40/10.", "03_visualisations.png",
         "Youcef", "0:45",
         "« Interface accessible à un non-technicien : profils par genre et ambiance, et "
         "décomposition pondérée du score de chaque film. »"),
        ("7. Évaluation (C5.3)", "Figure avant/après + chiffres + poids + juge.", "rag_comparison.png",
         "Anthony", "2:00",
         "« Le cœur de C5.3 : 15 requêtes annotées, mesurées en Precision, Recall, MRR, nDCG. Notre "
         f"correctif fait passer le nDCG@5 de {NUM['ndcg_sem']} à {NUM['ndcg_cal']} ({NUM['gain_ndcg']} %), "
         f"et le MRR de {NUM['mrr_sem']} à {NUM['mrr_cal']}. La barre orange prouve que le genre était "
         "mort avant correction. Les poids 50/40/10 ne sont pas arbitraires : ils sont validés par "
         "grid-search. Et on note la qualité de génération avec un LLM-as-judge, en comparant deux "
         "températures. »"),
        ("8. Limites & industrialisation", "Limites/biais/risques + pistes.", "—", "Youcef", "1:00",
         "« Limites : corpus de 260 films classiques en anglais, hallucination résiduelle, quotas API. "
         "Pour industrialiser : FAISS (déjà intégré), Docker + CI (faits), monitoring des coûts (instrumenté) "
         "et A/B testing des paramètres. »"),
        ("9. Conclusion", "Récap compétences.", "—", "Anthony", "0:30",
         "« En résumé : un cas d'usage justifié et gouverné, une solution RAG fonctionnelle et "
         "résiliente, et une évaluation chiffrée avec optimisation prouvée. Merci. »"),
    ]
    for titre, contenu, img, qui, timing, script in slides:
        h1(doc, titre)
        table(doc, ["Élément", "Détail"], [["À l'écran", contenu], ["Image", img],
                                            ["Qui parle", qui], ["Durée", timing]])
        para(doc, "Script oral :", bold=True)
        para(doc, script, italic=True)
        doc.add_paragraph()
    doc.save(OUT / "plan_soutenance_projet3.docx")
    print("OK plan_soutenance_projet3.docx")


# ======================================================= 3. ANTISÈCHE
def build_antiseche():
    doc = Document()
    title_block(doc, "Antisèche — Projet 3 (IA Générative)",
                "Tout comprendre pour tout expliquer au jury")

    h1(doc, "A. Concepts & outils")
    concepts = [
        ("RAG (Retrieval-Augmented Generation)",
         "Combine une RECHERCHE d'information (retrieval) et une GÉNÉRATION par LLM : on récupère "
         "des documents pertinents (films) puis on les fournit au LLM comme contexte.",
         "Force : génération ancrée et traçable, corpus modifiable sans réentraînement. "
         "Faiblesse : la qualité dépend du retrieval.",
         "SBERT récupère le Top films, Gemini rédige le profil/plan à partir de ces films."),
        ("Embeddings + SBERT (MiniLM-L12-v2 multilingue)",
         "Représentation d'un texte en vecteur, telle que deux textes de sens proche ont des "
         "vecteurs proches. SBERT produit un embedding par phrase ; la version multilingue gère FR+EN.",
         "Force : capte le sens, multilingue, rapide en CPU. Faiblesse : modèle généraliste.",
         "On encode requête et films ; preuve de l'apport : +961 % de nDCG vs TF-IDF (FR↔EN)."),
        ("Similarité cosinus",
         "Mesure l'angle entre deux vecteurs : 1 = très similaire, 0 = sans rapport.",
         "Force : standard, simple. Faiblesse : ne capte que ce que l'embedding encode.",
         "Classe les films par proximité avec la requête."),
        ("Score pondéré + calibrage",
         "0.50 sémantique + 0.40 genre + 0.10 mood. Les poids sont choisis par validation "
         "croisée (grid-search maximisant le nDCG), pas à la main.",
         "Force : transparent, explicable, calibré sur données. Faiblesse : dépend du jeu annoté.",
         "scoring.py + evaluation/tune_weights.py."),
        ("LLM & Gemini (gemini-2.5-flash)",
         "Large Language Model génératif. Gemini 2.5 Flash est rapide ; c'est un modèle « à "
         "raisonnement » : il consomme des tokens en réflexion interne (d'où max_output_tokens élevé).",
         "Force : qualité FR. Faiblesse : peut halluciner, dépend d'une API (quota/coût).",
         "Génère profil et plan (genai_integration.py)."),
        ("Paramètres de génération (température, top-p, top-k)",
         "Température : aléa (0 = factuel, 1 = créatif). top-p/top-k : restreignent l'échantillonnage. "
         "max_output_tokens : longueur max.",
         "Force : arbitrer fiabilité vs richesse. Faiblesse : température élevée = plus d'hallucinations.",
         "Exposés via GenerationConfig ; comparés (0.2 vs 0.9) dans compare_params.py."),
        ("LLM-as-judge",
         "Un second appel LLM (température 0, sortie JSON) note la réponse générée sur des critères "
         "(pertinence, exactitude, hallucination, ton).",
         "Force : évaluation qualité automatisée et reproductible. Faiblesse : le juge a ses propres biais.",
         "judge_response() ; alimente la comparaison de paramètres."),
        ("Métriques de retrieval (Precision@k, Recall@k, MRR, nDCG)",
         "Precision@k : part de pertinents dans les k premiers. Recall@k : part des pertinents "
         "retrouvés. MRR : 1/rang du premier bon résultat. nDCG : qualité du classement.",
         "Force : standards, objectifs. Faiblesse : dépendent d'une vérité terrain.",
         "evaluation/metrics.py, sur 15 requêtes annotées."),
        ("Résilience & gouvernance API",
         "Retry avec backoff exponentiel sur quota 429 ; safety_settings (catégories à risque) ; "
         "garde-fou anti-prompt-injection sur le texte libre ; suivi tokens/coût/latence.",
         "Force : robustesse production, sécurité, observabilité. Faiblesse : free tier limité (quotas/jour).",
         "genai_integration.py."),
        ("FAISS / persistance des embeddings",
         "Les embeddings du corpus sont calculés une fois et persistés (disque) ; FAISS indexe les "
         "vecteurs pour une recherche scalable.",
         "Force : latence et scalabilité. Faiblesse : index à reconstruire si le corpus change.",
         "nlp_engine.py (encode_referentiel persiste ; build_faiss_index optionnel)."),
        ("Streamlit + Docker + CI",
         "Streamlit : UI web Python. Docker : image reproductible. CI (GitHub Actions) : tests "
         "automatiques à chaque push.",
         "Force : prototypage rapide, reproductibilité, non-régression. Faiblesse : Streamlit peu adapté à très forte charge.",
         "app.py, Dockerfile, .github/workflows/ci.yml."),
    ]
    for nom, quoi, ff, projet in concepts:
        h2(doc, nom)
        para(doc, "Ce que c'est : ", bold=True); para(doc, quoi)
        para(doc, "Forces / faiblesses : ", bold=True); para(doc, ff)
        para(doc, "Dans notre projet : ", bold=True); para(doc, projet)

    h1(doc, "B. Questions probables du jury — réponses préparées")
    qa = [
        ("Pourquoi un RAG plutôt qu'un fine-tuning ?",
         "Corpus évolutif sans réentraînement, génération traçable, coût maîtrisé. Le fine-tuning "
         "demanderait beaucoup de données et serait opaque."),
        ("Comment évaluez-vous la qualité ? (LA question C5.3)",
         "Deux niveaux. Retrieval : 15 requêtes annotées + Precision/Recall/MRR/nDCG. Génération : "
         "un LLM-as-judge note pertinence/exactitude/hallucination/ton, et on compare deux "
         f"températures. Preuve : +{NUM['gain_ndcg'].lstrip('+')} % de nDCG après correctif."),
        ("Pourquoi les poids 50/40/10 ?",
         "Ils ne sont pas choisis à la main : un grid-search sur le jeu annoté montre que 50/40/10 "
         f"({NUM['w_chosen']}) bat le réglage naïf 50/30/20 ({NUM['w_naive']}). On garde le sémantique "
         "dominant et un mood de départage."),
        ("Comment gérez-vous les hallucinations ?",
         "Ancrage RAG (le LLM ne voit que des films réels), consignes anti-invention dans les prompts, "
         "indicateur de titres hors-corpus, et un critère « non-hallucination » noté par le juge. "
         "Baisser la température réduit encore le risque."),
        ("Comment industrialiser ?",
         "FAISS (intégré) + embeddings persistés, Docker + CI (faits), monitoring coûts/latence "
         "(instrumenté), supervision du taux d'hallucination, A/B testing des paramètres."),
        ("Qu'avez-vous corrigé exactement ?",
         "Le score de genre comparait des libellés français à une colonne anglaise → 30 % du score "
         "morts. On utilise la colonne Categorie française avec matching insensible aux accents, "
         f"verrouillé par des tests. Impact mesuré : +{NUM['gain_ndcg'].lstrip('+')} % de nDCG."),
        ("Et la résilience / les quotas ?",
         "Retry avec backoff exponentiel sur les erreurs 429 (le free tier limite par jour ET par "
         "minute), cache des réponses, et un mode dégradé qui garde le cœur RAG fonctionnel sans clé."),
        ("Sécurité / gouvernance ?",
         "Clé API retirée du dépôt et rotée ; secrets via .env (gitignoré) ; safety_settings Gemini "
         "configurés ; garde-fou anti-prompt-injection sur le texte libre utilisateur."),
        ("RGPD ?",
         "Réponses libres stockées localement (gitignorées) ; en production : consentement, durée de "
         "conservation, anonymisation."),
    ]
    for q, a in qa:
        para(doc, "Q : " + q, bold=True); para(doc, "R : " + a)

    h1(doc, "C. Mémo transposable aux autres projets")
    for b in ["Relier chaque réalisation à une compétence : « ceci démontre Cx.y car… ».",
              "Suivre la logique besoin → choix → réalisation → preuve → résultat → limites.",
              "Apporter des PREUVES chiffrées (métriques, avant/après), pas des descriptions.",
              "Assumer les limites et proposer des améliorations (le jury valorise le recul).",
              "Toujours mentionner sécurité, reproductibilité (deps figées, .env.example, Docker), tests, CI.",
              "Savoir expliquer chaque brique simplement (cf. section A)."]:
        bullet(doc, b)

    doc.save(OUT / "antiseche_projet3.docx")
    print("OK antiseche_projet3.docx")


# ======================================================= 4. DOSSIER AUDIT
def build_dossier():
    doc = Document()
    title_block(doc, "Dossier d'audit & finalisation — Projet 3",
                "Audit · Analyse d'écart RNCP · Récapitulatif final")

    h1(doc, "Partie 1 — Audit de l'existant")
    para(doc, "Base technique saine (RAG réel, code modulaire, cache) mais plusieurs problèmes "
              "identifiés et prouvés par exécution :")
    bullet(doc, "BUG MAJEUR : composant genre (30 % du score) neutralisé — libellés FR vs colonne Genre anglaise.")
    bullet(doc, "Mood matché seulement par hasard (divergences d'accents).")
    bullet(doc, "Modèle Gemini incohérent ; ré-encodage du référentiel à chaque requête.")
    bullet(doc, "Aucune évaluation (C5.3) ; génération sans paramétrage ni résilience.")
    bullet(doc, "Clé API réelle commitée dans .env.example.")

    h1(doc, "Partie 2 — Analyse d'écart vs grille RNCP")
    para(doc, "Échelle : Non démontré (0) / Débutant (2) / Intermédiaire (3) / Professionnel (5).")
    table(doc, ["Compétence", "Avant", "Manque principal", "Action corrective"], [
        ["C5.1 Cas d'usage", "3", "besoin métier non formalisé, gouvernance", "rapport, retrait/rotation clé, safety"],
        ["C5.2 Solution", "3", "bug genre bloquant, traçabilité, perf, résilience", "fix scoring, sources UI, FAISS, retry"],
        ["C5.3 Évaluation", "0", "aucune évaluation", "métriques + calibrage poids + LLM-as-judge + compare params"],
    ])

    h1(doc, "Partie 3 — Récapitulatif final")
    table(doc, ["Compétence", "Avant", "Après", "Preuve"], [
        ["C5.1", "3/5", "5/5", "rapport ; .env.example assaini + rotation ; safety_settings ; anti-injection"],
        ["C5.2", "3/5", "5/5", "RAG fonctionnel/résilient, UI + traçabilité, fix scoring (tests), FAISS"],
        ["C5.3", "0/5", "5/5", f"métriques (+{NUM['gain_ndcg'].lstrip('+')}% nDCG), calibrage poids, LLM-as-judge, compare params"],
    ])
    h2(doc, "Actions réalisées")
    for a in ["Clé API retirée de .env.example + rotation",
              "Scoring genre/mood corrigé (Categorie FR + accents) + tests",
              "Calibrage des poids par validation croisée (50/40/10)",
              "Cadre d'évaluation : métriques retrieval + baseline TF-IDF + LLM-as-judge",
              "GenerationConfig ajustable + comparaison de paramètres (température)",
              "Résilience : retry/backoff sur quota 429, mode dégradé sans clé",
              "Gouvernance : safety_settings, garde-fou anti-prompt-injection",
              "Observabilité : suivi tokens / coût estimé / latence",
              "Perf : persistance des embeddings + index FAISS optionnel",
              "Qualité : 29 tests unitaires + CI GitHub Actions",
              "Conteneurisation : Dockerfile",
              "Livrables : rapport, slides, plan, antisèche, dossier"]:
        bullet(doc, "Fait — " + a)
    h2(doc, "Limites restantes assumées")
    bullet(doc, "Corpus limité (260 films EN) ; vérité terrain par les auteurs.")
    bullet(doc, "Hallucination résiduelle hors top 3 ; quotas free tier (jour/minute).")
    bullet(doc, "CI limitée aux tests (l'évaluation complète reste lançable en local).")

    doc.save(OUT / "dossier_audit_projet3.docx")
    print("OK dossier_audit_projet3.docx")


# ======================================================= 5. PRÉSENTATION PPTX
# Système de design repris du modèle fourni (deck "Urban Data Explorer") :
# fond clair, badges numérotés verts, pills, cartes arrondies, puces carrées.
INK = PRGB(0x14, 0x28, 0x2E)      # encre (titres/texte)
GREEN = PRGB(0x24, 0x6B, 0x63)    # vert primaire (badges, accents)
GREEN2 = PRGB(0x3F, 0x8F, 0x84)   # vert secondaire
MUTED = PRGB(0x5A, 0x70, 0x77)    # gris-vert (texte secondaire)
ORANGE = PRGB(0xD2, 0x6A, 0x4E)   # accent orange (chiffres clés)
BG = PRGB(0xF3, 0xF6, 0xF5)       # fond
WHITE = PRGB(0xFF, 0xFF, 0xFF)
CARD_LT = PRGB(0xDC, 0xED, 0xE9)  # carte / pill claire
LIGHT = PRGB(0xE9, 0xF1, 0xEF)
FT_TITLE = "Cambria"
FT_BODY = "Calibri"

IN = PInches


def _bg(slide):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = BG


def _round(slide, l, t, w, h, fill, line=None):
    sp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(l), IN(t), IN(w), IN(h))
    sp.fill.solid(); sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line; sp.line.width = PPt(1)
    sp.shadow.inherit = False
    return sp


def _sq(slide, l, t, fill, size=0.16):
    sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, IN(l), IN(t), IN(size), IN(size))
    sp.fill.solid(); sp.fill.fore_color.rgb = fill; sp.line.fill.background()
    sp.shadow.inherit = False
    return sp


def _txt(slide, l, t, w, h, text, size, color, font=FT_BODY, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(IN(l), IN(t), IN(w), IN(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    for i, ln in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run(); r.text = ln
        r.font.name = font; r.font.size = PPt(size); r.font.bold = bold
        r.font.color.rgb = color
    return tb


def _header(slide, num, title, tag=None):
    """Bandeau : badge numéroté + titre + pill (comme le modèle)."""
    b = _round(slide, 0.6, 0.55, 0.62, 0.62, GREEN)
    tf = b.text_frame; tf.word_wrap = False; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = str(num)
    r.font.name = FT_TITLE; r.font.size = PPt(24); r.font.bold = True; r.font.color.rgb = WHITE
    _txt(slide, 1.4, 0.5, 8.6, 0.75, title, 27, INK, font=FT_TITLE, bold=True,
         anchor=MSO_ANCHOR.MIDDLE)
    if tag:
        pill = _round(slide, 10.05, 0.66, 2.68, 0.5, CARD_LT)
        tfp = pill.text_frame; tfp.vertical_anchor = MSO_ANCHOR.MIDDLE
        pp = tfp.paragraphs[0]; pp.alignment = PP_ALIGN.CENTER
        rp = pp.add_run(); rp.text = tag
        rp.font.name = FT_BODY; rp.font.size = PPt(12); rp.font.bold = True; rp.font.color.rgb = GREEN
    # filet vert sous le bandeau
    _round(slide, 0.6, 1.4, 12.13, 0.03, GREEN)


def _bullets(slide, items, top=1.9, x=0.9, w=11.6, gap=1.02, sq=ORANGE):
    for i, it in enumerate(items):
        y = top + i * gap
        _sq(slide, x, y + 0.06, sq)
        if isinstance(it, (tuple, list)):
            _txt(slide, x + 0.4, y - 0.05, w, 0.45, it[0], 18, INK, bold=True)
            _txt(slide, x + 0.4, y + 0.34, w, 0.55, it[1], 14, MUTED)
        else:
            _txt(slide, x + 0.4, y - 0.02, w, 0.7, it, 17, INK)


def _stat_cards(slide, stats, top=4.4):
    """Rangée de cartes chiffres (label + valeur en accent)."""
    n = len(stats); gapx = 0.3
    w = (12.13 - gapx * (n - 1)) / n
    for i, (val, label, color) in enumerate(stats):
        x = 0.6 + i * (w + gapx)
        _round(slide, x, top, w, 1.6, WHITE, line=CARD_LT)
        _txt(slide, x, top + 0.22, w, 0.7, val, 32, color, font=FT_TITLE, bold=True,
             align=PP_ALIGN.CENTER)
        _txt(slide, x, top + 1.02, w, 0.5, label, 12, MUTED, align=PP_ALIGN.CENTER)


def _image_card(slide, img, l, t, w, h):
    if img and Path(img).exists():
        _round(slide, l - 0.12, t - 0.12, w + 0.24, h + 0.24, WHITE, line=CARD_LT)
        slide.shapes.add_picture(str(img), IN(l), IN(t), height=IN(h))


def _new(prs, layout):
    s = prs.slides.add_slide(layout); _bg(s); return s


def build_pptx():
    # Deck vierge : le système de design ci-dessus applique explicitement la
    # palette et les polices du modèle fourni (Urban Data Explorer), donc le
    # rendu reprend le même style sans dépendre du fichier source (évite aussi
    # les parties orphelines d'un template dont on retirerait les slides).
    prs = Presentation()
    layout = prs.slide_layouts[6]
    prs.slide_width = IN(13.333); prs.slide_height = IN(7.5)

    # --- Slide 1 : titre ---
    s = _new(prs, layout)
    _round(s, 0.9, 2.15, 0.18, 1.9, GREEN)  # barre d'accent verticale
    _txt(s, 1.3, 2.05, 11, 1.3, "AISCA-Cinema", 52, INK, font=FT_TITLE, bold=True)
    _txt(s, 1.32, 3.35, 11.4, 0.8,
         "Agent de recommandation cinématographique (RAG)", 24, GREEN, font=FT_TITLE)
    pill = _round(s, 1.32, 4.5, 4.6, 0.55, CARD_LT)
    tfp = pill.text_frame; tfp.vertical_anchor = MSO_ANCHOR.MIDDLE
    pp = tfp.paragraphs[0]; pp.alignment = PP_ALIGN.CENTER
    rp = pp.add_run(); rp.text = "Projet 3 · IA Générative · Bloc 2"
    rp.font.name = FT_BODY; rp.font.size = PPt(13); rp.font.bold = True; rp.font.color.rgb = GREEN
    _txt(s, 1.32, 5.5, 11, 0.5, AUTHORS, 20, INK, bold=True)
    _txt(s, 1.32, 6.0, 11, 0.5, "RNCP40875 — Expert en Ingénierie des données (C5.1 → C5.3)",
         14, MUTED)

    # --- Slide 2 : besoin métier ---
    s = _new(prs, layout)
    _header(s, 2, "Besoin métier", "🎯 C5.1")
    _bullets(s, [
        ("Trop de films, choix coûteux", "Les filtres par mots-clés ne comprennent pas une envie en langage naturel."),
        ("Cible", "Un spectateur qui décrit une envie… mais pas un titre précis."),
        ("Valeur", "Recommander ET expliquer, à partir d'un référentiel maîtrisé."),
        ("Pourquoi la GenAI", "Compréhension sémantique + restitution personnalisée, hors de portée d'un simple filtre."),
    ])

    # --- Slide 3 : architecture RAG ---
    s = _new(prs, layout)
    _header(s, 3, "Architecture RAG", "🧭 Vue d'ensemble")
    steps = ["Questionnaire", "SBERT", "Scoring", "Gemini"]
    x = 0.9; cw = 2.5; gap = 0.55
    for i, st in enumerate(steps):
        cx = x + i * (cw + gap)
        c = _round(s, cx, 1.95, cw, 0.95, GREEN if i in (1, 3) else CARD_LT)
        tf = c.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        pp = tf.paragraphs[0]; pp.alignment = PP_ALIGN.CENTER
        r = pp.add_run(); r.text = st; r.font.name = FT_BODY; r.font.size = PPt(15)
        r.font.bold = True; r.font.color.rgb = WHITE if i in (1, 3) else INK
        if i < len(steps) - 1:
            _txt(s, cx + cw, 1.95, gap, 0.95, "→", 22, GREEN, bold=True,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    _txt(s, 0.9, 3.05, 11.6, 0.4, "Retrieval (récupération sémantique)  →  Generation (synthèse ancrée)",
         13, MUTED)
    _image_card(s, SHOTS / "01_questionnaire.png", 4.55, 3.7, 4.2, 3.3)
    _txt(s, 0.9, 3.7, 3.4, 3.2,
         "• Embeddings SBERT multilingue + cosinus (260 films)\n\n"
         "• Score 0.50 sém. + 0.40 genre + 0.10 mood\n\n"
         "• Génération Gemini ancrée sur les sources\n\n"
         "• Interface Streamlit accessible", 14, INK)

    # --- Slide 4 : choix techniques ---
    s = _new(prs, layout)
    _header(s, 4, "Choix techniques", "⚙️ C5.2")
    _bullets(s, [
        ("RAG", "Corpus évolutif sans réentraînement, génération traçable, coût maîtrisé."),
        ("vs Fine-tuning / Prompting seul", "Écartés : coût & opacité / risque d'hallucination sans ancrage."),
        (f"Embeddings vs mots-clés : SBERT +{NUM['tfidf_gain']} %",
         "Baseline TF-IDF s'effondre (requêtes FR / films EN) : seul le multilingue fait le pont."),
        ("Coûts maîtrisés", "Cache + retry/backoff + 2 appels API par session."),
    ])

    # --- Slide 5 : démo Top 3 ---
    s = _new(prs, layout)
    _header(s, 5, "Démo — Top 3 recommandations", "▶️ Live")
    _image_card(s, SHOTS / "02_top3.png", 3.4, 1.75, 6.5, 5.1)
    _txt(s, 0.9, 6.75, 11.6, 0.5,
         "Sortie réelle : Top 3 + décomposition du score (sémantique / genre / mood).",
         13, MUTED, align=PP_ALIGN.CENTER)

    # --- Slide 6 : visualisations ---
    s = _new(prs, layout)
    _header(s, 6, "Démo — Visualisations", "📊 UX")
    _image_card(s, SHOTS / "03_visualisations.png", 3.4, 1.75, 6.5, 5.1)
    _txt(s, 0.9, 6.75, 11.6, 0.5,
         "Profils par genre et ambiance ; score pondéré 50/40/10 par film.",
         13, MUTED, align=PP_ALIGN.CENTER)

    # --- Slide 7 : évaluation (chiffres) ---
    s = _new(prs, layout)
    _header(s, 7, "Évaluation — avant / après", "📈 C5.3")
    _image_card(s, FIGS / "rag_comparison.png", 0.7, 1.75, 6.6, 3.9)
    _txt(s, 7.6, 1.9, 5.2, 2.6,
         "• 15 requêtes annotées (vérité terrain)\n\n"
         "• Barre orange (genre buggé) ≈ sémantique : preuve du bug\n\n"
         "• Poids 50/40/10 validés par grid-search\n\n"
         "• LLM-as-judge + comparaison de température", 14, INK)
    _stat_cards(s, [
        (f"{NUM['ndcg_sem']}→{NUM['ndcg_cal']}", "nDCG@5", GREEN),
        (f"{NUM['gain_ndcg']} %", "gain nDCG", ORANGE),
        (f"{NUM['mrr_sem']}→{NUM['mrr_cal']}", "MRR", GREEN),
        (f"+{NUM['tfidf_gain'].lstrip('+')} %", "vs TF-IDF", ORANGE),
    ], top=5.75)

    # --- Slide 8 : robustesse / sécurité / limites ---
    s = _new(prs, layout)
    _header(s, 8, "Robustesse · Sécurité · Limites", "🛡️ Prod")
    _bullets(s, [
        ("Résilience", "Retry/backoff sur quota 429 + mode dégradé sans clé."),
        ("Gouvernance", "safety_settings + garde-fou anti-prompt-injection."),
        ("Observabilité", "Suivi tokens / coût estimé / latence par appel."),
        ("Limites assumées", "Corpus 260 films EN, hallucination résiduelle, quotas free tier."),
    ])

    # --- Slide 9 : industrialisation + conclusion ---
    s = _new(prs, layout)
    _header(s, 9, "Industrialisation & conclusion", "🚀 Bilan")
    _bullets(s, [
        ("Industrialisation", "FAISS + embeddings persistés, Docker + CI, monitoring coûts, A/B testing."),
        ("C5.1", "Cas d'usage justifié et gouverné."),
        ("C5.2", "Solution RAG fonctionnelle, accessible, résiliente."),
        (f"C5.3", f"Évaluation chiffrée avec optimisation prouvée ({NUM['gain_ndcg']} % nDCG)."),
    ], top=1.85, gap=0.92)
    _txt(s, 0.9, 6.6, 11.6, 0.5, "Merci — questions ?", 20, GREEN, font=FT_TITLE,
         bold=True, align=PP_ALIGN.CENTER)

    prs.save(OUT / "presentation_projet3.pptx")
    print("OK presentation_projet3.pptx")


if __name__ == "__main__":
    _load_numbers()
    build_rapport()
    build_plan()
    build_antiseche()
    build_dossier()
    build_pptx()
    print("\nLivrables dans", OUT)
