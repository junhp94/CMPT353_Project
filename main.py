# CMPT 353 Project
#
#   Eric Li 301436381
#   
#
import pandas as pd
import numpy as np
import math
import folium as fl

def input_field():
    
    # Ask for theme
    themes = ["food", "nature", "history", "science", "art", "entertainment"]
    while True:
        theme = input(f"Enter a theme ({', '.join(themes)}): ").strip().lower()
        if theme in themes:
            break
        print(f"Invalid choice. Please select from: {', '.join(themes)}.")

    # Ask for the number of amenities
    while True:
        try:
            num_amenities = input("Enter the number of amenities you want to visit: ").strip()
            if num_amenities:
                num_amenities = int(num_amenities)
                if num_amenities > 0:
                    break
            print("Please enter a valid positive number.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Ask for the starting location (latitude and longitude), can be changed later to ask for location rather than lat and lon
    while True:
        try:
            start_lat = input("Enter your starting latitude: ").strip()
            start_lon = input("Enter your starting longitude: ").strip()
            if start_lat and start_lon:
                start_lat, start_lon = float(start_lat), float(start_lon)
                break
            print("Latitude and longitude are required.")
        except ValueError:
            print("Invalid input. Please enter valid numeric values for latitude and longitude.")

    # Ask for mode of transportation
    transport_modes = ["walk", "drive", "bike"]
    while True:
        transportation = input(f"Choose your mode of transportation ({', '.join(transport_modes)}): ").strip().lower()
        if transportation in transport_modes:
            break
        print(f"Invalid choice. Please select from: {', '.join(transport_modes)}.")

    # Ask if they need a hotel stay
    while True:
        stay_hotel = input("Do you need a hotel stay? (yes/no): ").strip().lower()
        if stay_hotel == "yes":
            stay_hotel = True
            break
        elif stay_hotel == "no":
            stay_hotel = False
            break
        print("Invalid input. Please enter 'yes' or 'no'.")

    return theme, num_amenities, start_lat, start_lon, transportation, stay_hotel

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    R = 6371
    return R*c

# Finds a route by pathing to the nearest neighbour based on ['lat, lon'] pairs
def nearest_neighbor_route(points):

    route = [points[0]]
    unvisited = points[1:]
    
    while unvisited:
        last = route[-1]
        # Find the point in unvisited that's closest to the last visited point
        next_point = min(unvisited, key=lambda point: haversine(last[0], last[1], point[0], point[1]))
        route.append(next_point)
        unvisited.remove(next_point)
        
    return route
    
def create_tour_map(points, route):
    # Create a map centered on the first point
    map_center = [points.iloc[0]['lat'], points.iloc[0]['lon']]
    tour_map = fl.Map(location=map_center, zoom_start=13)
    
    # Add markers for each point
    for idx, row in points.iterrows():
        lat = row['lat']
        lon = row['lon']
        name = row.get('name', 'No Name')
        fl.Marker(location=[lat, lon], popup=name).add_to(tour_map)

    # draws the path connecting each point
    fl.PolyLine(locations=route, color='blue', weight=2.5, opacity=1).add_to(tour_map)
    
    return tour_map

# filter data to only include amenities in each theme.
def filter_by_theme(data, theme):

    themes = {
        "nature": ["park", "watering_place", "fountain", "ranger_station", "hunting_stand", "observation_platform"],
        "food": ["cafe", "fast_food", "bbq", "restaurant", "pub", "bar", "food_court", "ice_cream", "juice_bar", "bistro", "biergarten"],
        "history": ["place_of_worship", "monastery", "courthouse", "townhall"],
        "science": ["research_institute", "science", "healthcare", "hospital", "pharmacy", "clinic", "veterinary", "chiropractor", "ATLAS_clean_room"],
        "art": ["arts_centre", "theatre", "studio", "music_school"],
        "entertainment": ["cinema", "nightclub", "stripclub", "gambling", "casino", "events_venue", "marketplace", "spa", "events_venue", "internet_cafe", "lounge", "shop|clothes", "leisure"],
        "mode of travel": ["car_rental", "bicycle_rental", "car_sharing", "taxi", "bus_station", "ferry_terminal", "seaplane_terminal", "motorcycle_rental", "parking", "charging_station", "EVSE"]
    }
    if theme in themes:
        return data[data['amenity'].isin(themes[theme])]
    else:
        print(f"Warning: Theme '{themes}' not found. Available themes: {list(themes)}")
    return data[data['amenity'].isin(themes)]
    
def main():
    data = pd.read_json("amenities-vancouver.json.gz", compression="gzip", lines=True)
    
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
                                               'addr:housenumber' in x or
                                               'website' in x)]

    # starting point ideas
    transit_and_housing = [
    'ferry_terminal', 'seaplane terminal', 'bus_station', 'taxi', 
    'car_rental', 'car_sharing', 'bicycle_rental', 'motorcycle_rental',
    'parking', 'parking_entrance', 'parking_space', 'charging_station',
    'housing co-op', 'EVSE'
    ]
    starting_points = data[data['amenity'].isin(transit_and_housing)]
    
    # Takes inputs
    theme, num_amenities, start_lat, start_lon, transportation, stay_hotel = input_field()
    
    tour_points = filter_by_theme(interesting_data, theme).head(num_amenities)
    
     # Create a list of [lat, lon] pairs for route calculation
    points_list = [[row['lat'], row['lon']] for idx, row in tour_points.iterrows()]
    
    # Compute a logical route using nearest neighbor
    route = nearest_neighbor_route(points_list)
    
    # Create the tour map using the computed route and tour data for markers
    tour_map = create_tour_map(tour_points, route=route)
    tour_map.save("tour_map_30.html")
    
if __name__=='__main__':
    main()