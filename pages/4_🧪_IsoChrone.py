import streamlit as st
import folium
import requests
from streamlit_folium import st_folium

# OpenRouteService API Key
ORS_API_KEY = "5b3ce3597851110001cf6248004b6629175246d3ba57e3cbefcd5550"

# Define Lat, Lon
latitude = -6.2088  # Example: Jakarta
longitude = 106.8456
range = [0, 500]

# Fetch Isochrone from OpenRouteService
url = "https://api.openrouteservice.org/v2/isochrones/driving-car"
headers = {
    "Authorization": ORS_API_KEY,

}
body = {
    "locations": [[longitude, latitude]],
    "range": range,  # Road-based distance in meters
}
response = requests.post(url, json=body, headers=headers)
isochrone_data = response.json()
st.write(isochrone_data)

# Create Folium Map
m = folium.Map(location=[latitude, longitude], zoom_start=13)
folium.Marker([latitude, longitude], popup="Center Point").add_to(m)

# Add Isochrone Polygon
if "features" in isochrone_data:
    for feature in isochrone_data["features"]:
        folium.GeoJson(feature, name="Isochrone").add_to(m)

# Display in Streamlit
st.title("Streamlit Map with 5KM Road Distance Radius")
st_folium(m)
