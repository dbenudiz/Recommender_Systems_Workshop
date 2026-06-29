# Modules Description

## User Interface

- **Technology:** React + Vite
- **Responsibilities:** Display the beer recommendation dashboard; collect user interactions (ratings, onboarding inputs, search/filter inputs); manage local state for Favorites and rated beers; toggle between Demo Data and live backend mode.
- **Interactions:**
  - Calls backend APIs via `src/services/apiService.js` (e.g. `/recommendations/{user_id}`, `/beers/top`, `/beers/search`, `/onboarding/from-attributes`, `/ratings`).
  - Receives JSON responses from the backend and renders beer cards, match badges, and swimlanes.
- **More info:** Ships with bundled sample beers so the UI can be previewed without the backend running (Demo Data toggle). Dynamically fetches a valid user ID from `GET /users/sample` when switching to live mode — no hardcoded IDs.
- **Source code:** [`/frontend/src/`](./frontend/src/)

## Collaborative Filtering Pipeline

- **Technology:** scipy (sparse SVD), NumPy, joblib
- **Responsibilities:** Factorises the user–item rating matrix via truncated SVD; generates personalised score predictions for existing users; supports real-time fold-in so new ratings are reflected immediately without retraining.
- **Interactions:**
  - Trained offline by `train_models.py`; artifacts saved to `artifacts/`.
  - Loaded at server startup by `backend/api_server.py`.
  - Receives user rating vectors from the online store for fold-in.
  - Returns ranked beer score lists to the API server for hybrid blending.
- **More info:** Operates entirely on sparse matrices to handle tens of thousands of users × beers. Falls back to a small synthetic dataset (`dummy_data.py`) if real CSVs are absent.
- **Source code:** [`/cf_pipeline.py`](./cf_pipeline.py)

## Content-Based Pipeline

- **Technology:** scikit-learn (TF-IDF, cosine similarity), pandas
- **Responsibilities:** Builds a TF-IDF feature matrix over beer style, brewery, and text features; computes cosine similarity to generate item-based recommendations and similar-beer lookups.
- **Interactions:**
  - Trained offline by `train_models.py`; artifacts saved to `artifacts/`.
  - Loaded at server startup by `backend/api_server.py`.
  - Provides embeddings and similarity scores to the API server for hybrid blending and `/beers/similar/{beer_id}`.
- **More info:** Updates recommendations continuously as the user rates beers. Falls back to a 5-beer in-memory mini catalog if real CSVs are absent.
- **Source code:** [`/cb_pipeline.py`](./cb_pipeline.py)

## Cold-Start Module

- **Technology:** Item profiles CSV, CB pipeline, CF fold-in (SVD)
- **Responsibilities:** Generates initial recommendations for new users via two methods before any in-app interaction history exists.
- **Interactions:**
  - Reads item profiles from the CB pipeline (`cb.item_profiles`, `cb.beer_feature_matrix`).
  - **Method 1** (`cold_start_from_ratings`): receives a dict of `{beer_id: rating}` collected by the frontend; builds a CB user profile and, if ≥ 3 beers are rated, folds the new user into the CF latent space. CF weight scales linearly from 0 → 0.6 as ratings grow from 3 → 5.
  - **Method 2** (`cold_start_from_attributes`): receives aspect importance scores (taste/aroma/appearance/palate 1–5), ABV preference, and style chips; maps importance levels to quantile targets in the 8-column numeric sub-space of the beer feature matrix and blends 70% numeric similarity + 30% style-cluster prior.
  - Exposes `POST /onboarding/from-attributes` (Method 2) and `POST /onboarding/hybrid` (combined) in the API server; Method 1 ratings are submitted individually via `POST /ratings`.
- **More info:** Both functions return a `pd.Series` (index = beer_id, values = score) compatible with the hybrid pipeline. `GET /beers/search` (declared before `/beers/{beer_id}` to avoid path collision) supports the Method 1 beer search UI.
- **Source code:** [`/cold_start.py`](./cold_start.py)

## Real-Time Online Store

- **Technology:** In-memory Python module
- **Responsibilities:** Tracks session ratings, applies heuristic score adjustments (±20% for similar beers based on rating polarity), and records which beers have been rated so they can be excluded from future feeds.
- **Interactions:**
  - Updated by `POST /ratings` in the API server.
  - Consulted by the CF and CB pipelines when generating recommendations.
  - Appends ratings to `new_ratings.csv` for future offline retraining (best-effort, non-blocking).
- **More info:** State resets on server restart. `new_ratings.csv` persists across restarts and can be merged into training data before the next `train_models.py` run.
- **Source code:** [`/backend/online_store.py`](./backend/online_store.py)

## Data Ingestion Pipeline

- **Technology:** Python, psycopg2, pandas
- **Responsibilities:** Reads raw BeerAdvocate and RateBeer JSON files, validates rows, and loads them into PostgreSQL; then performs feature engineering and produces train/val/test CSV splits.
- **Interactions:**
  - Reads local JSON files (paths configured by the user).
  - Writes to the `recommend_db` PostgreSQL database.
  - Outputs `data/train_set.csv`, `data/val_set.csv`, `data/test_set.csv`, and `data/item_profiles_for_cold_start.csv`.
- **Source code:** [`/data_processing/`](./data_processing/)

## API Gateway / Backend Server

- **Technology:** FastAPI, Uvicorn
- **Responsibilities:** Exposes all HTTP endpoints; orchestrates requests between the CF pipeline, CB pipeline, cold-start module, and online store; handles hybrid score blending and MMR re-ranking.
- **Interactions:**
  - Handles all requests from the React frontend.
  - Loads CF and CB pipeline artifacts from `artifacts/` at startup.
  - Dispatches to the appropriate pipeline based on the endpoint called.
  - Returns JSON recommendation lists with beer metadata and match scores.
- **More info:** Hybrid blending uses `STANDARD_CF_WEIGHT = 0.6` (tunable via `py train_models.py --tune-weights`). Supports development (`fastapi dev`, auto-reload) and production (`fastapi run`) modes.
- **Source code:** [`/backend/api_server.py`](./backend/api_server.py)
