# CMPT 353 Project
#
#   Eric Li 301436381
#   
#
import pandas as pd
import numpy as np
import math
import folium as fl
import osmnx as ox
import networkx as nx
from SPARQLWrapper import SPARQLWrapper, JSON

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
    if route:
        fl.PolyLine(locations=route, color='blue', weight=2.5, opacity=1).add_to(tour_map)
    else:
        print("No valid route found.")
    
    return tour_map

# filter data to only include amenities in each theme.
def filter_by_theme(data, theme):

    themes = {
        "Nature": ["park", "watering_place", "fountain", "ranger_station", "hunting_stand", "observation_platform"],
        "Food": ["cafe", "fast_food", "bbq", "restaurant", "pub", "bar", "food_court", "ice_cream", "juice_bar", "bistro", "biergarten"],
        "History": ["place_of_worship", "monastery", "courthouse", "townhall"],
        "Science": ["research_institute", "science", "healthcare", "hospital", "pharmacy", "clinic", "veterinary", "chiropractor", "ATLAS_clean_room"],
        "Art": ["arts_centre", "theatre", "studio", "music_school"],
        "Entertainment": ["cinema", "nightclub", "stripclub", "gambling", "casino", "events_venue", "marketplace", "spa", "events_venue", "internet_cafe", "lounge", "shop|clothes", "leisure"],
        "Mode of Travel": ["car_rental", "bicycle_rental", "car_sharing", "taxi", "bus_station", "ferry_terminal", "seaplane_terminal", "motorcycle_rental", "parking", "charging_station", "EVSE"]
    }
    
    if theme in themes:
        return data[data['amenity'].isin(themes[theme])]
    else:
        print(f"Warning: Theme '{themes}' not found. Available themes: {list(themes)}")
    return data[data['amenity'].isin(themes)]


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

# For each city, download their street network and then combine them
def get_combined_graph(places, network_type='drive'):
    
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
    places = [
    "Vancouver, British Columbia, Canada",
    "Surrey, British Columbia, Canada",
    "Richmond, British Columbia, Canada",
    "Burnaby, British Columbia, Canada",
    "Coquitlam, British Columbia, Canada",
    "Delta, British Columbia, Canada",
    "Maple Ridge, British Columbia, Canada",
    "White Rock, British Columbia, Canada",
    "Abbotsford, British Columbia, Canada",
    "Langley City, British Columbia, Canada",
    "North Vancouver, British Columbia, Canada",
    "Pitt Meadows, British Columbia, Canada",
    "Bowen Island, British Columbia, Canada",
    "West Vancouver, British Columbia, Canada",
    "Mission, British Columbia, Canada"
]

    modes_of_travel = filter_by_theme(data, "Mode of Travel")
    
    food_points = filter_by_theme(interesting_data, "Food").head(50)
    
    # Create a list of [lat, lon] pairs for route calculation
    food_points_list = [[row['lat'], row['lon']] for idx, row in food_points.iterrows()]

    regions = [
    "Metro Vancouver, British Columbia, Canada",
    #"Fraser Valley, British Columbia, Canada"
    "Abbotsford, British Columbia, Canada",
    "Mission, British Columbia, Canada"
    ]
    housing = data[data['amenity'] == 'housing co-op']
    hotels = get_hotels(regions)
 
    if not housing.empty and not hotels.empty:
        lodging_points = pd.concat([housing, hotels], ignore_index=True)
    elif not housing.empty:
        lodging_points = housing
    else:
        lodging_points = hotels
        
    if lodging_points.empty:
        print("No lodging data found. Exiting.")
        return

  
    lodging_coords = [[row['lat'], row['lon']] for idx, row in lodging_points.iterrows()]
    """
    combined_graph = get_combined_graph(regions, network_type='drive')

    lodging_route = get_street_route(combined_graph, lodging_coords)
    
    lodging_map = create_tour_map(lodging_points, route=lodging_route)
    lodging_map.save("lodging_map_streets.html")
    
    lodging_route_2 = get_street_route(combined_graph, lodging_coords)
    lodging_map_2 = create_tour_map(lodging_points, route=lodging_route_2)
    lodging_map_2.save("lodging_map_2.html")
    """
    print("Downloading street network...")

    Graph = ox.graph_from_place(regions, network_type='drive', simplify=True)
    print("stage 0")
    G_undirected = Graph.to_undirected()
    print("stage 1")
    largest_component = max(nx.connected_components(G_undirected), key=len)
    print("stage 2")
    Graph = G_undirected.subgraph(largest_component).copy()
    print("stage 3")
    
    lodging_route_3 = get_street_route(Graph, lodging_coords)
    lodging_map_3 = create_tour_map(lodging_points, route=lodging_route_3)
    lodging_map_3.save("lodging_map_3.html")
    
    food_route = get_street_route(Graph, food_points_list)
    print("stage 4")
    food_tour = create_tour_map(food_points, route=food_route)
    food_tour.save("food_map_tour.html")

if __name__=='__main__':
    main()