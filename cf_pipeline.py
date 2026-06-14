"""
cf_pipeline.py
Build the User (U) and Item (V) latent factor matrices from the rating matrix
using truncated SVD, then use them to power cf_recommend().

Everything below operates on SPARSE matrices end-to-end. The real dataset is
~27k users × ~70k beers — a single dense (n_users × n_beers) array of that
size is ~14 GB, and the original implementation built several of them. Here
we never materialise a full dense user-by-beer matrix; predictions are
computed on demand for one user at a time.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.linalg import svds
from dummy_data import make_rating_matrix


BASE_DIR = Path(__file__).resolve().parent
TRAIN_PATH = BASE_DIR / "train_set_enriched.csv"


# ─────────────────────────────────────────────
# 1. LOAD DATA  →  sparse rating matrix
# ─────────────────────────────────────────────
if TRAIN_PATH.exists():
    train_df = pd.read_csv(TRAIN_PATH)
    train_df = train_df.dropna(subset=["username", "beer_id", "rating_overall"])
    train_df = (
        train_df.groupby(["username", "beer_id"], as_index=False)["rating_overall"]
        .mean()
    )

    user_cat = train_df["username"].astype("category")
    beer_cat = train_df["beer_id"].astype("category")

    user_ids = user_cat.cat.categories
    beer_ids = beer_cat.cat.categories

    R_sparse = coo_matrix(
        (
            train_df["rating_overall"].astype(float).values,
            (user_cat.cat.codes.values, beer_cat.cat.codes.values),
        ),
        shape=(len(user_ids), len(beer_ids)),
    ).tocsr()
    print("Real CSV file loaded.")
else:
    rating_matrix_demo = make_rating_matrix()        # shape: (n_users, n_beers)
    user_ids = rating_matrix_demo.index
    beer_ids = rating_matrix_demo.columns
    R_sparse = csr_matrix(rating_matrix_demo.fillna(0).values)
    print("Running with demo data.")

n_users, n_beers = R_sparse.shape
user_id_to_index = {user_id: idx for idx, user_id in enumerate(user_ids)}
print(f"Rating matrix : {n_users} users × {n_beers} beers")


# ─────────────────────────────────────────────
# 2. SCALE NORMALISATION  (0–1)
# ─────────────────────────────────────────────
# Person 1's pipeline.py may hand us raw ratings on different scales
# depending on whether they normalised before saving:
#
#   already [0, 1]  → dummy data, or a fixed pipeline.py
#   raw [0, 20]     → pipeline.py without normalisation (overall column)
#   raw [0, 10]     → aroma / taste columns
#   raw [0, 5]      → appearance / palate columns
#
# We detect the scale from the observed max and divide accordingly,
# so the CF pipeline is robust regardless of what we receive.
# All subsequent steps (user-mean subtraction, SVD, clip) assume [0, 1].

KNOWN_SCALES = [1.0, 5.0, 10.0, 20.0]   # only the denominators that exist in this dataset

def _detect_scale(sparse_matrix: csr_matrix) -> float:
    """
    Return the scale factor to divide by so all values land in [0, 1].
    Checks the max of the stored (rated) entries against known rating scales.
    Returns 1.0 if the matrix already looks like [0, 1].
    """
    if sparse_matrix.nnz == 0:
        return 1.0
    observed_max = sparse_matrix.data.max()
    if observed_max <= 1.0:
        return 1.0                      # already normalised — nothing to do
    for scale in sorted(KNOWN_SCALES):
        if observed_max <= scale:
            return scale
    return observed_max                 # fallback: normalise by observed max

scale = _detect_scale(R_sparse)

if scale != 1.0:
    print(f"Scale detected  : raw ratings on [0, {scale:.0f}] — dividing to reach [0, 1]")
    R_sparse = R_sparse / scale
else:
    print("Scale detected  : ratings already in [0, 1] — no rescaling needed")

if R_sparse.nnz:
    print(f"Rating range after scale fix: "
          f"{R_sparse.data.min():.3f} – {R_sparse.data.max():.3f}")


# ─────────────────────────────────────────────
# 3. NORMALISE  (remove per-user rating bias)
# ─────────────────────────────────────────────
# Each user's mean is subtracted so a 0.8 from a generous rater and
# a 0.8 from a harsh rater carry the same weight.
# This step runs AFTER scale normalisation so means are always in [0, 1].
#
# Only rated entries are centered; unrated cells stay at 0 ("no opinion"),
# matching the original rating_matrix_norm.fillna(0) behaviour while
# keeping the matrix sparse.
row_sums   = np.asarray(R_sparse.sum(axis=1)).flatten()
row_counts = np.diff(R_sparse.indptr)
row_counts_safe = np.where(row_counts == 0, 1, row_counts)
user_means = row_sums / row_counts_safe       # ndarray, shape (n_users,)

R_coo = R_sparse.tocoo()
centered_data = R_coo.data - user_means[R_coo.row]
R_centered = coo_matrix(
    (centered_data, (R_coo.row, R_coo.col)), shape=R_sparse.shape
).tocsr()


# ─────────────────────────────────────────────
# 4. TRUNCATED SVD  →  U  and  V
# ─────────────────────────────────────────────
#
# SVD factorises the matrix R into three matrices:
#
#     R  ≈  U · Σ · Vt
#
#   R  : (n_users × n_beers)   the normalised, mean-centered rating matrix
#   U  : (n_users × k)         USER  feature matrix  — one row per user
#   Σ  : (k × k)               diagonal matrix of singular values
#   Vt : (k × n_beers)         ITEM  feature matrix  — one column per beer
#                               (we transpose it to get V: n_beers × k)
#
# k is the number of latent factors (a hyperparameter you tune).
# Each latent factor loosely corresponds to a taste dimension
# (e.g. "hoppy", "dark and roasty", "sour") — not explicitly labelled,
# but learned from rating patterns.
#
# "Truncated" means we only keep the top-k singular values,
# which capture most of the signal and discard noise.

k = min(50, min(n_users, n_beers) - 1)    # start here; tune by plotting RMSE vs k (see bottom of file)

# svds returns singular values in ASCENDING order — we reverse everything
# so index 0 is the most important factor.
U_raw, sigma, Vt_raw = svds(R_centered, k=k)

# Reverse so factors are sorted strongest → weakest
U_raw  = U_raw[:, ::-1]        # (n_users × k)
sigma  = sigma[::-1]            # (k,)
Vt_raw = Vt_raw[::-1, :]       # (k × n_beers)

# Absorb Σ into both matrices (split evenly via sqrt so U and V are symmetric)
sigma_sqrt = np.sqrt(np.diag(sigma))    # (k × k)

U = U_raw  @ sigma_sqrt     # (n_users × k)  — user latent factors
V = Vt_raw.T @ sigma_sqrt   # (n_beers × k)  — item latent factors

# Wrap in DataFrames with meaningful indices
factor_cols = [f"factor_{i}" for i in range(k)]

U_df = pd.DataFrame(U, index=user_ids, columns=factor_cols)
V_df = pd.DataFrame(V, index=beer_ids, columns=factor_cols)

print(f"\nU (user feature matrix) : {U_df.shape}  — {k} latent factors per user")
print(f"V (item feature matrix) : {V_df.shape}  — {k} latent factors per beer")

print(f"\nU — first 3 users, first 5 factors:")
print(U_df.iloc[:3, :5].round(4))

print(f"\nV — first 3 beers, first 5 factors:")
print(V_df.iloc[:3, :5].round(4))


# ─────────────────────────────────────────────
# 5. RECONSTRUCT PREDICTED RATINGS  (on demand, per user)
# ─────────────────────────────────────────────
# Predicted rating = dot product of user vector and beer vector,
# then add back the user's mean rating to undo the normalisation.
#
#   R_hat[user] = U[user] · V^T  +  user_means[user]
#
# We never build the full (n_users × n_beers) prediction matrix —
# it's computed one user-row at a time, which is all cf_recommend needs.

def predict_user_row(user_idx: int) -> np.ndarray:
    row = U[user_idx] @ V.T + user_means[user_idx]
    return np.clip(row, 0.0, 1.0)


print(f"\nSample predictions (first 4 users, first 5 beers):")
sample_predictions = pd.DataFrame(
    [predict_user_row(i)[:5] for i in range(min(4, n_users))],
    index=user_ids[: min(4, n_users)],
    columns=beer_ids[:5],
)
print(sample_predictions.round(3))


# ─────────────────────────────────────────────
# 6. CF RECOMMEND
# ─────────────────────────────────────────────

def cf_recommend(user_id: str, n: int = 10) -> pd.Series:
    """
    Return the top-N beer recommendations for a user.

    Strategy: reconstruct the user's predicted ratings row, remove beers
    they have already rated, return the highest-scoring remainder.

    Parameters
    ----------
    user_id : must be a key in user_ids
    n       : number of recommendations to return

    Returns
    -------
    pd.Series  index = beer_id, values = predicted rating (0–1), sorted desc
    """
    if user_id not in user_id_to_index:
        raise ValueError(f"User '{user_id}' not found. "
                         f"Available users: {list(user_ids[:5])} ...")

    user_idx = user_id_to_index[user_id]
    predicted_row = predict_user_row(user_idx)

    rated_cols = R_sparse.getrow(user_idx).indices
    scores = pd.Series(predicted_row, index=beer_ids).drop(index=beer_ids[rated_cols])
    return scores.nlargest(n)


# ── Quick sanity check ────────────────────────────────────────────────────────
sample_user = user_ids[3]    # pick a user who has some ratings
sample_idx  = user_id_to_index[sample_user]

print(f"\n{'─'*45}")
print(f"Sample: beers already rated by '{sample_user}'")
sample_row    = R_sparse.getrow(sample_idx)
rated = pd.Series(sample_row.data, index=beer_ids[sample_row.indices]).sort_values(ascending=False)
print(rated.head(5).round(3))

print(f"\nTop-10 CF recommendations for '{sample_user}':")
recs = cf_recommend(sample_user, n=10)
print(recs.round(3))

# Sanity: none of the recommended beers should appear in the already-rated list
overlap = set(recs.index) & set(rated.index)
print(f"\nOverlap with already-rated beers: {len(overlap)}  (should be 0)")


# ─────────────────────────────────────────────
# 7. OPTIONAL — TUNE k  (plot RMSE vs k)
# ─────────────────────────────────────────────
# Run this block to find the best number of latent factors.
# Uses only rated cells (not the filled zeros) to measure true error.

def compute_rmse_for_k(R_sparse, R_centered, user_means, k_value):
    U_, sigma_, Vt_ = svds(R_centered, k=k_value)
    U_ = U_ @ np.diag(sigma_)    # (n_users × k)

    # Compare only on cells that were actually rated
    R_coo = R_sparse.tocoo()
    pred = np.einsum("ij,ij->i", U_[R_coo.row], Vt_.T[R_coo.col]) + user_means[R_coo.row]
    pred = np.clip(pred, 0.0, 1.0)

    return np.sqrt(np.mean((R_coo.data - pred) ** 2))


if __name__ == "__main__":
    print(f"\n{'─'*45}")
    print("Tuning k — RMSE on observed ratings:")
    print(f"{'─'*45}")
    for k_val in [5, 10, 20, 50, 100]:
        if k_val >= min(n_users, n_beers):
            continue
        rmse = compute_rmse_for_k(R_sparse, R_centered, user_means, k_val)
        bar  = "█" * int(rmse * 200)
        print(f"  k={k_val:>3}  RMSE={rmse:.4f}  {bar}")
