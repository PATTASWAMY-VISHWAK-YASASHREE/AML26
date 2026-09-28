"""Score feature parts with the stage-1 model.  usage: predict_stage1.py <work_dir> <part_prefix> <out.parquet>"""
import sys, glob, json, time
import numpy as np
import polars as pl
import lightgbm as lgb
from train import read_part

W, prefix, out = sys.argv[1], sys.argv[2], sys.argv[3]
meta = json.load(open(f"{W}/model_stage1.json"))
cols = meta["cols"]
m = lgb.Booster(model_file=f"{W}/model_stage1.txt")
t0 = time.time()
res = []
parts = sorted(glob.glob(f"{W}/feat/{prefix}_part*.parquet"))
for i, p in enumerate(parts):
    d = read_part(p)
    keep = ["rid", "s1"] + (["label"] if "label" in d.columns else [])
    res.append(d.select(keep).with_columns(pl.Series("p1", m.predict(d.select(cols).to_numpy().astype(np.float32), num_threads=2)).cast(pl.Float32)))
    if i % 10 == 0:
        print(f"  {i+1}/{len(parts)} {time.time()-t0:.0f}s", flush=True)
pl.concat(res).write_parquet(out)
print("done", out, f"{time.time()-t0:.0f}s")
