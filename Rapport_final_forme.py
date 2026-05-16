import markdown
import pdfkit
import os
import glob
import re

config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

# Prendre le rapport le plus récent
dossier = r"C:\Users\LENOVO\Desktop\4iiR\Semestre2\MSA\Projet\veille-sma-agentic\veille-sma-agentic\outputs\reports"
fichiers = glob.glob(os.path.join(dossier, "rapport_langgraph_*.md"))
fichier = max(fichiers, key=os.path.getmtime)

with open(fichier, "r", encoding="utf-8") as f:
    contenu = f.read()

# Nettoyer les lignes ====== (pas du vrai Markdown)
contenu = re.sub(r"={3,}", "", contenu)

# Transformer le header en vrai HTML propre
contenu = re.sub(
    r"📊 STRATEGIC TECHNOLOGY REPORT",
    "# 📊 Strategic Technology Report",
    contenu
)

# Convertir en HTML
html_body = markdown.markdown(contenu, extensions=["extra"])

html = f"""<html>
<head>
  <meta charset="utf-8">
  <title>Rapport Stratégique</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    body {{
      font-family: 'Inter', Segoe UI, sans-serif;
      max-width: 820px;
      margin: 0 auto;
      padding: 40px 30px;
      color: #1a1a2e;
      background: #fff;
    }}

    h1 {{
      font-size: 26px;
      font-weight: 700;
      color: #0f3460;
      border-bottom: 3px solid #0f3460;
      padding-bottom: 10px;
      margin-bottom: 6px;
    }}

    h2 {{
      font-size: 20px;
      font-weight: 600;
      color: #16213e;
      margin-top: 36px;
      margin-bottom: 12px;
      border-left: 4px solid #0f3460;
      padding-left: 10px;
    }}

    p {{
      font-size: 14px;
      line-height: 1.7;
      color: #333;
    }}

    ul, ol {{
      padding-left: 20px;
      margin: 10px 0;
    }}

    li {{
      font-size: 14px;
      margin: 6px 0;
      line-height: 1.6;
    }}

    /* Carte pour chaque trend */
    ol > li {{
      background: #f8f9ff;
      border: 1px solid #dde3f0;
      border-radius: 8px;
      padding: 12px 16px;
      margin: 10px 0;
      list-style-position: inside;
    }}

    strong {{
      color: #0f3460;
    }}

    hr {{
      border: none;
      border-top: 1px solid #dde3f0;
      margin: 30px 0;
    }}

    em {{
      color: #666;
      font-size: 13px;
    }}

    /* Badge décision */
    li:has(> *) {{
      position: relative;
    }}

    .header-block {{
      background: #0f3460;
      color: white;
      padding: 20px 24px;
      border-radius: 10px;
      margin-bottom: 30px;
    }}

    .header-block h1 {{
      color: white;
      border: none;
      margin: 0;
      font-size: 22px;
    }}

    .header-block p {{
      color: #aac4e8;
      margin: 4px 0 0;
      font-size: 13px;
    }}

    .stats {{
      display: flex;
      gap: 16px;
      margin: 20px 0;
    }}

    .stat {{
      flex: 1;
      text-align: center;
      padding: 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
    }}

    .stat.adopt {{ background: #e6f4ea; color: #2e7d32; }}
    .stat.monitor {{ background: #fff8e1; color: #f57f17; }}
    .stat.ignore {{ background: #fce4ec; color: #c62828; }}

    footer {{
      margin-top: 40px;
      padding-top: 16px;
      border-top: 1px solid #dde3f0;
      font-size: 12px;
      color: #999;
      text-align: center;
    }}
  </style>
</head>
<body>
{html_body}
<footer>Rapport généré automatiquement par le SMA Agentic AI — Équipe : HAJAR · FERDAOUS · KHADIJA · WAFAE</footer>
</body>
</html>"""

output_pdf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rapport.pdf")

options = {
    "encoding": "UTF-8",
    "page-size": "A4",
    "margin-top": "15mm",
    "margin-bottom": "15mm",
    "margin-left": "15mm",
    "margin-right": "15mm",
}

pdfkit.from_string(html, output_pdf, configuration=config, options=options)
print(f"✅ PDF généré : {{output_pdf}}")
os.startfile(output_pdf)