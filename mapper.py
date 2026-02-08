import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

st.set_page_config(page_title="Troy's Map", layout="wide")

SAVED_DATA = "permanent_work_log.csv"

# Initialize photo storage
if 'all_photos' not in st.session_state:
    st.session_state.all_photos = {}
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

# --- 1. DATA LOADING ---
if 'df' not in st.session_state:
    st.title("🛰️ Troy's Fielding Tool")
    if os.path.exists(SAVED_DATA):
        st.session_state.df = pd.read_csv(SAVED_DATA)
        st.rerun()

    uploaded_file = st.file_uploader("Upload CSV (Ticket, Lat, Lon, Notes)", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        df.columns.values[0], df.columns.values[1], df.columns.values[2] = 'Ticket', 'lat', 'lon'
        df['Notes'] = df.iloc[:, 3].fillna("No notes.") if len(df.columns) >= 4 else "No notes."
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df = df.dropna(subset=['lat', 'lon'])
        df['status'] = 'Pending'
        st.session_state.df = df
        df.to_csv(SAVED_DATA, index=False)
        st.rerun()
    st.stop()

df = st.session_state.df

# --- 2. THE MAP ---
m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=13, tiles="OpenStreetMap")

for i, row in df.iterrows():
    t_id = str(row['Ticket'])
    is_sel = (str(st.session_state.selected_id) == t_id)
    color = "orange" if is_sel else ("green" if row['status'] == 'Completed' else "blue")
    
    folium.Marker(
        [row['lat'], row['lon']],
        popup=f"ID:{t_id}",
        icon=folium.Icon(color=color, icon="camera" if not is_sel else "star")
    ).add_to(m)

# RENDER MAP
st.subheader("Field Map")
map_data = st_folium(m, height=400, width=None, key="troy_map", returned_objects=["last_object_clicked_popup"])

# Catch the click
if map_data and map_data.get("last_object_clicked_popup"):
    clicked_id = map_data["last_object_clicked_popup"].split(":")[1]
    if st.session_state.selected_id != clicked_id:
        st.session_state.selected_id = clicked_id
        st.rerun()

# --- 3. SIDEBAR (The New Layout) ---
st.sidebar.title("📍 Site Details")

if st.session_state.selected_id:
    t_id = st.session_state.selected_id
    sel = df[df['Ticket'].astype(str) == t_id].iloc[0]
    
    st.sidebar.markdown(f"## Ticket: {t_id}")
    
    # NAVIGATION
    nav_url = f"google.navigation:q={sel['lat']},{sel['lon']}"
    st.sidebar.link_button("🚗 Start Nav", nav_url, use_container_width=True)
    
    # CAMERA / PHOTO
    photos = st.sidebar.file_uploader("📸 Capture Photo", accept_multiple_files=True, key=f"cam_{t_id}")
    if photos:
        st.session_state.all_photos[t_id] = photos

    # COMPLETE BUTTON
    if st.sidebar.button("✅ Mark Complete", use_container_width=True):
        st.session_state.df.loc[st.session_state.df['Ticket'].astype(str) == t_id, 'status'] = 'Completed'
        st.session_state.selected_id = None
        st.session_state.df.to_csv(SAVED_DATA, index=False)
        st.rerun()

    st.sidebar.markdown("---")
    # LARGE NOTES BOX (At the bottom of sidebar)
    st.sidebar.subheader("📋 Field Notes")
    st.sidebar.info(sel['Notes'])
else:
    st.sidebar.write("Select a pin on the map to see details and notes.")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Reset Day", use_container_width=True):
    if os.path.exists(SAVED_DATA): os.remove(SAVED_DATA)
    st.session_state.clear()
    st.rerun()
