
# =============================================================
# main.py — Point d'entrée du SMA Agentic AI
# Lance le pipeline complet orchestré par HAJAR
# =============================================================

import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement (.env)
load_dotenv()

# Vérifications des clés requises
def check_env():
    missing = []
    if not os.getenv("GROQ_API_KEY"):
        missing.append("GROQ_API_KEY  (requis par WAFAE — analyse_agent.py)")
    if missing:
        print("\n⚠️  Variables manquantes dans le fichier .env :")
        for m in missing:
            print(f"   → {m}")
        print("\nCrée un fichier .env à la racine avec :")
        print("   GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx")
        print("   GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx  (optionnel)")
        print()


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║     Cellule Automatisée de Veille Technologique & Stratégique    ║
║                    SMA Agentic AI — 4AISDR                       ║
╠══════════════════════════════════════════════════════════════════╣
║  HAJAR    → Coordinatrice   (coordinator_agent.py)               ║
║  FERDAOUS → Scout externe   (scout_agent.py)                     ║
║  KHADIJA  → RAG interne     (internal_rag_agent.py)              ║
║  WAFAE    → Analyse+Rapport (analysis_agent.py)                  ║
╚══════════════════════════════════════════════════════════════════╝
""")


def main():
    print_banner()
    check_env()

    # ── Mode : demo ou production ────────────────────────────
    demo_mode = "--demo" in sys.argv or os.getenv("DEMO_MODE") == "1"

    if demo_mode:
        print("ℹ️  Mode DEMO activé — données simulées (pas d'appels API réels)")
    else:
        print("ℹ️  Mode PRODUCTION — appels API réels")

    print()

    # ── Sujet de veille ──────────────────────────────────────
    sujet = "frameworks IA et LLMs récents"
    if len(sys.argv) > 1 and sys.argv[1] != "--demo":
        sujet = sys.argv[1]

    # ── Lancement du coordinateur ────────────────────────────
    from agents.coordinator_agent import CoordinatorAgent

    hajar = CoordinatorAgent()

    try:
        rapport_path = hajar.run_cycle(
            sujet     = sujet,
            demo_mode = demo_mode,
        )

        print("\n" + "=" * 55)
        print("✅  SYSTÈME TERMINÉ AVEC SUCCÈS")
        print(f"📄  Rapport → {rapport_path}")
        print("=" * 55)

        # Afficher les 30 premières lignes du rapport
        print("\n── Aperçu du rapport ──────────────────────────────\n")
        with open(rapport_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print("".join(lines[:30]))
        if len(lines) > 30:
            print(f"... ({len(lines) - 30} lignes supplémentaires dans le fichier)")

    except KeyboardInterrupt:
        print("\n\nArrêt demandé par l'utilisateur.")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        print("\nConseil : lance en mode demo d'abord pour tester :")
        print("   python main.py --demo")
        sys.exit(1)

    # Afficher l'historique
    hajar.show_history()


if __name__ == "__main__":
    main()