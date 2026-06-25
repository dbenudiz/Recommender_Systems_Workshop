"""
train_models.py

One-shot offline training script for the beer recommender system.

Trains both pipelines and persists their artifacts to artifacts/ so the API
server can load precomputed matrices instead of training at request time:

  * CF (sparse truncated SVD)  -> U, V, user means, ids, sparse R, meta
  * CB (content-based)         -> fitted ColumnTransformer + feature matrix

Replicates the preprocessing of cf_pipeline.py and cb_pipeline.py exactly.
Reads flat CSVs from the project root only; no database access. Safe to re-run.

Usage:
    python train_models.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, csr_matrix, load_npz, save_npz
from scipy.sparse.linalg import svds

from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import joblib


BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"

TRAIN_PATH = BASE_DIR / "train_set_enriched.csv"
VAL_PATH = BASE_DIR / "val_set_enriched.csv"
TEST_PATH = BASE_DIR / "test_set_enriched.csv"
ITEM_PROFILES_PATH = BASE_DIR / "item_profiles_for_cold_start_enriched.csv"

K_CANDIDATES = [5, 10, 20, 50]
KNOWN_SCALES = [1.0, 5.0, 10.0, 20.0]

RATING_COLS = ["username", "beer_id", "rating_overall"]

TEXT_FEATURE = "all_reviews_text"
CATEGORICAL_FEATURES = ["beer_style"]
NUMERIC_FEATURES = [
    "beer_abv",
    "avg_overall_rating",
    "avg_taste_rating",
    "avg_aroma_rating",
    "avg_appearance_rating",
    "avg_palate_rating",
    "avg_review_word_count",
    "total_reviews_count",
]


def log(message: str) -> None:
    print(message, flush=True)


def require_files() -> None:
    missing = [
        str(p)
        for p in (TRAIN_PATH, VAL_PATH, TEST_PATH, ITEM_PROFILES_PATH)
        if not p.exists()
    ]
    if missing:
        log("ERROR: required input CSV(s) not found:")
        for path in missing:
            log(f"  - {path}")
        sys.exit(1)


# ─────────────────────────────────────────────
# CF preprocessing (mirrors cf_pipeline.py)
# ─────────────────────────────────────────────
def detect_scale(sparse_matrix: csr_matrix) -> float:
    """Return the factor to divide by so all stored values land in [0, 1]."""
    if sparse_matrix.nnz == 0:
        return 1.0
    observed_max = float(sparse_matrix.data.max())
    if observed_max <= 1.0:
        return 1.0
    for scale in sorted(KNOWN_SCALES):
        if observed_max <= scale:
            return scale
    return observed_max


def build_rating_matrix(ratings_df: pd.DataFrame):
    """Build a sparse CSR rating matrix + category indexes from a ratings df."""
    ratings_df = ratings_df.dropna(subset=RATING_COLS)
    ratings_df = (
        ratings_df.groupby(["username", "beer_id"], as_index=False)["rating_overall"]
        .mean()
    )

    user_cat = ratings_df["username"].astype("category")
    beer_cat = ratings_df["beer_id"].astype("category")

    user_ids = user_cat.cat.categories
    beer_ids = beer_cat.cat.categories

    R = coo_matrix(
        (
            ratings_df["rating_overall"].astype(float).values,
            (user_cat.cat.codes.values, beer_cat.cat.codes.values),
        ),
        shape=(len(user_ids), len(beer_ids)),
    ).tocsr()

    return R, user_ids, beer_ids


def center_ratings(R_sparse: csr_matrix):
    """Subtract per-user means from rated entries. Returns (R_centered, means)."""
    row_sums = np.asarray(R_sparse.sum(axis=1)).flatten()
    row_counts = np.diff(R_sparse.indptr)
    row_counts_safe = np.where(row_counts == 0, 1, row_counts)
    user_means = row_sums / row_counts_safe

    R_coo = R_sparse.tocoo()
    centered_data = R_coo.data - user_means[R_coo.row]
    R_centered = coo_matrix(
        (centered_data, (R_coo.row, R_coo.col)), shape=R_sparse.shape
    ).tocsr()
    return R_centered, user_means


def factorize(R_centered: csr_matrix, k: int):
    """Truncated SVD with sigma split evenly into U and V (sqrt). Returns U, V."""
    U_raw, sigma, Vt_raw = svds(R_centered, k=k)

    # svds returns ascending singular values; reverse to strongest-first.
    U_raw = U_raw[:, ::-1]
    sigma = sigma[::-1]
    Vt_raw = Vt_raw[::-1, :]

    sigma_sqrt = np.sqrt(np.diag(sigma))
    U = U_raw @ sigma_sqrt
    V = Vt_raw.T @ sigma_sqrt
    return U, V


def eval_rmse(eval_df, U, V, user_means, user_id_to_index, beer_id_to_index) -> float:
    """RMSE over (user, beer) pairs present in both eval set and training set."""
    eval_df = eval_df.dropna(subset=RATING_COLS)

    user_idx = eval_df["username"].map(user_id_to_index)
    beer_idx = eval_df["beer_id"].map(beer_id_to_index)
    valid = user_idx.notna() & beer_idx.notna()

    if not valid.any():
        return float("nan")

    rows = user_idx[valid].astype(int).to_numpy()
    cols = beer_idx[valid].astype(int).to_numpy()
    truth = eval_df.loc[valid, "rating_overall"].astype(float).to_numpy()

    preds = np.einsum("ij,ij->i", U[rows], V[cols]) + user_means[rows]
    preds = np.clip(preds, 0.0, 1.0)
    return float(np.sqrt(np.mean((truth - preds) ** 2)))


# ─────────────────────────────────────────────
# Ranking metrics (Hit Rate@K, NDCG@K, MRR)
# ─────────────────────────────────────────────
def _empty_ranking(k_values):
    return {k: {"hits": 0, "ndcg": 0.0, "mrr": 0.0} for k in k_values}


def _accumulate_rank(acc, rank, k_values):
    """Fold a single held-out item's rank into the running ranking totals."""
    for k in k_values:
        if rank <= k:
            acc[k]["hits"] += 1
            acc[k]["ndcg"] += 1.0 / np.log2(rank + 1)
            acc[k]["mrr"] += 1.0 / rank


def _finalize_ranking(acc, n_evaluated, k_values):
    """Turn summed counters into per-k averages over the evaluated items."""
    denom = n_evaluated if n_evaluated > 0 else 1
    return {
        k: {
            "hit_rate": acc[k]["hits"] / denom,
            "ndcg": acc[k]["ndcg"] / denom,
            "mrr": acc[k]["mrr"] / denom,
        }
        for k in k_values
    }


def _rank_of(scores, item_idx):
    """1-indexed rank of item_idx in scores sorted descending."""
    order = np.argsort(scores)[::-1]
    return int(np.where(order == item_idx)[0][0]) + 1


def _cb_user_profile(beer_indices, ratings, feature_matrix):
    """Weighted-average feature profile, matching cb_pipeline.build_user_profile."""
    weights = np.clip(np.asarray(ratings, dtype=float) / 5.0, 0.0, 1.0)
    vectors = feature_matrix[beer_indices]
    if hasattr(vectors, "toarray"):
        vectors = vectors.toarray()
    vectors = np.asarray(vectors)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    return np.average(vectors, axis=0, weights=weights).reshape(1, -1)


def eval_ranking_cf(
    test_df,
    U,
    V,
    user_means,
    user_id_to_index,
    beer_id_to_index,
    R_sparse,
    k_values=(5, 10, 20),
):
    """Hit Rate@K / NDCG@K / MRR for the CF model over the held-out test set."""
    k_values = list(k_values)
    acc = _empty_ranking(k_values)
    n_evaluated = 0
    n_cold_users = 0
    n_cold_items = 0

    test_df = test_df.dropna(subset=RATING_COLS)
    total = len(test_df)
    for i, (username, beer_id, _rating) in enumerate(test_df[RATING_COLS].itertuples(index=False)):
        if i % 2000 == 0:
            log(f"    CF ranking: {i:,}/{total:,} rows processed ...")
        user_idx = user_id_to_index.get(username)
        if user_idx is None:
            n_cold_users += 1
            continue
        item_idx = beer_id_to_index.get(beer_id)
        if item_idx is None:
            n_cold_items += 1
            continue

        pred = U[user_idx] @ V.T + user_means[user_idx]
        pred = np.clip(pred, 0.0, 1.0)
        pred[R_sparse.getrow(user_idx).indices] = -np.inf

        rank = _rank_of(pred, item_idx)
        _accumulate_rank(acc, rank, k_values)
        n_evaluated += 1

    log(f"    CF ranking: {total:,}/{total:,} rows processed — done")
    return _finalize_ranking(acc, n_evaluated, k_values), n_evaluated, n_cold_users, n_cold_items


def eval_ranking_cb(
    test_df,
    feature_matrix,
    cb_train_df,
    cb_beer_ids,
    k_values=(5, 10, 20),
):
    """Hit Rate@K / NDCG@K / MRR for the CB model over the held-out test set."""
    k_values = list(k_values)
    acc = _empty_ranking(k_values)
    n_evaluated = 0
    n_cold_users = 0
    n_cold_items = 0

    cb_beer_id_to_index = {bid: i for i, bid in enumerate(cb_beer_ids)}

    test_df = test_df.dropna(subset=RATING_COLS)
    train_by_user = {
        user: group for user, group in cb_train_df.groupby("username")
    }

    user_groups = list(test_df.groupby("username"))
    total = len(user_groups)
    for i, (username, user_tests) in enumerate(user_groups):
        if i % 2000 == 0:
            log(f"    CB ranking: {i:,}/{total:,} users processed ...")
        user_reviews = train_by_user.get(username)
        if user_reviews is None or len(user_reviews) == 0:
            n_cold_users += len(user_tests)
            continue

        user_reviews = user_reviews[user_reviews["beer_id"].isin(cb_beer_id_to_index)]
        if len(user_reviews) == 0:
            n_cold_users += len(user_tests)
            continue

        beer_indices = user_reviews["beer_id"].map(cb_beer_id_to_index).to_numpy()
        ratings = user_reviews["rating_overall"].to_numpy()
        profile = _cb_user_profile(beer_indices, ratings, feature_matrix)

        sims = cosine_similarity(profile, feature_matrix).flatten()
        sims[beer_indices] = -np.inf

        for beer_id in user_tests["beer_id"]:
            item_idx = cb_beer_id_to_index.get(beer_id)
            if item_idx is None:
                n_cold_items += 1
                continue
            rank = _rank_of(sims, item_idx)
            _accumulate_rank(acc, rank, k_values)
            n_evaluated += 1

    log(f"    CB ranking: {total:,}/{total:,} users processed — done")
    return _finalize_ranking(acc, n_evaluated, k_values), n_evaluated, n_cold_users, n_cold_items


def eval_ranking_hybrid(
    test_df,
    U,
    V,
    user_means,
    user_id_to_index,
    beer_id_to_index,
    R_sparse,
    feature_matrix,
    cb_train_df,
    cb_beer_ids,
    cf_weight=0.6,
    k_values=(5, 10, 20),
):
    """Hit Rate@K / NDCG@K / MRR for a CF+CB blend over the held-out test set.

    Scores are restricted to beers present in BOTH the CF and CB indexes so the
    two pipelines can be blended over a common candidate set.
    """
    k_values = list(k_values)
    acc = _empty_ranking(k_values)
    n_evaluated = 0
    n_cold_users = 0
    n_cold_items = 0

    cb_beer_id_to_index = {bid: i for i, bid in enumerate(cb_beer_ids)}

    # Beers usable by both pipelines, in a stable order.
    shared_beer_ids = [bid for bid in beer_id_to_index if bid in cb_beer_id_to_index]
    if not shared_beer_ids:
        return _finalize_ranking(acc, n_evaluated, k_values), n_evaluated, n_cold_users, n_cold_items

    cf_cols = np.array([beer_id_to_index[bid] for bid in shared_beer_ids])
    cb_cols = np.array([cb_beer_id_to_index[bid] for bid in shared_beer_ids])
    shared_pos = {bid: i for i, bid in enumerate(shared_beer_ids)}

    cb_index_to_beer_id = {i: bid for bid, i in cb_beer_id_to_index.items()}

    test_df = test_df.dropna(subset=RATING_COLS)
    train_by_user = {
        user: group for user, group in cb_train_df.groupby("username")
    }

    user_groups = list(test_df.groupby("username"))
    total = len(user_groups)
    for i, (username, user_tests) in enumerate(user_groups):
        if i % 2000 == 0:
            log(f"    Hybrid ranking: {i:,}/{total:,} users processed ...")
        cf_user_idx = user_id_to_index.get(username)
        user_reviews = train_by_user.get(username)
        cb_cold = user_reviews is None or len(user_reviews) == 0
        if cf_user_idx is None or cb_cold:
            n_cold_users += len(user_tests)
            continue

        cb_reviews = user_reviews[user_reviews["beer_id"].isin(cb_beer_id_to_index)]
        if len(cb_reviews) == 0:
            n_cold_users += len(user_tests)
            continue

        # CF scores restricted to shared beers.
        cf_full = np.clip(U[cf_user_idx] @ V.T + user_means[cf_user_idx], 0.0, 1.0)
        cf_scores = cf_full[cf_cols]

        # CB scores restricted to shared beers.
        beer_indices = cb_reviews["beer_id"].map(cb_beer_id_to_index).to_numpy()
        ratings = cb_reviews["rating_overall"].to_numpy()
        profile = _cb_user_profile(beer_indices, ratings, feature_matrix)
        cb_full = cosine_similarity(profile, feature_matrix).flatten()
        cb_scores = cb_full[cb_cols]

        hybrid = cf_weight * cf_scores + (1.0 - cf_weight) * cb_scores

        # Mask training items that fall within the shared set.
        for cb_idx in beer_indices:
            bid = cb_index_to_beer_id.get(cb_idx)
            pos = shared_pos.get(bid)
            if pos is not None:
                hybrid[pos] = -np.inf

        for beer_id in user_tests["beer_id"]:
            pos = shared_pos.get(beer_id)
            if pos is None:
                n_cold_items += 1
                continue
            rank = _rank_of(hybrid, pos)
            _accumulate_rank(acc, rank, k_values)
            n_evaluated += 1

    log(f"    Hybrid ranking: {total:,}/{total:,} users processed — done")
    return _finalize_ranking(acc, n_evaluated, k_values), n_evaluated, n_cold_users, n_cold_items


# ─────────────────────────────────────────────
# CB preprocessing (mirrors cb_pipeline.py)
# ─────────────────────────────────────────────
def build_cb_artifacts(item_profiles: pd.DataFrame):
    """Preprocess item profiles and fit the ColumnTransformer."""
    required = (
        ["beer_id", "beer_name", "beer_style", TEXT_FEATURE] + NUMERIC_FEATURES
    )
    missing = [c for c in required if c not in item_profiles.columns]
    if missing:
        log(f"ERROR: item_profiles missing required columns: {missing}")
        sys.exit(1)

    item_profiles = item_profiles.copy()
    item_profiles[TEXT_FEATURE] = item_profiles[TEXT_FEATURE].fillna("")
    item_profiles["beer_style"] = item_profiles["beer_style"].fillna("unknown")

    for col in NUMERIC_FEATURES:
        item_profiles[col] = pd.to_numeric(item_profiles[col], errors="coerce")

    if item_profiles["beer_abv"].notna().any():
        item_profiles["beer_abv"] = item_profiles["beer_abv"].fillna(
            item_profiles["beer_abv"].median()
        )
    else:
        item_profiles["beer_abv"] = item_profiles["beer_abv"].fillna(0)

    for col in NUMERIC_FEATURES:
        item_profiles[col] = item_profiles[col].fillna(0)

    preprocessor = ColumnTransformer(
        transformers=[
            ("style", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            (
                "text",
                TfidfVectorizer(max_features=2000, stop_words="english", min_df=1),
                TEXT_FEATURE,
            ),
        ],
        remainder="drop",
    )

    feature_matrix = preprocessor.fit_transform(item_profiles)
    beer_ids = item_profiles["beer_id"].astype(str).values
    return item_profiles, preprocessor, feature_matrix, beer_ids


# ─────────────────────────────────────────────
# Persistence helpers
# ─────────────────────────────────────────────
def ensure_csr(matrix):
    return matrix.tocsr() if hasattr(matrix, "tocsr") else csr_matrix(matrix)


def report_artifacts() -> None:
    log("\nArtifacts written to artifacts/:")
    total = 0
    for path in sorted(ARTIFACTS_DIR.iterdir()):
        if path.is_file():
            size = path.stat().st_size
            total += size
            log(f"  {path.name:<28} {size / 1024:>12,.1f} KB")
    log(f"  {'TOTAL':<28} {total / (1024 * 1024):>12,.2f} MB")


def append_gitignore() -> None:
    gitignore = BASE_DIR / ".gitignore"
    entry = "artifacts/"
    lines = []
    if gitignore.exists():
        lines = gitignore.read_text(encoding="utf-8").splitlines()
        if any(line.strip().rstrip("/") == "artifacts" for line in lines):
            return
    with gitignore.open("a", encoding="utf-8") as fh:
        if lines and lines[-1].strip() != "":
            fh.write("\n")
        fh.write(entry + "\n")
    log("Added 'artifacts/' to .gitignore")


# ─────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────
def evaluate_models() -> None:
    """Full evaluation of CF, CB, and Hybrid models on the held-out test set."""
    require_files()

    log("=" * 60)
    log("MODEL EVALUATION")
    log("=" * 60)

    # Load test data
    test_df = pd.read_csv(TEST_PATH, usecols=RATING_COLS)
    val_df = pd.read_csv(VAL_PATH, usecols=RATING_COLS)

    # Load CF artifacts
    log("\nLoading CF artifacts ...")
    U = np.load(ARTIFACTS_DIR / "cf_U.npy")
    V = np.load(ARTIFACTS_DIR / "cf_V.npy")
    user_means = np.load(ARTIFACTS_DIR / "cf_user_means.npy")
    user_ids = np.load(ARTIFACTS_DIR / "cf_user_ids.npy", allow_pickle=True)
    beer_ids = np.load(ARTIFACTS_DIR / "cf_beer_ids.npy", allow_pickle=True)
    R_sparse = load_npz(ARTIFACTS_DIR / "cf_R_sparse.npz")
    with open(ARTIFACTS_DIR / "cf_meta.json") as f:
        cf_meta = json.load(f)
    scale = cf_meta["scale"]

    user_id_to_index = {uid: i for i, uid in enumerate(user_ids)}
    beer_id_to_index = {bid: i for i, bid in enumerate(beer_ids)}

    # Saved artifact ids are strings; the raw CSV ids load as ints. Cast the
    # test/val id columns to str so lookups against the artifact indexes match.
    for df in (test_df, val_df):
        df["username"] = df["username"].astype(str)
        df["beer_id"] = df["beer_id"].astype(str)

    # Scale test ratings to match training scale
    if scale != 1.0:
        test_df["rating_overall"] = test_df["rating_overall"] / scale
        val_df["rating_overall"] = val_df["rating_overall"] / scale

    # CF RMSE
    log("\n--- CF Evaluation ---")
    test_rmse = eval_rmse(test_df, U, V, user_means, user_id_to_index, beer_id_to_index)
    val_rmse = eval_rmse(val_df, U, V, user_means, user_id_to_index, beer_id_to_index)
    log(f"  RMSE (val):  {val_rmse:.4f}")
    log(f"  RMSE (test): {test_rmse:.4f}")

    # CF Ranking
    k_values = [5, 10, 20]
    cf_ranking, cf_eval, cf_cold_u, cf_cold_i = eval_ranking_cf(
        test_df, U, V, user_means, user_id_to_index, beer_id_to_index, R_sparse, k_values
    )
    log(f"\n  Coverage: {cf_eval} evaluable pairs out of {len(test_df)} test rows")
    log(f"  Skipped: {cf_cold_u} cold-start users, {cf_cold_i} cold-start items")
    log(f"\n  {'K':>4}  {'Hit Rate':>10}  {'NDCG':>10}  {'MRR':>10}")
    log("  " + "-" * 38)
    for k in k_values:
        m = cf_ranking[k]
        log(f"  {k:>4}  {m['hit_rate']:>10.4f}  {m['ndcg']:>10.4f}  {m['mrr']:>10.4f}")

    # Load CB artifacts
    log("\n--- CB Evaluation ---")
    feature_matrix = load_npz(ARTIFACTS_DIR / "cb_feature_matrix.npz")
    cb_beer_ids = np.load(ARTIFACTS_DIR / "cb_beer_ids.npy", allow_pickle=True)
    cb_train_df = pd.read_csv(ARTIFACTS_DIR / "cb_train_df.csv")
    cb_train_df["username"] = cb_train_df["username"].astype(str)
    cb_train_df["beer_id"] = cb_train_df["beer_id"].astype(str)

    cb_ranking, cb_eval, cb_cold_u, cb_cold_i = eval_ranking_cb(
        test_df, feature_matrix, cb_train_df, cb_beer_ids, k_values
    )
    log(f"\n  Coverage: {cb_eval} evaluable pairs out of {len(test_df)} test rows")
    log(f"  Skipped: {cb_cold_u} cold-start users, {cb_cold_i} cold-start items")
    log(f"\n  {'K':>4}  {'Hit Rate':>10}  {'NDCG':>10}  {'MRR':>10}")
    log("  " + "-" * 38)
    for k in k_values:
        m = cb_ranking[k]
        log(f"  {k:>4}  {m['hit_rate']:>10.4f}  {m['ndcg']:>10.4f}  {m['mrr']:>10.4f}")

    # Hybrid evaluation
    log("\n--- Hybrid (60% CF + 40% CB) Evaluation ---")
    hybrid_ranking, hybrid_eval, hybrid_cold_u, hybrid_cold_i = eval_ranking_hybrid(
        test_df, U, V, user_means, user_id_to_index, beer_id_to_index, R_sparse,
        feature_matrix, cb_train_df, cb_beer_ids, cf_weight=0.6, k_values=k_values
    )
    log(f"\n  Coverage: {hybrid_eval} evaluable pairs out of {len(test_df)} test rows")
    log(f"  Skipped: {hybrid_cold_u} cold-start users, {hybrid_cold_i} cold-start items")
    log(f"\n  {'K':>4}  {'Hit Rate':>10}  {'NDCG':>10}  {'MRR':>10}")
    log("  " + "-" * 38)
    for k in k_values:
        m = hybrid_ranking[k]
        log(f"  {k:>4}  {m['hit_rate']:>10.4f}  {m['ndcg']:>10.4f}  {m['mrr']:>10.4f}")

    # Summary comparison
    log("\n" + "=" * 60)
    log("SUMMARY: Hit Rate@10 comparison")
    log("=" * 60)
    log(f"  CF:     {cf_ranking[10]['hit_rate']:.4f}")
    log(f"  CB:     {cb_ranking[10]['hit_rate']:.4f}")
    log(f"  Hybrid: {hybrid_ranking[10]['hit_rate']:.4f}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main() -> None:
    start = time.time()
    require_files()
    ARTIFACTS_DIR.mkdir(exist_ok=True)

    # ── CF: load + build rating matrix ──────────────────────────────
    log("Loading train ratings ...")
    train_ratings = pd.read_csv(TRAIN_PATH, usecols=RATING_COLS)
    log(f"  train rows: {len(train_ratings):,}")

    log("Building sparse rating matrix ...")
    R_sparse, user_ids, beer_ids = build_rating_matrix(train_ratings)
    n_users, n_beers = R_sparse.shape
    log(f"  rating matrix: {n_users:,} users x {n_beers:,} beers, nnz={R_sparse.nnz:,}")

    scale = detect_scale(R_sparse)
    if scale != 1.0:
        log(f"  scale detected: raw ratings on [0, {scale:.0f}] -> dividing to [0, 1]")
        R_sparse = R_sparse / scale
    else:
        log("  scale detected: ratings already in [0, 1]")

    R_centered, user_means = center_ratings(R_sparse)

    user_ids_str = np.asarray(user_ids.astype(str))
    beer_ids_str = np.asarray(beer_ids.astype(str))
    user_id_to_index = {uid: i for i, uid in enumerate(user_ids)}
    beer_id_to_index = {bid: i for i, bid in enumerate(beer_ids)}

    # ── CF: load eval sets ──────────────────────────────────────────
    log("Loading validation and test ratings ...")
    val_df = pd.read_csv(VAL_PATH, usecols=RATING_COLS)
    test_df = pd.read_csv(TEST_PATH, usecols=RATING_COLS)
    if scale != 1.0:
        val_df["rating_overall"] = val_df["rating_overall"] / scale
        test_df["rating_overall"] = test_df["rating_overall"] / scale

    # ── CF: tune k ──────────────────────────────────────────────────
    max_k = min(n_users, n_beers) - 1
    candidates = [k for k in K_CANDIDATES if k <= max_k]
    if not candidates:
        candidates = [max(1, max_k)]

    log("\nTuning k (val/test RMSE):")
    results = []
    best = None
    for k in candidates:
        log(f"  factorizing k={k} ...")
        U_k, V_k = factorize(R_centered, k)
        val_rmse = eval_rmse(val_df, U_k, V_k, user_means, user_id_to_index, beer_id_to_index)
        test_rmse = eval_rmse(test_df, U_k, V_k, user_means, user_id_to_index, beer_id_to_index)
        results.append((k, val_rmse, test_rmse))
        if best is None or val_rmse < best[1]:
            best = (k, val_rmse, U_k, V_k)

    log("\n  {:>4}  {:>10}  {:>10}".format("k", "val_RMSE", "test_RMSE"))
    log("  " + "-" * 28)
    for k, val_rmse, test_rmse in results:
        marker = "  <- best" if k == best[0] else ""
        log("  {:>4}  {:>10.4f}  {:>10.4f}{}".format(k, val_rmse, test_rmse, marker))

    best_k, _, U, V = best
    log(f"\nSelected k={best_k}")

    # ── CF: persist ─────────────────────────────────────────────────
    log("\nSaving CF artifacts ...")
    np.save(ARTIFACTS_DIR / "cf_U.npy", U.astype(np.float64))
    np.save(ARTIFACTS_DIR / "cf_V.npy", V.astype(np.float64))
    np.save(ARTIFACTS_DIR / "cf_user_means.npy", user_means.astype(np.float64))
    np.save(ARTIFACTS_DIR / "cf_user_ids.npy", user_ids_str)
    np.save(ARTIFACTS_DIR / "cf_beer_ids.npy", beer_ids_str)
    save_npz(ARTIFACTS_DIR / "cf_R_sparse.npz", ensure_csr(R_sparse))
    cf_meta = {
        "k": int(best_k),
        "scale": float(scale),
        "n_users": int(n_users),
        "n_beers": int(n_beers),
    }
    (ARTIFACTS_DIR / "cf_meta.json").write_text(json.dumps(cf_meta, indent=2))

    # Free CF eval frames before CB load (item profiles is large).
    del val_df, test_df, train_ratings, R_centered

    # ── CB: load + build ────────────────────────────────────────────
    log("\nLoading item profiles ...")
    item_profiles_raw = pd.read_csv(ITEM_PROFILES_PATH)
    log(f"  item profiles: {item_profiles_raw.shape}")

    log("Fitting CB preprocessor ...")
    item_profiles, preprocessor, feature_matrix, cb_beer_ids = build_cb_artifacts(
        item_profiles_raw
    )
    log(f"  feature matrix: {feature_matrix.shape}")

    log("Building cb_train_df ...")
    cb_train_df = pd.read_csv(TRAIN_PATH, usecols=RATING_COLS)
    cb_train_df = cb_train_df.dropna(subset=RATING_COLS)

    # ── CB: persist ─────────────────────────────────────────────────
    log("Saving CB artifacts ...")
    save_npz(ARTIFACTS_DIR / "cb_feature_matrix.npz", ensure_csr(feature_matrix))
    item_profiles.to_csv(ARTIFACTS_DIR / "cb_item_profiles.csv", index=False)
    cb_train_df.to_csv(ARTIFACTS_DIR / "cb_train_df.csv", index=False)
    np.save(ARTIFACTS_DIR / "cb_beer_ids.npy", cb_beer_ids)
    joblib.dump(preprocessor, ARTIFACTS_DIR / "cb_preprocessor.joblib")

    # ── gitignore + report ──────────────────────────────────────────
    append_gitignore()
    report_artifacts()

    log("\nRMSE summary:")
    log("  {:>4}  {:>10}  {:>10}".format("k", "val_RMSE", "test_RMSE"))
    for k, val_rmse, test_rmse in results:
        log("  {:>4}  {:>10.4f}  {:>10.4f}".format(k, val_rmse, test_rmse))

    # ── Full evaluation ────────────────────────────────────────────
    evaluate_models()

    elapsed = time.time() - start
    log(f"\nDone in {elapsed:.1f}s (selected k={best_k}, scale={scale:g})")


if __name__ == "__main__":
    if "--evaluate" in sys.argv:
        evaluate_models()
    else:
        main()
