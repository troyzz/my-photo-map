import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

st.set_page_config(page_title="Field Mapper PRO", layout="wide")

LOG_FILE = "work_log.csv"

# --- 1. DATA LOADING ---
if 'df' not in st.session_state:
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            
            # Show a preview so we can see if the phone is reading it right
            st.sidebar.write("File Preview (First 2 rows):", df.head(2))
            
            # Position-based rename
            df.columns.values[0] = "Ticket Numbers"
            df.columns.values[1] = "lat"
            df.columns.values[2] = "lon"
            
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df = df.dropna(subset=['lat', 'lon'])
            df['status'] = 'Pending'
            
            st.session_state.df = df
            st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {e}")
    st.stop()

df = st.session_state.df

# --- 2. MAP SETUP ---
st.sidebar.title("🔍 Search")
query = st.sidebar.text_input("Enter Ticket #")

v_lat, v_lon, zoom = df['lat'].mean(), df['lon'].mean(), 12

if query:
    match = df[df['Ticket Numbers'].astype(str).str.contains(query, na=False)]
    if not match.empty:
        v_lat, v_lon, zoom = match.iloc[0]['lat'], match.iloc[0]['lon'], 18

# --- 3. THE SATELLITE MAP ---
st.title("🛰️ Satellite Field View")

# Adding "Esri World Imagery" gives you a Google-like satellite view for free
m = folium.Map(location=[v_lat, v_lon], zoom_start=zoom, tiles='OpenStreetMap')
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Esri Satellite',
    overlay=False,
    control=True
).add_to(m)

for _, row in df.iterrows():
    color = "green" if row['status'] == 'Completed' else "blue"
    folium.Marker(
        [row['lat'], row['lon']],
        popup=f"Ticket: {row['Ticket Numbers']}",
        icon=folium.Icon(color=color, icon="camera")
    ).add_to(m)

st_folium(m, width="100%", height=500, key="field_map")

if st.sidebar.button("🗑️ Reset / New File"):
    st.session_state.clear()
    st.rerun()
