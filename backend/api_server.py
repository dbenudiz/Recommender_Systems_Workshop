import cf_pipeline as cf
import cb_pipeline as cb
import pandas as pd

from fastapi import FastAPI

STANDARD_LAMBDA = 0.5
CANDIDATE_NUM = 50
HYBRID_CANDIDATE_NUM = 25
FINAL_RECOMMENDATION_NUM = 10

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
    
@app.get("/recommendations/{user_id}")
async def get_recommendation(user_id):
    cb_candidates = cb.cb_recommend(user_id, CANDIDATE_NUM)
    cf_candidates = cf.cf_recommend(user_id, CANDIDATE_NUM)

    hybrid_candidates = create_hybrid_scores(user_id, cf_candidates, cb_candidates)
    # TODO: use cross-validation to select lambda
    selected_recommendations = rerank_recommendations(hybrid_candidates, FINAL_RECOMMENDATION_NUM)

    return {
            "recommended_ids:": selected_recommendations.index.tolist()
        }

def create_hybrid_scores(user_id: str, cf_scores: pd.Series, cb_scores: pd.Series) -> pd.Series:
    # TODO: adjust alpha based on how much data is available for user
    hybridized = hybrid_scores(cf_scores, cb_scores, 0.5)
    # reduce candidates after hybridizing scores
    return hybridized.nlargest(HYBRID_CANDIDATE_NUM)

def hybrid_scores(cf_scores: pd.Series, cb_scores: pd.Series, alpha: int) -> pd.Series:
    return alpha * cf_scores + (1 - alpha) * cb_scores


def rerank_recommendations(candidates: pd.Series, recommendation_num: int, diversity_weight: float = STANDARD_LAMBDA):
    # TODO: add MMR implementation
    return candidates.nlargest(recommendation_num)