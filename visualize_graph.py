import os
from dotenv import load_dotenv
load_dotenv()

from agents.coordinator_agent import GRAPHE  # type: ignore

# =============================================================
# MÉTHODE 1 — PNG (chemin absolu — fonctionne peu importe
# d'où Python est lancé)
# =============================================================

def afficher_png():
    try:
        # Génère le PNG du graphe
        image_bytes = GRAPHE.get_graph().draw_mermaid_png()

        # Chemin absolu basé sur l'emplacement de ce fichier
        base = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(os.path.join(base, "outputs"), exist_ok=True)
        path = os.path.join(base, "outputs", "graphe_langgraph.png")

        with open(path, "wb") as f:
            f.write(image_bytes)

        print(f"PNG sauvegardé → {path}")

        # Ouvrir automatiquement l'image (Windows)
        os.startfile(path)

    except Exception as e:
        print(f"PNG erreur : {e}")


if __name__ == "__main__":
    afficher_png()