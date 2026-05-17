import psycopg2
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

db_params = {
    "dbname": "recommend_db",
    "user": "postgres",
    "password": "123456",
    "host": "localhost",
    "port": 5432
}

def load_data_from_db():
    print("Loading filtered data from PostgreSQL...")
    conn = psycopg2.connect(**db_params)
    
    query = """
        SELECT 
            username, 
            beer_id, 
            review_time, 
            rating_overall, 
            rating_taste, 
            rating_aroma, 
            rating_appearance, 
            rating_palate 
        FROM filtered_reviews;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def run_comprehensive_recommendation_eda(df):
    print("\n" + "="*20 + " STARTING EXTENDED DATASET HEALTH CHECK " + "="*20)
    
    print("\n[1/6] Checking for Missing Values (NaNs):")
    missing_data = df.isnull().sum()
    print(missing_data[missing_data > 0] if missing_data.sum() > 0 else "Great! No missing values found.")
    
    print("\n[2/6] Calculating Matrix Sparsity:")
    n_reviews = len(df)
    n_users = df['username'].nunique()
    n_beers = df['beer_id'].nunique()
    
    total_possible_ratings = n_users * n_beers
    sparsity = (1 - (n_reviews / total_possible_ratings)) * 100
    
    print(f" - Unique Users (U): {n_users:,}")
    print(f" - Unique Beers (I): {n_beers:,}")
    print(f" - Total Ratings (R): {n_reviews:,}")
    print(f" - Matrix Sparsity:   {sparsity:.4f}% (The matrix is {100 - sparsity:.4f}% dense)")
    
    print("\n[3/6] Analyzing Long-Tail Distribution:")
    user_counts = df['username'].value_counts()
    beer_counts = df['beer_id'].value_counts()
    print(f" - Median reviews per user: {user_counts.median()}")
    print(f" - Median reviews per beer: {beer_counts.median()}")
    
    print("\n[4/6] Describing Rating Distributions (Check for bias):")
    rating_cols = ['rating_overall', 'rating_taste', 'rating_aroma', 'rating_appearance', 'rating_palate']
    print(df[rating_cols].describe().loc[['mean', 'std', 'min', '50%', 'max']])
    
    print("\n[5/6] Computing Extended Spearman Correlation Matrix:")
    correlation_matrix = df[rating_cols].corr(method='spearman')
    print("\n--- Correlation Matrix ---")
    print(correlation_matrix.round(3))
    print("-" * 26)
    
    if 'rating_overall' in correlation_matrix.columns:
        overall_corr = correlation_matrix['rating_overall'].drop('rating_overall').sort_values(ascending=False)
        print("\nRanked features driving the 'rating_overall' score:")
        for feature, value in overall_corr.items():
            print(f" - {feature}: {value:.4f}")
            
    print("\n[6/6] VARIANCE INFLATION FACTOR (VIF) TEST:")
    print("Testing if taste, aroma, appearance, and palate overlap too much...")
    
    feature_cols = ['rating_taste', 'rating_aroma', 'rating_appearance', 'rating_palate']
    X = df[feature_cols].dropna()
    X_with_const = sm.add_constant(X)
    
    vif_data = pd.DataFrame()
    vif_data["Feature"] = X_with_const.columns
    vif_data["VIF_Score"] = [variance_inflation_factor(X_with_const.values, i) for i in range(len(X_with_const.columns))]
    
    vif_results = vif_data[vif_data['Feature'] != 'const'].sort_values(by='VIF_Score', ascending=False)
    print(vif_results.round(2))
    
    print("\n--- VIF Guide ---")
    print("Score < 5: Good (Feature brings unique information)")
    print("Score 5-10: Warning (Moderate overlap between features)")
    print("Score > 10: Danger (High multicollinearity - consider dropping)")
            
    print("\n" + "="*23 + " END OF HEALTH CHECK " + "="*23)

if __name__ == "__main__":
    df_clean = load_data_from_db()
    run_comprehensive_recommendation_eda(df_clean)