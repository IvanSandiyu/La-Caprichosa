import io, gzip, zipfile, os, tempfile
import pandas as pd

zip_path = os.path.join(tempfile.gettempdir(), "la-caprichosa", "transfermarkt-datasets.zip")
with zipfile.ZipFile(zip_path) as z:
    def read(bn):
        nm = [n for n in z.namelist() if n.endswith(bn)][0]
        return pd.read_csv(io.BytesIO(gzip.decompress(z.read(nm))), low_memory=False)

    clubs = read("clubs.csv.gz")
    transfers = read("transfers.csv.gz")

print("--- transfers columns ---")
for c in transfers.columns:
    print("  ", c)

print("\n--- ejemplos transfers de/para clubes AR (muestra) ---")
# nombres que contienen u20/b/reserva/ii
res = clubs[clubs["name"].astype(str).str.contains("U20|U21|Reserva|Reserve|II|B T", case=False, na=False) & clubs.get("domestic_competition_id", pd.Series()).isna() | clubs["name"].astype(str).str.contains("U20|Reserva", case=False, na=False)]
print("clubes con U20/Reserva en nombre:", len(res))
for _, r in res.head(15).iterrows():
    print("   ", r["club_id"], "|", r["name"])
