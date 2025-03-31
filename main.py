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
    # Ask user how long their tour is
    while True:
        tour_length = input("Enter length of tour: ").strip()
        tour_length = int(tour_length)
        if tour_length > 0:
            break
        print("Invalid number. Please enter length of tour in days: ")
    
    # Ask for theme
    themes = ["food", "nature", "history", "science", "art", "entertainment", "random"]
    while True:
        theme = input(f"Enter a theme ({', '.join(themes)}): ").strip().lower()
        if theme in themes:
            break
        print(f"Invalid choice. Please select from: {', '.join(themes)}.")

    # Ask for the number of amenities
    while True:
        try:
            num_amenities = input("Enter the total number of amenities you want to visit: ").strip()
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

    return tour_length, theme, num_amenities, (start_lat, start_lon), transportation, stay_hotel

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    R = 6371
    return R*c

# Finds a route by pathing to the nearest neighbour based on ['lat, lon'] pairs
def find_nearest_amenities(amenities, start_coords, num_amenities):
    amenities_copy = amenities.copy()
    route = []
    current_location = start_coords
    
    for _ in range(num_amenities):
        if amenities_copy.empty:
            break
        
        amenities_copy["distance"] = amenities_copy.apply(
            lambda row: haversine(current_location[0], current_location[1], row["lat"], row["lon"]), axis=1
        )
        nearest_amenity = amenities_copy.nsmallest(1, "distance").iloc[0]
        
        route.append(nearest_amenity)
        current_location = (nearest_amenity["lat"], nearest_amenity["lon"])
        
        amenities_copy = amenities_copy.drop(nearest_amenity.name)
    
    return pd.DataFrame(route)

def filter_amenities_by_theme(amenities, selected_theme):
    themes = {
        "nature": ["park", "watering_place", "fountain", "ranger_station", "hunting_stand", "observation_platform"],
        "food": ["cafe", "bbq", "restaurant", "pub", "bar", "food_court", "ice_cream", "juice_bar", "bistro", "biergarten"],
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
def get_hotels(places):
    
    df_list = []
    tags = {'tourism': 'hotel'}
    
    for place in places:
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
            df_list.append(hotels_df)
            
        except Exception as e:
            print(f"Error retrieving hotels for {place}: {e}")
            
    if df_list:
        combined = pd.concat(df_list, ignore_index=True)
        print(f"Total hotels retrieved: {len(combined)}")
        return combined
    else:
        return pd.DataFrame()

# Goes through a list of places, searching for restaurants in each place and extracting their name and coordinates
def get_restaurants(places):
    
    df_list = []
    tags = { 'amenity': [ "bbq", "restaurant", "pub", "bar", "bistro"]}
    
    for place in places:
        print(f"Retrieving restaurants for {place}...")
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
                gdf['name'] = "Restaurant"
            else:
                gdf = gdf[gdf['name'].notna()]
                
            restaurants_df = gdf[['name', 'lat', 'lon']].reset_index(drop=True)
            print(f"Retrieved {len(restaurants_df)} restaurants for {place}.")
            df_list.append(restaurants_df)
            
        except Exception as e:
            print(f"Error retrieving restaurants for {place}: {e}")
            
    if df_list:
        combined = pd.concat(df_list, ignore_index=True)
        print(f"Total restaurants retrieved: {len(combined)}")
        return combined
    else:
        return pd.DataFrame()
    
def get_combined_graph(places, network_type):
    
    graphs = []
    for place in places:
        try:
            print(f"Downloading graph for {place}...")
            G = ox.graph_from_place(place, network_type=network_type)
            graphs.append(G)
        except Exception as e:
            print(f"Error downloading graph for {place}: {e}")
    if graphs:
        combined_graph = ox.graph_to_gdfs(nx.compose_all(graphs), nodes=True, edges=True)
        G = ox.graph_from_gdfs(combined_graph[0], combined_graph[1])
        return G
    else:
        return None
    
def create_tour_map(points, route, start_coords):
    # Create a map centered on the first point
    map_center = [points.iloc[0]['lat'], points.iloc[0]['lon']]
    tour_map = fl.Map(location=map_center, zoom_start=13)
    
    # Add start location marker
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
        
        marker_color = "blue"

        if "type" in row:
            if row["type"] == "restaurant":
                marker_color = "orange"
            elif row["type"] == "hotel":
                marker_color = "green"
        
        # Add the marker with the corresponding color
        fl.Marker(
            location=[lat, lon], 
            popup=name, 
            icon=fl.Icon(color=marker_color)
        ).add_to(tour_map)
    
    # Draw the path connecting each point
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

# Filters "popular" amenities based on number of tags
def filter_popular_amenities(data, min_tags=5):
    if 'tags' in data.columns:
        return data[data['tags'].apply(lambda tags: len(tags) >= min_tags)]
    else:
        print("No 'tags' column found in data.")
        return data  # Return unfiltered data if no 'tags' column is found

regions = [
    "Metro Vancouver, British Columbia, Canada",
    #"Fraser Valley, British Columbia, Canada"
    "Abbotsford, British Columbia, Canada",
    "Mission, British Columbia, Canada"
    ]
    
def main():
    data = pd.read_json("amenities-vancouver.json.gz", compression="gzip", lines=True)
    data = data[~data["name"].isna()]

    # Get inputs
    tour_length, theme, num_amenities, start_coords, transportation, stay_hotel = input_field()
    
    if theme == 'random':
        # Filters out big chains
        data = data[data['amenity'] != 'fast_food']
        data = data[data['name'] != 'Starbucks']
        data = data[~data['name'].isin(['Tim Hortons', 'Tim_Hortons'])]
        popular_amenities = filter_popular_amenities(data,min_tags=5) # Popular amenities have 5 or more tags
    else:
        filtered_amenities = filter_amenities_by_theme(data, theme)
        popular_amenities = filter_popular_amenities(filtered_amenities,min_tags=5) # Popular amenities have 5 or more tags
    
    nearest_amenities = find_nearest_amenities(popular_amenities, start_coords, num_amenities)

    route_points = [[start_coords[0], start_coords[1]]] + nearest_amenities[['lat', 'lon']].values.tolist()
    
    restaurants = get_restaurants(regions)
    
    if stay_hotel:
        housing = data[data['amenity'] == 'housing co-op']
        hotels = get_hotels(regions)

        if not hotels.empty or not housing.empty:
            # Combine hotels and housing
            lodging_points = pd.concat([housing, hotels], ignore_index=True)

    if not restaurants.empty:
        updated_route_points = [route_points[0]]  # Start point
        updated_amenities = pd.DataFrame([nearest_amenities.iloc[0]])  # First point

        amenities_per_day = num_amenities // tour_length  # Number of amenities per day
        day_index = 0  # Track amenities count per day
        restaurant_count = 0  # Track how many restaurants added per day

        for i in range(1, len(route_points)):
            updated_route_points.append(route_points[i])

            if i < len(nearest_amenities):
                updated_amenities = pd.concat([updated_amenities, nearest_amenities.iloc[[i]]], ignore_index=True)

            day_index += 1

            # Ensure exactly 3 restaurants per day
            if restaurant_count < 3:
                last_point = route_points[i]

                if not restaurants.empty:
                    restaurants["distance"] = restaurants.apply(
                        lambda row: haversine(last_point[0], last_point[1], row["lat"], row["lon"]), axis=1
                    )
                    nearest_restaurant = restaurants.nsmallest(1, "distance").iloc[0]

                    updated_route_points.append([nearest_restaurant["lat"], nearest_restaurant["lon"]])
                    nearest_restaurant["type"] = "restaurant"
                    updated_amenities = pd.concat([updated_amenities, nearest_restaurant.to_frame().T], ignore_index=True)

                    restaurant_count += 1

            # End of the day: Reset counters and add a hotel
            if day_index >= amenities_per_day:
                restaurant_count = 0  # Reset restaurant count for next day
                day_index = 0  # Reset amenity count for next day

                if stay_hotel and not lodging_points.empty:  # Add hotel at the end of each day
                    last_point = updated_route_points[-1]  # Get the last stop of the day

                    lodging_points["distance"] = lodging_points.apply(
                        lambda row: haversine(last_point[0], last_point[1], row["lat"], row["lon"]), axis=1
                    )

                    nearest_lodging = lodging_points.nsmallest(1, "distance").iloc[0]
                    updated_route_points.append([nearest_lodging["lat"], nearest_lodging["lon"]])

                    nearest_lodging["type"] = "hotel"
                    updated_amenities = pd.concat([updated_amenities, nearest_lodging.to_frame().T], ignore_index=True)

        route_points = updated_route_points
        nearest_amenities = updated_amenities
            
    Graph = ox.graph_from_place(regions, network_type=transportation, simplify=True)
    print("stage 0")
    G_undirected = Graph.to_undirected()
    print("stage 1")
    largest_component = max(nx.connected_components(G_undirected), key=len)
    print("stage 2")
    Graph = G_undirected.subgraph(largest_component).copy()
    print("stage 3")

    route = get_street_route(Graph, route_points)
    tour_map = create_tour_map(nearest_amenities, route=route, start_coords=start_coords)
    tour_map.save("nearest_amenities_tour.html")

if __name__ == "__main__":
    main()