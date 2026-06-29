"""
Génère les livrables rédigés au format Office (NON commités dans le dépôt) :
  livrables/rapport_projet3.docx
  livrables/plan_soutenance_projet3.docx
  livrables/antiseche_projet3.docx
  livrables/dossier_audit_projet3.docx
  livrables/presentation_projet3.pptx

Captures réelles : screenshots/*.png ; figure d'éval : evaluation/figures/*.png
Usage : python scripts/generate_deliverables.py
"""

from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pptx import Presentation
from pptx.util import Inches as PInches, Pt as PPt
from pptx.dml.color import RGBColor as PRGB
from pptx.enum.text import PP_ALIGN

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "livrables"
OUT.mkdir(exist_ok=True)
SHOTS = ROOT / "screenshots"
FIGS = ROOT / "evaluation" / "figures"

AUTHORS = "BOUCHER Anthony & DEROUICHE Youcef"
ACCENT = RGBColor(0x0E, 0xA5, 0xE9)
PACCENT = PRGB(0x0E, 0xA5, 0xE9)
DARK = PRGB(0x0F, 0x34, 0x60)


# ---------------------------------------------------------------- DOCX helpers
def h1(doc, text):
    p = doc.add_heading(text, level=1)
    return p


def h2(doc, text):
    return doc.add_heading(text, level=2)


def para(doc, text, bold=False, italic=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.italic = italic
    return p


def bullet(doc, text):
    doc.add_paragraph(text, style="List Bullet")


def numbered(doc, text):
    doc.add_paragraph(text, style="List Number")


def table(doc, headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    for i, htxt in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(htxt)
        run.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    return t


def title_block(doc, title, subtitle):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title)
    r.bold = True
    r.font.size = Pt(24)
    r.font.color.rgb = ACCENT
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run(subtitle)
    r2.font.size = Pt(12)
    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = p3.add_run(AUTHORS + "  —  RNCP40875, Bloc 2 (C5.1 → C5.3)")
    r3.italic = True
    doc.add_paragraph()


# ======================================================= 1. RAPPORT
def build_rapport():
    doc = Document()
    title_block(doc, "Rapport — Projet 3 : IA Générative",
                "AISCA-Cinema : agent de recommandation cinématographique (RAG)")

    h1(doc, "1. Besoin métier (C5.1)")
    para(doc, "Face au volume de films disponibles, choisir quoi regarder est "
              "coûteux. Les moteurs par mots-clés ne comprennent pas une envie "
              "exprimée en langage naturel et n'expliquent pas leurs suggestions. "
              "AISCA-Cinema répond au besoin de découverte personnalisée : "
              "l'utilisateur décrit son envie avec ses mots, et l'agent recommande "
              "des films pertinents ET justifie son choix, à partir d'un référentiel "
              "maîtrisé (pas d'invention).")
    para(doc, "Pourquoi la GenAI ici : la valeur tient à la compréhension "
              "sémantique de la demande (SBERT) et à une restitution personnalisée "
              "en langage naturel (LLM), hors de portée d'un simple filtre par genres.")

    h1(doc, "2. Choix techniques")
    para(doc, "L'approche retenue est un RAG (Retrieval-Augmented Generation) : "
              "récupération sémantique de films pertinents puis génération de "
              "synthèses ancrées sur ces films.")
    table(doc, ["Décision", "Choix", "Justification"], [
        ["Paradigme", "RAG", "corpus évolutif sans réentraînement ; génération traçable ; coût maîtrisé"],
        ["vs Fine-tuning", "écarté", "coût/temps d'entraînement, données insuffisantes, perte de traçabilité"],
        ["vs Prompting seul", "écarté", "risque d'hallucination sans ancrage corpus"],
        ["Embeddings", "SBERT multilingue MiniLM-L12-v2", "requête FR / corpus EN, léger et rapide en CPU"],
        ["Similarité", "Cosinus", "standard pour embeddings denses"],
        ["Génération", "Google Gemini (gemini-2.0-flash)", "qualité FR, free tier, latence faible"],
        ["Coûts API", "cache + 2 appels/session max", "respect du free tier, reproductibilité"],
    ])

    h1(doc, "3. Réalisation")
    para(doc, "Code modulaire (pas de notebook monolithique) :")
    bullet(doc, "questionnaire.py : acquisition et structuration des préférences.")
    bullet(doc, "nlp_engine.py : retrieval SBERT (embeddings + cosinus) + cache des embeddings du référentiel.")
    bullet(doc, "scoring.py : ranking pondéré 0.50 sémantique + 0.30 genre + 0.20 mood.")
    bullet(doc, "genai_integration.py : génération Gemini, GenerationConfig ajustable, garde-fou anti-hallucination, cache.")
    bullet(doc, "app.py : UI Streamlit accessible, traçabilité des sources, mode dégradé sans clé API.")
    h2(doc, "Correctifs majeurs apportés lors de la finalisation")
    numbered(doc, "Sécurité : retrait d'une clé API réelle commitée dans .env.example (à révoquer côté Google).")
    numbered(doc, "Bug fonctionnel (C5.2) : le composant genre (30 % du score) était neutralisé "
                  "(libellés FR comparés à la colonne Genre anglaise). Corrigé via la colonne "
                  "Categorie (FR) + matching insensible aux accents.")
    numbered(doc, "Évaluation (C5.3) : création d'un cadre d'évaluation complet (inexistant).")
    numbered(doc, "Paramétrage (C5.3) : generate_content était appelé sans configuration ; "
                  "les paramètres sont désormais explicites et ajustables.")
    numbered(doc, "Conteneurisation (Dockerfile) et mode dégradé (résilience sans clé API).")

    h1(doc, "4. Preuve (mesures réelles)")
    h2(doc, "4.1 Qualité du RAG — comparaison avant / après")
    para(doc, "Jeu de cas : 15 requêtes annotées (vérité terrain). Pool de 20 candidats "
              "récupérés par SBERT, reclassés selon 3 configurations. Métriques @5 :")
    table(doc, ["Configuration", "Precision@5", "Recall@5", "MRR", "nDCG@5"], [
        ["A. Sémantique seule (baseline)", "0.267", "0.297", "0.593", "0.333"],
        ["B. Pondéré — genre buggé (colonne EN)", "0.293", "0.331", "0.575", "0.347"],
        ["C. Pondéré — corrigé (Categorie FR)", "0.387", "0.408", "0.783", "0.489"],
    ])
    para(doc, "Lecture : le correctif (A → C) améliore le nDCG@5 de +46,8 % et le MRR "
              "de 0.59 à 0.78. La config B (genre buggé) reste collée au sémantique seul "
              "— preuve chiffrée que le composant genre était inopérant avant correctif.")
    if (FIGS / "rag_comparison.png").exists():
        doc.add_picture(str(FIGS / "rag_comparison.png"), width=Inches(5.8))
    para(doc, "Commande : python -m evaluation.evaluate_rag", italic=True)
    h2(doc, "4.2 Qualité de la génération — grille + paramètres")
    para(doc, "Une grille d'évaluation (pertinence, exactitude, complétude, absence "
              "d'hallucination, traçabilité, ton ; barème 1-5, seuil pro ≥ 4.0) est "
              "appliquée sur le jeu de cas. Le script compare_params.py génère le profil "
              "sous deux réglages (Factuelle temp=0.2 / Créative temp=0.9) et mesure des "
              "indicateurs objectifs (longueur, diversité lexicale, titres hors-corpus = "
              "proxy d'hallucination) pour justifier le réglage retenu.")
    h2(doc, "4.3 Tests")
    para(doc, "10 tests unitaires (pytest) verrouillent le correctif de scoring, dont un "
              "test prouvant que la préférence de genre modifie réellement le classement.")

    h1(doc, "5. Résultat")
    para(doc, "Une application fonctionnelle et accessible, un RAG réellement personnalisé "
              "(correctif prouvé), une génération ancrée et traçable, et une évaluation "
              "chiffrée avec comparaison avant/après — couvrant C5.1, C5.2 et C5.3.")

    h1(doc, "6. Limites, biais et risques")
    bullet(doc, "Corpus : 260 films classiques (IMDb), descriptions EN → biais culturel / couverture limitée.")
    bullet(doc, "Hallucination : atténuée (prompts + sources) mais résiduelle sur les pistes hors top 3.")
    bullet(doc, "Dépendance API : quotas/indisponibilité Gemini → mode dégradé prévu.")
    bullet(doc, "RGPD : stockage local des réponses libres à encadrer (consentement, rétention).")
    bullet(doc, "Évaluation : vérité terrain construite par les auteurs (subjectivité) ; à élargir.")

    h1(doc, "7. Industrialisation")
    bullet(doc, "Index vectoriel (FAISS / base vectorielle) + embeddings persistés.")
    bullet(doc, "Docker (déjà présent) + CI exécutant tests ET évaluation (garde-fou de non-régression).")
    bullet(doc, "Monitoring coûts/latence API, supervision du taux d'hallucination, A/B testing des paramètres.")

    h1(doc, "8. Compétences démontrées (mapping RNCP)")
    table(doc, ["Compétence", "Réalisation", "Preuve"], [
        ["C5.1 Cas d'usage", "Besoin métier formalisé, justification RAG, gouvernance", "§1, §6 ; .env.example ; audit"],
        ["C5.2 Solution", "RAG fonctionnel, accessible, traçable ; correctif scoring", "app ; §3 ; tests ; sources UI"],
        ["C5.3 Évaluation", "Jeu de cas + métriques + grille + comparaison avant/après", "evaluation/ ; +46,8 % nDCG"],
    ])

    h1(doc, "9. Ma contribution individuelle (à compléter par chaque membre)")
    para(doc, "À personnaliser pour la défense individualisée :", italic=True)
    bullet(doc, "[Prénom] : (ex.) moteur de retrieval SBERT et système de scoring ; "
                "identification et correction du bug genre/mood ; tests unitaires. "
                "Choix défendus : SBERT multilingue, pondération 50/30/20, colonne Categorie.")
    bullet(doc, "[Prénom] : (ex.) intégration Gemini (prompts, GenerationConfig, cache), "
                "cadre d'évaluation (jeu de cas, métriques, grille), UI Streamlit et "
                "traçabilité. Choix défendus : RAG vs fine-tuning, paramètres de génération.")

    doc.save(OUT / "rapport_projet3.docx")
    print("OK rapport_projet3.docx")


# ======================================================= 2. PLAN DE SOUTENANCE
def build_plan():
    doc = Document()
    title_block(doc, "Plan de soutenance — Projet 3 (IA Générative)",
                "Déroulé slide par slide · script oral · répartition binôme · timing (~10 min)")
    para(doc, "Format global : 3 projets en 30 min au total (~10 min/projet) puis 20 min "
              "de questions. Ce plan vise ~10 min pour le projet 3 (9 slides).", italic=True)

    slides = [
        ("1. Titre", "Slide titre (AISCA-Cinema, noms, RNCP).", "—",
         "Anthony", "0:30",
         "« Bonjour, nous présentons AISCA-Cinema, notre projet d'IA générative : un "
         "agent de recommandation de films basé sur une architecture RAG. »"),
        ("2. Besoin métier", "Le problème + la cible + la valeur.", "—",
         "Anthony", "1:00",
         "« Choisir un film est devenu difficile. Les filtres par mots-clés ne "
         "comprennent pas une envie formulée en langage naturel et n'expliquent rien. "
         "Notre cible : un spectateur qui sait décrire une envie mais pas un titre. "
         "Valeur : recommander ET justifier. C'est notre cas d'usage C5.1. »"),
        ("3. Architecture RAG", "Schéma du pipeline + capture du questionnaire.",
         "01_questionnaire.png", "Youcef", "1:30",
         "« L'architecture est un RAG : le questionnaire alimente SBERT qui encode la "
         "demande et le catalogue, on récupère les films par similarité cosinus, on les "
         "reclasse par un score pondéré, puis Gemini génère des synthèses ancrées sur "
         "ces films. Retrieval + Generation. »"),
        ("4. Choix techniques", "Tableau RAG vs fine-tuning vs prompting.", "—",
         "Youcef", "1:00",
         "« Pourquoi un RAG ? Le corpus évolue sans réentraînement, la génération reste "
         "traçable, et le coût est maîtrisé par un cache. Le fine-tuning serait coûteux "
         "et moins traçable ; le prompting seul hallucine. C'est notre justification C5.2. »"),
        ("5. Démo — Top 3", "Capture des recommandations réelles + composantes.",
         "02_top3.png", "Anthony", "1:30",
         "« Voici une vraie sortie pour une requête de SF philosophique : le Top 3 avec "
         "le détail du score — sémantique, genre, mood. La recommandation est expliquée "
         "et tracée. »"),
        ("6. Démo — Visualisations", "Radars de préférences + barres de score 50/30/20.",
         "03_visualisations.png", "Youcef", "0:45",
         "« L'interface est accessible à un non-technicien : profils par genre et ambiance, "
         "et décomposition pondérée du score de chaque film. »"),
        ("7. Évaluation (C5.3)", "Figure de comparaison avant/après + chiffres clés.",
         "rag_comparison.png", "Anthony", "1:45",
         "« Le cœur de C5.3 : on a annoté 15 requêtes avec une vérité terrain et mesuré "
         "Precision, Recall, MRR et nDCG. Notre correctif du scoring fait passer le nDCG@5 "
         "de 0.33 à 0.49, soit +47 %, et le MRR de 0.59 à 0.78. La barre orange (genre "
         "buggé) prouve chiffrement que le composant genre était mort avant correction. "
         "On compare aussi les paramètres LLM (température) via une grille d'évaluation. »"),
        ("8. Limites & industrialisation", "Limites/biais/risques + pistes.", "—",
         "Youcef", "1:00",
         "« Limites assumées : corpus de 260 films classiques en anglais, hallucination "
         "résiduelle, dépendance API. Pour industrialiser : index vectoriel FAISS, Docker "
         "(déjà fait) + CI avec l'évaluation comme garde-fou, monitoring et A/B testing. »"),
        ("9. Conclusion", "Récap compétences C5.1/C5.2/C5.3.", "—",
         "Anthony", "0:30",
         "« En résumé : un cas d'usage justifié, une solution RAG fonctionnelle et "
         "accessible, et une évaluation chiffrée avec optimisation prouvée. Merci, nous "
         "sommes à votre disposition pour vos questions. »"),
    ]
    for titre, contenu, img, qui, timing, script in slides:
        h1(doc, titre)
        table(doc, ["Élément", "Détail"], [
            ["À l'écran", contenu],
            ["Image", img],
            ["Qui parle", qui],
            ["Durée", timing],
        ])
        para(doc, "Script oral :", bold=True)
        para(doc, script, italic=True)
        doc.add_paragraph()

    h1(doc, "Récapitulatif timing")
    table(doc, ["Bloc", "Durée cumulée"], [
        ["Slides 1-4 (intro + archi + choix)", "~4:00"],
        ["Slides 5-6 (démo)", "~2:15"],
        ["Slide 7 (évaluation)", "~1:45"],
        ["Slides 8-9 (limites + conclusion)", "~1:30"],
        ["TOTAL", "~9:30 (marge sur 10 min)"],
    ])
    doc.save(OUT / "plan_soutenance_projet3.docx")
    print("OK plan_soutenance_projet3.docx")


# ======================================================= 3. ANTISÈCHE
def build_antiseche():
    doc = Document()
    title_block(doc, "Antisèche — Projet 3 (IA Générative)",
                "Tout comprendre pour tout expliquer au jury")

    h1(doc, "A. Concepts & outils — à quoi ça sert, comment ça marche")

    concepts = [
        ("RAG (Retrieval-Augmented Generation)",
         "Architecture qui combine une RECHERCHE d'information (retrieval) et une "
         "GÉNÉRATION par LLM. On récupère d'abord des documents pertinents (ici des "
         "films) puis on les fournit au LLM comme contexte pour qu'il réponde sans "
         "inventer.",
         "Force : génération ancrée et traçable, corpus modifiable sans réentraînement. "
         "Faiblesse : la qualité dépend du retrieval (si on récupère mal, on génère mal).",
         "Dans le projet : SBERT récupère le Top films, Gemini rédige le profil/plan à "
         "partir de ces films uniquement."),
        ("Embeddings (plongements vectoriels)",
         "Représentation d'un texte sous forme de vecteur de nombres, telle que deux "
         "textes de sens proche ont des vecteurs proches. Permet de comparer le SENS, "
         "pas les mots exacts.",
         "Force : capture la sémantique, multilingue. Faiblesse : boîte noire, sensible "
         "au modèle choisi.",
         "On encode la requête utilisateur et chaque film en vecteurs."),
        ("SBERT (Sentence-BERT, MiniLM-L12-v2 multilingue)",
         "Variante de BERT optimisée pour produire un embedding par PHRASE/paragraphe "
         "(et non par mot), rapide à comparer. La version multilingue gère le français "
         "(requête) et l'anglais (descriptions).",
         "Force : rapide, léger (tourne en CPU), multilingue. Faiblesse : modèle "
         "généraliste, pas spécialisé cinéma.",
         "C'est notre moteur de retrieval (src/nlp_engine.py)."),
        ("Similarité cosinus",
         "Mesure l'angle entre deux vecteurs : 1 = même direction (très similaire), 0 = "
         "orthogonaux (sans rapport). Indépendante de la longueur du texte.",
         "Force : standard, simple, efficace. Faiblesse : ne capte que ce que l'embedding "
         "encode.",
         "Sert à classer les films par proximité avec la requête."),
        ("Score pondéré (ranking)",
         "Combinaison linéaire : 0.50×sémantique + 0.30×genre + 0.20×mood. Permet de "
         "mêler la proximité de sens et les préférences explicites de l'utilisateur.",
         "Force : transparent, ajustable, explicable. Faiblesse : poids fixés à la main "
         "(pas appris).",
         "src/scoring.py. C'est ici qu'était le bug corrigé (genre)."),
        ("LLM & Google Gemini (gemini-2.0-flash)",
         "Large Language Model : modèle génératif entraîné à prédire le texte suivant, "
         "capable de rédiger des synthèses en langage naturel. Gemini est le LLM de "
         "Google ; la variante flash est rapide et économique.",
         "Force : qualité rédactionnelle, multilingue. Faiblesse : peut halluciner, "
         "dépend d'une API externe (coût, quota).",
         "Génère le profil cinéphile et le plan de découverte (src/genai_integration.py)."),
        ("Paramètres de génération : température, top-p, top-k",
         "Température : contrôle l'aléa (0 = déterministe/factuel, 1 = créatif/varié). "
         "Top-p (nucleus) : on échantillonne dans les tokens dont la proba cumulée "
         "atteint p. Top-k : on se limite aux k tokens les plus probables. "
         "max_output_tokens : longueur max.",
         "Force : permet d'arbitrer fiabilité vs richesse. Faiblesse : température élevée "
         "= plus d'hallucinations.",
         "Exposés via GenerationConfig ; comparés (0.2 vs 0.9) dans compare_params.py."),
        ("Cache (CacheManager)",
         "Mémorise les réponses déjà générées (clé = hash du prompt + paramètres) pour "
         "éviter de rappeler l'API. Persistant sur disque.",
         "Force : réduit coûts et latence, reproductibilité. Faiblesse : peut servir une "
         "réponse périmée si le prompt ne change pas.",
         "La clé de cache intègre les paramètres pour ne pas mélanger les réglages."),
        ("Métriques d'évaluation (Precision@k, Recall@k, MRR, nDCG)",
         "Precision@k : part de pertinents dans les k premiers. Recall@k : part des "
         "pertinents retrouvés. MRR : 1/rang du premier bon résultat (qualité du tout "
         "premier). nDCG@k : qualité du classement, pénalise un pertinent mal placé.",
         "Force : standards, objectifs. Faiblesse : dépendent d'une vérité terrain "
         "(annotation subjective).",
         "evaluation/metrics.py ; calculées sur 15 requêtes annotées."),
        ("Streamlit",
         "Framework Python pour créer des applications web de data science sans HTML/JS. "
         "Chaque interaction relance le script de haut en bas (modèle 'rerun').",
         "Force : prototypage très rapide, accessible. Faiblesse : peu adapté aux très "
         "fortes charges (réexécution à chaque interaction).",
         "C'est notre interface (app.py)."),
        ("Conteneurisation (Docker)",
         "Empaquette l'app + ses dépendances dans une image reproductible, lançable "
         "partout de façon identique.",
         "Force : reproductibilité, déploiement. Faiblesse : image volumineuse (torch).",
         "Dockerfile fourni (torch CPU, modèle SBERT pré-téléchargé)."),
    ]
    for nom, quoi, ff, projet in concepts:
        h2(doc, nom)
        para(doc, "Ce que c'est / comment ça marche : ", bold=True)
        para(doc, quoi)
        para(doc, "Forces / faiblesses : ", bold=True)
        para(doc, ff)
        para(doc, "Dans notre projet : ", bold=True)
        para(doc, projet)

    h1(doc, "B. Questions probables du jury — réponses préparées")
    qa = [
        ("Pourquoi un RAG plutôt qu'un fine-tuning ?",
         "Notre corpus de films évolue ; le RAG l'intègre sans réentraîner un modèle. "
         "Il garde la traçabilité (on sait quels films ont servi) et coûte moins cher. "
         "Le fine-tuning aurait demandé un gros jeu d'entraînement et serait opaque."),
        ("Comment évaluez-vous la qualité ? (LA question C5.3)",
         "Deux niveaux. Retrieval : 15 requêtes annotées + Precision/Recall/MRR/nDCG. "
         "Génération : grille (pertinence, exactitude, hallucination, ton) + comparaison "
         "de paramètres. On a une preuve chiffrée : +47 % de nDCG après notre correctif."),
        ("Comment gérez-vous les hallucinations ?",
         "Trois leviers : ancrage RAG (le LLM ne voit que des films réels), consignes "
         "anti-invention dans les prompts, et un indicateur qui compte les titres cités "
         "hors corpus. On peut aussi baisser la température."),
        ("Quelle est la limite principale ?",
         "Le corpus : 260 films classiques en anglais. Couverture limitée des sorties "
         "récentes/de niche, et biais culturel. C'est notre première piste d'amélioration."),
        ("Comment industrialiser ?",
         "Index vectoriel (FAISS) au lieu de recalculer les embeddings, Docker (déjà "
         "fait) + CI lançant tests et évaluation comme garde-fou de non-régression, "
         "monitoring des coûts/latence et du taux d'hallucination, A/B testing des params."),
        ("Pourquoi ces poids 50/30/20 ?",
         "La description libre (sémantique) porte le plus d'information, d'où 50 %. Les "
         "préférences explicites de genre comptent plus que l'ambiance, d'où 30/20. Ces "
         "poids sont ajustables et pourraient être appris sur des retours utilisateurs."),
        ("Qu'avez-vous corrigé exactement ?",
         "Un bug : le score de genre comparait des libellés français à une colonne "
         "anglaise, donc 30 % du score étaient constants (morts). On utilise désormais "
         "la colonne Categorie française avec un matching insensible aux accents, "
         "verrouillé par des tests. Impact mesuré : +47 % de nDCG."),
        ("Données personnelles / RGPD ?",
         "Les réponses libres sont stockées localement et exclues du dépôt (gitignore). "
         "En production il faudrait consentement explicite, durée de conservation et "
         "anonymisation."),
        ("Sécurité ?",
         "Une vraie clé API traînait dans .env.example : retirée et à révoquer. Les "
         "secrets passent par .env (gitignoré) ou les secrets Streamlit. .env.example "
         "ne contient qu'un placeholder."),
    ]
    for q, a in qa:
        para(doc, "Q : " + q, bold=True)
        para(doc, "R : " + a)

    h1(doc, "C. Mémo transposable aux autres projets")
    bullet(doc, "Toujours relier une réalisation à une compétence : « ceci démontre Cx.y car… ».")
    bullet(doc, "Suivre la logique besoin → choix → réalisation → preuve → résultat → limites.")
    bullet(doc, "Apporter des PREUVES chiffrées (métriques, avant/après), pas des descriptions.")
    bullet(doc, "Assumer les limites et proposer des améliorations : le jury valorise le recul.")
    bullet(doc, "Sécurité, repro (deps figées, .env.example, Docker), tests : toujours mentionnés.")
    bullet(doc, "Savoir expliquer CHAQUE brique technique simplement (cf. section A).")

    doc.save(OUT / "antiseche_projet3.docx")
    print("OK antiseche_projet3.docx")


# ======================================================= 4. DOSSIER AUDIT
def build_dossier():
    doc = Document()
    title_block(doc, "Dossier d'audit & finalisation — Projet 3",
                "Audit · Analyse d'écart RNCP · Récapitulatif final")

    h1(doc, "Partie 1 — Audit de l'existant")
    para(doc, "Base technique saine (RAG réel, code modulaire, cache LLM) mais plusieurs "
              "problèmes identifiés et prouvés par exécution :")
    h2(doc, "Défauts fonctionnels")
    bullet(doc, "BUG MAJEUR : composant genre (30 % du score) neutralisé — comparaison de "
                "libellés FR à la colonne Genre anglaise ; preuve : score genre constant à 0.5.")
    bullet(doc, "Mood matché seulement par hasard (divergences d'accents questionnaire/CSV).")
    bullet(doc, "Modèle Gemini incohérent (3 valeurs différentes selon les fichiers).")
    bullet(doc, "Ré-encodage du référentiel à chaque requête (pas de cache d'embeddings).")
    h2(doc, "Manques (C5.3)")
    bullet(doc, "Aucune évaluation : pas de grille, pas de jeu de cas, pas de métriques, "
                "pas de comparaison avant/après.")
    bullet(doc, "Génération sans paramétrage explicite (température, top-p…).")
    h2(doc, "Sécurité")
    bullet(doc, "Clé API Google réelle commitée dans .env.example (présente dans tout "
                "l'historique git) — à révoquer.")

    h1(doc, "Partie 2 — Analyse d'écart vs grille RNCP")
    para(doc, "Échelle : Non démontré (0) / Débutant (2) / Intermédiaire (3) / Professionnel (5).")
    table(doc, ["Compétence", "Avant", "Manque principal", "Action corrective"], [
        ["C5.1 Cas d'usage", "3", "besoin métier non formalisé, gouvernance", "rapport §1/§6, retrait clé API"],
        ["C5.2 Solution", "3", "bug genre bloquant, traçabilité, perf", "fix scoring, sources UI, cache embeddings"],
        ["C5.3 Évaluation", "0", "aucune évaluation", "cadre evaluation/ complet + comparaison"],
    ])

    h1(doc, "Partie 3 — Récapitulatif final")
    table(doc, ["Compétence", "Avant", "Après", "Preuve"], [
        ["C5.1", "3/5", "5/5", "rapport (besoin, gouvernance) ; .env.example assaini"],
        ["C5.2", "3/5", "5/5", "RAG fonctionnel, UI + traçabilité, fix scoring (10 tests)"],
        ["C5.3", "0/5", "5/5", "evaluation/ : +46,8 % nDCG@5, MRR 0.59→0.78, grille + params"],
    ])
    h2(doc, "Actions réalisées")
    for a in ["Clé API retirée de .env.example",
              "Scoring genre/mood corrigé (Categorie FR + accents) + 10 tests",
              "Cadre d'évaluation (jeu de cas + métriques + comparaison avant/après)",
              "GenerationConfig ajustable (température/top-p)",
              "Traçabilité des sources + garde-fou anti-hallucination",
              "Cache des embeddings du référentiel",
              "Dockerfile + mode dégradé sans clé API",
              "Livrables : rapport, slides, plan, antisèche, dossier"]:
        bullet(doc, "Fait — " + a)
    h2(doc, "Limites restantes assumées")
    bullet(doc, "Corpus limité (260 films EN) ; vérité terrain construite par les auteurs.")
    bullet(doc, "Hallucination résiduelle hors top 3 ; comparaison LLM nécessite une clé API.")
    bullet(doc, "Pas encore d'index vectoriel persistant ni de CI.")

    doc.save(OUT / "dossier_audit_projet3.docx")
    print("OK dossier_audit_projet3.docx")


# ======================================================= 5. PRÉSENTATION PPTX
def _slide_title(prs, title, subtitle):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    # bandeau
    box = s.shapes.add_textbox(PInches(0.7), PInches(2.0), PInches(12), PInches(1.6))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = title
    r.font.size = PPt(40); r.font.bold = True; r.font.color.rgb = PACCENT
    p2 = tf.add_paragraph()
    r2 = p2.add_run(); r2.text = subtitle
    r2.font.size = PPt(20); r2.font.color.rgb = PRGB(0x33, 0x41, 0x55)
    box2 = s.shapes.add_textbox(PInches(0.7), PInches(5.2), PInches(12), PInches(1.2))
    tf2 = box2.text_frame
    r3 = tf2.paragraphs[0].add_run(); r3.text = AUTHORS
    r3.font.size = PPt(22); r3.font.bold = True
    p4 = tf2.add_paragraph()
    r4 = p4.add_run(); r4.text = "Projet 3 — IA Générative · RNCP40875, Bloc 2 (C5.1 → C5.3)"
    r4.font.size = PPt(16); r4.font.color.rgb = PRGB(0x33, 0x41, 0x55)
    return s


def _slide_bullets(prs, title, bullets, note=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    tb = s.shapes.add_textbox(PInches(0.6), PInches(0.4), PInches(12.1), PInches(0.9))
    r = tb.text_frame.paragraphs[0].add_run(); r.text = title
    r.font.size = PPt(30); r.font.bold = True; r.font.color.rgb = PACCENT
    body = s.shapes.add_textbox(PInches(0.8), PInches(1.5), PInches(11.7), PInches(5.4))
    tf = body.text_frame; tf.word_wrap = True
    for i, b in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = p.add_run(); run.text = "•  " + b
        run.font.size = PPt(20)
        p.space_after = PPt(10)
    if note:
        np_ = tf.add_paragraph()
        rr = np_.add_run(); rr.text = note
        rr.font.size = PPt(16); rr.font.italic = True; rr.font.color.rgb = PACCENT
    return s


def _slide_image(prs, title, img, caption=None, bullets=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    tb = s.shapes.add_textbox(PInches(0.6), PInches(0.3), PInches(12.1), PInches(0.8))
    r = tb.text_frame.paragraphs[0].add_run(); r.text = title
    r.font.size = PPt(28); r.font.bold = True; r.font.color.rgb = PACCENT
    if img and Path(img).exists():
        # image à gauche si bullets, sinon centrée
        if bullets:
            s.shapes.add_picture(str(img), PInches(0.5), PInches(1.3), height=PInches(5.4))
            body = s.shapes.add_textbox(PInches(8.0), PInches(1.5), PInches(5.0), PInches(5.0))
            tf = body.text_frame; tf.word_wrap = True
            for i, b in enumerate(bullets):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                run = p.add_run(); run.text = "•  " + b
                run.font.size = PPt(16); p.space_after = PPt(8)
        else:
            s.shapes.add_picture(str(img), PInches(2.2), PInches(1.3), height=PInches(5.2))
    if caption:
        cap = s.shapes.add_textbox(PInches(0.6), PInches(6.8), PInches(12), PInches(0.5))
        rr = cap.text_frame.paragraphs[0].add_run(); rr.text = caption
        rr.font.size = PPt(14); rr.font.italic = True
    return s


def build_pptx():
    prs = Presentation()
    prs.slide_width = PInches(13.333)
    prs.slide_height = PInches(7.5)

    _slide_title(prs, "AISCA-Cinema",
                 "Agent de recommandation cinématographique (RAG)")

    _slide_bullets(prs, "1. Besoin métier (C5.1)", [
        "Trop de films : choisir est coûteux et frustrant.",
        "Les filtres par mots-clés ne comprennent pas une envie en langage naturel.",
        "Cible : un spectateur qui décrit une envie, pas un titre.",
        "Valeur : recommander ET expliquer, à partir d'un référentiel maîtrisé.",
    ], note="Cas d'usage cohérent avec le besoin métier → C5.1")

    _slide_image(prs, "2. Architecture RAG", SHOTS / "01_questionnaire.png",
                 caption="Questionnaire → SBERT (retrieval) → scoring → Gemini (génération ancrée).",
                 bullets=[
                     "Retrieval : SBERT multilingue + cosinus (260 films).",
                     "Ranking : 0.50 sémantique + 0.30 genre + 0.20 mood.",
                     "Generation : Gemini, ancrée sur les films récupérés.",
                     "Interface Streamlit accessible.",
                 ])

    _slide_bullets(prs, "3. Choix techniques — pourquoi un RAG ?", [
        "Corpus évolutif sans réentraînement.",
        "Génération traçable (sources = films récupérés).",
        "Coût maîtrisé : cache + 2 appels API/session.",
        "Fine-tuning écarté (coût, opacité) ; prompting seul écarté (hallucination).",
    ], note="Solution pertinente et adaptée au contexte → C5.2")

    _slide_image(prs, "4. Démo — Top 3 recommandations", SHOTS / "02_top3.png",
                 caption="Sortie réelle : Top 3 + décomposition du score (sémantique / genre / mood).")

    _slide_image(prs, "5. Démo — Visualisations", SHOTS / "03_visualisations.png",
                 caption="Profils par genre et ambiance ; score pondéré 50/30/20 par film.")

    _slide_image(prs, "6. Évaluation (C5.3) — avant / après", FIGS / "rag_comparison.png",
                 caption="15 requêtes annotées. Correctif : nDCG@5 0.33→0.49 (+47 %), MRR 0.59→0.78.",
                 bullets=[
                     "Métriques : Precision@k, Recall@k, MRR, nDCG.",
                     "Barre orange (genre buggé) ≈ sémantique : preuve du bug.",
                     "Grille qualité + comparaison de la température (0.2 vs 0.9).",
                     "Garde-fou anti-hallucination mesuré.",
                 ])

    _slide_bullets(prs, "7. Limites · Biais · Risques", [
        "Corpus : 260 films classiques en anglais → couverture limitée.",
        "Hallucination résiduelle sur les pistes hors top 3.",
        "Dépendance API (quota) → mode dégradé prévu.",
        "RGPD : réponses libres stockées localement à encadrer.",
    ])

    _slide_bullets(prs, "8. Industrialisation", [
        "Index vectoriel (FAISS) + embeddings persistés.",
        "Docker (fait) + CI exécutant tests ET évaluation (non-régression).",
        "Monitoring coûts/latence + taux d'hallucination.",
        "A/B testing des paramètres de génération.",
    ])

    _slide_bullets(prs, "9. Conclusion — compétences démontrées", [
        "C5.1 : cas d'usage justifié et gouverné.",
        "C5.2 : solution RAG fonctionnelle, accessible, traçable.",
        "C5.3 : évaluation chiffrée avec optimisation prouvée (+47 % nDCG).",
        "Merci — questions ?",
    ])

    prs.save(OUT / "presentation_projet3.pptx")
    print("OK presentation_projet3.pptx")


if __name__ == "__main__":
    build_rapport()
    build_plan()
    build_antiseche()
    build_dossier()
    build_pptx()
    print("\nTous les livrables sont dans", OUT)
