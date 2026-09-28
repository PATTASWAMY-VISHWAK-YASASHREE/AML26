"""Train the stage-2 acceptance model on the T subset, evaluate on the V subset.

usage: python train_stage2.py <work_dir>
needs: work/predT.parquet, work/predV.parquet (stage-1 scores), feat parts, qT, val_s1, T_s1
"""
import sys, glob, json, time
import numpy as np
import polars as pl
import lightgbm as lgb
import stage2
from train import read_part
from metrics import macro_f05

W = sys.argv[1]
S1_FEATS = json.load(open(f"{W}/model_stage1.json"))["cols"]


def best_with_feats(pred_path, part_prefix, qtext, s1dups):
    pred = pl.read_parquet(pred_path)
    cf = pl.concat([read_part(p).select("rid", "s1", "a_tset", "nf_tset") for p in sorted(glob.glob(f"{W}/feat/{part_prefix}_part*.parquet"))])
    b = stage2.build(pred.select("rid", "s1", "p1"), qtext, cf, s1dups)
    del cf
    keys = b.select("rid", "s1")
    fs = []
    for p in sorted(glob.glob(f"{W}/feat/{part_prefix}_part*.parquet")):
        fs.append(read_part(p).join(keys, on=["rid", "s1"]))
    f = pl.concat(fs)
    return b.join(f.drop([c for c in ("p",) if c in f.columns]), on=["rid", "s1"], how="left")


def s2_cols(df):
    drop = {"rid", "s1", "label", "true_s1", "brank", "src"}
    return [c for c in df.columns if c not in drop]


if __name__ == "__main__":
    t0 = time.time()
    qt_cols = ["rid", "entity_id", "ncore", "atoks", "anums"]
    qT = pl.read_parquet(f"{W}/qT.parquet")
    s1T = pl.read_parquet(f"{W}/T_s1.parquet"); s1V = pl.read_parquet(f"{W}/val_s1.parquet")
    predV = pl.read_parquet(f"{W}/predV.parquet")
    qV = predV.select("rid").unique()
    qtext = pl.scan_parquet(f"{W}/train_q.parquet").select(qt_cols).join(pl.concat([qT, qV]).unique().lazy(), on="rid").collect()
    s1dups = stage2.s1_duplicates(pl.read_parquet(f"{W}/train_s1.parquet", columns=["rid", "country", "ncore", "atoks"]))
    T = best_with_feats(f"{W}/predT.parquet", "train_T", qtext, s1dups)
    V = best_with_feats(f"{W}/predV.parquet", "train_val", qtext, s1dups)
    print("built", T.height, V.height, f"{time.time()-t0:.0f}s", flush=True)
    gt_all = pl.read_parquet(f"{W}/train_gt_pairs.parquet").rename({"true_s1": "s1"})
    qT_ = qT
    Tt = T.join(s1T, on="s1")
    Vv = V.join(s1V, on="s1")
    cols = s2_cols(Tt)
    params = dict(objective="binary", learning_rate=0.03, num_leaves=63, min_data_in_leaf=100, feature_fraction=0.7,
                  bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, num_threads=2, verbose=-1)
    ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 800

    def fit(df):
        df = df.filter(pl.col("p1") >= 0.02)
        return lgb.train(params, lgb.Dataset(df.select(cols).to_numpy().astype(np.float32), label=df["label"].to_numpy()), num_boost_round=ROUNDS)

    # cross-fitting: model on T scores V, model on V scores T (training rows exclude queries of the other subset)
    mT = fit(Tt.join(qV, on="rid", how="anti"))
    mV = fit(Vv.join(qT, on="rid", how="anti"))
    Vv = Vv.with_columns(pl.Series("p2", mT.predict(Vv.select(cols).to_numpy().astype(np.float32))))
    Tt = Tt.with_columns(pl.Series("p2", mV.predict(Tt.select(cols).to_numpy().astype(np.float32))))
    Vv.select("rid", "s1", "p1", "p2", "label").write_parquet(f"{W}/val_pred_stage2.parquet")
    Tt.select("rid", "s1", "p1", "p2", "label").write_parquet(f"{W}/T_pred_stage2.parquet")
    res = {}
    for col in ("p1", "p2"):
        rows = []
        for thr in np.arange(0.3, 0.96, 0.025):
            fv = macro_f05(Vv.filter(pl.col(col) >= thr).select("s1", "rid"), gt_all.join(s1V, on="s1"), s1V)
            ft = macro_f05(Tt.filter(pl.col(col) >= thr).select("s1", "rid"), gt_all.join(s1T, on="s1"), s1T)
            rows.append(((fv * s1V.height + ft * s1T.height) / (s1V.height + s1T.height), fv, ft, float(thr)))
        best = max(rows)
        print(col, "BEST pooled=%.5f V=%.5f T=%.5f thr=%.3f" % best, flush=True)
        res[col] = best
    # final model on both subsets
    m = fit(pl.concat([Tt.drop("p2"), Vv.drop("p2")], how="diagonal_relaxed"))
    m.save_model(f"{W}/model_stage2.txt")
    imp = sorted(zip(cols, m.feature_importance("gain")), key=lambda x: -x[1])
    print([(c, int(g)) for c, g in imp[:25]])
    json.dump({"cols": cols, "thr": res["p2"][3], "cv_f05": res["p2"][0], "val_f05": res["p2"][1], "cv_f05_stage1": res["p1"][0]}, open(f"{W}/model_stage2.json", "w"))
    print(f"{time.time()-t0:.0f}s")
