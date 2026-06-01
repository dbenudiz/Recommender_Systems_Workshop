import cf_pipeline as cf
import cb_pipeline as cb
import numpy as np
import pandas as pd

from fastapi import FastAPI

STANDARD_LAMBDA = 0.5
CANDIDATE_NUM = 50

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
    
@app.get("/recommendations/{user_id}")
async def get_recommendation(user_id):
    cb_candidates = cb.cb_recommend(user_id, CANDIDATE_NUM)

    cf_candidates = cf.cf_recommend(user_id, CANDIDATE_NUM)

def create_hybrid_scores(user_id: str, cf_scores: pd.Series, cb_scores: pd.Series) -> pd.Series:
    return hybrid_scores(cf_scores, cb_scores, 0.5)

def hybrid_scores(cf_scores: pd.Series, cb_scores: pd.Series, alpha: int) -> pd.Series:
    return alpha * cf_scores + (1 - alpha) * cb_scores


def rerank_recommendations(candidates, recommendation_num, diversity_weight = STANDARD_LAMBDA):
    pass