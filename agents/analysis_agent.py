from groq import Groq
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
import os
import json
import glob
import time
import random
from deep_translator import GoogleTranslator

load_dotenv(override=True)

class AnalysisAgent:

    def __init__(self):

        self.client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )

        self.company_name = "AI Future Company"

        self.focus_areas = [
            "ai", "agent", "llm", "automation",
            "rag", "framework", "embedding",
            "autonomous", "workflow", "model"
        ]

    # =====================================================
    # LOAD DATA
    # =====================================================
    def load_external_data(self):

        files = glob.glob("data/external_data/*.json")
        latest = max(files)

        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("items", [])

    def load_internal_docs(self):

        docs = []
        files = glob.glob("data/internal_docs/*.txt")

        for f in files:
            with open(f, "r", encoding="utf-8") as file:
                docs.append(file.read())

        return docs

    # =====================================================
    # CORE SIGNALS
    # =====================================================
    def weak_signal_score(self, item):

        text = (item.get("title", "") + item.get("summary", "")).lower()

        signals = [
            "new",
            "beta",
            "experimental",
            "paper",
            "research",
            "release"
        ]

        return sum(1 for s in signals if s in text)

    def trend_velocity(self, item):

        stars = item.get("extra", {}).get("stars", 0)

        if stars > 100000:
            return 3
        elif stars > 50000:
            return 2
        elif stars > 10000:
            return 1

        return 0

    def type_weight(self, item):

        text = (item.get("title", "") + item.get("summary", "")).lower()

        if "agent" in text:
            return 1.5
        if "rag" in text:
            return 1.3
        if "llm" in text:
            return 1.2
        if "cli" in text:
            return 0.9

        return 1.0

    def hype_penalty(self, item):

        text = (item.get("title", "") + item.get("summary", "")).lower()

        if "awesome" in text:
            return -1

        return 0


    # =====================================================
    # COMPATIBILITY CHECK (OPTIONAL)
    # =====================================================
    def compatibility_reason(self, item):

        title = (item.get("title", "") + " " + item.get("summary", "")).lower()

        if "browser-use" in title or "firecrawl" in title:
            return (
                "Très compatible avec le projet de veille automatisée. "
                "Peut améliorer la collecte web, le scraping et l'enrichissement "
                "des données externes."
            )

        if "codex" in title or "claude-code" in title or "opencode" in title or "openhands" in title:
            return (
                "Compatible avec les workflows de développement internes. "
                "Peut accélérer le codage, l'analyse de code et l'automatisation Git, "
                "mais nécessite un contrôle strict des données sensibles."
            )

        if "agent" in title or "multi-agent" in title or "agents" in title:
            return (
                "Compatible avec l'objectif stratégique de mise en production "
                "d'agents autonomes en Q3 2026."
            )

        if "rag" in title or "retrieval" in title:
            return (
                "Compatible avec le pipeline RAG existant basé sur LangChain, "
                "ChromaDB et MiniLM."
            )

        if "awesome" in title or "system-prompts" in title or "skills" in title:
            return (
                "Utile pour la veille et l'inspiration, mais ce n'est pas une "
                "technologie directement intégrable en production."
            )

        if "trading" in title:
            return (
                "Compatibilité faible sauf si l'entreprise vise des cas d'usage "
                "finance ou analyse de marché."
            )

        return (
            "Compatibilité à valider par un POC. Le lien avec les objectifs internes "
            "n'est pas encore suffisamment direct."
        )

    # =====================================================
    # SCORE ENGINE (FINAL SMA VERSION)
    # =====================================================
    def compute_score(self, item):

        text = (item.get("title", "") + item.get("summary", "")).lower()

        stars = item.get("extra", {}).get("stars", 0)

        score = 0

        # popularity
        if stars > 100000:
            score += 5
        elif stars > 50000:
            score += 4
        elif stars > 10000:
            score += 3
        elif stars > 1000:
            score += 1

        # relevance
        score += sum(1 for k in self.focus_areas if k in text)

        return score

    # =====================================================
    # NORMALIZATION
    # =====================================================
    def normalize_scores(self, scores):

        if not scores:
            return []

        max_s = max(scores)
        min_s = min(scores)

        if max_s == min_s:
            return scores

        return [
            (s - min_s) / (max_s - min_s) * 10
            for s in scores
        ]
    # =====================================================
    # Aproche : le meilleur élément n’est pas forcément le plus populaire
    # =====================================================
    def company_fit_score(self, item):

        text = (
            item.get("title", "")
            + " "
            + item.get("summary", "")
        ).lower()

        score = 0

        # Très aligné avec les besoins internes
        if "browser-use" in text or "firecrawl" in text:
            score += 5

        if "rag" in text or "retrieval" in text:
            score += 4

        if "langgraph" in text:
            score += 4

        if "multi-agent" in text or "autonomous agent" in text:
            score += 4

        if "agent" in text:
            score += 3

        if "memory" in text or "context" in text:
            score += 3

        if "codex" in text or "claude-code" in text or "opencode" in text or "openhands" in text:
            score += 2

        # Moins aligné avec l'entreprise
        if "trading" in text or "financial" in text:
            score -= 3

        if "awesome" in text or "system-prompts" in text or "prompts" in text:
            score -= 4

        if item.get("source_type") == "arxiv":
            score -= 1

        if item.get("source_type") == "hackernews":
            score -= 2

        return score
    # =====================================================
    # FINAL SCORE (IMPORTANT)
    # =====================================================
    def final_score(self, item, raw, norm):

        return (
            raw * 0.20
            + norm * 0.15
            + self.company_fit_score(item) * 1.8
            + self.weak_signal_score(item) * 1.5
            + self.trend_velocity(item) * 0.8
            + self.type_weight(item) * 1.5
            + self.hype_penalty(item)
        )

    # =====================================================
    # CLASSIFICATION
    # =====================================================
    def classify(self, score):

        if score >= 10:
            return "ADOPT"
        elif score >= 6:
            return "MONITOR"

        return "IGNORE"

    # =====================================================
    # LLM ANALYSIS
    # =====================================================
    def llm_reasoning(self, item, score, context, max_retries=5):

        prompt = f"""
Tu es un analyste senior en stratégie IA.

Analyse uniquement cette technologie externe :

Nom :
{item.get("title") or "Titre inconnu"}

Description :
{item.get("summary") or "description non disponible."}

Stars GitHub :
{item.get("extra", {}).get("stars", 0)}

Score final :
{score}

Contexte interne de l'entreprise :
{context[:2000]}


Réponds en français, en te basant sur le contexte interne.
Reformule aussi la description en français.

Format obligatoire :
1. Compatibilité avec l'entreprise :
2. Aide concrète pour l'entreprise :
3. Risques :
4. Recommandation finale :
"""

        for attempt in range(max_retries):

            try:
                res = self.client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a senior AI analyst."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=450
                )

                return res.choices[0].message.content

            except Exception as e:
                error = str(e)

                if (
                    "429" in error
                    or "rate_limit" in error.lower()
                    or "Too Many Requests" in error
                ):
                    wait = (2 ** attempt) + random.uniform(0, 1)

                    print(
                        f"[Groq Rate Limit] Attente {wait:.1f}s avant retry..."
                    )

                    time.sleep(wait)
                    continue

                return f"[LLM ERROR] {error}"

        return "[LLM ERROR] Rate limit Groq dépassé après plusieurs tentatives."

    # =====================================================
    # ANALYSIS PIPELINE
    # =====================================================
    def analyze(self, external_data, internal_docs):

        results = {
            "adopt": [],
            "monitor": [],
            "ignore": [],
            "all": []
        }

        context = "\n".join(internal_docs)

        scores = [
            self.compute_score(i)
            for i in external_data
        ]

        norm_scores = self.normalize_scores(scores)

        scored_items = []

        for item, raw, norm in zip(external_data, scores, norm_scores):

            fscore = self.final_score(item, raw, norm)
            decision = self.classify(fscore)

            scored_items.append({
                "item": item,
                "raw": raw,
                "norm": norm,
                "final_score": fscore,
                "decision": decision
            })

        # On garde Groq uniquement pour les 5 meilleurs
        top_for_llm = sorted(
            scored_items,
            key=lambda x: x["final_score"],
            reverse=True
        )[:5]

        top_titles = {
            x["item"].get("title")
            for x in top_for_llm
        }

        for x in scored_items:

            item = x["item"]
            fscore = x["final_score"]
            decision = x["decision"]

            if item.get("title") in top_titles:
                analysis = self.llm_reasoning(
                    item,
                    fscore,
                    context
                )
                time.sleep(2)
            else:
                analysis = (
                    "Analyse LLM non exécutée pour éviter "
                    "le rate limit Groq."
                )

            enriched = {
                "title": item.get("title") or "Titre non disponible",
                "summary": item.get("summary") or "description non disponible.",
                "summary_fr": self.translate_to_french(
                    item.get("summary") or "description non disponible."
                ),
                "score": x["raw"],
                "normalized": round(x["norm"], 2),
                "company_fit_score": self.company_fit_score(item),
                "final_score": round(fscore, 2),
                "decision": decision,
                "compatibility": self.compatibility_reason(item),
                "analysis": analysis
            }

            results["all"].append(enriched)

            if decision == "ADOPT":
                results["adopt"].append(enriched)
            elif decision == "MONITOR":
                results["monitor"].append(enriched)
            else:
                results["ignore"].append(enriched)

        return results

    # =====================================================
    # TOP TRENDS
    # =====================================================
    def top_trends(self, results):

        return sorted(
            results["all"],
            key=lambda x: x["final_score"],
            reverse=True
        )[:5]
    

    def translate_to_french(self, text):

        if not text:
            return "Description non disponible."

        try:
            return GoogleTranslator(
                source="auto",
                target="fr"
            ).translate(text[:4500])

        except Exception:
            return text

    # =====================================================
    # REPORT
    # =====================================================
    def generate_report(self, results, rag_context=None):

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        top = self.top_trends(results)

        report = f"""# Rapport de Veille Technologique & Stratégique

**Entreprise :** {self.company_name}
**Date :** {now}
**Cycle :** Production
**Agents :** HAJAR (Coord.) · FERDAOUS (Scout) · KHADIJA (RAG) · WAFAE (Analyse)

---

## Résumé Exécutif

| Métrique | Valeur |
|---|---|
| Sources analysées | {len(results["all"])} |
| Décision ADOPT | {len(results["adopt"])} |
| Décision MONITOR | {len(results["monitor"])} |
| Décision IGNORE | {len(results["ignore"])} |

> Ce cycle révèle une accélération des frameworks d'orchestration multi-agents.
> Les architectures agentiques s'imposent comme paradigme dominant.
> Signal fort détecté sur la convergence RAG + agents autonomes.

---

## Top 5 Tendances Détectées

"""

        for i, item in enumerate(top, 1):

            score_pct = min(int((item["final_score"] / 25 ) * 100), 100)

            bar = (
                "█" * (score_pct // 10)
                + "░" * (10 - score_pct // 10)
            )
            description_fr = self.translate_to_french(
                item.get("summary", "Description non disponible.")
            )

            report += f"""### {i}. {item["title"]}

| Champ | Valeur |
|---|---|
| Score final | {item["final_score"]}  |
| Score normalisé | {item["normalized"]} / 10 |
| Adéquation entreprise | {item.get("company_fit_score", "N/A")} |
| Décision | **{item["decision"]}** |

`{bar}` {score_pct}%


**Description :** {description_fr}

**Compatibilité avec l'entreprise :**

{item.get("compatibility", "Compatibilité non évaluée.")}

**Analyse stratégique (LLM) :**

{item.get("analysis", "N/A")}

---

"""

        if rag_context:

            report += f"""## Analyse Comparative Interne / Externe (KHADIJA × WAFAE)

**Question posée à la base interne :**

> {rag_context.get("question", "N/A")}

**Score de similarité :** `{rag_context.get("score", "N/A")}`

**Source interne :** `{rag_context.get("source", "N/A")}`

**Extrait pertinent :**

> {rag_context.get("content", "N/A")}

**Écart détecté :**

Les tendances externes révèlent des technologies non encore
intégrées en interne. Opportunité d'adoption identifiée
sur les items ADOPT.

---

"""

        report += "## Recommandations Stratégiques\n\n"

        adopt_items = sorted(
            results["adopt"],
            key=lambda x: x["final_score"],
            reverse=True
        )[:3]

        priorities = [
            "🔴 Priorité 1",
            "🟠 Priorité 2",
            "🟡 Priorité 3"
        ]

        for i, item in enumerate(adopt_items):

            prio = priorities[i]

            report += f"""**{prio} — Adopter {item["title"]}**

Score : {item["final_score"]}

Lancer un POC dans les 30 prochains jours.

Alignement stratégique fort avec les objectifs IA de
{self.company_name}.

"""

        report += f"""---

*Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}*

*Équipe : HAJAR (LangGraph) · FERDAOUS (Scout) · KHADIJA (RAG) · WAFAE (Analyse)*

"""

        return report

    # =====================================================
    # SAVE
    # =====================================================
    def save_report(self, report):

        os.makedirs("outputs", exist_ok=True)

        path = "outputs/reports/final_report.md"

        with open(path, "w", encoding="utf-8") as f:
            f.write(report)

        print("[Analysis] Report saved ->", path)

    # =====================================================
    # RUN
    # =====================================================
    def run(self):

        print("\n[Analysis] GROQ AGENT RUNNING...\n")

        external = self.load_external_data()
        internal = self.load_internal_docs()

        results = self.analyze(external, internal)

        report = self.generate_report(results)

        self.save_report(report)

        print("\n[Analysis] COMPLETED SUCCESSFULLY\n")

        return report

if __name__ == "__main__":

    agent = AnalysisAgent()
    print(agent.run())

