"""Extract the OSAP wide CSV and convert to column-selectable parquet (streaming)."""
import zipfile, time
from pathlib import Path
import polars as pl
OUT = Path(__file__).resolve().parents[1] / "data" / "osap"
zp = OUT / "signed_predictors_dl_wide.zip"
csvp = OUT / "signed_predictors_dl_wide.csv"
pqp = OUT / "firm_char.parquet"
if not csvp.exists():
    t = time.time(); print("extracting 8.35 GB ...", flush=True)
    with zipfile.ZipFile(zp) as z:
        z.extract("signed_predictors_dl_wide.csv", OUT)
    print(f"  extracted in {time.time()-t:.0f}s", flush=True)
t = time.time(); print("csv -> parquet (streaming) ...", flush=True)
(pl.scan_csv(csvp, infer_schema_length=10000, ignore_errors=True)
   .sink_parquet(pqp, compression="zstd"))
print(f"  parquet written in {time.time()-t:.0f}s -> {pqp}", flush=True)
lf = pl.scan_parquet(pqp)
print("rows:", lf.select(pl.len()).collect().item(), "cols:", len(lf.collect_schema().names()), flush=True)
csvp.unlink(missing_ok=True); print("removed intermediate csv", flush=True)
