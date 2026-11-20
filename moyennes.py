import datetime as dt
import json
import os
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

DATABASE_ID = "41e864f0-8119-8054-be00-d06839d4c5ec"
DATA_SOURCE_ID = "41e864f0-8119-8020-9dc3-000b25738681"
NOTION_VERSIONS = ("2025-09-03", "2022-06-28")
PARIS = ZoneInfo("Europe/Paris")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moyennes CNED</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
html,body{margin:0;min-height:100%;font-family:sans-serif;background:#fff;color:#172033}
#w{max-width:900px;margin:auto;padding:20px;box-sizing:border-box}
#chart{height:min(70vh,620px)}
.note{margin:0 0 16px;color:#526070;font-size:.95rem}
#empty{color:#526070}
#m{color:#697586;font-size:.85rem;text-align:right}
</style></head>
<body><main id="w">
<h1>Moyennes des matières</h1>
<p class="note">Calcul non pondéré : la moyenne générale est la moyenne des moyennes
des matières, avec un poids égal entre matières. Ce résultat est indicatif et ne
constitue pas une moyenne officielle du bac.</p>
<p id="empty"></p><div id="chart"><canvas id="c"></canvas></div><p id="m"></p>
</main>
<script>
const D = __DATA__;
document.getElementById('m').textContent = 'Mis à jour le ' + D.updated_at;
if (!D.labels.length) {
  document.getElementById('empty').textContent = 'Aucune note valide à afficher.';
  document.getElementById('chart').hidden = true;
}
new Chart(document.getElementById('c'), {
  type: 'bar',
  data: {labels: D.labels, datasets: [{
    label: 'Moyenne sur 20', data: D.values,
    backgroundColor: D.labels.map((label, i) =>
      i === D.labels.length - 1 ? '#f59e0b' : '#2563eb')
  }]},
  options: {indexAxis: 'y', responsive: true, maintainAspectRatio: false,
    scales: {x: {min: 0, max: 20, title: {display: true, text: 'Note sur 20'}}},
    plugins: {legend: {display: false},
      tooltip: {callbacks: {label: item => item.raw.toFixed(2) + ' / 20'}}}}
});
</script></body></html>
"""


def _property_text(property_value):
    values = property_value.get("title") or property_value.get("rich_text") or []
    return "".join(item.get("plain_text", "") for item in values).strip()


def _property_number(property_value):
    value = property_value.get("number")
    if value is None:
        return None
    return float(value)


def valid_score(value):
    return value is not None and value == value and value not in (float("inf"), float("-inf")) and 0 <= value <= 20


def calculate_averages(rows):
    scores = defaultdict(list)
    for row in rows:
        properties = row.get("properties", {})
        subject = _property_text(properties.get("Enseignement", {}))
        score = _property_number(properties.get("Note obtenue", {}))
        if subject and valid_score(score):
            scores[subject].append(score)
    subject_averages = {
        subject: sum(values) / len(values)
        for subject, values in sorted(scores.items(), key=lambda item: item[0].casefold())
    }
    overall = sum(subject_averages.values()) / len(subject_averages) if subject_averages else None
    return subject_averages, overall


def query_notion(token, url, version):
    import requests

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": version,
        "Content-Type": "application/json",
    }
    rows = []
    cursor = None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        response = requests.post(url, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if "results" not in payload:
            raise RuntimeError(f"Réponse Notion invalide : {payload}")
        rows.extend(payload["results"])
        if not payload.get("has_more"):
            return rows
        cursor = payload.get("next_cursor")
        if not cursor:
            raise RuntimeError("Réponse Notion invalide : curseur manquant")


def fetch_rows(token):
    import requests

    errors = []
    endpoints = (
        f"https://api.notion.com/v1/data_sources/{DATA_SOURCE_ID}/query",
        f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
    )
    for url in endpoints:
        for version in NOTION_VERSIONS:
            try:
                return query_notion(token, url, version)
            except requests.RequestException as error:
                errors.append(f"{url} ({version}): {error}")
            except RuntimeError as error:
                errors.append(f"{url} ({version}): {error}")
    raise RuntimeError("Impossible de lire la base Notion : " + " | ".join(errors))


def render_html(subject_averages, overall, updated_at):
    labels = list(subject_averages) + (["Moyenne générale"] if overall is not None else [])
    values = list(subject_averages.values()) + ([overall] if overall is not None else [])
    payload = {
        "labels": labels,
        "values": [round(value, 2) for value in values],
        "updated_at": updated_at,
    }
    return HTML_TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False))


def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise SystemExit("NOTION_TOKEN est requis")
    rows = fetch_rows(token)
    subject_averages, overall = calculate_averages(rows)
    updated_at = dt.datetime.now(PARIS).strftime("%d/%m/%Y %H:%M")
    Path("moyennes.html").write_text(
        render_html(subject_averages, overall, updated_at), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
