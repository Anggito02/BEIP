import pandas as pd
import streamlit as st

import os
import requests
from dotenv import load_dotenv

import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen, MeasureControl
import plotly.express as px
from collections import Counter

load_dotenv()

st.set_page_config(
    page_title="Business Environment Coverage",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

OUTLET_DATA = os.getenv('OUTLET_DATA')

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
        selection_mode="single-row",
        height=300
    )
    return event

def categorize_osm_node(node):
    """Categorize an OSM node based on its tags."""
    tags = node.get("tags", {})
    
    # Define category mappings
    category_mappings = {
        "Food & Drink": {
            "amenity": ["restaurant", "cafe", "fast_food", "bar", "pub", "food_court", "ice_cream", "biergarten"],
            "shop": ["bakery", "butcher", "convenience", "deli", "dairy", "greengrocer", "supermarket", "alcohol", "beverages"]
        },
        "Retail": {
            "shop": ["clothes", "shoes", "jewelry", "electronics", "mobile_phone", "department_store", 
                     "mall", "supermarket", "hardware", "furniture", "books", "gift", "convenience", 
                     "computer", "fashion", "general", "boutique", "cosmetics", "toys", "outdoor"]
        },
        "Services": {
            "shop": ["hairdresser", "beauty", "optician", "travel_agency", "laundry", "dry_cleaning", "tailor"],
            "office": ["insurance", "lawyer", "accountant", "estate_agent", "travel_agent", "company", "government"],
            "craft": ["carpenter", "plumber", "electrician", "painter", "photographer", "glaziery"]
        },
        "Healthcare": {
            "amenity": ["hospital", "clinic", "doctors", "dentist", "pharmacy", "veterinary"],
            "healthcare": ["*"]  # All healthcare tags
        },
        "Transportation": {
            "amenity": ["bus_station", "taxi", "bicycle_rental", "car_rental", "car_sharing", "fuel", "charging_station"],
            "public_transport": ["station", "stop_position", "platform", "stop"],
            "building": ["transportation"],
            "shop": ["car", "car_repair", "motorcycle", "bicycle"]
        },
        "Accommodation": {
            "tourism": ["hotel", "hostel", "motel", "guest_house", "apartment", "camp_site"],
            "building": ["hotel", "dormitory"]
        },
        "Leisure & Recreation": {
            "leisure": ["*"],  # All leisure tags
            "amenity": ["cinema", "theatre", "arts_centre", "nightclub", "gym", "fitness_centre", "community_centre"],
            "tourism": ["museum", "gallery", "attraction", "viewpoint", "zoo"],
            "shop": ["sports", "games"]
        },
        "Education": {
            "amenity": ["school", "university", "college", "kindergarten", "library", "language_school", "driving_school"],
            "building": ["school", "university"]
        },
        "Financial": {
            "amenity": ["bank", "atm", "bureau_de_change"],
            "office": ["financial", "insurance", "tax"]
        },
        "Natural & Parks": {
            "natural": ["*"],
            "landuse": ["park", "forest", "meadow", "recreation_ground", "grass"],
            "leisure": ["park", "garden", "nature_reserve"]
        },
        "Infrastructure": {
            "man_made": ["*"],
            "power": ["*"],
            "telecom": ["*"],
            "waterway": ["*"],
            "building": ["industrial", "commercial", "office", "warehouse"]
        },
        "Religious & Cultural": {
            "amenity": ["place_of_worship", "community_centre", "social_centre"],
            "building": ["church", "mosque", "temple", "synagogue", "cathedral"],
            "historic": ["*"]
        }
    }
    
    # Check each tag against our category mappings
    for category, mapping in category_mappings.items():
        for tag_key, tag_values in mapping.items():
            if tag_key in tags:
                # If the value is ["*"], any value for this key matches
                if tag_values == ["*"] or tags[tag_key] in tag_values:
                    return category
    
    # If no specific category was found, try to determine a general category
    if "shop" in tags:
        return "Retail"
    elif "amenity" in tags:
        return "Services"
    elif "tourism" in tags:
        return "Tourism & Recreation"
    elif "office" in tags:
        return "Business Services"
    elif "craft" in tags:
        return "Crafts & Trades"
    elif "industrial" in tags:
        return "Industrial"
    elif "building" in tags:
        return "Buildings"
    elif "historic" in tags:
        return "Historic"
        
    return "Other"

def _get_business_data(data, radius):
    filtered = event.selection.rows
    data = data.iloc[filtered]

    if data.shape[0] == 0:
        st.markdown("### 👈 Please select one office location to display on the map")
        return None

    lat = data["Lat"].mean()
    lon = data["Lon"].mean()

    st.subheader(f"💵 Business Around in {int(radius/1000)} KM radius")

    query = f"""
        [out:json];
            (
            node["shop"](around:{radius},{lat},{lon});
            node["amenity"](around:{radius},{lat},{lon});
            node["tourism"](around:{radius},{lat},{lon});
            node["office"](around:{radius},{lat},{lon});
            node["craft"](around:{radius},{lat},{lon});
            node["industrial"](around:{radius},{lat},{lon});
            node["leisure"](around:{radius},{lat},{lon});
            node["man_made"](around:{radius},{lat},{lon});
            node["building"](around:{radius},{lat},{lon});
            node["public_transport"](around:{radius},{lat},{lon});
            node["historic"](around:{radius},{lat},{lon});
            node["landuse"](around:{radius},{lat},{lon});
            node["natural"](around:{radius},{lat},{lon});
            node["waterway"](around:{radius},{lat},{lon});
            node["power"](around:{radius},{lat},{lon});
            node["telecom"](around:{radius},{lat},{lon});
            );
        out;
    """

    url = "https://overpass-api.de/api/interpreter"
    
    with st.spinner("Fetching data from OpenStreetMap..."):
        response = requests.get(url, params={'data': query})
        osm_data = response.json()
    
    # Process and categorize the data
    categorized_nodes = []
    categories_count = Counter()
    
    with st.spinner("Processing and categorizing data..."):
        for node in osm_data.get('elements', []):
            if node.get('type') == 'node' and 'tags' in node:
                category = categorize_osm_node(node)
                node['category'] = category
                
                # Get the name or a description if no name is available
                name = node.get('tags', {}).get('name', '')
                if not name:
                    # Try to create a descriptive name based on available tags
                    for key in ['shop', 'amenity', 'tourism', 'office', 'craft', 'leisure']:
                        if key in node.get('tags', {}):
                            name = f"{key.capitalize()}: {node['tags'][key].capitalize()}"
                            break
                    if not name:
                        continue
                
                node['display_name'] = name
                categories_count[category] += 1
                categorized_nodes.append(node)
    
    # Create a DataFrame for easier manipulation
    if categorized_nodes:
        business_df = pd.DataFrame([
            {
                'name': node['display_name'],
                'category': node['category'],
                'lat': node['lat'],
                'lon': node['lon'],
                'tags': node.get('tags', {})
            }
            for node in categorized_nodes
        ])

        # Filter out 'name' that contains "Amenity"
        business_df = business_df[~business_df['name'].str.contains(":")]
        
        # Filter out 'category' == 'Other'
        business_df = business_df[business_df['category'] != 'Other']
        
        # Display statistics
        st.write(f"Found {len(categorized_nodes)} businesses/points of interest in the area")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["📊 Categories", "🗺️ Map", "📋 Detailed List"])
        
        with tab1:
            # Create a bar chart of categories
            fig = px.bar(
                x=list(categories_count.keys()),
                y=list(categories_count.values()),
                labels={'x': 'Category', 'y': 'Count'},
                title="Business Categories Distribution",
                color=list(categories_count.keys())
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Pie chart for proportion
            fig2 = px.pie(values=list(categories_count.values()), 
                          names=list(categories_count.keys()), 
                          title="Category Proportions")
            st.plotly_chart(fig2, use_container_width=True)

        with tab2:
            # Create an interactive map
            map = folium.Map(
                location=[lat, lon],
                zoom_start=12,
                max_zoom=20,
                min_zoom=15,
                control_scale=True,
            )

            # Add fullscreen control
            Fullscreen().add_to(map)
            
            # Add measurement tool
            MeasureControl(position='topleft', primary_length_unit='kilometers').add_to(map)
            
            # Add marker for selected location
            folium.Marker(
                [lat, lon],
                popup="Selected Office",
                icon=folium.Icon(color="red", icon="star")
            ).add_to(map)
            
            # Add circle for radius
            folium.Circle(
                [lat, lon],
                radius=radius,
                color="blue",
                fill=True,
                fill_opacity=0.1
            ).add_to(map)
            
            # Color mapping for categories
            category_colors = {
                "Food & Drink": "green",
                "Retail": "blue",
                "Services": "purple",
                "Healthcare": "red",
                "Transportation": "orange",
                "Accommodation": "pink",
                "Leisure & Recreation": "lightblue",
                "Education": "darkblue",
                "Financial": "cadetblue",
                "Natural & Parks": "darkgreen",
                "Infrastructure": "gray",
                "Religious & Cultural": "darkpurple",
                "Other": "black"
            }

            # Icon mapping for categories
            category_icons = {
                "Food & Drink": "cutlery",
                "Retail": "shopping-cart",
                "Services": "wrench",
                "Healthcare": "plus-sign",
                "Transportation": "road",
                "Accommodation": "home",
                "Leisure & Recreation": "glass",
                "Education": "book",
                "Financial": "usd",
                "Natural & Parks": "tree-conifer",
                "Infrastructure": "cog",
                "Religious & Cultural": "star",
                "Other": "info-sign"
            }
            
            # Create marker clusters for each category
            category_clusters = {}
            for category in business_df['category'].unique():
                category_clusters[category] = MarkerCluster(name=category)
            
            # Add markers to appropriate clusters
            for _, row in business_df.iterrows():
                category = row['category']
                color = category_colors.get(category, "gray")
                icon_name = category_icons.get(category, "info-sign")
                
                popup_content = f"""
                <strong>{row['name']}</strong><br>
                Category: {category}
                """
                
                folium.Marker(
                    [row['lat'], row['lon']],
                    popup=folium.Popup(popup_content, max_width=300),
                    icon=folium.Icon(color=color, icon=icon_name, prefix="glyphicon")
                ).add_to(category_clusters[category])
            
            # Add all clusters to the map
            for category, cluster in category_clusters.items():
                cluster.add_to(map)
            
            # Add layer control to toggle categories
            folium.LayerControl().add_to(map)
            
            if map is not None:
                with st.container():
                    st_folium(map, width=None, height=600, returned_objects=["last_active_drawing"])
            else:
                st.error("An error occurred while generating the map. Please try again.")
        
        with tab3:
            st.subheader("📊 Business Directory with Filter & Map")

            # Sidebar-like filters using columns
            col1, col2 = st.columns(2)
            with col1:
                selected_category = st.selectbox(
                    "Filter by Category",
                    ["All"] + sorted(business_df['category'].unique().tolist()),
                    index=0
                )

            # Apply filter
            filtered_df = business_df.copy()
            if selected_category != "All":
                filtered_df = filtered_df[filtered_df['category'] == selected_category]

            # Display Table
            st.markdown("### 📄 Filtered Business List")
            selected_rows = st.dataframe(
                filtered_df[['name', 'category']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "name": st.column_config.TextColumn("Name", width="large"),
                    "category": st.column_config.TextColumn("Category", width="medium"),
                },
                key="business_table",
                selection_mode="multi-row",
                on_select="rerun"
            )

            # Show Details
            st.markdown("### 🔍 Business Details")
            if st.button("Show Details for Selected"):
                selected_idx = selected_rows.selection.rows
                if not selected_idx:
                    st.warning("Please select at least one business.")
                else:
                    for idx in selected_idx:
                        row = filtered_df.iloc[idx]
                        with st.expander(f"📌 {row['name']} ({row['category']})"):
                            st.write(f"**Tags:**")
                            st.json(row['tags'])

                # Optional: Show all filtered businesses on a map
                st.markdown("### 🗺️ Map of Filtered Businesses")
                map = folium.Map(
                    location=[row['lat'].mean(), row['lon'].mean()],
                    zoom_start=16,
                    max_zoom=20,
                    min_zoom=12,
                    control_scale=True
                )

                # Add fullscreen control
                Fullscreen().add_to(map)
                
                # Add measurement tool
                MeasureControl(position='topleft', primary_length_unit='kilometers').add_to(map)
                
                # Add layer control
                folium.LayerControl().add_to(map)

                folium.Marker(
                    [lat, lon],
                    popup="Selected Office",
                    icon=folium.Icon(color="red", icon="star")
                ).add_to(map)

                # Add businesses marker
                for idx in selected_idx:
                    row = filtered_df.iloc[idx]
                    popup_content = f"""
                    <strong>{row['name']}</strong><br>
                    Category: {row['category']}<br>
                    <i><a href="https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}" target="_blank">Open in Google Maps</a></i>
                    """
                    folium.Marker(
                        [row['lat'], row['lon']],
                        popup=folium.Popup(popup_content, max_width=300),
                        icon=folium.Icon(color="blue", icon="info-sign", prefix="glyphicon")
                    ).add_to(map)

                if map is not None:
                    with st.container():
                        st_folium(map, width=None, height=600, returned_objects=["last_active_drawing"])
                else:
                    st.error("An error occurred while generating the map. Please try again.")

if __name__ == '__main__':    
    data = _read_data()

    # Selection table
    event = _show_raw(data)

    # Get Business Data
    radius = st.slider("Radius (km)", 1, 5, 1, 1)
    radius = radius*1000
    _get_business_data(data, radius)