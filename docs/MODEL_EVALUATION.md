# Model Evaluation

This document describes the evaluation pipeline for the beer recommender system: how
data is split, how leakage is prevented, which metrics are reported, and how to run and
interpret the evaluation. It is intended as a reference for developers working on the
project.

The system evaluates three models:

1. **CF** — Collaborative Filtering (SVD latent factors), pure latent-factor predictions.
2. **CB** — Content-Based, cosine similarity from a user profile to item features.
3. **Hybrid** — a weighted blend (60% CF + 40% CB) over beers known to both pipelines.

---

## 1. How the Data Is Split

The system uses a **temporal, per-user, leave-last-1 split** into Train / Validation /
Test.

- **Implementation:** `data_processing/pipeline.py`, function `execute_final_split()`
- Each user's reviews are sorted chronologically by `review_time` (a UNIX timestamp).
- For each user:
  - **Last (most recent) review** → Test set
  - **Second-to-last review** → Validation set
  - **All earlier reviews** → Training set
- **Guardrail:** Only users with **≥ 3 reviews** (`MIN_REVIEWS_FOR_SPLIT = 3`) are split.
  Users with fewer reviews are placed entirely into the training set, so every held-out
  user still has training history.
- **Approximate split ratio:** ~94.6% train / ~0.6% validation / ~0.6% test. The split
  is heavily skewed toward training because each eligible user contributes at most one row
  to validation and one to test, regardless of how many reviews they have.

**Output files:**

| File | Contents |
|------|----------|
| `train_set_enriched.csv` | All training reviews |
| `val_set_enriched.csv` | One held-out review per eligible user |
| `test_set_enriched.csv` | One held-out (most recent) review per eligible user |

### Why temporal splitting matters

A recommender in production only ever sees a user's **past** behavior and must predict
their **future** preferences. Temporal splitting reproduces this: the model trains on
older reviews and is scored on each user's most recent one.

A random split would let earlier-in-time information leak through the test set — the model
could effectively "see the future" by training on reviews that occurred *after* the ones
it is being asked to predict. That inflates offline metrics and produces a model that
looks better in evaluation than it performs in production. Temporal splitting avoids this.

---

## 2. How Data Leakage Is Prevented

Every learned component is derived **only** from the training set. The table below lists
each safeguard.

| Component | Safeguard |
|-----------|-----------|
| **Rating matrix (CF)** | Built exclusively from `train_set_enriched.csv`. |
| **User mean centering (CF)** | Per-user means computed from training ratings only. |
| **SVD factorization (CF)** | Trained on the centered training matrix only. |
| **Item rating statistics (CB)** | Aggregated from training data only (e.g. `avg_overall_rating`, `total_reviews_count`). |
| **Review text / TF-IDF (CB)** | `all_reviews_text` is concatenated from training reviews only; the TF-IDF vocabulary is learned from that text. |
| **User profiles (CB)** | Built from training ratings and training item features only. |
| **Static metadata** | Beer name, style, and ABV come from the full dataset. This is acceptable because they are time-invariant attributes, not learned signals. |

### Cold-start handling vs. leakage

The evaluation functions (`eval_rmse`, `eval_ranking_cf`, `eval_ranking_cb`,
`eval_ranking_hybrid`) only score users and items that appear in the **training** indexes.
Test pairs involving a cold-start user or a cold-start item are **skipped** and reported
separately as coverage statistics.

This is a deliberate **scope limitation**, not a leakage issue: the offline metrics
measure quality on warm-start users/items only. Cold-start recommendation quality is *not*
measured here (the cold-start path is handled separately at serving time via
`cold_start.py`).

---

## 3. Metrics and Why They Are Used

All ranking metrics are computed for **K = 5, 10, and 20**, and reported for each of CF,
CB, and Hybrid.

### RMSE (Root Mean Squared Error)

- **Measures:** prediction accuracy — how close predicted ratings are to actual ratings.
- **Formula:** `RMSE = sqrt(mean((actual - predicted)^2))`
- **Used for:** hyperparameter tuning on the **validation set** (selecting `k` for SVD),
  and final reporting on the **test set**.
- **Limitation:** measures point-prediction accuracy, *not* ranking quality. A model can
  have good RMSE but still order recommendations poorly.

### Hit Rate@K

- **Measures:** the fraction of test users whose held-out item appears in the model's
  top-K recommendations.
- **Why:** the most intuitive top-N metric — it directly answers "did we surface the
  relevant item in a realistic top-K list?"
- With exactly one held-out item per user, Hit Rate@K equals **Recall@K**.

### NDCG@K (Normalized Discounted Cumulative Gain)

- **Measures:** *where* in the top-K the held-out item lands, rewarding higher ranks.
- **Formula:** for each test user whose held-out item is within the top-K, the gain is
  `1 / log2(rank + 1)`; this is averaged across all test users.
- **Why:** distinguishes models that rank relevant items near the top from those that
  merely place them "somewhere in the top K."

### MRR (Mean Reciprocal Rank)

- **Measures:** `1 / rank` of the held-out item, averaged across test users; only items
  inside the top-K window are counted.
- **Why:** heavily rewards putting the relevant item at the very top and penalizes
  burying it near the bottom of the list.

### Coverage Statistics

- **Reports:** how many test pairs were evaluable (warm-start) versus skipped
  (cold-start users / items).
- **Why:** the ranking metrics only describe the evaluable subset. Coverage tells you how
  representative that subset is of the full test set.

---

## 4. Running and Interpreting the Evaluation

### Running

```bash
# Full training + evaluation (evaluation runs automatically after training)
python train_models.py

# Evaluation only (requires pre-trained artifacts in artifacts/)
python train_models.py --evaluate
```

### Output format

The evaluation prints a structured report:

```
============================================================
MODEL EVALUATION
============================================================

--- CF Evaluation ---
  RMSE (val):  0.XXXX
  RMSE (test): 0.XXXX

  Coverage: NNNNN evaluable pairs out of NNNNN test rows
  Skipped: NNN cold-start users, NNN cold-start items

     K    Hit Rate        NDCG         MRR
  --------------------------------------
     5      0.XXXX      0.XXXX      0.XXXX
    10      0.XXXX      0.XXXX      0.XXXX
    20      0.XXXX      0.XXXX      0.XXXX

--- CB Evaluation ---
  ...

--- Hybrid (60% CF + 40% CB) Evaluation ---
  ...

============================================================
SUMMARY: Hit Rate@10 comparison
============================================================
  CF:     0.XXXX
  CB:     0.XXXX
  Hybrid: 0.XXXX
```

### What to look for

- **RMSE** — lower is better. Compare validation vs. test: a large gap suggests
  overfitting. RMSE is used for `k`-tuning only, not for final model selection.
- **Hit Rate@K** — higher is better. The most intuitive signal: "is the held-out item in
  the top K?" For this dataset, expect low single-digit percentages at K=5, rising with K.
- **NDCG@K** — higher is better. If two models have similar Hit Rate@10 but different
  NDCG@10, the higher-NDCG model is placing relevant items nearer the top.
- **MRR** — higher is better. Dominated by cases where the relevant item ranks 1st or 2nd,
  so it is sensitive to top-of-list quality.
- **Coverage** — if coverage is low (many cold-start skips), the metrics reflect only
  well-known users and items, not the full population.
- **Hybrid vs. individual models** — if Hybrid beats both CF and CB, the blend is adding
  value. If it underperforms the best individual model, the 60/40 weighting likely needs
  adjustment.

### Prerequisites

- Trained artifacts must exist in `artifacts/` (run `python train_models.py` first).
- Data files must exist:
  - `train_set_enriched.csv`
  - `val_set_enriched.csv`
  - `test_set_enriched.csv`
  - `item_profiles_for_cold_start_enriched.csv`
- To regenerate the data files from raw data, run `data_processing/pipeline.py`.

### Running unit tests

```bash
pytest test_pipelines.py -v
```

These tests verify:

- No user–beer overlap between the train / validation / test splits.
- Rating matrix construction correctness.
- Rating-scale detection and normalization.
- Recommendation function behavior.
- Feature engineering.
