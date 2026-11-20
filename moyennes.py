import json
import math
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


DB_ID = "41e864f0-8119-8054-be00-d06839d4c5ec"
DS_ID = "41e864f0-8119-8020-9dc3-000b25738681"
NOTION_VERSION = "2025-09-03"
OUTPUT = "moyennes.html"

HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Moyennes par matière</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
  <style>
    html, body { margin: 0; min-height: 100%; font-family: sans-serif; background: #fff; }
    #w { width: 100%; max-width: 900px; min-height: 420px; margin: 0 auto; padding: 12px; box-sizing: border-box; }
    #chart-wrap { position: relative; height: min(70vh, 620px); min-height: 360px; }
    #notice { color: #444; font-size: 13px; line-height: 1.45; }
    #m { color: #777; font-size: 11px; text-align: right; }
  </style>
</head>
<body>
  <div id="w">
    <h1>Moyennes par matière</h1>
    <p id="notice">Calcul non pondéré : moyenne arithmétique des notes de chaque matière, puis moyenne générale des moyennes par matière à poids égaux. Ce calcul ne constitue pas une moyenne officielle du bac.</p>
    <div id="chart-wrap"><canvas id="c"></canvas></div>
    <div id="m"></div>
  </div>
  <script>
    const D = __DATA__;
    document.getElementById('m').textContent = 'Mis à jour le ' + D.maj;
    new Chart(document.getElementById('c'), {
      type: 'bar',
      data: {
        labels: D.labels,
        datasets: [{
          label: 'Moyenne',
          data: D.values,
          backgroundColor: D.colors
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: { display: true, text: 'Moyennes par matière', font: { size: 16 } },
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => ctx.raw.toFixed(2) } }
        },
        scales: {
          x: { beginAtZero: true, min: 0, max: 20, title: { display: true, text: 'Note sur 20' } }
        }
      },
      plugins: [{
        id: 'values',
        afterDatasetsDraw(chart) {
          const ctx = chart.ctx;
          ctx.save();
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.font = '12px sans-serif';
          ctx.fillStyle = '#111';
          chart.getDatasetMeta(0).data.forEach((bar, i) => {
            ctx.fillText(chart.data.datasets[0].data[i].toFixed(2), bar.x + 6, bar.y);
          });
          ctx.restore();
        }
      }]
    });
  </script>
</body>
</html>
"""


def notion_text(prop):
    if not isinstance(prop, dict):
        return ""
    items = prop.get("title") or prop.get("rich_text") or []
    if not isinstance(items, list):
        return ""
    return "".join(item.get("plain_text", "") for item in items).strip()


def valid_grade(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value) or value < 0 or value > 20:
        return None
    return value


def calculate_averages(rows):
    grades_by_subject = {}
    for row in rows:
        properties = row.get("properties", {})
        subject = notion_text(properties.get("Enseignement"))
        if not subject:
            continue
        grade_prop = properties.get("Note obtenue")
        grade = valid_grade(grade_prop.get("number") if isinstance(grade_prop, dict) else None)
        if grade is None:
            continue
        grades_by_subject.setdefault(subject, []).append(grade)

    subject_averages = {
        subject: sum(grades) / len(grades)
        for subject, grades in sorted(grades_by_subject.items(), key=lambda item: item[0].casefold())
        if grades
    }
    if not subject_averages:
        return None
    general = sum(subject_averages.values()) / len(subject_averages)
    return subject_averages, general


def query_notion(token):
    headers = {
        "Authorization": "Bearer " + token,
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    endpoints = (
        f"https://api.notion.com/v1/data_sources/{DS_ID}/query",
        f"https://api.notion.com/v1/databases/{DB_ID}/query",
    )
    last_error = None
    for endpoint in endpoints:
        rows = []
        cursor = None
        try:
            while True:
                body = {"page_size": 100}
                if cursor:
                    body["start_cursor"] = cursor
                response = requests.post(endpoint, headers=headers, json=body, timeout=30)
                if not response.ok:
                    last_error = "Réponse API non valide"
                    break
                payload = response.json()
                if not isinstance(payload, dict) or "results" not in payload:
                    last_error = "Réponse API incomplète"
                    break
                rows.extend(payload["results"])
                if not payload.get("has_more"):
                    return rows, None
                cursor = payload.get("next_cursor")
                if not cursor:
                    last_error = "Pagination API incomplète"
                    break
        except (requests.RequestException, ValueError):
            last_error = "Erreur de communication avec l'API"
    return None, last_error or "Erreur API"


def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Erreur: secret NOTION_TOKEN indisponible", file=sys.stderr)
        return 1

    rows, error = query_notion(token)
    if error:
        print("Erreur Notion: impossible de récupérer les données", file=sys.stderr)
        return 1

    averages = calculate_averages(rows)
    if averages is None:
        print("Aucune note valide disponible: moyennes.html n'a pas été écrasée", file=sys.stderr)
        return 0

    subject_averages, general = averages
    subjects = list(subject_averages)
    values = [subject_averages[subject] for subject in subjects]
    subjects.append("Moyenne générale")
    values.append(general)

    payload = {
        "labels": subjects,
        "values": [round(value, 2) for value in values],
        "colors": ["#3b82f6"] * (len(subjects) - 1) + ["#f97316"],
        "maj": datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y %H:%M"),
    }
    temp_output = OUTPUT + ".tmp"
    with open(temp_output, "w", encoding="utf-8") as output:
        output.write(HTML.replace("__DATA__", json.dumps(payload, ensure_ascii=False)))
    os.replace(temp_output, OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
