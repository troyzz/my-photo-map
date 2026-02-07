import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

st.set_page_config(page_title="Field Mapper PRO", layout="wide")

# --- 1. DATA LOADING ---
if 'df' not in st.session_state:
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        df.columns.values[0], df.columns.values[1], df.columns.values[2] = "Ticket", "lat", "lon"
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df = df.dropna(subset=['lat', 'lon'])
        df['status'] = 'Pending'
        st.session_state.df = df
        st.rerun()
    st.stop()

df = st.session_state.df

# --- 2. SEARCH ---
st.sidebar.title("🔍 Search")
query = st.sidebar.text_input("Enter Ticket #").strip()
v_lat, v_lon, zoom = df['lat'].mean(), df['lon'].mean(), 14

if query:
    match = df[df['Ticket'].astype(str).str.contains(query, na=False)]
    if not match.empty:
        v_lat, v_lon, zoom = match.iloc[0]['lat'], match.iloc[0]['lon'], 18

# --- 3. THE MOBILE-READY MAP ---
st.title("🛰️ Satellite Field View")

m = folium.Map(location=[v_lat, v_lon], zoom_start=zoom)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri', name='Satellite', overlay=False
).add_to(m)

for _, row in df.iterrows():
    color = "green" if row['status'] == 'Completed' else "blue"
    # Added a 'tooltip' - this often helps mobile browsers register the tap better
    folium.Marker(
        [row['lat'], row['lon']],
        popup=f"ID:{row['Ticket']}",
        tooltip=f"Ticket {row['Ticket']}",
        icon=folium.Icon(color=color, icon="camera")
    ).add_to(m)

# CRITICAL MOBILE FIX: width=None and returned_objects
map_data = st_folium(
    m, 
    width=None, 
    height=450, 
    returned_objects=["last_object_clicked_popup"],
    key="mobile_map"
)

# --- 4. THE SIDEBAR ACTIONS ---
# If a pin is tapped, show the camera
if map_data and map_data.get("last_object_clicked_popup"):
    try:
        # Extract ID from the popup text "ID:123"
        raw_id = map_data["last_object_clicked_popup"].split(":")[1]
        st.sidebar.markdown(f"## 📍 Selected: {raw_id}")
        
        # Camera Input
        photo = st.sidebar.camera_input("Take Site Photo", key=f"photo_{raw_id}")
        
        if st.sidebar.button("✅ Mark Completed"):
            st.session_state.df.loc[st.session_state.df['Ticket'].astype(str) == raw_id, 'status'] = 'Completed'
            st.success(f"Ticket {raw_id} Updated!")
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"Tap again to select pin.")

if st.sidebar.button("🗑️ Reset Map"):
    st.session_state.clear()
    st.rerun()
