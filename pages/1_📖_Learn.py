import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Learning Page",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="auto"
)


st.title('Pickups in NYC')

DATA_URL = ("https://s3-us-west-2.amazonaws.com/streamlit-demo-data/uber-raw-data-sep14.csv.gz")

@st.cache_data
def _load_data(nrows):
    data_load_state = st.text('Loading data...')
    data = pd.read_csv(DATA_URL, nrows=nrows)
    lowercase = lambda x: str(x).lower()
    data.rename(lowercase, axis='columns', inplace=True)
    data['date/time'] = pd.to_datetime(data['date/time'])
    data_load_state.text('Loading data...done!')
    return data

def _raw_data(data):
    st.subheader('Raw data')
    st.write(data)

def _pickup_per_hour(data):
    st.subheader('Pickups per hour')
    hist_values = np.histogram(data['date/time'].dt.hour, bins=24, range=(0,24))[0]
    st.bar_chart(hist_values)

def _map(data, title):
    st.subheader(title)

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position=["lon", "lat"],
        get_color="[200, 30, 0, 160]",
        get_radius=10,
    )

    view_state = pdk.ViewState(
        latitude=40.7,
        longitude=-74,
        min_zoom=10,
        max_zoom=10,
        pitch=0,
    )

    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))

def _filter_map(data, type: str):
    if type == "hour":
        hour_to_filter = st.slider("hour", min_value=0, max_value=23, value=(0, 23))
        st.subheader(f'Pickups between {hour_to_filter[0]} and {hour_to_filter[1]}' if hour_to_filter[0] != hour_to_filter[1] else f'Pickups at {hour_to_filter[0]}')
        filtered = data[data['date/time'].dt.hour.between(hour_to_filter[0], hour_to_filter[1])]
        _map(filtered, "Filtered Map")

def _chatbox(text):
    st.chat_message(text)
    st.chat_input(placeholder="Say Hello!")


# MAIN
def main():
    # Load Data
    data = _load_data(50000)

    # Display Data
    if st.checkbox("Show Raw Data"):
        _raw_data(data)
    _pickup_per_hour(data)
    _map(data, "Raw Map")
    _filter_map(data, "hour")
    _chatbox("Hello, User")
main()