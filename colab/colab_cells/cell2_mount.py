# SECTION 2 - mount Drive, locate the dataset
# -----------------------------------------------------------------------------
import os
import sys
import shutil
import time
from pathlib import Path

# TWO directories with OPPOSITE requirements - do not merge them:
#   WORK_DIR  durable cache (parquet shards). On Drive, so a pre-empted Colab
#             session resumes rather than redoing the ~10 min normalisation.
#   SPILL_DIR DuckDB overflow blocks. On /content: local disk is faster and far
#             larger. Putting spill on Drive fills the quota and then fails with
#             "failed to offload data block ... max_temp_directory_size".
WORK_DIR = "/content/drive/MyDrive/er_run"
SPILL_DIR = "/content/er_spill"
Path(WORK_DIR).mkdir(parents=True, exist_ok=True)
Path(SPILL_DIR).mkdir(parents=True, exist_ok=True)

FOLDER_ID = "1ZXJ6FXwsYcchoKQNjdQb_yNgNAJik6LA"
DATASET_DIR = Path("/content/drive/MyDrive/student_resource")

from google.colab import drive
drive.mount("/content/drive", force_remount=True)


def resolve_dataset_dir(base: Path) -> Path:
    """Find the dataset root, tolerating an extra level of nesting."""
    if (base / "dataset" / "train" / "train_source1.tsv").exists():
        return base
    for p in base.rglob("train_source1.tsv"):
        return p.parent.parent.parent
    raise FileNotFoundError(
        f"No train_source1.tsv under {base}. Check the Drive folder name.")


DATASET_DIR = resolve_dataset_dir(DATASET_DIR)
print("dataset   :", DATASET_DIR)
print("folder id :", FOLDER_ID)
for name, d in (("cache", WORK_DIR), ("spill", SPILL_DIR)):
    u = shutil.disk_usage(d)
    print(f"{name:>10} : {d}  ({u.free / 2**30:.1f} GB free)")

# -----------------------------------------------------------------------------
