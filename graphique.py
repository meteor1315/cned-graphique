import os, json, datetime as dt
import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

TOKEN = os.environ["NOTION_TOKEN"]
DB_ID = "41d864f08119809e816ff62d2fb69b71"
DS_ID = "41d864f0-8119-8076-908f-000bc63760bd"

HTML = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Progression des devoirs CNED</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>html,body{margin:0;height:100%;font-family:sans-serif;background:#fff}
#w{position:relative;height:100vh;padding:8px;box-sizing:border-box}
#m{position:absolute;right:12px;bottom:4px;font-size:11px;color:#888}</style></head>
<body><div id="w"><canvas id="c"></canvas><div id="m"></div></div>
<script>
const D = __DATA__;
document.getElementById('m').textContent = 'Mis à jour le ' + D.maj;
const today = {id:'today', afterDraw(ch){
  const x=ch.scales.x, y=ch.scales.y, t=Date.now(); let i=-1;
  for(let k=0;k<D.ts.length-1;k++){ if(t>=D.ts[k] && t<=D.ts[k+1]){ i=k; break; } }
  if(i<0) return;
  const a=x.getPixelForValue(i), b=x.getPixelForValue(i+1);
  const p=a+(t-D.ts[i])/(D.ts[i+1]-D.ts[i])*(b-a), c=ch.ctx;
  c.save(); c.setLineDash([6,4]); c.strokeStyle='gray'; c.beginPath();
  c.moveTo(p,y.top); c.lineTo(p,y.bottom); c.stroke();
  c.fillStyle='gray'; c.fillText("Aujourd'hui", p+4, y.top+12); c.restore();
}};
new Chart(document.getElementById('c'), {
  type:'line',
  data:{labels:D.labels, datasets:[
    {label:'Attendus cumulés', data:D.att, borderColor:'#3b82f6', backgroundColor:'#3b82f6', pointRadius:4, tension:0},
    {label:'Rendus cumulés', data:D.ren, borderColor:'#22c55e', backgroundColor:'#22c55e', pointRadius:4, tension:0, spanGaps:false}
  ]},
  options:{responsive:true, maintainAspectRatio:false,
    plugins:{title:{display:true, text:'Progression des devoirs CNED', font:{size:16}}},
    scales:{y:{beginAtZero:true, title:{display:true, text:'Nombre de devoirs'}}}},
  plugins:[today]
});
</script></body></html>
"""


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

payload = {
    "labels": [d.strftime("%d/%m/%y") for d in df["date"]],
    "ts": [int(d.timestamp() * 1000) for d in df["date"]],
    "att": [float(v) for v in df["att_cum"]],
    "ren": [float(v) for v in ren["ren_cum"]] + [None] * (len(df) - len(ren)),
    "maj": dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
}
with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML.replace("__DATA__", json.dumps(payload)))

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
