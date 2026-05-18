# =============================================================
# coordinator_agent.py — HAJAR (VRAI LangGraph StateGraph)
# Noeuds + Edges + State + compile() — conforme au cours
# =============================================================

import os, json, glob, shutil, logging
from datetime import datetime
from typing import TypedDict, Optional
from dotenv import load_dotenv
load_dotenv()

# ── VRAI LangGraph ──────────────────────────────────────────
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HAJAR] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("hajar")


# =============================================================
# ÉTAPE 1 — STATE (TypedDict)
# C'est le "bus de données" partagé entre TOUS les noeuds
# Chaque noeud lit depuis le state et écrit dans le state
# =============================================================

class VeilleState(TypedDict):
    # ── Entrées (données de départ) ──────────────────────────
    sujet:        str           # thème de veille (ex: "frameworks IA")
    demo_mode:    bool          # True = données simulées

    # ── Sorties intermédiaires (chaque noeud enrichit le state)
    dataset_path: Optional[str] # chemin JSON produit par FERDAOUS
    rag_result:   Optional[dict]# extrait interne produit par KHADIJA
    rapport:      Optional[str] # texte du rapport produit par WAFAE
    rapport_path: Optional[str] # chemin .md sauvegardé par HAJAR
    pdf_path:     Optional[str] # chemin .pdf exporté

    # ── Gestion des erreurs ──────────────────────────────────
    erreur:       Optional[str] # message d'erreur si un noeud échoue


# =============================================================
# ÉTAPE 2 — NOEUDS (fonctions Python)
# Chaque noeud reçoit le state complet et retourne
# un dictionnaire PARTIEL pour mettre à jour le state
# =============================================================

def noeud_scout(state: VeilleState) -> dict:
    """
    Noeud 1 — Lance FERDAOUS (Agent Scout).
    Lit  : state["demo_mode"]
    Écrit: state["dataset_path"] ou state["erreur"]
    """
    log.info("NOEUD scout — démarrage (demo=%s)", state["demo_mode"])

    try:
        from agents.scout_agent import FerdaousAgent, generate_demo_dataset

        # Appel de l'agent FERDAOUS
        if state["demo_mode"]:
            filepath = generate_demo_dataset()
        else:
            filepath = FerdaousAgent().run()

        # Copier vers data/external_data/ (chemin lu par WAFAE)
        os.makedirs("data/external_data", exist_ok=True)
        dest = os.path.join("data", "external_data", os.path.basename(filepath))
        shutil.copy2(filepath, dest)

        log.info("NOEUD scout — terminé → %s", dest)

        # Retourne UNIQUEMENT les clés modifiées
        return {"dataset_path": dest}

    except Exception as e:
        log.error("NOEUD scout — erreur : %s", e)
        return {"erreur": f"Scout ERREUR: {e}"}


def noeud_rag(state: VeilleState) -> dict:
    """
    Noeud 2 — Lance KHADIJA (Agent RAG Interne).
    Lit  : state["sujet"]
    Écrit: state["rag_result"] ou state["erreur"]
    """
    log.info("NOEUD rag — démarrage")

    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        from langchain_community.document_loaders import TextLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        # Chemin absolu vers les docs internes de KHADIJA
        base      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        docs_path = os.path.join(base, "data", "internal_docs")

        # Charger tous les .txt
        documents = []
        for fname in os.listdir(docs_path):
            if fname.endswith(".txt"):
                loader = TextLoader(
                    os.path.join(docs_path, fname), encoding="utf-8"
                )
                documents.extend(loader.load())

        if not documents:
            return {"rag_result": {"score": 0.0,
                                   "content": "Aucun doc interne.",
                                   "source": ""}}

        # Chunking + embeddings (code de KHADIJA)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=300, chunk_overlap=50
        )
        chunks     = splitter.split_documents(documents)
        model      = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode([c.page_content for c in chunks])

        # Recherche sémantique
        question = f"Position stratégique sur : {state['sujet']}"
        q_emb    = model.encode([question])
        scores   = cosine_similarity(q_emb, embeddings)[0]
        idx      = int(np.argmax(scores))

        result = {
            "score":   float(round(scores[idx], 4)),
            "content": chunks[idx].page_content,
            "source":  chunks[idx].metadata.get("source", ""),
        }

        log.info("NOEUD rag — score: %.4f", result["score"])
        return {"rag_result": result}

    except Exception as e:
        log.error("NOEUD rag — erreur : %s", e)
        return {"erreur": f"RAG ERREUR: {e}"}


def noeud_analyse(state: VeilleState) -> dict:
    """
    Noeud 3 — Lance WAFAE (Agent Analyse + Rapport).
    Lit  : state["rag_result"] (contexte interne)
    Écrit: state["rapport"] ou state["erreur"]
    """
    log.info("NOEUD analyse — démarrage")

    try:
        from agents.analysis_agent import AnalysisAgent

        agent    = AnalysisAgent()
        external = agent.load_external_data()
        internal = agent.load_internal_docs()
        results  = agent.analyze(external, internal)
        rapport  = agent.generate_report(results)
        agent.save_report(rapport)

        log.info("NOEUD analyse — terminé")
        return {"rapport": rapport}

    except Exception as e:
        log.error("NOEUD analyse — erreur : %s", e)
        return {"erreur": f"Analyse ERREUR: {e}"}


def noeud_sauvegarder(state: VeilleState) -> dict:
    """
    Noeud 4 — Sauvegarde le rapport final enrichi.
    Lit  : state["rapport"] + state["rag_result"]
    Écrit: state["rapport_path"]
    """
    log.info("NOEUD sauvegarder — démarrage")

    os.makedirs("outputs/reports", exist_ok=True)
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    rapport_path = f"outputs/reports/rapport_final_{timestamp}.md"

    rag = state.get("rag_result") or {}
    enriched = (state.get("rapport") or "") + f"""

---

## Contexte interne (RAG — KHADIJA)

**Score de similarité :** {rag.get('score', 'N/A')}

**Extrait pertinent :**
{rag.get('content', 'N/A')}

**Source :** {rag.get('source', 'N/A')}

---
*Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — SMA Agentic AI*
*HAJAR (coord.) · FERDAOUS (scout) · KHADIJA (RAG) · WAFAE (analyse)*
"""
    with open(rapport_path, "w", encoding="utf-8") as f:
        f.write(enriched)

    log.info("NOEUD sauvegarder → %s", rapport_path)
    return {"rapport_path": rapport_path}


# =============================================================
# ÉTAPE 3 — EDGE CONDITIONNEL
# Après le noeud scout, on vérifie s'il y a une erreur
# Si erreur → on saute directement à END
# Si OK     → on continue vers noeud_rag
# =============================================================

def router_apres_scout(state: VeilleState) -> str:
    """
    Fonction de routage : décide quel noeud vient après scout.
    Retourne le NOM du prochain noeud.
    """
    if state.get("erreur"):
        log.warning("Erreur détectée → arrêt du pipeline")
        return "fin_avec_erreur"  # → END
    return "noeud_rag"            # → continuer normalement


# =============================================================
# ÉTAPE 4 — CONSTRUCTION DU GRAPHE
# C'est ici qu'on assemble les noeuds et les edges
# =============================================================

def construire_graphe():
    """
    Construit et compile le StateGraph LangGraph.

    Structure :
      START → noeud_scout
                ↓ (si OK)
              noeud_rag
                ↓
              noeud_analyse
                ↓
              noeud_sauvegarder
                ↓
              END

      noeud_scout → END  (si erreur, via edge conditionnel)
    """

    # Créer le graphe avec notre TypedDict comme State
    graphe = StateGraph(VeilleState)

    # ── Ajouter les noeuds ────────────────────────────────────
    # add_node(nom, fonction)
    graphe.add_node("noeud_scout",       noeud_scout)
    graphe.add_node("noeud_rag",         noeud_rag)
    graphe.add_node("noeud_analyse",     noeud_analyse)
    graphe.add_node("noeud_sauvegarder", noeud_sauvegarder)

    # ── Ajouter les edges (connexions) ────────────────────────
    # Edge de départ : START → noeud_scout
    graphe.add_edge(START, "noeud_scout")

    # Edge CONDITIONNEL après scout
    # router_apres_scout() décide du prochain noeud
    graphe.add_conditional_edges(
        "noeud_scout",           # noeud source
        router_apres_scout,      # fonction de routage
        {
            "noeud_rag":       "noeud_rag",  # si OK
            "fin_avec_erreur": END,           # si erreur
        }
    )

    # Edges normaux (séquentiels)
    graphe.add_edge("noeud_rag",         "noeud_analyse")
    graphe.add_edge("noeud_analyse",     "noeud_sauvegarder")
    graphe.add_edge("noeud_sauvegarder", END)

    # ── Compiler le graphe avec la mémoire ───────────────────
    # checkpointer = InMemorySaver → mémoire volatile (cours ch.4)
    # thread_id → chaque cycle a sa propre mémoire isolée
    graphe_compile = graphe.compile(
        checkpointer=InMemorySaver()
    )

    log.info("Graphe LangGraph compilé avec succès")
    return graphe_compile


# Compiler une seule fois au chargement du module
GRAPHE = construire_graphe()


# =============================================================
# ÉTAPE 5 — CLASSE PRINCIPALE
# =============================================================

class CoordinatorAgent:
    """
    HAJAR — Agent Coordinateur LangGraph (vrai StateGraph).

    Utilise StateGraph + TypedDict + add_node + add_edge + compile
    conformément au cours SMA Agentic AI.
    """

    def __init__(self):
        self.graphe  = GRAPHE
        self.history = []
        os.makedirs("data/external_data", exist_ok=True)
        os.makedirs("data/internal_docs",  exist_ok=True)
        os.makedirs("outputs/reports",     exist_ok=True)

    def run_cycle(
        self,
        sujet:     str  = "frameworks IA et LLMs récents",
        demo_mode: bool = False,
    ) -> str:
        """
        Exécute un cycle de veille via le StateGraph.

        Le graphe fait circuler le VeilleState de noeud en noeud.
        Chaque noeud enrichit le state avec ses résultats.
        """
        log.info("=" * 55)
        log.info("   HAJAR StateGraph — DÉMARRAGE")
        log.info("   Sujet : %s", sujet)
        log.info("   Mode  : %s", "DEMO" if demo_mode else "PRODUCTION")
        log.info("=" * 55)

        debut = datetime.now()

        # State initial : seules les entrées sont renseignées
        # Les autres champs seront remplis par les noeuds
        state_initial: VeilleState = {
            "sujet":        sujet,
            "demo_mode":    demo_mode,
            "dataset_path": None,
            "rag_result":   None,
            "rapport":      None,
            "rapport_path": None,
            "pdf_path":     None,
            "erreur":       None,
        }

        # thread_id unique = mémoire isolée pour ce cycle
        thread_id = f"cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Lancer le graphe — il traverse les noeuds automatiquement
        resultat = self.graphe.invoke(
            state_initial,
            config={"configurable": {"thread_id": thread_id}}
        )

        duree         = round((datetime.now() - debut).total_seconds(), 1)
        rapport_path  = resultat.get("rapport_path", "outputs/reports/rapport.md")

        if resultat.get("erreur"):
            log.error("Pipeline terminé avec erreur : %s", resultat["erreur"])
        else:
            log.info("=" * 55)
            log.info("   CYCLE TERMINÉ EN %ss", duree)
            log.info("   Rapport → %s", rapport_path)
            log.info("=" * 55)

        self.history.append({
            "sujet":     sujet,
            "thread_id": thread_id,
            "mode":      "demo" if demo_mode else "production",
            "duree_sec": duree,
            "rapport":   rapport_path,
            "erreur":    resultat.get("erreur"),
            "timestamp": datetime.now().isoformat(),
        })

        return rapport_path

    def show_history(self):
        print("\n" + "=" * 55)
        print("   HISTORIQUE DES CYCLES")
        print("=" * 55)
        for i, h in enumerate(self.history, 1):
            print(f"\n  Cycle {i}   : {h['sujet']}")
            print(f"  Thread ID : {h['thread_id']}")
            print(f"  Durée     : {h['duree_sec']}s")
            print(f"  Mode      : {h['mode']}")
            if h.get("erreur"):
                print(f"  Erreur    : {h['erreur']}")
        print("=" * 55 + "\n")
__all__ = ["CoordinatorAgent", "GRAPHE", "construire_graphe", "VeilleState"]
