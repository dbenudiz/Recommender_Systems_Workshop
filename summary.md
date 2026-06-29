# Project Summary

## Datasets Used

- **BeerAdvocate** — user beer reviews, [Stanford SNAP / BeerAdvocate dataset](https://cseweb.ucsd.edu//~jmcauley/datasets.html#multi_aspect).
- **RateBeer** — user beer reviews, [Stanford SNAP / RateBeer dataset](https://cseweb.ucsd.edu//~jmcauley/datasets.html#multi_aspect).

Both JSON files are ingested via `data_processing/process_json.py` into PostgreSQL, then passed through a feature-engineering and train/val/test split pipeline (`data_processing/pipeline.py`) to produce enriched CSV files used by the recommendation pipelines.

&nbsp;<br>

## Technologies and Frameworks

### Frontend

- **React + Vite** — single-page application with tab-based dashboard, beer card rendering, and a Demo Data toggle for standalone exploration.

### Backend

- **FastAPI** — HTTP server wiring the CF, CB, and cold-start pipelines into REST endpoints; supports both development (`fastapi dev`) and production (`fastapi run`) modes.
- **Uvicorn** — ASGI server running the FastAPI application.

### Algorithmic

- **scikit-learn** — TF-IDF vectorisation and cosine similarity for the content-based pipeline.
- **scipy** — sparse matrix operations and truncated SVD for the collaborative filtering pipeline.
- **NumPy / pandas** — data manipulation, feature engineering, and train/val/test splits.

### Data Platforms

- **PostgreSQL** — stores the ingested BeerAdvocate and RateBeer review data.
- **In-memory online store** (`backend/online_store.py`) — holds real-time session ratings and score adjustments; resets on server restart.
- **`new_ratings.csv`** — append-only flat file persisting session ratings across restarts for eventual offline retraining.

### AI

- **Sparse SVD (scipy)** — matrix factorisation for collaborative filtering; operates entirely on sparse matrices to handle tens of thousands of users × beers without memory issues.
- **TF-IDF + cosine similarity (scikit-learn)** — content-based similarity across beer style, brewery, and textual features.

&nbsp;<br>

## Main Algorithms

- **Collaborative Filtering (sparse SVD)** — factorises the user–item rating matrix into latent factors; used for personalised recommendations for existing users. Supports real-time fold-in so new ratings are reflected immediately without retraining.
- **Content-Based (TF-IDF + cosine similarity)** — represents each beer as a feature vector and finds similar beers based on style, brewery, and text. Updates continuously as the user rates beers.
- **Hybrid blending** — CF and CB scores are linearly blended for the main recommendation feed.
- **MMR re-ranking** — Maximal Marginal Relevance applied to the hybrid scores to promote diversity in the recommendations.
- **Cold-start (cluster-based CB)** — new users complete a 10-beer quiz; answers are mapped to four style clusters (`hoppy`, `dark`, `sour`, `light`) and used to generate initial CB recommendations instantly.

&nbsp;<br>

## System Architecture

The system has three main layers: a React frontend, a FastAPI backend, and a pair of offline-trained recommendation pipelines.

1. A user enters the website and is either a guest or logged in to a user
2. Depending on user state(guest, new user, old user) in the database A user request (generic recommendation, quiz submission, tailored recommendation) is sent from the React frontend to the FastAPI backend via the `apiService.js` API client.
3. The backend routes the request to the appropriate pipeline — generic recommendations, cold-start, or hybrid scoring — and consults the in-memory online store for any pending session ratings.
4. Recommendations are generated: the CF pipeline projects the user's rating vector into the SVD latent space; the CB pipeline computes cosine similarities against pre-built item feature vectors. Scores are blended and MMR-reranked.
5. The backend returns a JSON list of beer recommendations (with metadata and match scores) to the frontend, which renders them as beer cards in the relevant tab.
6. When a user rates a beer, the rating is posted to `POST /ratings`, immediately excluded from future feeds, and used to apply heuristic score adjustments. It is also appended to `new_ratings.csv` for future offline retraining.

## Development Environment

- **VS Code + Claude** — used for both backend and frontend development.
- **PowerShell / terminal** — used for running scripts, managing services, and testing API endpoints.
- **pytest** — 102 unit tests (`test_pipelines.py`) and integration tests (`test_integration.py`).

&nbsp;<br>

## Development Evolution

- **Milestone 1:** Set up data ingestion from BeerAdvocate and RateBeer JSON files into PostgreSQL; basic feature engineering pipeline.
- **Milestone 2:** Implemented sparse SVD-based collaborative filtering pipeline with train/val/test evaluation across k ∈ {5, 10, 20, 50}.
- **Milestone 3:** Added TF-IDF content-based pipeline 
- **Milestone 4:** Created React based frontend for app using dummy data
- **Milestone 5:** Built FastAPI backend with hybrid recommendation endpoint; 
- **Milestone 6:** Created cold-start quiz flow with matching backend endpoint.
- **Milestone 7:** Improved React + Vite frontend Favorites, Discover, Top 50, and Adventurous tabs; added support for using real data and Demo Data toggle for standalone exploration.
- **Milestone 8:** Added MMR re-ranking for diversity, group recommendations endpoint, and CF weight tuning sweep.
- **Milestone 9:** Added real-time feedback loop: immediate exclusion of rated beers, heuristic score adjustments, and SVD fold-in for live recommendation updates without retraining.

&nbsp;<br>

## Evaluation

Model quality is evaluated by running `py train_models.py`, which trains the SVD model and reports per-k RMSE on the validation and test sets for k ∈ {5, 10, 20, 50}. The k with the lowest validation RMSE is selected automatically.

Hybrid CF/CB blending weights are evaluated separately via `py train_models.py --tune-weights`, which sweeps CF weights `[0.3, 0.4, 0.5, 0.6, 0.7, 0.8]` and reports Hit Rate@10 on the validation set for each blend.

## Main Features

- **Personalised recommendation feed** — hybrid CF + CB swimlanes ("Top Matches", "You Might Also Like") on the Home tab, MMR-reranked for diversity.
- **Cold-start onboarding** — new users rate 10 beers in a quiz; recommendations are available immediately, before any in-app interactions.
- **Real-time feedback loop** — rating a beer instantly removes it from feeds, applies score adjustments to similar beers, and triggers SVD fold-in so recommendations update live without retraining.
- **Adventurous tab** — surfaces mid-range picks (positions 50–200 of the user's predicted ranking) that diverge from core taste, with a "Surprise Me Again" re-roll button.
- **Top 50 tab** — community leaderboard sorted by average overall rating across all users.
- **Demo Data toggle** — the frontend ships with bundled sample beers so the UI can be previewed without the backend or database running.
- **Group recommendations** — `GET /recommendations/group` generates hybrid recommendations for a set of users simultaneously.
- **% Match badges** — every beer card displays a personalised hybrid score, a community average rating, or a rank badge depending on the tab.

## Open Issues, Limitations, and Future Work

- The in-memory online store resets on server restart; a persistent store (e.g. Redis) would allow session state to survive restarts.
- The SVD fold-in approach for real-time updates is a heuristic approximation; periodic full retraining using the accumulated `new_ratings.csv` is needed for long-term accuracy.
- CF fold-in for new users requires ≥ 5 session ratings before activating; users with fewer interactions rely on CB only.
- Hybrid blending weights are currently global; per-user weight adaptation could improve personalisation.
- The frontend does not yet persist Favorites or rated beers across browser sessions.

&nbsp;<br>

## Additional Comments

The decision to use sparse SVD (via scipy) rather than a dense matrix was critical for scaling to the full BeerAdvocate + RateBeer dataset (tens of thousands of users × beers). The Demo Data toggle proved very useful during frontend development, allowing UI work to proceed independently of backend availability. The `--tune-weights` flag in `train_models.py` provides a lightweight way to re-verify the optimal CF/CB blend after new data is added, without running a full grid search.
