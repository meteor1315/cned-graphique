import os, datetime as dt
import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

TOKEN = os.environ["NOTION_TOKEN"]
DB_ID = "41d864f08119809e816ff62d2fb69b71"
DS_ID = "41d864f0-8119-8076-908f-000bc63760bd"


def query(url, version):
    h = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": version,
         "Content-Type": "application/json"}
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(url, headers=h, json=body).json()
        if "results" not in r:
            return None, r
        rows += r["results"]
        if not r.get("has_more"):
            return rows, None
        cursor = r["next_cursor"]


rows, err = query(f"https://api.notion.com/v1/databases/{DB_ID}/query", "2022-06-28")
if rows is None:
    rows, err2 = query(f"https://api.notion.com/v1/data_sources/{DS_ID}/query", "2025-09-03")
    if rows is None:
        raise SystemExit(f"Erreur Notion : {err} / {err2}")


def txt(p):
    arr = p.get("title") or p.get("rich_text") or []
    return "".join(t["plain_text"] for t in arr).strip()


def num(s):
    try:
        return float(s.replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


data = []
for row in rows:
    p = row["properties"]
    d = txt(p["Date"])
    try:
        date = dt.datetime.strptime(d, "%d/%m/%Y")
    except ValueError:
        continue
    data.append({"date": date,
                 "attendus": num(txt(p["Devoirs attendus"])),
                 "rendus": num(txt(p["Devoirs rendus"]))})

df = pd.DataFrame(data).sort_values("date").reset_index(drop=True)
df["att_cum"] = df["attendus"].fillna(0).cumsum()
df["ren_cum"] = df["rendus"].fillna(0).cumsum()
derniere = df["rendus"].last_valid_index()
ren = df.loc[:derniere] if derniere is not None else df.iloc[0:0]
print(df)

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(df["date"], df["att_cum"], marker="o", color="#3b82f6", label="Attendus cumulés")
ax.plot(ren["date"], ren["ren_cum"], marker="o", color="#22c55e", label="Rendus cumulés")
ax.axvline(dt.datetime.now(), ls="--", color="gray", label="Aujourd'hui")
ax.set_title("Progression des devoirs CNED")
ax.set_ylabel("Nombre de devoirs")
ax.grid(alpha=0.3)
ax.legend()
ax.set_xticks(list(df["date"]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
fig.tight_layout()
fig.savefig("progression_devoirs.png", dpi=150)
