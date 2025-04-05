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
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta

geolocator = Nominatim(user_agent="CMPT353-Project")

def input_field():
    # Ask user how long their tour is
    while True:
        tour_length = input("Enter length of tour in days: ").strip()
        try:
            tour_length = int(tour_length)
            if tour_length > 0:
                break
            else:
                print("Invalid number. Please enter a positive integer.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")
    
    # Ask for theme
    themes = ["food", "nature", "history", "science", "art", "entertainment", "random"]
    while True:
        theme = input(f"Enter a theme ({', '.join(themes)}): ").strip().lower()
        if theme in themes:
            break
        print(f"Invalid choice. Please select from: {', '.join(themes)}.")

    # Ask for the number of amenities
    while True:
        num_amenities = input("Enter the total number of amenities you want to visit: ").strip()
        if not num_amenities:
            print("Input cannot be empty. Please enter a valid positive number.")
            continue
        try:
            num_amenities = int(num_amenities)
            if num_amenities > 0:
                break
            else:
                print("Please enter a valid positive number.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Ask for the starting location (latitude and longitude), can be changed later to ask for location rather than lat and lon
    while True:
        address = input("Please enter your current address (Ex. 1234 Mountain Drive Vancouver BC V1N 5Z6): ")
        location = geolocator.geocode(address)
        if location:
            start_lat, start_lon = float(location.latitude), float(location.longitude)
            break
        print("Invalid address. Please try again.")

    # Ask for mode of transportation
    transport_modes = ["walk", "drive", "bike"]
    options = ["yes", "no"]
    while True:
        transportation = input(f"Choose your mode of transportation ({', '.join(transport_modes)}): ").strip().lower()
        if transportation in transport_modes:
            if transportation == "walk":
                while True:
                    want_rental = input("Do you want to rent a form of transportation? (yes or no): ").strip().lower()
                    if want_rental in options:
                        break
            else: 
                want_rental = "no"
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

    return tour_length, theme, num_amenities, (start_lat, start_lon), transportation, want_rental, stay_hotel

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
        "nature": ["park", "watering_place", "fountain", "ranger_station", "hunting_stand", "observation_platform", "water_point"],
        "food": ["cafe", "bbq", "restaurant", "pub", "bar", "food_court", "ice_cream", "juice_bar", "bistro", "biergarten"],
        "history": ["place_of_worship", "monastery", "courthouse", "townhall", "clock"],
        "science": ["research_institute", "science", "ATLAS_clean_room"],
        "art": ["arts_centre", "theatre", "studio"],
        "entertainment": ["cinema", "nightclub", "stripclub", "gambling", "casino", "marketplace", "spa", "events_venue", "internet_cafe", "lounge", "shop|clothes", "leisure", "Observation Platform", "photo_booth"],
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

# If the user selects that they are walking, then find some place of transportation.
def get_rental(places):
    
    df_list = []
    tags = { 'amenity': ["car_rental", "bicycle_rental", "bus_station", "motorcycle_rental"]}
    
    for place in places:
        print(f"Retrieving rentals for {place}...")
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
                gdf['name'] = "Rentals"
            else:
                gdf = gdf[gdf['name'].notna()]
                
            rentals_df = gdf[['name', 'lat', 'lon']].reset_index(drop=True)
            print(f"Retrieved {len(rentals_df)} rentals for {place}.")
            df_list.append(rentals_df)
            
        except Exception as e:
            print(f"Error retrieving rentals for {place}: {e}")
            
    if df_list:
        combined = pd.concat(df_list, ignore_index=True)
        print(f"Total rentals retrieved: {len(combined)}")
        return combined
    else:
        return pd.DataFrame()

# Creates a daily schedule for the tour based on time constraints
def daily_schedule(route_points, amenities, transportation, tour_length):
    # Predetermined average speeds for different modes of travel in km/h
    speeds = {"walk": 5, "bike": 15, "drive": 50}
    
    # Rough amounts of time spent at different amenity types in minutes
    time_spent = {"hotel": 720, "restaurant": 60, "rental": 20, "default": 60}

    schedule = []
    current_day = 1

    # for this system, date doesn't matter, only time
    day_start = datetime(2025, 1, 1, 9, 0) # Tour days begin 9am
    day_end = datetime(2025, 1, 1, 21, 0) # Tour days end at 9pm
    current_time = day_start
    current_location = route_points[0]

    schedule.append({
         "day": current_day,
         "name": "Start Location",
         "type": "start",
         "lat": current_location[0],
         "lon": current_location[1],
         "arrival": current_time,
         "departure": current_time
    })

    # Meal targets for each day (breakfast, lunch, dinner)
    meal_times = {"breakfast": datetime(current_time.year, current_time.month, current_time.day, 9, 0),
                  "lunch":     datetime(current_time.year, current_time.month, current_time.day, 13, 0),
                  "dinner":    datetime(current_time.year, current_time.month, current_time.day, 18, 0)}
    meals_taken = {"breakfast": False, "lunch": False, "dinner": False}

    # Iterate through each stop (starting from index 1)
    for i in range(1, len(route_points)):
         next_point = route_points[i]
         # Calculate travel time (in minutes) from current_location to next_point
         distance = haversine(current_location[0], current_location[1], next_point[0], next_point[1])
         speed = speeds.get(transportation, 5)
         travel_minutes = (distance / speed) * 60
         travel_time = timedelta(minutes=travel_minutes)
         arrival_time = current_time + travel_time

        # If arrival is after the day's end, force a hotel stop at day_end and then start next day.
         if arrival_time > day_end:
             schedule.append({
                 "day": current_day,
                 "name": "Hotel (End of Day)",
                 "type": "hotel",
                 "lat": current_location[0],
                 "lon": current_location[1],
                 "arrival": day_end,
                 "departure": day_end
             })
             current_day += 1
             # Prepare next day: shift start and end by one day.
             day_start += timedelta(days=1)
             day_end += timedelta(days=1)
             meal_times = {"breakfast": datetime(day_start.year, day_start.month, day_start.day, 9, 0),
                           "lunch":     datetime(day_start.year, day_start.month, day_start.day, 13, 0),
                           "dinner":    datetime(day_start.year, day_start.month, day_start.day, 18, 0)}
             meals_taken = {"breakfast": False, "lunch": False, "dinner": False}
             current_time = day_start
             # Recalc travel from new day's start to next_point.
             distance = haversine(current_location[0], current_location[1], next_point[0], next_point[1])
             travel_minutes = (distance / speed) * 60
             travel_time = timedelta(minutes=travel_minutes)
             arrival_time = current_time + travel_time
         if i < len(amenities):
            amenity_info = amenities.iloc[i]
            amenity_type = amenity_info.get('type', 'default')
            amenity_name = amenity_info.get('name', f"Point {i}")
         else:
            amenity_type = 'default'
            amenity_name = f"Point {i}"

         duration = time_spent.get(amenity_type, time_spent['default'])
         visit_time = timedelta(minutes=duration)
         departure_time = arrival_time + visit_time

         # check if time is near a meal time, currently set to be within 30min, and stop tour for a meal
         for meal, meal_target in meal_times.items():
             if not meals_taken[meal]:
                 if meal_target - timedelta(minutes=30) <= arrival_time <= meal_target + timedelta(minutes=30):
                     if amenity_type != "restaurant":
                         amenity_type = "restaurant"
                         duration = time_spent.get("restaurant", 60)
                         visit_time = timedelta(minutes=duration)
                     meals_taken[meal] = True
                     break

         # shortens time spent at amenity so tour can stop at 9pm
         if departure_time > day_end:
            visit_time = day_end - arrival_time
            departure_time = day_end

         schedule.append({
             "day": current_day,
             "name": amenity_name,
             "type": amenity_type,
             "lat": next_point[0],
             "lon": next_point[1],
             "arrival": arrival_time,
             "departure": departure_time
          })

         current_time = departure_time
         current_location = next_point

        # If little time remains in the day, end the day with a hotel stop.
         if (day_end - current_time) < timedelta(minutes=30):
             schedule.append({
                 "day": current_day,
                 "name": "Hotel (End of Day)",
                 "type": "hotel",
                 "lat": current_location[0],
                 "lon": current_location[1],
                 "arrival": day_end,
                 "departure": day_end
             })
             current_day += 1
             day_start += timedelta(days=1)
             day_end += timedelta(days=1)
             meal_times = {"breakfast": datetime(day_start.year, day_start.month, day_start.day, 9, 0),
                           "lunch":     datetime(day_start.year, day_start.month, day_start.day, 13, 0),
                           "dinner":    datetime(day_start.year, day_start.month, day_start.day, 18, 0)}
             meals_taken = {"breakfast": False, "lunch": False, "dinner": False}
             current_time = day_start
             
    # Once set tour days have been completed, drops remaining amenities.
    schedule = [stop for stop in schedule if stop["day"] <= tour_length]
    return schedule

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
    
def create_tour_map(schedule, route):

    # Create a map centered on the first point
    map_center = [schedule[0]['lat'], schedule[0]['lon']]
    tour_map = fl.Map(location=map_center, zoom_start=13)
    
    # Add markers with popups that show name, type, day, arrival and departure times.
    for stop in schedule:
         popup_text = (
             f"Name: {stop['name']}\n\n"
             f"Type: {stop['type']}\n\n"
             f"Day: {stop['day']}\n\n"
             f"Arrival: {stop['arrival'].strftime('%I:%M %p')}\n\n"
             f"Departure: {stop['departure'].strftime('%I:%M %p')}"
         )
         marker_color = "blue"
         if stop['type'] == "restaurant":
             marker_color = "orange"
         elif stop['type'] == "hotel":
             marker_color = "green"
         elif stop['type'] == "rental":
             marker_color = "black"
         fl.Marker(
             location=[stop['lat'], stop['lon']],
             popup=popup_text,
             icon=fl.Icon(color=marker_color)
         ).add_to(tour_map)
    
    # Draw the path connecting the scheduled route.
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
    "Mission, British Columbia, Canada",
    "Bowen Island, British Columbia, Canada"
    ]

interesting_amenities = ['cafe', 'bbq', 'place_of_worship', 
    'restaurant', 'pub', 'community_centre', 'public_building', 'cinema', 'theatre',
    'ferry_terminal', 'bar', 'library', 'car_rental',
    'car_sharing', 'bicycle_rental', 'public_bookcase',
    'university', 'dojo', 'food_court', 'seaplane terminal', 'arts_centre',
    'ice_cream', 'fountain',
    'photo_booth', 'nightclub', 'social_facility', 'taxi',
    'bus_station', 'clock', 'marketplace', 'stripclub',
    'gambling', 'family_centre', 'townhall',
    'bistro', 'playground', 'boat_rental', 'spa', 'events_venue', 'science', 
    'ATLAS_clean_room', 'juice_bar', 'internet_cafe', 'social_centre', 'EVSE', 'studio',
    'ranger_station', 'watering_place', 'lounge', 'water_point',
    'Observation Platform', 'housing co-op', 'gym',
    'park', 'biergarten', 'casino', 'hunting_stand', 'shop|clothes', 'research_institute',
    'motorcycle_rental', "observation_platform", "monastery", "courthouse", "leisure", "seaplane_terminal", 
    "parking", "charging_station"]
    
def main():
    original_data = pd.read_json("amenities-vancouver.json.gz", compression="gzip", lines=True)
    data = original_data[~original_data["name"].isna()]
    data = data[data["amenity"].isin(interesting_amenities)]

    # Get inputs
    tour_length, theme, num_amenities, start_coords, transportation, want_rental, stay_hotel = input_field()
    
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
    
    # Adds a rental if transportation is walking
    if transportation == 'walk' and want_rental == 'yes':
        rentals = get_rental(regions)
                    
    if stay_hotel:
        housing = data[data['amenity'] == 'housing co-op']
        hotels = get_hotels(regions)

        if not hotels.empty or not housing.empty:
            # Combine hotels and housing
            lodging_points = pd.concat([housing, hotels], ignore_index=True)

    if not restaurants.empty:
        updated_route_points = [route_points[0]]  # Start point remains the same
        updated_amenities = pd.DataFrame([nearest_amenities.iloc[0]])  # First point

        amenities_per_day = num_amenities // tour_length  # Number of amenities per day
        day_index = 0  # Track amenities count per day
        restaurant_count = 0  # Track how many restaurants added per day
        
        # Ensure that the rental is the closest to the starting point using haversine
        if want_rental == 'yes':
            rentals["distance"] = rentals.apply(
                lambda row: haversine(start_coords[0], start_coords[1], row["lat"], row["lon"]), axis=1
            )
            
            # Find the nearest rental
            nearest_rental = rentals.nsmallest(1, "distance").iloc[0]
            # Insert the nearest rental at the start of route_points
            updated_route_points.append([nearest_rental["lat"], nearest_rental["lon"]])
            nearest_rental["type"] = "rental"
            updated_amenities = pd.concat([updated_amenities, nearest_rental.to_frame().T], ignore_index=True)

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

    schedule = daily_schedule(route_points, nearest_amenities, transportation, tour_length)
    tour_map = create_tour_map(schedule, route)
    tour_map.save("nearest_amenities_tour.html")
    
if __name__ == "__main__":
    main()