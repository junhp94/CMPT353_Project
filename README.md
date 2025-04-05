Document your code and how to run it: required libraries, commands (and arguments), order of execution, files produced/expected. (To be deleted)
# 🗺️ CMPT 353 Personalized Tour Planner

A personalized tour planning tool that helps users generate a multi-day travel itinerary with selected amenities, restaurants, hotels, and optimized routes using real-world geospatial data.

---

## Contributors
- **Eric Li** - 301436381  
- **Steven Duong** - 301552606
- **Jun Park** - Enter yours please

---

## Features
- Customize tour **length**, **theme**, and **number of stops**
- Choose **transportation mode** (`walk`, `bike`, or `drive`)
- Option to **rent a form of transportation**
- Include **hotel stays** (if needed)
- Automatically recommends **3 restaurants/day**
- Plots route using real road networks (via OSMnx)
- Generates **interactive map** using Folium
- Retrieves real-time data from **OpenStreetMap** and **Nominatim**

---

## 🔧 Requirements
### Setting up a Virtual Environment
#### 🔹 Step 1: Create the Virtual Environment
```bash
python3 -m venv venv
```
This creates a folder named venv containing the isolated Python environment.

#### 🔹 Step 2: Activate the Virtual Environment
On MacOS/Linux:
```bash
source venv/bin/activate
```
On Windows (CMD):
```bash
venv\Scripts\activate
```
On Windows (PowerShell):
```bash
.\venv\Scripts\Activate.ps1
```
Once activated, your terminal should have a (venv) at the beginning of the line

#### 🔹 Step 3: Installing Project Dependencies:
Put these libraries in a file called `requirements.tx`
```bash
pandas
numpy
folium
osmnx
networkx
geopy
math
SPARQLWrapper
```
Then to install them
```bash
pip install -r requirements.txt
```
Or if want to enter it manually:
```bash
pip install pandas numpy folium osmnx networkx geopy SPARQLWrapper
```

#### 🔹 Note: To Exit the Virtual Environment:
Just type `deactivate` in the command line

---

## 💨 Running the Code
Once in the virtual environment and installed the proper dependencies:
To run:
```bash
python3 main.py
```
You'll then be prompted for the following information:
- Length of your tour
- Theme of the tour
- Total number of amenities
- Address of your current location
- Mode of transportation
  - If you choose to walk, you will be asked if you want to rent
- If you want to stay in a hotel

Once your have filled out your information, please wait for a file called
- `nearest_amenities_tour.html` and
- `tour_schedule.csv`
to be added in your directory

### 📍 Opening the output file
To open this file and view the map, press the `Run and Debug` button in VS Code to open it in Google Chrome.
Opening the CSV file will give you the order of the amenities for each day.

