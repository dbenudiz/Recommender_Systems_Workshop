"""
cb_pipeline.py

Content-Based recommendation pipeline for beer recommendations.

This recommends beers based on beer features, not similar users.

Uses:
- item_profiles_for_cold_start_enriched.csv
- train_set_enriched.csv

Main functions:
- cb_recommend(user_id, n=10)
- similar_beers(beer_id, n=10)
"""

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ─────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────

ITEM_PROFILES_PATH = "item_profiles_for_cold_start_enriched.csv"
TRAIN_PATH = "train_set_enriched.csv"

item_profiles = pd.read_csv(ITEM_PROFILES_PATH)
train_df = pd.read_csv(TRAIN_PATH)

print(f"Item profiles loaded: {item_profiles.shape}")
print(f"Train data loaded:    {train_df.shape}")


# ─────────────────────────────────────────────
# 2. CLEAN / PREPARE FEATURES
# ─────────────────────────────────────────────

text_feature = "all_reviews_text"
categorical_features = ["beer_style"]

numeric_features = [
    "beer_abv",
    "avg_overall_rating",
    "avg_taste_rating",
    "avg_aroma_rating",
    "avg_appearance_rating",
    "avg_palate_rating",
    "avg_review_word_count",
    "total_reviews_count",
]

item_profiles[text_feature] = item_profiles[text_feature].fillna("")
item_profiles["beer_style"] = item_profiles["beer_style"].fillna("unknown")

for col in numeric_features:
    item_profiles[col] = pd.to_numeric(item_profiles[col], errors="coerce")

item_profiles["beer_abv"] = item_profiles["beer_abv"].fillna(
    item_profiles["beer_abv"].median()
)

for col in numeric_features:
    item_profiles[col] = item_profiles[col].fillna(0)


# ─────────────────────────────────────────────
# 3. BUILD BEER FEATURE MATRIX
# ─────────────────────────────────────────────

preprocessor = ColumnTransformer(
    transformers=[
        (
            "style",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features,
        ),
        (
            "numeric",
            StandardScaler(),
            numeric_features,
        ),
        (
            "text",
            TfidfVectorizer(
                max_features=5000,
                stop_words="english",
                min_df=2,
            ),
            text_feature,
        ),
    ],
    remainder="drop",
)

beer_feature_matrix = preprocessor.fit_transform(item_profiles)

beer_ids = item_profiles["beer_id"].values
beer_id_to_index = {beer_id: idx for idx, beer_id in enumerate(beer_ids)}

print(f"Beer feature matrix: {beer_feature_matrix.shape}")


# ─────────────────────────────────────────────
# 4. SIMILAR BEERS
# ─────────────────────────────────────────────

def similar_beers(beer_id, n: int = 10) -> pd.DataFrame:
    """
    Return top-N beers most similar to a given beer.
    """

    if beer_id not in beer_id_to_index:
        raise ValueError(f"Beer id '{beer_id}' not found.")

    beer_idx = beer_id_to_index[beer_id]

    similarities = cosine_similarity(
        beer_feature_matrix[beer_idx],
        beer_feature_matrix,
    ).flatten()

    ranked_indices = np.argsort(similarities)[::-1]

    # Remove the beer itself
    ranked_indices = [idx for idx in ranked_indices if idx != beer_idx]

    top_indices = ranked_indices[:n]

    results = item_profiles.iloc[top_indices][
        [
            "beer_id",
            "beer_name",
            "beer_style",
            "beer_abv",
            "avg_overall_rating",
            "total_reviews_count",
        ]
    ].copy()

    results["cb_score"] = similarities[top_indices]

    return results.sort_values("cb_score", ascending=False)


# ─────────────────────────────────────────────
# 5. BUILD USER TASTE PROFILE
# ─────────────────────────────────────────────

def build_user_profile(user_id: str):
    """
    Build a user profile vector from beers the user rated.

    Beers with higher rating_overall influence the profile more.
    """

    user_reviews = train_df[train_df["username"] == user_id].copy()

    if user_reviews.empty:
        raise ValueError(f"User '{user_id}' not found in train data.")

    user_reviews = user_reviews[user_reviews["beer_id"].isin(beer_id_to_index)]

    if user_reviews.empty:
        raise ValueError(
            f"User '{user_id}' has no rated beers available in item profiles."
        )

    beer_indices = user_reviews["beer_id"].map(beer_id_to_index).values
    ratings = user_reviews["rating_overall"].astype(float).values

    # Normalize ratings to [0, 1] if needed
    if ratings.max() > 1:
        ratings = ratings / ratings.max()

    weights = ratings.reshape(-1, 1)

    user_beer_vectors = beer_feature_matrix[beer_indices]

    # Weighted average of beer feature vectors
    user_profile = np.asarray(
        user_beer_vectors.multiply(weights).mean(axis=0)
    )

    return user_profile


# ─────────────────────────────────────────────
# 6. CB RECOMMEND
# ─────────────────────────────────────────────

def cb_recommend(user_id: str, n: int = 10) -> pd.DataFrame:
    """
    Return top-N content-based beer recommendations for a user.

    Strategy:
    1. Build user taste profile from beers they rated in train set.
    2. Compare profile to every beer using cosine similarity.
    3. Remove beers already rated by the user.
    4. Return the highest-scoring beers.
    """

    user_profile = build_user_profile(user_id)

    similarities = cosine_similarity(
        user_profile,
        beer_feature_matrix,
    ).flatten()

    already_rated = set(
        train_df[train_df["username"] == user_id]["beer_id"]
    )

    candidate_indices = [
        idx
        for idx, beer_id in enumerate(beer_ids)
        if beer_id not in already_rated
    ]

    candidate_scores = similarities[candidate_indices]
    top_order = np.argsort(candidate_scores)[::-1][:n]
    top_indices = [candidate_indices[i] for i in top_order]

    results = item_profiles.iloc[top_indices][
        [
            "beer_id",
            "beer_name",
            "beer_style",
            "beer_abv",
            "avg_overall_rating",
            "total_reviews_count",
        ]
    ].copy()

    results["cb_score"] = similarities[top_indices]

    return results.sort_values("cb_score", ascending=False)


# ─────────────────────────────────────────────
# 7. QUICK SANITY TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    sample_user = train_df["username"].iloc[0]

    print(f"\nTop-10 CB recommendations for user: {sample_user}")
    print(cb_recommend(sample_user, n=10))

    sample_beer = item_profiles["beer_id"].iloc[0]

    print(f"\nTop-10 beers similar to beer_id={sample_beer}")
    print(similar_beers(sample_beer, n=10))
