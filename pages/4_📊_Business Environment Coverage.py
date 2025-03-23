import pandas as pd
import streamlit as st

import os
import requests
from dotenv import load_dotenv
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
        selection_mode="multi-row",
        height=300
    )

    return event

def _get_business_data(data, radius):
    filtered = event.selection.rows
    data = data.iloc[filtered]

    if data.shape[0] == 0:
        st.markdown("### 👈 Please select one or more locations to display on the map")
        return None

    lat = data["Lat"].mean()
    lon = data["Lon"].mean()

    st.subheader("💵 Business Around in 5km radius")

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
            node["highway"](around:{radius},{lat},{lon});
            node["railway"](around:{radius},{lat},{lon});
            node["aeroway"](around:{radius},{lat},{lon});
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

    response = requests.get(url, params={'data': query})
    data = response.json()

    for element in data['elements']:
        st.write(element.get('tags', {}).get('name'))

if __name__ == '__main__':    
    data = _read_data()

    # Selection table
    event = _show_raw(data)

    # Get Business Data
    radius = st.slider("Radius (km)", 1, 10, 5, 1)
    _get_business_data(data, radius*1000)