# CMPT 353 Project
#
#   Eric Li 301436381
#   Steven Duong 301552606
#
import pandas as pd
import numpy as np
import math
import folium as fl
import osmnx as ox
import networkx as nx
from SPARQLWrapper import SPARQLWrapper, JSON

def input_field():
    # Ask user for city. Assuming they will be in British Columbia, Canada
    city = input("Enter your city in British Columbia: ").strip()
    location = f"{city}, British Columbia, Canada"
    
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

    # Ask if they need a hotel to stay at
    while True:
        stay_hotel = input("Do you need a hotel? (yes/no): ").strip().lower()
        if stay_hotel == "yes":
            stay_hotel = True
            break
        elif stay_hotel == "no":
            stay_hotel = False
            break
        print("Invalid input. Please enter 'yes' or 'no'.")

    return location, theme, num_amenities, (start_lat, start_lon), transportation, stay_hotel

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    R = 6371
    return R*c

# Finds a route by pathing to the nearest neighbour based on ['lat, lon'] pairs
def find_nearest_amenities(data, start_coords, num_nearest):
    data["distance"] = data.apply(lambda row: haversine(start_coords[0], start_coords[1], row["lat"], row["lon"]), axis=1)
    nearest_amenities = data.nsmallest(num_nearest, "distance")  # Get the closest N amenities
    return nearest_amenities

def filter_amenities_by_theme(amenities, selected_theme):
    themes = {
        "nature": ["park", "watering_place", "fountain", "ranger_station", "hunting_stand", "observation_platform"],
        "food": ["cafe", "fast_food", "bbq", "restaurant", "pub", "bar", "food_court", "ice_cream", "juice_bar", "bistro", "biergarten"],
        "history": ["place_of_worship", "monastery", "courthouse", "townhall"],
        "science": ["research_institute", "science", "healthcare", "hospital", "pharmacy", "clinic", "veterinary", "chiropractor", "ATLAS_clean_room"],
        "art": ["arts_centre", "theatre", "studio", "music_school"],
        "entertainment": ["cinema", "nightclub", "stripclub", "gambling", "casino", "events_venue", "marketplace", "spa", "events_venue", "internet_cafe", "lounge", "shop|clothes", "leisure"],
        "mode of travel": ["car_rental", "bicycle_rental", "car_sharing", "taxi", "bus_station", "ferry_terminal", "seaplane_terminal", "motorcycle_rental", "parking", "charging_station", "EVSE"]
    }
    
    if selected_theme in themes:
        relevant_amenities = themes[selected_theme]
        return amenities[amenities["amenity"].isin(relevant_amenities)]
    else:
        return amenities  # Show all if no theme is selected
    
# Goes through a list of places, searching for hotels in each place and extracting their name and coordinates
def get_hotel(place):
    df_list = []
    tags = {'tourism': 'hotel'}
    
    print(f"Retrieving hotels for {place}...")
    try:
        gdf = ox.features_from_place(place, tags)

        def extract_coords(geom):
            if geom.geom_type == 'Point':
                return geom.y, geom.x
            else:
                return geom.centroid.y, geom.centroid.x
                
        gdf['lat'] = gdf['geometry'].apply(lambda geom: extract_coords(geom)[0])
        gdf['lon'] = gdf['geometry'].apply(lambda geom: extract_coords(geom)[1])

        if 'name' not in gdf.columns:
            gdf['name'] = "Hotel"
        else:
            gdf = gdf[gdf['name'].notna()]
            
        hotels_df = gdf[['name', 'lat', 'lon']].reset_index(drop=True)
        print(f"Retrieved {len(hotels_df)} hotels for {place}.")
        
        return hotels_df
    
    except Exception as e:
        print(f"Error retrieving hotels for {place}: {e}")
        return pd.DataFrame()
    
def create_tour_map(points, route, start_coords):
    # Create a map centered on the first point
    map_center = [points.iloc[0]['lat'], points.iloc[0]['lon']]
    tour_map = fl.Map(location=map_center, zoom_start=13)
    
    fl.Marker(
        location=start_coords, 
        popup="Start Location", 
        icon=fl.Icon(color="red")
    ).add_to(tour_map)
    
    # Add markers for each point
    for idx, row in points.iterrows():
        lat = row['lat']
        lon = row['lon']
        name = row.get('name', 'No Name')
        fl.Marker(location=[lat, lon], popup=name).add_to(tour_map)

    # draws the path connecting each point
    fl.PolyLine(locations=route, color='blue', weight=2.5, opacity=1).add_to(tour_map)
    
    return tour_map

# Finds proper paths between points using street network graph
def get_street_route(G, points_list):
    full_route = []
    for i in range(len(points_list) - 1):
        start_lat, start_lon = points_list[i]
        end_lat, end_lon = points_list[i+1]
        start_node = ox.distance.nearest_nodes(G, start_lon, start_lat)
        end_node = ox.distance.nearest_nodes(G, end_lon, end_lat)
        if not nx.has_path(G, start_node, end_node):
            print(f"No route found between {points_list[i]} and {points_list[i+1]}. Skipping.")
            continue
        try:
            path_nodes = nx.shortest_path(G, start_node, end_node, weight='length')
        except Exception as e:
            print(f"Error finding path between {points_list[i]} and {points_list[i+1]}: {e}")
            continue
        segment = []
        for node in path_nodes:
            node_data = G.nodes[node]
            segment.append([node_data['y'], node_data['x']])
        if i > 0 and segment:
            segment = segment[1:]
        full_route.extend(segment)

    return full_route
    
def main():
    data = pd.read_json("amenities-vancouver.json.gz", compression="gzip", lines=True)
    data = data[~data["name"].isna()]

    # Get inputs
    location, theme, num_amenities, start_coords, transportation, stay_hotel = input_field()
    
    filtered_amenities = filter_amenities_by_theme(data, theme)
    
    nearest_amenities = find_nearest_amenities(filtered_amenities, start_coords, num_amenities)

    route_points = [[start_coords[0], start_coords[1]]] + nearest_amenities[['lat', 'lon']].values.tolist()
    
    if stay_hotel:
        last_point = route_points[-1]
        hotel = get_hotel(location)
        
        if not hotel.empty:
            hotel["distance"] = hotel.apply(lambda row: haversine(last_point[0], last_point[1], row["lat"], row["lon"]), axis=1)
            nearest_hotel = hotel.nsmallest(1, "distance").iloc[0]
            route_points.append([nearest_hotel["lat"], nearest_hotel["lon"]])
            nearest_amenities = pd.concat([nearest_amenities, nearest_hotel.to_frame().T], ignore_index=True)
        else:
            print("No hotels found.")
    
    # Vancouver so far
    Graph = ox.graph_from_place(location, network_type=transportation, simplify=True)
    route = get_street_route(Graph, route_points)

    # Generate map
    tour_map = create_tour_map(nearest_amenities, route=route, start_coords=start_coords)
    tour_map.save("nearest_amenities_tour.html")

if __name__ == "__main__":
    main()