# Modules Description

## User Interface

- **Technology:** React + Vite
- **Responsibilities:** Display the beer recommendation dashboard; collect user interactions (ratings, quiz answers, search/filter inputs); manage local state for Favorites and rated beers; toggle between Demo Data and live backend mode.
- **Interactions:**
  - Calls backend APIs via `src/services/apiService.js` (e.g. `/recommendations/{user_id}`, `/beers/top`, `/quiz`, `/ratings`).
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

- **Technology:** Item profiles CSV, cluster-based scoring
- **Responsibilities:** Generates initial recommendations for new users based on their onboarding quiz answers, before any in-app interactions.
- **Interactions:**
  - Reads `data/item_profiles_for_cold_start.csv` (produced by `data_processing/pipeline.py`).
  - Receives cluster scores (`hoppy`, `dark`, `sour`, `light`) posted by the frontend to `POST /recommendations/cold-start`.
  - Returns a ranked list of beers to the API server.
- **More info:** The frontend maps the 10-beer quiz ratings to the four clusters and posts average cluster scores. Recommendations are available immediately after quiz submission.
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
