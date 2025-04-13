import pandas as pd
import numpy as np
import math
import folium as fl
import osmnx as ox
import networkx as nx
from SPARQLWrapper import SPARQLWrapper, JSON
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta


def extract_wikidata_ids(amenities_df):
    """Extract Wikidata Q-numbers from tags column"""
    if "tags" not in amenities_df.columns:
        return amenities_df

    def get_wikidata_id(tags):
        if not isinstance(tags, dict):
            return None
        return tags.get("wikidata") or tags.get("brand:wikidata")

    amenities_df["wikidata_id"] = amenities_df["tags"].apply(get_wikidata_id)
    return amenities_df


# def fetch_wikidata_info(wikidata_id):
#     """Fetch basic info from Wikidata"""
#     if not wikidata_id:
#         return None

#     try:
#         sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
#         query = f"""
#         SELECT ?itemLabel ?description WHERE {{
#             wd:{wikidata_id} rdfs:label ?itemLabel.
#             FILTER(LANG(?itemLabel) = "en").
#             OPTIONAL {{ wd:{wikidata_id} schema:description ?description.
#                        FILTER(LANG(?description) = "en") }}
#         }}
#         """
#         sparql.setQuery(query)
#         sparql.setReturnFormat(JSON)
#         results = sparql.query().convert()

#         if results["results"]["bindings"]:
#             return {
#                 "name": results["results"]["bindings"][0]
#                 .get("itemLabel", {})
#                 .get("value"),
#                 "description": results["results"]["bindings"][0]
#                 .get("description", {})
#                 .get("value"),
#             }
#     except Exception as e:
#         print(f"Error fetching Wikidata info for {wikidata_id}: {e}")
#     return None


def fetch_wikidata_info(wikidata_id):
    """Fetch all available info from Wikidata for exploration."""
    if not wikidata_id:
        return None

    try:
        sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        query = f"""
        SELECT ?itemLabel ?description WHERE {{
            wd:{wikidata_id} rdfs:label ?itemLabel.
            FILTER(LANG(?itemLabel) = "en").
            OPTIONAL {{ wd:{wikidata_id} schema:description ?description.
                       FILTER(LANG(?description) = "en") }}
        }}
        """
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        # Print the full raw result for inspection
        print(f"Raw SPARQL result for {wikidata_id}:")
        import json

        print(json.dumps(results, indent=2))
        print()

        return results  # or just results['results']['bindings'] if you want that part
    except Exception as e:
        print(f"Error fetching Wikidata info for {wikidata_id}: {e}")
    return None


def main():
    original_data = pd.read_json(
        "amenities-vancouver.json.gz", compression="gzip", lines=True
    )

    print(original_data["amenity"].unique())
    # data = original_data[
    #     (~original_data["name"].isna()) & (original_data["amenity"] == "restaurant")
    #     | (original_data["amenity"] == "bistro")
    # ]

    # data = extract_wikidata_ids(data)
    # data_with_wikidata = data[~data["wikidata_id"].isna()]

    # # Fetch and print info for first 5 entries
    # for idx, row in data_with_wikidata.head(20).iterrows():
    #     wikidata_id = row["wikidata_id"]
    #     info = fetch_wikidata_info(wikidata_id)
    #     print(f"{row['name']} ({wikidata_id}):")
    #     print(f"  Name: {info.get('name') if info else 'N/A'}")
    #     print(f"  Description: {info.get('description') if info else 'N/A'}")
    #     print()

    # Just look at the first one for now
    # first = data_with_wikidata.iloc[100]
    # fetch_wikidata_info(first["wikidata_id"])


if __name__ == "__main__":
    main()
