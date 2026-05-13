"""
╔══════════════════════════════════════════════════════════════════╗
║        FERDAOUS — Agent Scout (Collecte & Veille Externe)        ║
║     Cellule Automatisée de Veille Technologique & Stratégique    ║
║         Pr. Hasnaa CHAABI & Pr. Nadia IDRISSI Zouggari           ║
╚══════════════════════════════════════════════════════════════════╝

Description :
    FERDAOUS est l'agent de veille externe du SMA. Elle collecte,
    nettoie, filtre et structure les données depuis :
      - GitHub API  (repositories IA trending)
      - arXiv API   (articles scientifiques récents)
      - RSS Feeds   (blogs tech)
      - Web Scraping (Hacker News, sites IA)

Livrable :  scout_agent.py  +  dataset JSON structuré
"""

# ─────────────────────────────────────────────
# 0.  IMPORTS
# ─────────────────────────────────────────────
import os
import json
import time
import hashlib
import logging
import re
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from typing import Optional
from xml.etree import ElementTree as ET

# ─────────────────────────────────────────────
# 1.  CONFIGURATION CENTRALE
# ─────────────────────────────────────────────
CONFIG = {
    # ── GitHub ──────────────────────────────
    "github": {
        "token": os.getenv("GITHUB_TOKEN", ""),          # optionnel mais recommandé
        "trending_query": "artificial-intelligence OR LLM OR agents OR langchain OR transformers",
        "languages": ["Python", "Jupyter Notebook"],
        "min_stars": 100,
        "max_results": 20,
        "sort": "stars",                                   # stars | updated
        "created_after": "2024-01-01",
    },

    # ── arXiv ────────────────────────────────
    "arxiv": {
        "search_queries": [
            "large language models agents",
            "autonomous AI agents",
            "LLM tool use",
            "multi-agent systems AI",
            "retrieval augmented generation",
        ],
        "max_results_per_query": 5,
        "categories": ["cs.AI", "cs.LG", "cs.CL"],
    },

    # ── RSS Feeds ────────────────────────────
    "rss": {
        "feeds": [
            {"name": "Towards Data Science",      "url": "https://towardsdatascience.com/feed"},
            {"name": "The Batch (DeepLearning.AI)","url": "https://www.deeplearning.ai/the-batch/feed/"},
            {"name": "Google AI Blog",             "url": "https://blog.research.google/feeds/posts/default"},
            {"name": "Hugging Face Blog",          "url": "https://huggingface.co/blog/feed.xml"},
            {"name": "OpenAI News",                "url": "https://openai.com/news/rss.xml"},
        ],
        "max_articles_per_feed": 5,
    },

    # ── Hacker News ──────────────────────────
    "hackernews": {
        "n_top_stories": 30,
        "ai_keywords": [
            "llm", "gpt", "claude", "gemini", "mistral", "agent", "langchain",
            "openai", "anthropic", "hugging face", "transformer", "rag",
            "fine-tun", "embedding", "vector", "ai ", "machine learning",
            "deep learning", "neural", "benchmark", "multimodal",
        ],
    },

    # ── Filtre global ─────────────────────────
    "filter_keywords": [
        "AI", "LLM", "agent", "transformer", "neural", "deep learning",
        "machine learning", "GPT", "Claude", "Gemini", "Mistral",
        "langchain", "RAG", "embedding", "fine-tun", "multimodal",
        "benchmark", "autonomous", "framework", "hugging face",
    ],

    # ── Output ───────────────────────────────
    "output": {
        "directory": "ferdaous_data",
        "filename_prefix": "scout_dataset",
    },
}

# ─────────────────────────────────────────────
# 2.  LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FERDAOUS] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("ferdaous")


# ─────────────────────────────────────────────
# 3.  UTILITAIRES COMMUNS
# ─────────────────────────────────────────────

def _unique_id(text: str) -> str:
    """Génère un identifiant court et unique à partir du texte."""
    return hashlib.md5(text.encode()).hexdigest()[:12]


def _clean_text(text: str) -> str:
    """Supprime le bruit : balises HTML, espaces multiples, retours."""
    if not text:
        return ""
    # Supprimer les balises HTML
    text = re.sub(r"<[^>]+>", " ", text)
    # Décoder les entités HTML courantes
    entities = {"&amp;": "&", "&lt;": "<", "&gt;": ">",
                 "&quot;": '"', "&#39;": "'", "&nbsp;": " "}
    for ent, char in entities.items():
        text = text.replace(ent, char)
    # Normaliser les espaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_relevant(text: str, keywords: Optional[list] = None) -> bool:
    """Vérifie si le texte contient au moins un mot-clé IA."""
    if keywords is None:
        keywords = CONFIG["filter_keywords"]
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _http_get(url: str, headers: Optional[dict] = None, timeout: int = 15) -> Optional[str]:
    """HTTP GET simple avec urllib (sans dépendances externes)."""
    req = urllib.request.Request(url, headers=headers or {})
    req.add_header("User-Agent", "FERDAOUS-ScoutAgent/1.0 (academic project)")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        log.warning("HTTP %s → %s", e.code, url)
        return None
    except Exception as e:
        log.warning("Erreur réseau (%s) → %s", e, url)
        return None


def _build_item(
    source: str,
    source_type: str,
    title: str,
    url: str,
    summary: str,
    authors: list,
    tags: list,
    published_at: str,
    extra: Optional[dict] = None,
) -> dict:
    """Construit un élément unifié du dataset."""
    return {
        "id":           _unique_id(url + title),
        "source":       source,
        "source_type":  source_type,           # github | arxiv | rss | hackernews
        "title":        _clean_text(title),
        "url":          url,
        "summary":      _clean_text(summary),
        "authors":      authors,
        "tags":         tags,
        "published_at": published_at,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "relevance_score": _compute_relevance_score(_clean_text(title + " " + summary)),
        "extra":        extra or {},
    }


def _compute_relevance_score(text: str) -> float:
    """Score de pertinence simple basé sur la densité de mots-clés (0.0–1.0)."""
    text_lower = text.lower()
    hits = sum(1 for kw in CONFIG["filter_keywords"] if kw.lower() in text_lower)
    # Normalisation logarithmique
    score = min(hits / max(len(CONFIG["filter_keywords"]) * 0.3, 1), 1.0)
    return round(score, 3)


# ─────────────────────────────────────────────
# 4.  COLLECTEUR GITHUB
# ─────────────────────────────────────────────

class GitHubCollector:
    """Collecte les repositories GitHub trending en IA."""

    BASE_URL = "https://api.github.com/search/repositories"

    def __init__(self):
        cfg = CONFIG["github"]
        self.token = cfg["token"]
        self.query = cfg["trending_query"]
        self.min_stars = cfg["min_stars"]
        self.max_results = cfg["max_results"]
        self.sort = cfg["sort"]
        self.created_after = cfg["created_after"]

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def collect(self) -> list:
        log.info("▶ GitHub — Démarrage de la collecte")
        items = []

        full_query = f"{self.query} stars:>{self.min_stars} created:>{self.created_after}"
        params = urllib.parse.urlencode({
            "q":        full_query,
            "sort":     self.sort,
            "order":    "desc",
            "per_page": min(self.max_results, 30),
        })
        url = f"{self.BASE_URL}?{params}"
        raw = _http_get(url, headers=self._headers())

        if not raw:
            log.warning("GitHub — Pas de réponse")
            return items

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            log.error("GitHub — Réponse JSON invalide")
            return items

        repos = data.get("items", [])
        log.info("GitHub — %d repositories récupérés", len(repos))

        for repo in repos:
            title   = repo.get("full_name", "")
            desc    = repo.get("description") or ""
            topics  = repo.get("topics", [])
            text    = f"{title} {desc} {' '.join(topics)}"

            if not _is_relevant(text):
                continue

            items.append(_build_item(
                source      = repo.get("full_name", ""),
                source_type = "github",
                title       = title,
                url         = repo.get("html_url", ""),
                summary     = desc,
                authors     = [repo.get("owner", {}).get("login", "")],
                tags        = topics,
                published_at= repo.get("created_at", ""),
                extra={
                    "stars":       repo.get("stargazers_count", 0),
                    "forks":       repo.get("forks_count", 0),
                    "language":    repo.get("language", ""),
                    "open_issues": repo.get("open_issues_count", 0),
                    "updated_at":  repo.get("updated_at", ""),
                    "watchers":    repo.get("watchers_count", 0),
                },
            ))

        log.info("GitHub — %d éléments pertinents retenus", len(items))
        return items


# ─────────────────────────────────────────────
# 5.  COLLECTEUR arXiv
# ─────────────────────────────────────────────

class ArXivCollector:
    """Collecte les articles scientifiques depuis l'API arXiv."""

    BASE_URL = "http://export.arxiv.org/api/query"
    NS = "http://www.w3.org/2005/Atom"

    def __init__(self):
        cfg = CONFIG["arxiv"]
        self.queries          = cfg["search_queries"]
        self.max_per_query    = cfg["max_results_per_query"]
        self.categories       = cfg["categories"]

    def collect(self) -> list:
        log.info("▶ arXiv — Démarrage de la collecte")
        items = []
        seen_ids = set()

        for query in self.queries:
            cat_filter = " OR ".join(f"cat:{c}" for c in self.categories)
            full_query = f"({query}) AND ({cat_filter})"
            params = urllib.parse.urlencode({
                "search_query": full_query,
                "start":        0,
                "max_results":  self.max_per_query,
                "sortBy":       "submittedDate",
                "sortOrder":    "descending",
            })
            url = f"{self.BASE_URL}?{params}"
            raw = _http_get(url)
            if not raw:
                continue

            try:
                root = ET.fromstring(raw)
            except ET.ParseError as e:
                log.error("arXiv — XML invalide : %s", e)
                continue

            entries = root.findall(f"{{{self.NS}}}entry")
            log.info("arXiv — '%s' → %d articles", query, len(entries))

            for entry in entries:
                arxiv_id = (entry.findtext(f"{{{self.NS}}}id") or "").strip()
                if arxiv_id in seen_ids:
                    continue
                seen_ids.add(arxiv_id)

                title    = entry.findtext(f"{{{self.NS}}}title") or ""
                abstract = entry.findtext(f"{{{self.NS}}}summary") or ""
                published= entry.findtext(f"{{{self.NS}}}published") or ""

                authors = [
                    a.findtext(f"{{{self.NS}}}name") or ""
                    for a in entry.findall(f"{{{self.NS}}}author")
                ]

                # Catégories / tags
                cats = [
                    c.get("term", "")
                    for c in entry.findall("{http://arxiv.org/schemas/atom}primary_category")
                ] + [
                    c.get("term", "")
                    for c in entry.findall(f"{{{self.NS}}}category")
                ]
                cats = list(set(filter(None, cats)))

                if not _is_relevant(title + " " + abstract):
                    continue

                items.append(_build_item(
                    source      = "arXiv",
                    source_type = "arxiv",
                    title       = title.replace("\n", " "),
                    url         = arxiv_id,
                    summary     = abstract.replace("\n", " ")[:500],
                    authors     = authors[:5],
                    tags        = cats,
                    published_at= published,
                    extra={
                        "query_used": query,
                        "categories": cats,
                    },
                ))

            time.sleep(3)   # Respecter les 3 secondes recommandées par arXiv

        log.info("arXiv — %d articles pertinents retenus", len(items))
        return items


# ─────────────────────────────────────────────
# 6.  COLLECTEUR RSS
# ─────────────────────────────────────────────

class RSSCollector:
    """Parse des flux RSS de blogs technologiques."""

    NS_CONTENT = "http://purl.org/rss/1.0/modules/content/"

    def __init__(self):
        cfg = CONFIG["rss"]
        self.feeds   = cfg["feeds"]
        self.max_art = cfg["max_articles_per_feed"]

    def _parse_rss_date(self, date_str: str) -> str:
        """Normalise la date RSS en ISO-8601."""
        if not date_str:
            return ""
        # Format RFC-822 courant dans RSS
        import email.utils
        try:
            parsed = email.utils.parsedate_to_datetime(date_str)
            return parsed.isoformat()
        except Exception:
            return date_str.strip()

    def _parse_feed(self, feed_name: str, url: str) -> list:
        items = []
        raw = _http_get(url)
        if not raw:
            return items

        # Retirer les déclarations XML qui pourraient perturber ElementTree
        raw = re.sub(r"<\?xml[^?]*\?>", "", raw, count=1)
        # Retirer les namespaces inconnus potentiellement problématiques
        raw = re.sub(r'\sxmlns(?::\w+)?="[^"]*"', "", raw)

        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            log.warning("RSS '%s' — XML invalide : %s", feed_name, e)
            return items

        # Support RSS 2.0 et Atom
        channel = root.find("channel")
        entries = (channel or root).findall("item") if channel else root.findall("entry")

        for entry in entries[:self.max_art]:
            title   = _clean_text(entry.findtext("title") or
                                   entry.findtext("{http://www.w3.org/2005/Atom}title") or "")
            link    = (entry.findtext("link") or
                       entry.findtext("{http://www.w3.org/2005/Atom}link") or
                       (entry.find("{http://www.w3.org/2005/Atom}link") or ET.Element("x")).get("href", ""))
            desc    = _clean_text(entry.findtext("description") or
                                   entry.findtext("{http://www.w3.org/2005/Atom}summary") or "")
            pub_date= entry.findtext("pubDate") or entry.findtext("{http://www.w3.org/2005/Atom}published") or ""

            if not _is_relevant(title + " " + desc):
                continue

            items.append(_build_item(
                source      = feed_name,
                source_type = "rss",
                title       = title,
                url         = link.strip(),
                summary     = desc[:500],
                authors     = [],
                tags        = [],
                published_at= self._parse_rss_date(pub_date),
                extra={"feed_url": url},
            ))

        return items

    def collect(self) -> list:
        log.info("▶ RSS — Démarrage de la collecte (%d feeds)", len(self.feeds))
        all_items = []
        for feed in self.feeds:
            items = self._parse_feed(feed["name"], feed["url"])
            log.info("  RSS '%s' → %d articles retenus", feed["name"], len(items))
            all_items.extend(items)
            time.sleep(1)
        log.info("RSS — %d articles au total", len(all_items))
        return all_items


# ─────────────────────────────────────────────
# 7.  COLLECTEUR HACKER NEWS
# ─────────────────────────────────────────────

class HackerNewsCollector:
    """Scrape les top stories de Hacker News et filtre sur l'IA."""

    HN_TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"
    HN_ITEM        = "https://hacker-news.firebaseio.com/v0/item/{}.json"

    def __init__(self):
        cfg = CONFIG["hackernews"]
        self.n_stories    = cfg["n_top_stories"]
        self.ai_keywords  = cfg["ai_keywords"]

    def collect(self) -> list:
        log.info("▶ Hacker News — Démarrage de la collecte")
        items = []

        raw = _http_get(self.HN_TOP_STORIES)
        if not raw:
            return items

        try:
            story_ids = json.loads(raw)[: self.n_stories]
        except (json.JSONDecodeError, TypeError):
            log.error("HN — Impossible de parser la liste des stories")
            return items

        log.info("HN — %d stories candidates à analyser", len(story_ids))

        for sid in story_ids:
            story_raw = _http_get(self.HN_ITEM.format(sid))
            if not story_raw:
                continue
            try:
                story = json.loads(story_raw)
            except json.JSONDecodeError:
                continue

            title = story.get("title", "")
            url   = story.get("url", f"https://news.ycombinator.com/item?id={sid}")
            text  = story.get("text", "")

            if not _is_relevant(title + " " + text, keywords=self.ai_keywords):
                continue

            # Convertir le timestamp Unix en ISO-8601
            ts = story.get("time", 0)
            published_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else ""

            items.append(_build_item(
                source      = "Hacker News",
                source_type = "hackernews",
                title       = title,
                url         = url,
                summary     = _clean_text(text)[:500],
                authors     = [story.get("by", "")],
                tags        = ["hacker news"],
                published_at= published_at,
                extra={
                    "hn_id":    sid,
                    "score":    story.get("score", 0),
                    "comments": story.get("descendants", 0),
                },
            ))

            time.sleep(0.1)   # Polite crawl

        log.info("HN — %d stories pertinentes retenues", len(items))
        return items


# ─────────────────────────────────────────────
# 8.  PIPELINE PRINCIPAL FERDAOUS
# ─────────────────────────────────────────────

class FerdaousAgent:
    """
    Agent Scout FERDAOUS — Pipeline complet de veille externe.

    Étapes :
        1. Collecte depuis toutes les sources
        2. Fusion & déduplication
        3. Nettoyage & filtrage final
        4. Tri par pertinence
        5. Sauvegarde JSON structurée
    """

    def __init__(self):
        self.github_collector = GitHubCollector()
        self.arxiv_collector  = ArXivCollector()
        self.rss_collector    = RSSCollector()
        self.hn_collector     = HackerNewsCollector()

        # Préparer le répertoire de sortie
        os.makedirs(CONFIG["output"]["directory"], exist_ok=True)

    # ── 8.1  Collecte ──────────────────────────────────────────────
    def _collect_all(self) -> list:
        all_items = []

        # GitHub
        try:
            all_items.extend(self.github_collector.collect())
        except Exception as e:
            log.error("GitHub — Erreur inattendue : %s", e)

        # arXiv
        try:
            all_items.extend(self.arxiv_collector.collect())
        except Exception as e:
            log.error("arXiv — Erreur inattendue : %s", e)

        # RSS
        try:
            all_items.extend(self.rss_collector.collect())
        except Exception as e:
            log.error("RSS — Erreur inattendue : %s", e)

        # Hacker News
        try:
            all_items.extend(self.hn_collector.collect())
        except Exception as e:
            log.error("HN — Erreur inattendue : %s", e)

        return all_items

    # ── 8.2  Déduplication ─────────────────────────────────────────
    def _deduplicate(self, items: list) -> list:
        seen_ids   = set()
        seen_titles= set()
        unique     = []
        for item in items:
            norm_title = item["title"].lower().strip()
            if item["id"] in seen_ids or norm_title in seen_titles:
                continue
            seen_ids.add(item["id"])
            seen_titles.add(norm_title)
            unique.append(item)
        removed = len(items) - len(unique)
        log.info("Déduplication — %d doublons supprimés → %d éléments", removed, len(unique))
        return unique

    # ── 8.3  Filtrage final ────────────────────────────────────────
    def _filter(self, items: list) -> list:
        filtered = [
            item for item in items
            if item["relevance_score"] > 0.05
            and len(item["title"]) > 5
        ]
        log.info("Filtrage final — %d éléments retenus / %d", len(filtered), len(items))
        return filtered

    # ── 8.4  Tri par pertinence ────────────────────────────────────
    def _sort(self, items: list) -> list:
        return sorted(items, key=lambda x: x["relevance_score"], reverse=True)

    # ── 8.5  Construction du dataset final ────────────────────────
    def _build_dataset(self, items: list) -> dict:
        stats = {
            "total":      len(items),
            "by_source":  {},
            "by_type":    {},
            "top_tags":   {},
        }

        for item in items:
            # Par source type
            stype = item["source_type"]
            stats["by_type"][stype] = stats["by_type"].get(stype, 0) + 1
            # Par source
            src = item["source"]
            stats["by_source"][src] = stats["by_source"].get(src, 0) + 1
            # Tags
            for tag in item.get("tags", []):
                if tag:
                    stats["top_tags"][tag] = stats["top_tags"].get(tag, 0) + 1

        # Garder top 20 tags
        stats["top_tags"] = dict(
            sorted(stats["top_tags"].items(), key=lambda x: x[1], reverse=True)[:20]
        )

        return {
            "metadata": {
                "agent":          "FERDAOUS — Agent Scout",
                "version":        "1.0.0",
                "generated_at":   datetime.now(timezone.utc).isoformat(),
                "project":        "Cellule Automatisée de Veille Technologique & Stratégique",
                "supervisors":    ["Pr. Hasnaa CHAABI", "Pr. Nadia IDRISSI Zouggari"],
                "sources_used":   ["GitHub API", "arXiv API", "RSS Feeds", "Hacker News"],
                "filter_keywords":CONFIG["filter_keywords"],
            },
            "statistics":  stats,
            "items":       items,
        }

    # ── 8.6  Sauvegarde ───────────────────────────────────────────
    def _save(self, dataset: dict) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"{CONFIG['output']['filename_prefix']}_{timestamp}.json"
        filepath  = os.path.join(CONFIG["output"]["directory"], filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        log.info("Dataset sauvegardé → %s", filepath)
        return filepath

    # ── 8.7  Méthode principale ───────────────────────────────────
    def run(self) -> str:
        """Lance le pipeline complet et retourne le chemin du dataset."""
        log.info("═" * 60)
        log.info("   FERDAOUS — Agent Scout démarré")
        log.info("═" * 60)

        start_time = time.time()

        # Pipeline
        raw_items  = self._collect_all()
        dedup      = self._deduplicate(raw_items)
        filtered   = self._filter(dedup)
        sorted_    = self._sort(filtered)
        dataset    = self._build_dataset(sorted_)
        output_path= self._save(dataset)

        elapsed = round(time.time() - start_time, 1)

        # Résumé
        log.info("═" * 60)
        log.info("   RÉSUMÉ FERDAOUS")
        log.info("   ──────────────────────────────────")
        log.info("   Total collecté  : %d éléments", dataset["statistics"]["total"])
        log.info("   Par type        : %s", dataset["statistics"]["by_type"])
        log.info("   Durée           : %ss", elapsed)
        log.info("   Fichier sortie  : %s", output_path)
        log.info("═" * 60)

        return output_path


# ─────────────────────────────────────────────
# 9.  INTERFACE CLI
# ─────────────────────────────────────────────

def _print_sample(filepath: str, n: int = 5) -> None:
    """Affiche un aperçu du dataset collecté."""
    with open(filepath, "r", encoding="utf-8") as f:
        ds = json.load(f)

    print("\n" + "═" * 60)
    print("  APERÇU DU DATASET — Top 5 par pertinence")
    print("═" * 60)
    for i, item in enumerate(ds["items"][:n], 1):
        print(f"\n[{i}] [{item['source_type'].upper()}] {item['title'][:70]}")
        print(f"    Score : {item['relevance_score']} | {item['url'][:60]}")
        print(f"    {item['summary'][:120]}…")
    print("\n" + "═" * 60)
    print(f"  Statistiques : {json.dumps(ds['statistics']['by_type'], ensure_ascii=False)}")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    agent = FerdaousAgent()
    output_file = agent.run()
    _print_sample(output_file)


# ─────────────────────────────────────────────
# 10.  GÉNÉRATEUR DE DONNÉES DE DÉMONSTRATION
# ─────────────────────────────────────────────

DEMO_DATA = [
    # ── GitHub ──────────────────────────────────────────────────────
    {"source":"microsoft/autogen","source_type":"github","title":"microsoft/autogen",
     "url":"https://github.com/microsoft/autogen","summary":"AutoGen is a framework enabling multi-agent LLM applications via automated agent conversations. Supports tool calling, code execution, RAG, and human-in-the-loop workflows.",
     "authors":["microsoft"],"tags":["llm","multi-agent","python","openai","autogen"],"published_at":"2024-02-10T00:00:00Z",
     "extra":{"stars":39800,"forks":5700,"language":"Python","open_issues":423}},
    {"source":"langchain-ai/langchain","source_type":"github","title":"langchain-ai/langchain",
     "url":"https://github.com/langchain-ai/langchain","summary":"Build context-aware reasoning applications with LangChain. Provides tools, chains, agents, and memory abstractions for LLMs.",
     "authors":["langchain-ai"],"tags":["llm","agents","rag","python","langchain"],"published_at":"2024-01-05T00:00:00Z",
     "extra":{"stars":95000,"forks":15600,"language":"Python","open_issues":1200}},
    {"source":"unslothai/unsloth","source_type":"github","title":"unslothai/unsloth",
     "url":"https://github.com/unslothai/unsloth","summary":"2-5x faster LLM fine-tuning with 70% less memory. Compatible with Llama 3, Mistral, Phi-3, Gemma and others.",
     "authors":["unslothai"],"tags":["fine-tuning","llm","mistral","llama","efficient"],"published_at":"2024-03-01T00:00:00Z",
     "extra":{"stars":22000,"forks":1500,"language":"Python","open_issues":88}},
    {"source":"oobabooga/text-generation-webui","source_type":"github","title":"oobabooga/text-generation-webui",
     "url":"https://github.com/oobabooga/text-generation-webui","summary":"A Gradio web UI for Large Language Models. Supports transformers, GPTQ, AWQ, llama.cpp, and many others.",
     "authors":["oobabooga"],"tags":["llm","inference","gradio","transformers"],"published_at":"2024-02-20T00:00:00Z",
     "extra":{"stars":41000,"forks":5300,"language":"Python","open_issues":300}},
    {"source":"meta-llama/llama3","source_type":"github","title":"meta-llama/llama3",
     "url":"https://github.com/meta-llama/llama3","summary":"The Meta Llama 3 collection of multilingual LLMs. State-of-the-art open source model family at 8B, 70B, and 405B parameters.",
     "authors":["meta-llama"],"tags":["llm","llama","open-source","meta"],"published_at":"2024-04-18T00:00:00Z",
     "extra":{"stars":28000,"forks":3000,"language":"Python","open_issues":250}},

    # ── arXiv ────────────────────────────────────────────────────────
    {"source":"arXiv","source_type":"arxiv","title":"ReAct: Synergizing Reasoning and Acting in Language Models",
     "url":"https://arxiv.org/abs/2210.03629","summary":"We present ReAct, a framework that combines reasoning and acting in language models. The agent generates reasoning traces and task-specific actions interleaved, allowing dynamic reasoning and tool use.",
     "authors":["Shunyu Yao","Jeffrey Zhao","Dian Yu","Nan Du"],"tags":["cs.AI","cs.CL"],"published_at":"2024-01-15T00:00:00Z",
     "extra":{"categories":["cs.AI","cs.CL"],"query_used":"LLM tool use"}},
    {"source":"arXiv","source_type":"arxiv","title":"Toolformer: Language Models Can Teach Themselves to Use Tools",
     "url":"https://arxiv.org/abs/2302.04761","summary":"We introduce Toolformer, a model trained to decide which APIs to call, when to call them, and how to incorporate results in future token prediction, achieving substantially improved zero-shot performance.",
     "authors":["Timo Schick","Jane Dwivedi-Yu","Roberto Dessì","Roberta Raileanu"],"tags":["cs.CL","cs.AI"],"published_at":"2024-02-01T00:00:00Z",
     "extra":{"categories":["cs.CL","cs.AI"],"query_used":"LLM tool use"}},
    {"source":"arXiv","source_type":"arxiv","title":"A Survey on Large Language Model based Autonomous Agents",
     "url":"https://arxiv.org/abs/2308.11432","summary":"Comprehensive survey of LLM-based autonomous agents covering their construction, applications, and evaluation. Reviews over 700 papers on planning, memory, tool use, and multi-agent cooperation.",
     "authors":["Lei Wang","Chen Ma","Xueyang Feng","Zeyu Zhang"],"tags":["cs.AI","cs.LG"],"published_at":"2024-03-10T00:00:00Z",
     "extra":{"categories":["cs.AI","cs.LG"],"query_used":"autonomous AI agents"}},
    {"source":"arXiv","source_type":"arxiv","title":"RAG vs Fine-tuning: Pipelines, Tradeoffs, and a Case Study on Agriculture",
     "url":"https://arxiv.org/abs/2401.08406","summary":"We compare retrieval-augmented generation and fine-tuning paradigms for adapting LLMs to domain-specific tasks, analyzing accuracy, cost, and inference latency across multiple settings.",
     "authors":["Angels Balaguer","Vinamra Benara","Renato Cunha"],"tags":["cs.AI","cs.LG","cs.IR"],"published_at":"2024-04-05T00:00:00Z",
     "extra":{"categories":["cs.AI","cs.LG"],"query_used":"retrieval augmented generation"}},
    {"source":"arXiv","source_type":"arxiv","title":"GPT-4 Technical Report",
     "url":"https://arxiv.org/abs/2303.08774","summary":"GPT-4 is a large-scale multimodal model which accepts image and text inputs and produces text outputs. The model exhibits human-level performance on various academic and professional benchmarks.",
     "authors":["OpenAI"],"tags":["cs.CL","cs.AI"],"published_at":"2024-01-20T00:00:00Z",
     "extra":{"categories":["cs.CL","cs.AI"],"query_used":"large language models agents"}},

    # ── RSS ──────────────────────────────────────────────────────────
    {"source":"Hugging Face Blog","source_type":"rss","title":"Introducing Llama 3.1: Our Most Capable Open Source LLM",
     "url":"https://huggingface.co/blog/llama31","summary":"Meta releases Llama 3.1, featuring 405B, 70B, and 8B parameter models. The 405B model rivals GPT-4 on several benchmarks while remaining fully open source.",
     "authors":[],"tags":["llama","open-source","meta","llm"],"published_at":"2024-07-23T10:00:00+00:00",
     "extra":{"feed_url":"https://huggingface.co/blog/feed.xml"}},
    {"source":"Towards Data Science","source_type":"rss","title":"Building Production-Ready RAG Applications",
     "url":"https://towardsdatascience.com/production-rag-applications","summary":"A comprehensive guide to building RAG pipelines in production, covering chunking strategies, embedding models, vector stores, reranking, and evaluation frameworks.",
     "authors":[],"tags":["rag","production","llm","vector-db"],"published_at":"2024-06-15T09:30:00+00:00",
     "extra":{"feed_url":"https://towardsdatascience.com/feed"}},
    {"source":"The Batch (DeepLearning.AI)","source_type":"rss","title":"Agentic AI: The Next Frontier in Automation",
     "url":"https://www.deeplearning.ai/the-batch/agentic-ai-frontier","summary":"Andrew Ng explores agentic AI workflows where LLMs autonomously plan, use tools, and execute multi-step tasks. Four key patterns: reflection, tool use, planning, and multi-agent collaboration.",
     "authors":[],"tags":["agentic","llm","automation","deeplearning"],"published_at":"2024-04-12T08:00:00+00:00",
     "extra":{"feed_url":"https://www.deeplearning.ai/the-batch/feed/"}},
    {"source":"Google AI Blog","source_type":"rss","title":"Gemini 1.5 Pro: Our Best Model to Date",
     "url":"https://blog.research.google/2024/02/gemini-15-pro.html","summary":"Gemini 1.5 Pro introduces a 1 million token context window, enabling unprecedented long-context understanding across text, video, audio, and code.",
     "authors":[],"tags":["gemini","google","llm","multimodal","context-window"],"published_at":"2024-02-15T12:00:00+00:00",
     "extra":{"feed_url":"https://blog.research.google/feeds/posts/default"}},

    # ── Hacker News ──────────────────────────────────────────────────
    {"source":"Hacker News","source_type":"hackernews","title":"Show HN: I built an open-source alternative to Devin AI",
     "url":"https://github.com/OpenDevin/OpenDevin","summary":"OpenDevin is an open-source AI software engineer capable of executing complex engineering tasks with natural language instructions. Discussion thread with 847 points.",
     "authors":["neubig"],"tags":["hacker news","ai","agents"],"published_at":"2024-04-02T16:30:00+00:00",
     "extra":{"hn_id":39876543,"score":847,"comments":312}},
    {"source":"Hacker News","source_type":"hackernews","title":"Mistral AI releases Mixtral 8x22B — Best open model yet",
     "url":"https://mistral.ai/news/mixtral-8x22b","summary":"Mistral AI open-sources Mixtral 8x22B, a sparse mixture-of-experts model outperforming LLaMA 2 70B on most benchmarks at lower inference cost.",
     "authors":["MistralAI"],"tags":["hacker news","mistral","llm","open-source"],"published_at":"2024-04-10T14:00:00+00:00",
     "extra":{"hn_id":39923456,"score":1203,"comments":445}},
    {"source":"Hacker News","source_type":"hackernews","title":"The unreasonable effectiveness of multi-agent systems",
     "url":"https://blog.langchain.dev/multi-agent-systems","summary":"LangChain blog post discussing architectures for multi-agent AI systems including orchestrator-subagent patterns, agent communication, and failure recovery strategies.",
     "authors":["hwchase17"],"tags":["hacker news","langchain","agents","multi-agent"],"published_at":"2024-05-01T11:00:00+00:00",
     "extra":{"hn_id":40134567,"score":654,"comments":189}},
    {"source":"Hacker News","source_type":"hackernews","title":"Claude 3 Opus beats GPT-4 on MMLU, HumanEval and others",
     "url":"https://www.anthropic.com/news/claude-3-family","summary":"Anthropic releases the Claude 3 model family. Opus sets new benchmarks in reasoning, coding, and multilingual tasks while improving safety alignment.",
     "authors":["anthropic_hq"],"tags":["hacker news","claude","anthropic","llm","benchmark"],"published_at":"2024-03-04T09:00:00+00:00",
     "extra":{"hn_id":39607890,"score":2341,"comments":789}},
]


def generate_demo_dataset() -> str:
    """
    Génère un dataset de démonstration réaliste
    (utile en environnement sans accès réseau ou pour les tests).
    """
    import hashlib

    log.info("═" * 60)
    log.info("   FERDAOUS — Mode Démonstration (données simulées)")
    log.info("═" * 60)

    now = datetime.now(timezone.utc).isoformat()

    items = []
    for d in DEMO_DATA:
        item = dict(d)
        item["id"]             = hashlib.md5((item["url"] + item["title"]).encode()).hexdigest()[:12]
        item["collected_at"]   = now
        item["relevance_score"]= _compute_relevance_score(item["title"] + " " + item["summary"])
        items.append(item)

    # Tri par pertinence
    items = sorted(items, key=lambda x: x["relevance_score"], reverse=True)

    stats = {"total": len(items), "by_type": {}, "by_source": {}, "top_tags": {}}
    for it in items:
        stats["by_type"][it["source_type"]] = stats["by_type"].get(it["source_type"], 0) + 1
        stats["by_source"][it["source"]]    = stats["by_source"].get(it["source"], 0) + 1
        for tag in it.get("tags", []):
            if tag:
                stats["top_tags"][tag] = stats["top_tags"].get(tag, 0) + 1
    stats["top_tags"] = dict(sorted(stats["top_tags"].items(), key=lambda x: x[1], reverse=True)[:20])

    dataset = {
        "metadata": {
            "agent":          "FERDAOUS — Agent Scout",
            "version":        "1.0.0",
            "mode":           "DEMO",
            "generated_at":   now,
            "project":        "Cellule Automatisée de Veille Technologique & Stratégique",
            "supervisors":    ["Pr. Hasnaa CHAABI", "Pr. Nadia IDRISSI Zouggari"],
            "sources_used":   ["GitHub API", "arXiv API", "RSS Feeds", "Hacker News"],
            "filter_keywords":CONFIG["filter_keywords"],
        },
        "statistics":  stats,
        "items":       items,
    }

    os.makedirs(CONFIG["output"]["directory"], exist_ok=True)
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename    = f"{CONFIG['output']['filename_prefix']}_demo_{timestamp}.json"
    filepath    = os.path.join(CONFIG["output"]["directory"], filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    log.info("DEMO dataset sauvegardé → %s", filepath)
    log.info("  Total : %d éléments | Par type : %s", stats["total"], stats["by_type"])
    log.info("═" * 60)

    return filepath


if __name__ == "__main__":
    import sys
    demo_mode = "--demo" in sys.argv or os.getenv("FERDAOUS_DEMO") == "1"
    if demo_mode:
        output_file = generate_demo_dataset()
    else:
        agent = FerdaousAgent()
        output_file = agent.run()
    _print_sample(output_file)