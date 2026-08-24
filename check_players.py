import gzip
import io
import sqlite3
import sys
import zipfile

import pandas as pd

sys.path.insert(0, "backend")
from app.text import normalize  # noqa: E402

z = zipfile.ZipFile(r"C:\Users\Ivan\AppData\Local\Temp\la-caprichosa\transfermarkt-datasets.zip")

p = pd.read_csv(io.BytesIO(gzip.decompress(z.read("players.csv.gz"))), low_memory=False)
t = pd.read_csv(io.BytesIO(gzip.decompress(z.read("transfers.csv.gz"))), low_memory=False)

for target in ["Santiago Silva", "Cristian Lema"]:
    print(f"\n=== {target} ===")
    hits = p[p["name"].str.contains(target.split()[1], case=False, na=False) & p["name"].str.contains(target.split()[0], case=False, na=False)]
    print(hits[["player_id", "name", "position", "current_club_name"]].to_string(index=False))
    for pid in hits["player_id"]:
        tr = t[t["player_id"] == pid]
        cols = ["transfer_date", "from_club_name", "to_club_name"]
        print(tr[cols].to_string(index=False) if len(tr) else "  (sin transfers)")

# ¿qué jugadores argentinos importantes hay en transfers hacia clubes AR?
print("\n=== llegadas a clubes AR por año (total) ===")
clubs = pd.read_csv(io.BytesIO(gzip.decompress(z.read("clubs.csv.gz"))), low_memory=False)
arg_ids = set(clubs.loc[clubs["domestic_competition_id"] == "ARG1", "club_id"].astype(int))
games = pd.read_csv(io.BytesIO(gzip.decompress(z.read("games.csv.gz"))), low_memory=False, usecols=["competition_id", "home_club_id", "away_club_id"])
hist = games.loc[games["competition_id"] == "ARG1"]
arg_ids |= set(hist["home_club_id"].dropna().astype(int)) | set(hist["away_club_id"].dropna().astype(int))

t_arg = t[t["to_club_id"].isin(arg_ids)].copy()
t_arg["year"] = pd.to_datetime(t_arg["transfer_date"]).dt.year
print(t_arg.groupby(t_arg["year"] // 5 * 5).size())

conn = sqlite3.connect("backend/data/futbol_argentino.db")
db_names = {r[0] for r in conn.execute("SELECT norm FROM players")}
for target in ["Santiago Silva", "Cristian Lema"]:
    print(f"{target} en DB:", normalize(target) in db_names)
