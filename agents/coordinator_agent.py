# =============================================================
# coordinator_agent.py — HAJAR (version LangGraph + ReAct)
# Conforme au cours : create_agent + @tool + InMemorySaver
# =============================================================

import os
import json
import glob
import shutil
import logging
from datetime import datetime
from dotenv import load_dotenv
from markdown_pdf import MarkdownPdf, Section
load_dotenv()

# ── LangGraph / LangChain (cours de la prof) ──────────────────
from langchain.agents import create_agent          # crée l'agent ReAct
from langchain_openai import ChatOpenAI            # le LLM coordinateur
from langchain.tools import tool                   # décorateur @tool
from langgraph.checkpoint.memory import InMemorySaver  # mémoire volatile
from langchain_core.messages import HumanMessage   # message utilisateur

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HAJAR] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("hajar")


# =============================================================
# ÉTAPE 1 — Définir les OUTILS (@tool)
# Le LLM lit la docstring pour décider QUEL outil appeler et QUAND
# =============================================================

@tool
def outil_scout(demo_mode: str = "true") -> str:
    """
    Lance l'Agent Scout FERDAOUS pour collecter les dernières
    tendances IA depuis GitHub, arXiv, RSS et Hacker News.
    Utilise demo_mode='true' pour des données simulées (test),
    demo_mode='false' pour les vraies APIs (production).
    Retourne le chemin du fichier JSON produit.
    """
    # --- La docstring ci-dessus est lue par le LLM ---
    # --- pour décider quand appeler cet outil       ---

    log.info("@tool outil_scout appelé (demo=%s)", demo_mode)
    is_demo = demo_mode.lower() == "true"

    try:
        from agents.scout_agent import FerdaousAgent, generate_demo_dataset

        if is_demo:
            filepath = generate_demo_dataset()
        else:
            agent = FerdaousAgent()
            filepath = agent.run()

        # Copier vers data/external_data/ (chemin lu par WAFAE)
        os.makedirs("data/external_data", exist_ok=True)
        dest = os.path.join("data", "external_data", os.path.basename(filepath))
        shutil.copy2(filepath, dest)

        log.info("Scout terminé → %s", dest)
        return f"Scout OK — dataset: {dest}"

    except Exception as e:
        log.error("Scout erreur: %s", e)
        return f"Scout ERREUR: {e}"


@tool
def outil_rag(question: str) -> str:
    """
    Lance l'Agent RAG KHADIJA pour interroger la base
    documentaire interne de l'entreprise.
    Fournir une question précise sur les positions stratégiques
    ou connaissances internes de l'entreprise sur l'IA.
    Retourne l'extrait interne le plus pertinent avec son score.
    """
    log.info("@tool outil_rag appelé — question: %s", question[:50])

    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        from langchain_community.document_loaders import TextLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        # Chemin absolu — fonctionne peu importe d'où Python est lancé
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        docs_path = os.path.join(base, "data", "internal_docs")

        documents = []
        for fname in os.listdir(docs_path):
            if fname.endswith(".txt"):
                loader = TextLoader(os.path.join(docs_path, fname), encoding="utf-8")
                documents.extend(loader.load())

        if not documents:
            return "RAG: aucun document interne trouvé."

        splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
        chunks = splitter.split_documents(documents)

        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode([c.page_content for c in chunks])
        q_emb = model.encode([question])
        scores = cosine_similarity(q_emb, embeddings)[0]
        idx = int(np.argmax(scores))

        best = chunks[idx]
        score = float(round(scores[idx], 4))
        log.info("RAG terminé — score: %.4f", score)

        return (
            f"RAG OK — score: {score}\n"
            f"Source: {best.metadata.get('source', '')}\n"
            f"Contenu: {best.page_content}"
        )

    except Exception as e:
        log.error("RAG erreur: %s", e)
        return f"RAG ERREUR: {e}"


@tool
def outil_analyse(rag_result: str = "") -> str:
    """
    Lance l'Agent Analyste WAFAE. 
    Passer rag_result = la sortie de outil_rag pour enrichir le rapport.
    Doit être appelé APRÈS outil_scout et outil_rag.
    """
    try:
        from agents.analysis_agent import AnalysisAgent
        agent = AnalysisAgent()

        # Parser le résultat RAG reçu de KHADIJA
        rag_context = None
        if rag_result and "RAG OK" in rag_result:
            lines = rag_result.strip().split("\n")
            rag_context = {
                "question": "Quels frameworks IA utilise l'entreprise ?",
                "score":    lines[0].replace("RAG OK — score: ", "").strip() if lines else "N/A",
                "source":   next((l.replace("Source: ", "") for l in lines if l.startswith("Source:")), "N/A"),
                "content":  next((l.replace("Contenu: ", "") for l in lines if l.startswith("Contenu:")), "N/A"),
            }

        external = agent.load_external_data()
        internal = agent.load_internal_docs()
        results  = agent.analyze(external, internal)

        # Passer le contexte RAG au générateur de rapport
        report   = agent.generate_report(results, rag_context=rag_context)
        agent.save_report(report)
        return report

    except Exception as e:
        return f"Analyse ERREUR: {e}"


@tool
def outil_sauvegarder(contenu: str) -> str:
    """
    Sauvegarde le rapport final dans outputs/reports/
    avec un nom horodaté. Appeler en dernier, après analyse.
    Retourne le chemin du fichier sauvegardé.
    """
    log.info("@tool outil_sauvegarder appelé")

    os.makedirs("outputs/reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"outputs/reports/rapport_langgraph_{timestamp}.md"

    enriched = contenu 
    with open(path, "w", encoding="utf-8") as f:
        f.write(enriched)

    log.info("Rapport sauvegardé → %s", path)
    return path

@tool
def outil_export_pdf(markdown_path: str) -> str:
    """
    Convertit un rapport Markdown sauvegardé en PDF.
    Fournir le chemin du fichier .md généré par outil_sauvegarder.
    Retourne le chemin du fichier PDF.
    """

    log.info("@tool outil_export_pdf appelé — fichier: %s", markdown_path)

    try:
        if not os.path.exists(markdown_path):
            return f"PDF ERREUR: fichier introuvable: {markdown_path}"

        with open(markdown_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        pdf_path = markdown_path.replace(".md", ".pdf")

        pdf = MarkdownPdf(toc_level=2)

        pdf.add_section(
            Section(md_content)
        )

        pdf.save(pdf_path)

        log.info("PDF généré → %s", pdf_path)

        return pdf_path

    except Exception as e:
        log.error("PDF erreur: %s", e)
        return f"PDF ERREUR: {e}"
# =============================================================
# ÉTAPE 2 — Créer le LLM coordinateur
# Utilise OpenRouter (gratuit) comme dans le cours
# =============================================================

llm = ChatOpenAI(
    # Modèle gratuit via OpenRouter — comme dans le cours de la prof
    model="openai/gpt-4o-mini",
    openai_api_key=os.getenv("OPENROUTER_API_KEY", ""),
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0.3,   # moins créatif = plus fiable pour orchestration
)

# =============================================================
# ÉTAPE 3 — Mémoire (InMemorySaver + thread_id)
# Comme vu en cours chapitre 4
# =============================================================

# InMemorySaver = mémoire volatile (RAM)
# Chaque cycle a son propre thread_id → conversations isolées
checkpointer = InMemorySaver()

# =============================================================
# ÉTAPE 4 — Créer l'agent ReAct avec create_agent()
# 3 paramètres fondamentaux du cours : model, tools, system_prompt
# =============================================================

TOOLS = [outil_scout, outil_rag, outil_analyse, outil_sauvegarder,outil_export_pdf]

SYSTEM_PROMPT = """Tu es HAJAR, coordinatrice du SMA de veille technologique.

Ordre d'exécution OBLIGATOIRE :
1. outil_scout(demo_mode) — collecte les données externes
2. outil_rag(question) — interroge la base interne sur le sujet de veille
3. outil_analyse(rag_result=<résultat de l'étape 2>) — croise et génère le rapport
4. outil_sauvegarder(contenu=<rapport de l'étape 3>) — sauvegarde
5. outil_export_pdf(markdown_path=<chemin du fichier Markdown>) — convertit en PDF
CRITIQUE : Le résultat de outil_rag DOIT être passé comme paramètre rag_result
à outil_analyse. Sans cela, la section comparative interne/externe sera absente.
- Le chemin retourné par outil_sauvegarder DOIT être passé à outil_export_pdf.
"""

# create_agent() = la fonction centrale du cours
# Elle crée automatiquement la boucle ReAct : Thought → Action → Observation
agent_hajar = create_agent(
    model=llm,
    tools=TOOLS,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,   # active la mémoire
)


# =============================================================
# ÉTAPE 5 — Classe principale CoordinatorAgent
# =============================================================

class CoordinatorAgent:
    """
    HAJAR — Agent Coordinateur LangGraph.

    Utilise create_agent() + @tool + InMemorySaver
    conformément au cours SMA Agentic AI.
    """

    def __init__(self):
        self.agent = agent_hajar
        self.history = []
        os.makedirs("data/external_data", exist_ok=True)
        os.makedirs("data/internal_docs",  exist_ok=True)
        os.makedirs("outputs/reports",     exist_ok=True)

    def run_cycle(self, sujet: str = "frameworks IA et LLMs récents",
                  demo_mode: bool = False) -> str:
        """
        Lance un cycle complet via l'agent LangGraph.

        L'agent ReAct décide lui-même :
          - Quels outils appeler
          - Dans quel ordre
          - Que faire en cas d'erreur
        """
        log.info("=" * 55)
        log.info("   HAJAR LangGraph — DÉMARRAGE")
        log.info("   Sujet : %s", sujet)
        log.info("   Mode  : %s", "DEMO" if demo_mode else "PRODUCTION")
        log.info("=" * 55)

        debut = datetime.now()

        # thread_id unique par cycle = mémoire isolée
        thread_id = f"cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Message envoyé à l'agent — il décide seul comment répondre
        tache = (
            f"Lance un cycle complet de veille technologique sur : '{sujet}'. "
            f"Mode demo : {'true' if demo_mode else 'false'}. "
            f"Étapes : 1) Scout, 2) RAG sur le sujet, 3) Analyse, 4) Sauvegarde rapport."
        )

        # invoke() = la boucle ReAct s'exécute automatiquement
        # L'agent appelle les outils jusqu'à avoir une réponse finale
        response = self.agent.invoke(
            input={"messages": [HumanMessage(tache)]},
            config={"configurable": {"thread_id": thread_id}},
        )

        # La réponse finale est toujours dans le dernier message
        resultat = response["messages"][-1].content
        duree = round((datetime.now() - debut).total_seconds(), 1)

        # Trouver le chemin du rapport dans la réponse
        rapport_path = "outputs/reports/rapport_langgraph_latest.md"
        for line in resultat.split("\n"):
            if "outputs/reports" in line:
                import re
                m = re.search(r"outputs/reports/\S+\.md", line)
                if m:
                    rapport_path = m.group()
                    break

        self.history.append({
            "sujet": sujet,
            "thread_id": thread_id,
            "mode": "demo" if demo_mode else "production",
            "duree_sec": duree,
            "timestamp": datetime.now().isoformat(),
            "rapport": rapport_path,
        })

        log.info("=" * 55)
        log.info("   CYCLE TERMINÉ EN %ss", duree)
        log.info("=" * 55)
        log.info("Réponse agent :\n%s", resultat)

        return rapport_path

    def show_history(self):
        print("\n" + "=" * 55)
        print("   HISTORIQUE DES CYCLES")
        print("=" * 55)
        for i, h in enumerate(self.history, 1):
            print(f"\n  Cycle {i}   : {h['sujet']}")
            print(f"  Thread ID : {h['thread_id']}")
            print(f"  Durée (timing)    : {h['duree_sec']}s")
            print(f"  Mode      : {h['mode']}")
        print("=" * 55 + "\n")