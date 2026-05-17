import ast
import psycopg2
import os

# ==========================================
# CENTRAL CONFIGURATION
# ==========================================
file_path_1 = r'C:\year3\recommenderSystem\beeradvocate.json\beeradvocate.json'
file_path_2 = r'C:\year3\recommenderSystem\beeradvocate.json\ratebeer.json\ratebeer.json'
log_file_path = r'C:\year3\recommenderSystem\bad_rows_log.txt'

DB_PARAMS = {
    "dbname": "recommend_db",
    "user": "postgres",
    "password": "123456",
    "host": "localhost",
    "port": 5432
}

BATCH_SIZE = 1000

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def parse_rating(rating_str):
    """Normalizes all ratings (fractions or integers) to a clean 1.0 - 5.0 float."""
    if not rating_str:
        return 0.0
    rating_str = str(rating_str).strip()
    if '/' in rating_str:
        try:
            parts = rating_str.split('/')
            return (float(parts[0]) / float(parts[1])) * 5.0
        except (ValueError, ZeroDivisionError, IndexError):
            return 0.0
    try:
        val = float(rating_str)
        return (val / 20.0) * 5.0 if val > 5.0 else val
    except ValueError:
        return 0.0

def create_database_schema(cursor):
    """Initializes the PostgreSQL Star Schema with full 5-rating tracking."""
    print("Initializing Database Schema...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY
        );
        
        CREATE TABLE IF NOT EXISTS beers (
            beer_id INT PRIMARY KEY,
            beer_name TEXT,
            brewer_id INT,
            beer_abv FLOAT,
            beer_style TEXT
        );
        
        CREATE TABLE IF NOT EXISTS reviews (
            username TEXT,
            beer_id INT,
            review_time BIGINT,
            rating_overall FLOAT,
            rating_taste FLOAT,
            rating_aroma FLOAT,
            rating_appearance FLOAT,
            rating_palate FLOAT,
            review_text TEXT,
            PRIMARY KEY (username, beer_id)
        );
    """)

# ==========================================
# PHASE 1: MAIN INGESTION & ERROR LOGGING
# ==========================================
def process_main_file(path, file_label, cursor, conn):
    """Reads raw dataset, ingests clean rows, and logs malformed rows in one single pass."""
    print(f"\n--- Starting Ingestion & Log Discovery for {file_label} ---")
    
    batch_users = set()
    batch_beers = {}
    batch_reviews = []
    
    good_row_count = 0          
    bad_row_count = 0
    physical_line_count = 0 
    
    with open(path, 'r', encoding='utf-8') as f, open(log_file_path, 'a', encoding='utf-8') as log_file:
        for line in f:
            physical_line_count += 1
            line = line.strip()
            
            if not line:
                continue
                
            if physical_line_count % 250000 == 0:
                print(f"[Progress] Evaluated {physical_line_count:,} lines... Staged: {good_row_count:,} | Logged Bad: {bad_row_count:,}")
            
            if '\x00' in line:
                log_file.write(f"[{file_label}] Line {physical_line_count} | Error: Contains NUL (0x00) | Data: {line}\n")
                bad_count += 1
                continue
                
            try:
                row = ast.literal_eval(line)
                
                raw_username = row.get('review/profileName')
                username = raw_username.replace('\x00', '') if raw_username else None
                
                raw_beer_id = row.get('beer/beerId')
                if not username or not raw_beer_id:
                    continue
                
                beer_id = int(raw_beer_id)
                
                batch_users.add(username)
                
                try:
                    abv = float(row.get('beer/ABV')) if row.get('beer/ABV') else None
                except ValueError:
                    abv = None
                    
                beer_name = row.get('beer/name').replace('\x00', '') if row.get('beer/name') else None
                beer_style = row.get('beer/style').replace('\x00', '') if row.get('beer/style') else None
                    
                batch_beers[beer_id] = (beer_name, int(row.get('beer/brewerId')) if row.get('beer/brewerId') else None, abv, beer_style)
                
                try:
                    review_time = int(row.get('review/time', 0))
                except ValueError:
                    review_time = 0

                review_text = row.get('review/text', '').replace('\x00', '') if row.get('review/text') else ''

                batch_reviews.append((
                    username, beer_id, review_time,
                    parse_rating(row.get('review/overall')),
                    parse_rating(row.get('review/taste')),
                    parse_rating(row.get('review/aroma')),
                    parse_rating(row.get('review/appearance')),
                    parse_rating(row.get('review/palate')),
                    review_text
                ))
                good_row_count += 1
                
                if len(batch_reviews) >= BATCH_SIZE:
                    execute_batch_insert(cursor, conn, batch_users, batch_beers, batch_reviews)
                    batch_users, batch_beers, batch_reviews = set(), {}, []
                    
            except Exception as e:
                log_file.write(f"[{file_label}] Line {physical_line_count} | Error: {e} | Data: {line}\n")
                bad_row_count += 1

        if batch_reviews:
            execute_batch_insert(cursor, conn, batch_users, batch_beers, batch_reviews)

    print(f"[SUCCESS] {file_label} complete. Ingested: {good_row_count:,} | Logged for recovery: {bad_row_count:,}")

def execute_batch_insert(cursor, conn, batch_users, batch_beers, batch_reviews):
    """Executes the standard fast batch insert with UPSERT logic."""
    try:
        cursor.executemany("INSERT INTO users (username) VALUES (%s) ON CONFLICT (username) DO NOTHING", [(u,) for u in batch_users])
        cursor.executemany("INSERT INTO beers (beer_id, beer_name, brewer_id, beer_abv, beer_style) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (beer_id) DO NOTHING", [(k, v[0], v[1], v[2], v[3]) for k, v in batch_beers.items()])
        cursor.executemany("""
            INSERT INTO reviews (username, beer_id, review_time, rating_overall, rating_taste, rating_aroma, rating_appearance, rating_palate, review_text) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
            ON CONFLICT (username, beer_id) 
            DO UPDATE SET 
                rating_overall = CASE WHEN EXCLUDED.review_time >= reviews.review_time THEN EXCLUDED.rating_overall ELSE reviews.rating_overall END,
                rating_taste = CASE WHEN EXCLUDED.review_time >= reviews.review_time THEN EXCLUDED.rating_taste ELSE reviews.rating_taste END,
                rating_aroma = CASE WHEN EXCLUDED.review_time >= reviews.review_time THEN EXCLUDED.rating_aroma ELSE reviews.rating_aroma END,
                rating_appearance = CASE WHEN EXCLUDED.review_time >= reviews.review_time THEN EXCLUDED.rating_appearance ELSE reviews.rating_appearance END,
                rating_palate = CASE WHEN EXCLUDED.review_time >= reviews.review_time THEN EXCLUDED.rating_palate ELSE reviews.rating_palate END,
                review_time = GREATEST(reviews.review_time, EXCLUDED.review_time),
                review_text = CASE 
                    WHEN reviews.review_text = EXCLUDED.review_text THEN reviews.review_text
                    WHEN EXCLUDED.review_text = '' THEN reviews.review_text
                    ELSE reviews.review_text || ' | Update: ' || EXCLUDED.review_text 
                END
        """, batch_reviews)
        conn.commit()
    except Exception as db_e:
        conn.rollback()
        print(f"[Warning] Rolling back batch due to error: {db_e}")

# ==========================================
# PHASE 2: ERROR RECOVERY & INJECTION
# ==========================================
def process_bad_rows_log(cursor, conn):
    """Parses the generated error log, applies specialized regex/string mending, and forces ingestion."""
    print("\n--- [Phase 2] מתחיל לחלץ ולתקן נתונים מקובץ הלוג ---")
    
    if not os.path.exists(log_file_path) or os.path.getsize(log_file_path) == 0:
        print("קובץ הלוג ריק או לא קיים. אין שורות פגומות לתיקון.")
        return

    batch_users = set()
    batch_beers = {}
    batch_reviews = []
    recovered_count = 0
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if 'Data: {' not in line:
                continue
                
            try:
                data_str = line.split('Data: ', 1)[1]
                row = ast.literal_eval(data_str)
                
                username = row.get('review/profileName').replace('\x00', '') if row.get('review/profileName') else None
                
                # תיקון מזהה בירה משובש (פיצול מקפים)
                raw_beer_id = row.get('beer/beerId')
                if not raw_beer_id:
                    beer_id = None
                else:
                    try:
                        beer_id = int(raw_beer_id)
                    except ValueError:
                        if isinstance(raw_beer_id, str) and '-' in raw_beer_id:
                            try:
                                beer_id = int(raw_beer_id.split('-')[-1])
                            except ValueError:
                                beer_id = None
                        else:
                            beer_id = None
                            
                if not username or not beer_id:
                    continue
                    
                batch_users.add(username)
                
                try:
                    abv = float(row.get('beer/ABV')) if row.get('beer/ABV') else None
                except ValueError:
                    abv = None
                    
                beer_name = row.get('beer/name').replace('\x00', '') if row.get('beer/name') else None
                beer_style = row.get('beer/style').replace('\x00', '') if row.get('beer/style') else None
                    
                batch_beers[beer_id] = (beer_name, int(row.get('beer/brewerId')) if row.get('beer/brewerId') else None, abv, beer_style)
                
                try:
                    review_time = int(row.get('review/time', 0))
                except ValueError:
                    review_time = 0

                review_text = row.get('review/text', '').replace('\x00', '') if row.get('review/text') else ''

                batch_reviews.append((
                    username, beer_id, review_time,
                    parse_rating(row.get('review/overall')),
                    parse_rating(row.get('review/taste')),
                    parse_rating(row.get('review/aroma')),
                    parse_rating(row.get('review/appearance')), 
                    parse_rating(row.get('review/palate')),     
                    review_text
                ))
                recovered_count += 1
                
            except Exception:
                continue

    if batch_reviews:
        try:
            print(f"נאספו {recovered_count:,} שורות משובשות שתוקנו בהצלחה! מזריק ל-DB...")
            cursor.executemany("INSERT INTO users (username) VALUES (%s) ON CONFLICT (username) DO NOTHING", [(u,) for u in batch_users])
            cursor.executemany("INSERT INTO beers (beer_id, beer_name, brewer_id, beer_abv, beer_style) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (beer_id) DO NOTHING", [(k, v[0], v[1], v[2], v[3]) for k, v in batch_beers.items()])
            cursor.executemany("""
                INSERT INTO reviews (username, beer_id, review_time, rating_overall, rating_taste, rating_aroma, rating_appearance, rating_palate, review_text) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
                ON CONFLICT (username, beer_id) 
                DO UPDATE SET 
                    rating_overall = CASE WHEN EXCLUDED.review_time >= reviews.review_time THEN EXCLUDED.rating_overall ELSE reviews.rating_overall END,
                    rating_taste = CASE WHEN EXCLUDED.review_time >= reviews.review_time THEN EXCLUDED.rating_taste ELSE reviews.rating_taste END,
                    rating_aroma = CASE WHEN EXCLUDED.review_time >= reviews.review_time THEN EXCLUDED.rating_aroma ELSE reviews.rating_aroma END,
                    rating_appearance = CASE WHEN EXCLUDED.review_time >= reviews.review_time THEN EXCLUDED.rating_appearance ELSE reviews.rating_appearance END,
                    rating_palate = CASE WHEN EXCLUDED.review_time >= reviews.review_time THEN EXCLUDED.rating_palate ELSE reviews.rating_palate END,
                    review_time = GREATEST(reviews.review_time, EXCLUDED.review_time),
                    review_text = CASE 
                        WHEN reviews.review_text = EXCLUDED.review_text THEN reviews.review_text
                        WHEN EXCLUDED.review_text = '' THEN reviews.review_text
                        ELSE reviews.review_text || ' | Update: ' || EXCLUDED.review_text 
                    END
            """, batch_reviews)
            conn.commit()
            print("מבצע חילוץ והצלה הסתיים בהצלחה!")
        except Exception as db_e:
            conn.rollback()
            print(f"שגיאת Database בזמן הזרקת התיקונים מהלוג: {db_e}")

# ==========================================
# MAIN ROUTINE
# ==========================================
if __name__ == "__main__":
    open(log_file_path, 'w', encoding='utf-8').close()
    
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    create_database_schema(cursor)
    conn.commit()
    
    process_main_file(file_path_1, "File 1 (BeerAdvocate)", cursor, conn)
    process_main_file(file_path_2, "File 2 (RateBeer)", cursor, conn)
    
    process_bad_rows_log(cursor, conn)
    
    cursor.close()
    conn.close()
    print("\n[SUCCESS].")