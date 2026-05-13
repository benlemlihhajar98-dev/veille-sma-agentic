from groq import Groq
from datetime import datetime
from dotenv import load_dotenv
import os
import json
import glob

load_dotenv()


class AnalysisAgent:

    def __init__(self):

        self.client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
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

        text = (item.get("title", "") + item.get("description", "")).lower()

        signals = ["new", "beta", "experimental", "paper", "research", "release"]

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

        text = (item.get("title", "") + item.get("description", "")).lower()

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

        text = (item.get("title", "") + item.get("description", "")).lower()

        if "awesome" in text:
            return -1

        return 0

    # =====================================================
    # SCORE ENGINE (FINAL SMA VERSION)
    # =====================================================
    def compute_score(self, item):

        text = (item.get("title", "") + item.get("description", "")).lower()

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

        max_s = max(scores)
        min_s = min(scores)

        if max_s == min_s:
            return scores

        return [(s - min_s) / (max_s - min_s) * 10 for s in scores]

    # =====================================================
    # FINAL SCORE (IMPORTANT)
    # =====================================================
    def final_score(self, item, raw, norm):

        return (
            raw * 0.35 +
            norm * 0.25 +
            self.weak_signal_score(item) * 2 +
            self.trend_velocity(item) * 1.5 +
            self.type_weight(item) * 2 +
            self.hype_penalty(item)
        )

    # =====================================================
    # CLASSIFICATION
    # =====================================================
    def classify(self, score):

        if score >= 8:
            return "ADOPT"
        elif score >= 5:
            return "MONITOR"
        return "IGNORE"

    # =====================================================
    # LLM ANALYSIS
    # =====================================================
    def llm_reasoning(self, item, score, context):

        prompt = f"""
You are a Gartner-level AI strategist.

Analyze:

- Tech: {item.get('title')}
- Score: {score}

Context:
{context}

Return:
- strategic importance
- hype vs real trend
- risks
- recommendation
"""

        try:
            res = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a senior AI analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            return res.choices[0].message.content

        except Exception as e:
            return f"[LLM ERROR] {str(e)}"

    # =====================================================
    # ANALYSIS PIPELINE
    # =====================================================
    def analyze(self, external_data, internal_docs):

        results = {"adopt": [], "monitor": [], "ignore": [], "all": []}

        context = "\n".join(internal_docs)

        scores = [self.compute_score(i) for i in external_data]
        norm_scores = self.normalize_scores(scores)

        for item, raw, norm in zip(external_data, scores, norm_scores):

            fscore = self.final_score(item, raw, norm)

            decision = self.classify(fscore)

            enriched = {
                "title": item.get("title"),
                "description": item.get("description"),
                "score": raw,
                "normalized": round(norm, 2),
                "final_score": round(fscore, 2),
                "decision": decision,
                "analysis": self.llm_reasoning(item, fscore, context)
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

    # =====================================================
    # REPORT
    # =====================================================
    def generate_report(self, results):

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""
====================================================
📊 STRATEGIC TECHNOLOGY REPORT
====================================================

Company: {self.company_name}
Date: {now}

====================================================

# 🧠 Executive Summary

Total analyzed: {len(results["all"])}

- Adopt: {len(results["adopt"])}
- Monitor: {len(results["monitor"])}
- Ignore: {len(results["ignore"])}

# 🚀 Top Trends
"""

        for i, item in enumerate(self.top_trends(results), 1):

            report += f"""

{i}. {item["title"]}
Final Score: {item["final_score"]}
Decision: {item["decision"]}

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