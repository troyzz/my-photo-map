import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import zipfile
from io import BytesIO

# 1. FORCE MOBILE OPTIMIZATION
st.set_page_config(page_title="Troy's Tool", layout="centered")

# Use a fresh filename to bypass any "ghost" files on the server
SAVED_DATA = "current_work_log_v2.csv"

# Initialize Session States
if 'all_photos' not in st.session_state: st.session_state.all_photos = {}
if 'selected_id' not in st.session_state: st.session_state.selected_id = None

# 2. DATA LOADING
if 'df' not in st.session_state:
    st.title("🛰️ Troy's Fielding Tool")
    
    # Check if we have a saved file from earlier
    if os.path.exists(SAVED_DATA):
        try:
            st.session_state.df = pd.read_csv(SAVED_DATA)
            st.rerun()
        except:
            os.remove(SAVED_DATA)

    uploaded_file = st.file_uploader("Upload CSV (Ticket, Lat, Lon, Notes)", type=["csv"])
    if uploaded_file:
        try:
            raw = pd.read_csv(uploaded_file).dropna(how='all')
            df = pd.DataFrame()
            df['Ticket'] = raw.iloc[:, 0].astype(str)
            df['lat'] = pd.to_numeric(raw.iloc[:, 1], errors='coerce')
            df['lon'] = pd.to_numeric(raw_df.iloc[:, 2], errors='coerce') if 'raw_df' not in locals() else pd.to_numeric(raw.iloc[:, 2], errors='coerce')
            df['Notes'] = raw.iloc[:, 3].fillna("No notes.") if len(raw.columns) >= 4 else "No notes."
            df = df.dropna(subset=['lat', 'lon'])
            df['status'] = 'Pending'
            st.session_state.df = df
            df.to_csv(SAVED_DATA, index=False)
            st.rerun()
        except Exception as e:
            st.error(f"Upload Error: {e}")
    st.stop()

df = st.session_state.df

# 3. SIDEBAR (Search & Reset)
search_query = st.sidebar.text_input("🔍 Search Ticket")
if st.sidebar.button("🗑️ Reset / New CSV"):
    if os.path.exists(SAVED_DATA): os.remove(SAVED_DATA)
    st.session_state.clear()
    st.rerun()

# 4. LIGHTWEIGHT MAP
# We are using standard map tiles (faster) instead of Satellite imagery for this test
m = folium.Map(tiles="OpenStreetMap")

if search_query:
    match = df[df['Ticket'].astype(str).str.contains(search_query, na=False)]
    if not match.empty:
        st.session_state.selected_id = str(match.iloc[0]['Ticket'])
        m.location = [match.iloc[0]['lat'], match.iloc[0]['lon']]
        m.zoom_start = 17
else:
    # Auto-fit all pins
    sw, ne = df[['lat', 'lon']].min().values.tolist(), df[['lat', 'lon']].max().values.tolist()
    m.fit_bounds([sw, ne])

for _, row in df.iterrows():
    t_id = str(row['Ticket'])
    is_sel = (t_id == st.session_state.selected_id)
    color = "orange" if is_sel else ("green" if row['status'] == 'Completed' else "blue")
    folium.Marker([row['lat'], row['lon']], icon=folium.Icon(color=color)).add_to(m)

# 5. DISPLAY
st.subheader("Field Map")
# Using a slightly smaller height to save mobile memory
map_data = st_folium(m, height=350, width=700, key="mobile_map")

if map_data and map_data.get("last_object_clicked_popup"):
    # Note: Using simpler logic for mobile click detection
    pass 

# 6. SITE DETAILS
if st.session_state.selected_id:
    t_id = st.session_state.selected_id
    sel = df[df['Ticket'].astype(str) == t_id].iloc[0]
    
    st.divider()
    st.markdown(f"### 📍 Ticket: {t_id}")
    st.info(f"**Notes:** {sel['Notes']}")
    
    nav_url = f"google.navigation:q={sel['lat']},{sel['lon']}"
    st.link_button("🚗 Start Nav", nav_url, use_container_width=True)
    
    if st.button("✅ Mark Complete", use_container_width=True):
        st.session_state.df.loc[st.session_state.df['Ticket'].astype(str) == t_id, 'status'] = 'Completed'
        st.session_state.selected_id = None
        st.session_state.df.to_csv(SAVED_DATA, index=False)
        st.rerun()
