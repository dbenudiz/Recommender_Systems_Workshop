"""
dummy_data.py
Generates a realistic dummy rating_matrix for testing the CF pipeline.

Usage:
    from dummy_data import make_rating_matrix
    rating_matrix = make_rating_matrix()

The matrix mirrors real-world properties:
  - Power-law sparsity (most users rate very few beers)
  - User rating bias (some users are harsh, some are generous)
  - Taste clusters (users loosely belong to style groups)
  - Ratings normalised to [0, 1] to match the real pipeline
"""

import numpy as np
import pandas as pd

def make_rating_matrix(
    n_users: int = 200,
    n_beers: int = 500,
    sparsity: float = 0.97,   # fraction of missing cells — real data is often 98–99%
    n_clusters: int = 4,      # taste clusters: hoppy, dark, sour, light
    seed: int = 42,
) -> pd.DataFrame:
    """
    Returns a DataFrame of shape (n_users, n_beers) with float ratings in [0, 1].
    Missing ratings are NaN, matching the format expected by cf_recommend.

    Parameters
    ----------
    n_users   : number of simulated users
    n_beers   : number of simulated beers
    sparsity  : fraction of cells that are NaN (0.97 = 97% missing)
    n_clusters: number of latent taste groups (drives rating coherence)
    seed      : random seed for reproducibility
    """
    rng = np.random.default_rng(seed)

    # ── 1. Beer and user IDs ──────────────────────────────────────────
    user_ids = [f"user_{i:04d}" for i in range(n_users)]
    beer_ids = [f"beer_{j:04d}" for j in range(n_beers)]

    # ── 2. Assign latent taste clusters ──────────────────────────────
    # Each user belongs to one cluster; each beer belongs to one cluster.
    # Users and beers in the same cluster rate each other higher on average.
    user_cluster = rng.integers(0, n_clusters, size=n_users)
    beer_cluster = rng.integers(0, n_clusters, size=n_beers)

    # ── 3. Per-user rating bias (harsh vs generous raters) ───────────
    # Sampled from a narrow normal — keeps most biases within ±0.15
    user_bias = rng.normal(loc=0.0, scale=0.10, size=n_users).clip(-0.25, 0.25)

    # ── 4. Build the underlying "true" rating matrix ──────────────────
    # Base rating depends on whether user and beer share a cluster.
    same_cluster = (user_cluster[:, None] == beer_cluster[None, :])  # (n_users, n_beers)

    base_rating = np.where(same_cluster, 0.75, 0.45)          # high if same cluster
    noise       = rng.normal(loc=0.0, scale=0.12,             # individual variation
                             size=(n_users, n_beers))
    bias_matrix = user_bias[:, None]                           # broadcast user bias

    true_ratings = (base_rating + noise + bias_matrix).clip(0.0, 1.0)

    # ── 5. Apply sparsity mask ────────────────────────────────────────
    # Real datasets follow a power law: a few users rate hundreds of beers,
    # most rate only a handful.  We simulate this with a per-user density draw.
    ratings = np.full((n_users, n_beers), np.nan)

    for i in range(n_users):
        # Each user gets a personal density drawn from a skewed distribution
        # so some users are very active and most are sparse.
        personal_density = rng.beta(a=0.5, b=8.0)          # skewed toward 0
        personal_density = np.clip(personal_density, 1 - sparsity - 0.10,
                                                     1 - sparsity + 0.15)
        n_rated = max(1, int(personal_density * n_beers))   # at least 1 rating
        rated_beers = rng.choice(n_beers, size=n_rated, replace=False)
        ratings[i, rated_beers] = true_ratings[i, rated_beers]

    rating_matrix = pd.DataFrame(ratings, index=user_ids, columns=beer_ids)
    return rating_matrix


# ── Quick inspection ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    rating_matrix = make_rating_matrix()

    total_cells  = rating_matrix.size
    filled_cells = rating_matrix.notna().sum().sum()
    actual_sparsity = 1 - filled_cells / total_cells

    print("=" * 45)
    print("Dummy rating matrix summary")
    print("=" * 45)
    print(f"Shape        : {rating_matrix.shape}  (users × beers)")
    print(f"Filled cells : {filled_cells:,} / {total_cells:,}")
    print(f"Sparsity     : {actual_sparsity:.2%}")
    print(f"Rating range : {rating_matrix.min().min():.3f} – "
          f"{rating_matrix.max().max():.3f}")

    reviews_per_user = rating_matrix.notna().sum(axis=1)
    print(f"\nReviews per user:")
    print(f"  min    : {reviews_per_user.min()}")
    print(f"  median : {reviews_per_user.median():.0f}")
    print(f"  mean   : {reviews_per_user.mean():.1f}")
    print(f"  max    : {reviews_per_user.max()}")

    print(f"\nSample (first 5 users, first 8 beers):")
    print(rating_matrix.iloc[:5, :8].round(3).to_string())

    print(f"\nUsers with ≥ 5 ratings : "
          f"{(reviews_per_user >= 5).sum()} / {len(reviews_per_user)}")
    print(f"Users with ≥ 10 ratings: "
          f"{(reviews_per_user >= 10).sum()} / {len(reviews_per_user)}")
