import numpy as np
import pandas as pd
import streamlit as st

import pydeck as pdk
import folium
from streamlit_folium import st_folium

import os
import requests
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="Main Page",
    page_icon="📖",
    layout="centered",
    initial_sidebar_state="auto"
)

OUTLET_DATA = "./data/outlets.csv"

def _read_data():
    df = pd.read_csv(OUTLET_DATA, delimiter=";")
    return df

def _raw(data):
    st.dataframe(data, hide_index=True)

def _mapRad(data):
    st.subheader("Radius 5KM Map")
    
    layers = [
        pdk.Layer(
            "ScatterplotLayer",
            data=data,
            get_position=["Lon", "Lat"],
            get_color=[0, 0, 255, 80],
            get_radius=500
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=data,
            get_position=["Lon", "Lat"],
            get_color=[200, 30, 0, 160],
            get_radius=100
        )
    ]

    view_state = pdk.ViewState(
        latitude=np.average(data["Lat"]),
        longitude=np.average(data["Lon"]),
        min_zoom=12.5,
        max_zoom=12.5,
        pitch=0,
    )
    
    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        layers=layers,
        initial_view_state=view_state
        ))
    
def _foliumMap(data):
    # Initiate Map View
    map = folium.Map(
        location=[data["Lat"].mean(), data["Lon"].mean()],
        zoom_start=12.5
    )

    for _, row in data.iterrows():
        folium.Marker([row["Lat"], row["Lon"]], popup="Center Point").add_to(map)

        folium.Circle(
            location=[row["Lat"], row["Lon"]],
            radius=500,
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.3,
        ).add_to(map)

    st.subheader("Radius 5KM Map")
    st_folium(map)

def _foliumMapRad(data):


if __name__ == '__main__':
    data = _read_data()
    _raw(data)
    # _mapRad(data)
    _foliumMap(data)
    _foliumMapRad(data)