import numpy as np
import pandas as pd
import streamlit as st

import pydeck as pdk
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, MeasureControl, Fullscreen

import os
import requests
from dotenv import load_dotenv
load_dotenv()

import math
import random

ORS_API_KEY = os.getenv('ORS_API_KEY')
# Enhanced color palette with more vibrant colors and better contrast
COLOR_LISTS = [
    ("#3366CC", "#FFB6C1"), ("#DC3912", "#ADDFAD"), ("#FF9900", "#ADD8E6"), 
    ("#109618", "#FFD700"), ("#990099", "#98FB98"), ("#0099C6", "#FFA07A"),
    ("#DD4477", "#00FFFF"), ("#66AA00", "#E6E6FA"), ("#B82E2E", "#AFEEEE"),
    ("#316395", "#FFFFE0"), ("#994499", "#E0FFFF"), ("#22AA99", "#FFDAB9"),
    ("#AAAA11", "#D8BFD8"), ("#6633CC", "#FFE4E1"), ("#E67300", "#F0FFFF"),
    ("#8B0707", "#F0F8FF"), ("#651067", "#F5F5DC")
]

st.set_page_config(
    page_title="Outlet Mapping Dashboard",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="auto"
)

OUTLET_DATA = "./data/outlets.csv"

def _read_data():
    df = pd.read_csv(OUTLET_DATA, delimiter=";", dtype={"Lat": str, "Lon": str})
    # Convert latitude and longitude to float for better handling
    df["Lat"] = df["Lat"].astype(float)
    df["Lon"] = df["Lon"].astype(float)
    return df

def _show_raw(data):
    st.subheader("📍 Select KC/Outlet Locations")
    data = data[["ID", "Type", "Name"]]

    event = st.dataframe(
        data=data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn("ID", width="small"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Name": st.column_config.TextColumn("Name", width="large"),
            "Lat": st.column_config.NumberColumn("Latitude", width="medium"),
            "Lon": st.column_config.NumberColumn("Longitude", width="medium"),
        },
        on_select="rerun",
        selection_mode="multi-row",
        height=300
    )

    return event
    
@st.cache_data
def generate_map(data, colors):
    # Create maps
    map = folium.Map(
        location=[data["Lat"].mean(), data["Lon"].mean()],
        zoom_start=12,
        max_zoom=18,
        min_zoom=11,
        control_scale=True,
        tiles="CartoDB Positron"
    )
    
    # Add fullscreen control
    Fullscreen().add_to(map)
    
    # Add measurement tool
    MeasureControl(position='topleft', primary_length_unit='kilometers').add_to(map)
    
    # Add layer control
    folium.LayerControl().add_to(map)

    for i in range(len(data)):
        row = data.iloc[i]
        # Create a custom icon with more visual appeal
        icon = folium.Icon(
            icon="building" if row["Type"] == "KC" else "bank",
            prefix="fa",
            color=COLOR_LISTS[colors[i % len(COLOR_LISTS)]][0].lstrip('#'),
            icon_color="#ffffff"
        )
        
        # Add popup with more information
        popup_html = f"""
        <div style="width: 200px; font-family: Calibri;">
            <h4 style="color: {COLOR_LISTS[colors[i % len(COLOR_LISTS)]][0]}; margin-bottom: 5px;">{row['Type']} { row['Name']}</h4>
            <p><strong>ID:</strong> {row['ID']}</p>
            <p><strong>Type:</strong> {row['Type']}</p>
            <p><strong>Coordinates:</strong><br>{row['Lat']:.6f}, {row['Lon']:.6f}</p>
        </div>
        """
        popup = folium.Popup(folium.Html(popup_html, script=True), max_width=150)
        
        # Add marker
        folium.Marker(
            [row["Lat"], row["Lon"]],
            tooltip=row["Name"],
            popup=popup,
            icon=icon
        ).add_to(map)

        # Add circle
        folium.Circle(
            location=[row["Lat"], row["Lon"]],
            color=COLOR_LISTS[colors[i % len(COLOR_LISTS)]][0],
            weight=2,
            opacity=0.7,
            fill_color=COLOR_LISTS[colors[i % len(COLOR_LISTS)]][0],
            fill=True,
            fill_opacity=0.15,
            radius=5000,
            popup=row["Name"],
            tooltip=f"5km radius - {row['Name']}"
        ).add_to(map)

    return map

def _foliumMap(event, data):
    filtered = event.selection.rows
    data = data.iloc[filtered]

    if data.shape[0] == 0:
        st.markdown("### 👈 Please select one or more locations to display on the map")
        return None

    if "colors" not in st.session_state or len(st.session_state.colors) < data.shape[0]:
        st.session_state.colors = [random.randint(0, len(COLOR_LISTS)-1) for _ in range(data.shape[0])]

    colors = st.session_state.colors
    map = generate_map(data, colors)

    if map is not None:
        st.subheader("🔵 5KM Radius Map")
        with st.container():
            st_folium(map, width=None, height=450, returned_objects=["last_active_drawing"])
    else:
        st.error("An error occurred while generating the map. Please try again.")

@st.cache_data
def generate_marker_map(data, colors):
    # Create Folium Map with a different tile
    map = folium.Map(
        location=[data["Lat"].mean(), data["Lon"].mean()],
        zoom_start=12.5,
        max_zoom=18,
        min_zoom=10,
        control_scale=True,
        tiles="CartoDB Voyager"  # Different style for this map
    )
    
    # Add fullscreen control
    Fullscreen().add_to(map)
    
    # Add measurement tool
    MeasureControl(position='topleft', primary_length_unit='kilometers').add_to(map)
    
    for i in range(len(data)):
        row = data.iloc[i]
        
        # Create a visually distinct marker for this map
        icon = folium.Icon(
            icon="building" if row["Type"] == "KC" else "bank",
            prefix="fa",
            color=COLOR_LISTS[colors[i % len(COLOR_LISTS)]][0].lstrip('#'),
            icon_color="#ffffff"
        )
        
        # Enhanced popup with more information
        popup_html = f"""
        <div style="width: 200px; font-family: Calibri;">
            <h4 style="color: {COLOR_LISTS[colors[i % len(COLOR_LISTS)]][0]}; margin-bottom: 5px;">{row['Name']}</h4>
            <p><strong>ID:</strong> {row['ID']}</p>
            <p><strong>Type:</strong> {row['Type']}</p>
            <p><strong>Coordinates:</strong><br>{row['Lat']:.6f}, {row['Lon']:.6f}</p>
        </div>
        """
        popup = folium.Popup(folium.Html(popup_html, script=True), max_width=300)
        
        # Add marker
        folium.Marker(
            [row["Lat"], row["Lon"]],
            tooltip=row["Name"],
            popup=popup,
            icon=icon
        ).add_to(map)
        
    return map

# Get Isochrone Data
@st.cache_data
def getIsoChroneData(data, max_dist):
    url = os.getenv("ORS_URL")
    lonlatlist = data[["Lon", "Lat"]].values.tolist()

    # Processing in batches of 5 requests (API requirements)
    idx_start = 0
    idx_end = 4
    iter = math.ceil(len(data)/5)

    json_list = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(iter):
        if idx_end > len(data)-1:
            idx_end = len(data)-1

        status_text.text(f"Processing isochrones batch {i+1}/{iter}...")
        lonlatlist_itr = lonlatlist[idx_start:idx_end+1]    
        headers = {"Authorization": ORS_API_KEY}
        body = {
            "locations": lonlatlist_itr,
            "attributes": ["area", "reachfactor", "total_pop"],
            "range": [max_dist],
            "range_type": "distance",
            "units": "km"
        }

        response = requests.post(url, json=body, headers=headers)
        json_list.append(response.json())

        idx_start = idx_end + 1
        idx_end += 5
        
        # Update progress bar
        progress_bar.progress((i + 1) / iter)
    
    status_text.empty()
    progress_bar.empty()

    merged_json = {"type": "FeatureCollection", "features": []}
    for json in json_list:
        merged_json["features"].extend(json["features"])

    return merged_json

def _foliumMapRad(data, max_dist):
    filtered = event.selection.rows
    data = data.iloc[filtered]

    if data.shape[0] == 0:
        st.markdown("### 👈 Please select one or more locations to display on the map")
        return None

    # Color selection for consistency
    if "colors" not in st.session_state or len(st.session_state.colors) < data.shape[0]:
        st.session_state.colors = [random.randint(0, len(COLOR_LISTS)-1) for _ in range(data.shape[0])]

    colors = st.session_state.colors

    map = generate_marker_map(data, colors)
    
    with st.spinner("Calculating service areas based on road network..."):
        response = getIsoChroneData(data, max_dist)

    if "features" in response:
        idx = 0
        for feature in response["features"]:
            folium.GeoJson(
                feature,
                name=f"{data.iloc[idx]['Name']}",
                tooltip=f"Service Area: {data.iloc[idx]['Name']}",
                style_function=lambda feature, idx=idx: {
                    "color": COLOR_LISTS[colors[idx % len(COLOR_LISTS)]][0],  # Border color
                    "weight": 2,  # Border thickness
                    "fillColor": COLOR_LISTS[colors[idx % len(COLOR_LISTS)]][1],  # Fill color
                    "fillOpacity": 0.4,  # Transparency
                    "dashArray": "5, 5"  # Dashed line for better visibility
                }
            ).add_to(map)
            idx += 1
            
    # Add layer control for toggling different service areas
    folium.LayerControl().add_to(map)
    
    st.subheader("🚗 Road Network Service Area Map")
    st.markdown("""
    This map shows the actual areas serviceable within a travel distance via the road network.
    These areas reflect real-world accessibility rather than simple circular radius.
    """)
    
    with st.container():
        ret = st_folium(map, width=None, height=450, returned_objects=["last_active_drawing"])

def display_dashboard_info():
    st.title("🏦 Banking Outlet Service Area Visualization")
    st.markdown("""
    ### Analyze the coverage and reach of banking outlets across different locations
    
    This dashboard allows you to visualize:
    - 5km radius coverage areas
    - Realistic service areas based on the road network (adjustable travel distance)
    """)

if __name__ == '__main__':
    display_dashboard_info()
    data = _read_data()
    
    # Selection table
    event = _show_raw(data)
    
    # Create a tab layout
    tab2, tab3 = st.tabs(["5Km Radius Map", "Road Network Service Area"])
        
    with tab2:
        _foliumMap(event, data)
        
    with tab3:
        max_dist = st.slider("Service Area Distance (km)", 1, 10, 5, 1)
        _foliumMapRad(data, max_dist)