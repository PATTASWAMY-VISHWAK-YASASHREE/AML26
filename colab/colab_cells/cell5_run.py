# SECTION 5 - run
# -----------------------------------------------------------------------------
t0 = time.time()
summary = ER.run(work_dir=WORK_DIR, dataset_dir=str(DATASET_DIR),
                 spill_dir=SPILL_DIR)
print(f"\ntotal {time.time() - t0:.0f}s")

print()
print("=" * 70)
print("blocking recall ceiling :", summary["blocking_recall"])
print("decision threshold      :", round(summary["threshold"], 4))
print("test S1 entities        :", summary["test_s1_entities"])
print("test target entities    :", summary["test_target_entities"])
print("=" * 70)

from google.colab import files
zip_path = Path(WORK_DIR) / "submission.zip"
print("submission:", zip_path, f"({zip_path.stat().st_size / 2**20:.1f} MB)")
files.download(str(zip_path))
