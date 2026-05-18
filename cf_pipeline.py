"""
cf_pipeline.py
Build the User (U) and Item (V) latent factor matrices from the rating matrix
using truncated SVD, then use them to power cf_recommend().
"""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from dummy_data import make_rating_matrix


# ─────────────────────────────────────────────
# 1. LOAD DUMMY DATA
# ─────────────────────────────────────────────
rating_matrix = make_rating_matrix()        # shape: (n_users, n_beers)

n_users, n_beers = rating_matrix.shape
print(f"Rating matrix : {n_users} users × {n_beers} beers")


# ─────────────────────────────────────────────
# 2. NORMALISE  (remove per-user rating bias)
# ─────────────────────────────────────────────
# Each user's mean is subtracted so a 0.8 from a generous rater and
# a 0.8 from a harsh rater carry the same weight.
user_means = rating_matrix.mean(axis=1)          # Series, shape (n_users,)

rating_matrix_norm   = rating_matrix.sub(user_means, axis=0)
rating_matrix_filled = rating_matrix_norm.fillna(0)   # NaN → 0 ("no opinion")


# ─────────────────────────────────────────────
# 3. TRUNCATED SVD  →  U  and  V
# ─────────────────────────────────────────────
#
# SVD factorises the matrix R into three matrices:
#
#     R  ≈  U · Σ · Vt
#
#   R  : (n_users × n_beers)   the normalised, filled rating matrix
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

k = 50    # start here; tune by plotting RMSE vs k (see bottom of file)

R_sparse = csr_matrix(rating_matrix_filled.values)   # sparse for efficiency

# svds returns singular values in ASCENDING order — we reverse everything
# so index 0 is the most important factor.
U_raw, sigma, Vt_raw = svds(R_sparse, k=k)

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

U_df = pd.DataFrame(U, index=rating_matrix.index,   columns=factor_cols)
V_df = pd.DataFrame(V, index=rating_matrix.columns, columns=factor_cols)

print(f"\nU (user feature matrix) : {U_df.shape}  — {k} latent factors per user")
print(f"V (item feature matrix) : {V_df.shape}  — {k} latent factors per beer")

print(f"\nU — first 3 users, first 5 factors:")
print(U_df.iloc[:3, :5].round(4))

print(f"\nV — first 3 beers, first 5 factors:")
print(V_df.iloc[:3, :5].round(4))


# ─────────────────────────────────────────────
# 4. RECONSTRUCT PREDICTED RATINGS
# ─────────────────────────────────────────────
# Predicted rating = dot product of user vector and beer vector,
# then add back the user's mean rating to undo the normalisation.
#
#   R_hat = U · V^T  +  user_means
#
# This gives a predicted rating for EVERY user-beer pair,
# including ones that were originally NaN (the missing ratings
# are what we actually want to predict).

predicted_norm = U @ V.T                      # (n_users × n_beers)

predicted_df = pd.DataFrame(
    predicted_norm + user_means.values[:, np.newaxis],
    index=rating_matrix.index,
    columns=rating_matrix.columns
).clip(0.0, 1.0)                              # keep within valid rating range

print(f"\nPredicted rating matrix : {predicted_df.shape}")
print(f"\nSample predictions (first 4 users, first 5 beers):")
print(predicted_df.iloc[:4, :5].round(3))


# ─────────────────────────────────────────────
# 5. CF RECOMMEND
# ─────────────────────────────────────────────

def cf_recommend(user_id: str, n: int = 10) -> pd.Series:
    """
    Return the top-N beer recommendations for a user.

    Strategy: take the user's row from predicted_df, remove beers
    they have already rated, return the highest-scoring remainder.

    Parameters
    ----------
    user_id : must be a key in rating_matrix.index
    n       : number of recommendations to return

    Returns
    -------
    pd.Series  index = beer_id, values = predicted rating (0–1), sorted desc
    """
    if user_id not in predicted_df.index:
        raise ValueError(f"User '{user_id}' not found. "
                         f"Available users: {list(predicted_df.index[:5])} ...")

    already_rated = rating_matrix.loc[user_id].dropna().index
    scores        = predicted_df.loc[user_id].drop(index=already_rated)
    return scores.nlargest(n)


# ── Quick sanity check ────────────────────────────────────────────────────────
sample_user = rating_matrix.index[3]    # pick a user who has some ratings

print(f"\n{'─'*45}")
print(f"Sample: beers already rated by '{sample_user}'")
rated = rating_matrix.loc[sample_user].dropna().sort_values(ascending=False)
print(rated.head(5).round(3))

print(f"\nTop-10 CF recommendations for '{sample_user}':")
recs = cf_recommend(sample_user, n=10)
print(recs.round(3))

# Sanity: none of the recommended beers should appear in the already-rated list
overlap = set(recs.index) & set(rated.index)
print(f"\nOverlap with already-rated beers: {len(overlap)}  (should be 0)")


# ─────────────────────────────────────────────
# 6. OPTIONAL — TUNE k  (plot RMSE vs k)
# ─────────────────────────────────────────────
# Run this block to find the best number of latent factors.
# Uses only rated cells (not the filled zeros) to measure true error.

def compute_rmse_for_k(rating_matrix, user_means, k_value):
    R_sparse = csr_matrix(
        rating_matrix.sub(user_means, axis=0).fillna(0).values
    )
    U_, sigma_, Vt_ = svds(R_sparse, k=k_value)
    pred_norm = U_ @ np.diag(sigma_) @ Vt_
    pred = pd.DataFrame(
        pred_norm + user_means.values[:, np.newaxis],
        index=rating_matrix.index,
        columns=rating_matrix.columns
    ).clip(0, 1)

    # Compare only on cells that were actually rated
    mask    = rating_matrix.notna()
    true    = rating_matrix.values[mask]
    guessed = pred.values[mask]
    return np.sqrt(np.mean((true - guessed) ** 2))


if __name__ == "__main__":
    print(f"\n{'─'*45}")
    print("Tuning k — RMSE on observed ratings:")
    print(f"{'─'*45}")
    for k_val in [5, 10, 20, 50, 100]:
        rmse = compute_rmse_for_k(rating_matrix, user_means, k_val)
        bar  = "█" * int(rmse * 200)
        print(f"  k={k_val:>3}  RMSE={rmse:.4f}  {bar}")
