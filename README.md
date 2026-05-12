# veille-sma-agentic
 MSA Projet 2 > Cellule Automatisée de Veille Technologique &amp; Stratégique 
# 🤖 Veille SMA Agentic AI
**Projet 4AISDR — Module SMA Agentic AI**  
*Cellule Automatisée de Veille Technologique & Stratégique*  
Proposé par : Pr. Hasnââ CHAABI & Pr. Nadia IDRISSI Zouggari

---

## 👥 Équipe

| Membre | Rôle | Agent | Fichier |
|--------|------|-------|---------|
| **HAJAR** | Coordinatrice | Agent Coordinateur | `coordinator_agent.py` + `main.py` |
| **FERDAOUS** | Scout | Agent Scout (veille externe) | `scout_agent.py` |
| **KHADIJA** | Analyste Interne | Agent RAG (mémoire interne) | `internal_rag_agent.py` |
| **WAFAE** | Comparatrice & Rédactrice | Agent Analyse + Rapport | `analysis_agent.py` + `report_generator.py` |

---

## 🎯 Objectif

Concevoir un système multi-agents (SMA) autonome qui :
- Surveille en continu les tendances IA (GitHub, arXiv, Hacker News, RSS)
- Croise avec la base documentaire interne de l'entreprise (RAG)
- Produit périodiquement un rapport de synthèse stratégique

---

## 🏗️ Architecture

```
veille-sma-agentic/
├── main.py                          ← Point d'entrée (HAJAR)
├── requirements.txt                 ← Dépendances Python
├── agents/
│   ├── scout_agent.py               ← Collecte externe (FERDAOUS)
│   ├── internal_rag_agent.py        ← Mémoire RAG (KHADIJA)
│   ├── analysis_agent.py            ← Analyse comparative (WAFAE)
│   ├── report_generator.py          ← Génération rapport (WAFAE)
│   └── coordinator_agent.py         ← Orchestration (HAJAR)
├── data/
│   └── internal_docs/               ← Documents internes simulés (KHADIJA)
└── outputs/
    └── reports/                     ← Rapports générés automatiquement
```

---

## 🔄 Workflow du système

```
HAJAR (Coordinateur)
    │
    ├──► FERDAOUS (Scout)        → collecte GitHub, arXiv, RSS, Hacker News
    │         │
    ├──► KHADIJA (RAG)           → interroge base documentaire interne
    │         │
    └──► WAFAE (Analyse+Rapport) → croise les sources → génère rapport PDF/Markdown
```

---

## ⚙️ Installation

```bash
# 1. Cloner le repo
git clone https://github.com/benlemlihhajar98-dev/veille-sma-agentic.git
cd veille-sma-agentic

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer la clé API
cp .env.example .env
# Éditer .env et ajouter : OPENAI_API_KEY=ta_clé_ici

# 4. Lancer le système
python main.py
```

---

## 🌿 Branches Git

| Branche | Membre | Description |
|---------|--------|-------------|
| `main` | — | Code stable et validé |
| `feature/scout-ferdaous` | FERDAOUS | Agent Scout |
| `feature/rag-khadija` | KHADIJA | Agent RAG |
| `feature/analysis-wafae` | WAFAE | Agent Analyse & Rapport |
| `feature/coordinator-hajar` | HAJAR | Agent Coordinateur |

---

## 🛠️ Technologies utilisées

- **LangChain** — orchestration des agents et chaînes LLM
- **OpenAI GPT** — modèle de langage principal
- **FAISS / ChromaDB** — base vectorielle pour le RAG
- **arXiv API** — collecte de papers scientifiques
- **GitHub API** — trending repositories IA
- **BeautifulSoup** — web scraping
- **feedparser** — parsing des flux RSS

---

## 📦 Livrables

- [ ] `scout_agent.py` — pipeline de collecte fonctionnel
- [ ] `internal_rag_agent.py` — système RAG opérationnel
- [ ] `analysis_agent.py` — logique d'analyse comparative
- [ ] `report_generator.py` — génération automatique de rapports
- [ ] `coordinator_agent.py` — orchestration multi-agents
- [ ] `main.py` — pipeline complet end-to-end
- [ ] Rapport automatique (Markdown / PDF)
- [ ] Présentation PowerPoint (15–25 slides)

---

## 📄 Format du rapport généré

1. **Executive Summary**
2. **Top 5 tendances détectées**
3. **Analyse technique détaillée**
4. **Opportunités et risques**
5. **Recommandations stratégiques**

---

*Projet réalisé dans le cadre du module SMA — 4AISDR*
