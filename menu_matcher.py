# pip install rapidfuzz

from rapidfuzz import process, fuzz
import pandas as pd
import re

_DROP_WORDS = re.compile(
    r'\b(brewery|brewing|beer|ale|lager|bier|co|company|ltd|inc)\b', re.I
)


def _normalize(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9\s]', ' ', name)   # strip punctuation
    name = _DROP_WORDS.sub(' ', name)
    return re.sub(r'\s+', ' ', name).strip()


def match_menu_beers(
    extracted: list[dict],        # [{"name": str, "brewery": str | None}, ...]
    item_profiles_df,             # pd.DataFrame with columns: beer_id, beer_name
    threshold: int = 75,
) -> tuple[list, int]:
    """
    Fuzzy-match extracted menu beer names to item_profiles entries.
    Returns: (matched_beer_ids, total_extracted_count)
    - matched_beer_ids: list of beer_id values (native dtype from the DataFrame)
    - total_extracted_count: len(extracted) — how many names were found on the menu
    """
    total_extracted_count = len(extracted)

    catalog_names = item_profiles_df['beer_name'].tolist()
    catalog_ids = item_profiles_df['beer_id'].tolist()
    catalog_names_norm = [_normalize(n) for n in catalog_names]

    matched_beer_ids = []
    seen_ids = set()

    for item in extracted:
        name = item.get('name', '')
        brewery = item.get('brewery')
        if brewery is not None:
            search_str = f"{name} {brewery}"
        else:
            search_str = name
        search_norm = _normalize(search_str)

        result = process.extractOne(
            search_norm,
            catalog_names_norm,
            scorer=fuzz.token_set_ratio,
        )
        if result is None:
            continue

        _match, score, idx = result
        if score >= threshold:
            beer_id = catalog_ids[idx]
            if beer_id not in seen_ids:
                seen_ids.add(beer_id)
                matched_beer_ids.append(beer_id)

    return matched_beer_ids, total_extracted_count
