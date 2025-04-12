import pandas as pd
import numpy as np
import folium as fl

def main():
    data = pd.read_json("amenities-vancouver.json.gz", compression="gzip", lines=True)
    
    # Different Themes of amenities
    themes = {
        "Nature": ["park", "watering_place", "fountain", "ranger_station", "hunting_stand", "observation_platform"],
        "Food": ["cafe", "fast_food", "bbq", "restaurant", "pub", "bar", "food_court", "ice_cream", "juice_bar", "bistro", "biergarten"],
        "History": ["place_of_worship", "monastery", "courthouse", "townhall"],
        "Science": ["research_institute", "science", "healthcare", "hospital", "pharmacy", "clinic", "veterinary", "chiropractor", "ATLAS_clean_room"],
        "Art": ["arts_centre", "theatre", "studio", "music_school"],
        "Entertainment": ["cinema", "nightclub", "stripclub", "gambling", "casino", "events_venue", "marketplace", "spa", "events_venue", "internet_cafe", "lounge", "shop|clothes", "leisure"],
        "Mode of Travel": ["car_rental", "bicycle_rental", "car_sharing", "taxi", "bus_station", "ferry_terminal", "seaplane_terminal", "motorcycle_rental", "parking", "charging_station", "EVSE"]
    }
    
    # Small filtering
    data = data[~data['name'].isna()]
    
    # Data with tags that contain wikidata or wikipedia values and other things that may be useful
    # Some places may not have wikidata or wikipedia, but may be interesting and contain other keys
    interesting_data = data[data['tags'].apply(lambda x: 'brand:wikidata' in x or 
                                               'brand:wikipedia' in x or 
                                               'official_name' in x or
                                               'opening_hours' in x or
                                               'cuisine' in x or
                                               'addr:street' in x or
                                               'addr:housenumber' in x)]
    print(interestin


    
if __name__=='__main__':
    main()