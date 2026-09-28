# Colab cells - run in this order

cell0_header.py      35 lines    2,099 B   Banner: OOM tuning order + 'GPU not needed' note.
cell1_deps.py       5 lines      235 B   Install dependencies. Fast, safe to re-run.
cell2_mount.py      44 lines    1,811 B   Mount Drive and locate the dataset.
cell3_pipeline_module.py    1005 lines   48,188 B   The pipeline module (single raw string - do not split).
cell4_config.py      45 lines    2,424 B   Configuration. EDIT THIS to tune for your runtime.
cell5_run.py      19 lines      768 B   Run the pipeline end to end.

Total across cells: 1153 lines (55,525 B)

Cells 2-5 share one namespace, so run them top to bottom in a
single Colab session. cell2 defines WORK_DIR / SPILL_DIR /
DATASET_DIR; cell3 defines ER; cell4 and cell5 consume both.
