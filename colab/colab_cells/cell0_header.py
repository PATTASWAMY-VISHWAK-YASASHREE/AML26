# =============================================================================
#  AMAZON ML CHALLENGE 2026  -  BUSINESS ENTITY RESOLUTION
#  Single-cell Google Colab notebook (DuckDB, fully out-of-core)
#
#  FIXES THE OOM in stage_candidates that killed the previous run. Three
#  independent changes do it:
#    1. Each blocking channel is now its own COPY that streams to disk, instead
#       of all 7 being UNION ALL-ed into one query that had to hold every
#       channel's join output at the same time.
#    2. Every channel projects only the columns it uses. The old code did
#       SELECT *, pulling the token-list columns through all ~10M target rows
#       on every single join.
#    3. max_temp_directory_size is set. Without it DuckDB refuses to spill and
#       raises OutOfMemoryError instead of writing to disk - the exact failure
#       you hit: "could not allocate block of size 256.0 KiB (5.5 GiB/5.5 GiB)".
#  The per-channel cap is provably identical to the old behaviour: the final
#  answer is the top max_candidates per S1 ordered by (priority, tid), and
#  priority is constant within a channel, so nothing that survives the final
#  cap can have been dropped by capping a channel early.
#
#  HOW TO USE
#    1. Runtime > Change runtime type. A GPU is NOT needed, but a HIGH-RAM
#       runtime (Pro) makes the run substantially faster.
#    2. Paste this whole cell and Run. Authorise the Drive mount.
#    3. Re-runs are cheap: each stage is cached by a config fingerprint, so a
#       second run skips normalisation and only redoes what you changed.
#    4. submission.zip downloads automatically at the end.
#
#  IF IT STILL OOMs, edit ER.CFG.update(...) in SECTION 4, in this order:
#    max_candidates 30 -> 15      (biggest single lever; small recall cost)
#    max_token_df   5000 -> 2000  (shrinks the rare-token posting table)
#    memory_limit   "6GB" -> "4GB"
# =============================================================================

# -----------------------------------------------------------------------------
