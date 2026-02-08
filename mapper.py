import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import zipfile
from io import BytesIO

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="Troy's Fielding Tool", 
    page_icon="🛰️", 
    layout="wide"
)

SAVED_DATA = "permanent_work_log.csv"

if 'all_photos' not in st.session_state:
    st.session_state.all_photos = {}
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

def save_progress():
    st.session_state.df.to_csv(SAVED_DATA, index=False)

# --- 2. DATA LOADING (Bulletproof Version) ---
if 'df' not in st.session_state:
    if os.path.exists(SAVED_DATA):
        st.session_state.df = pd.read_csv(SAVED_DATA)
    else:
        uploaded_file = st.sidebar.file_uploader("Upload CSV (Ticket, Lat, Lon, Notes)", type=["csv"])
        if uploaded_file:
            try:
                raw_df = pd.read_csv(uploaded_file)
                # Remove completely empty rows
                raw_df = raw_df.dropna(how='all')
                
                # Create a clean dataframe with standard names
                clean_df = pd.DataFrame()
                clean_df['Ticket'] = raw_df.iloc[:, 0].astype(str)
                clean_df['lat'] = pd.to_numeric(raw_df.iloc[:, 1], errors='coerce')
                clean_df['lon'] = pd.to_numeric(raw_df.iloc[:, 2], errors='coerce')
                
                # Handle Notes column safely
                if len(raw_df.columns) >= 4:
                    clean_df['Notes'] = raw_df.iloc[:, 3].fillna("No notes.")
                else:
                    clean_df['Notes'] = "No notes provided."
                
                # Drop any rows where Lat/Lon failed to convert
                clean_df = clean_df.dropna(subset=['lat', 'lon'])
                clean_df['status'] = 'Pending'
                
                st.session_state.df = clean_df
                save_progress()
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error loading CSV: {e}")
        st.stop()

df = st.session_state.df

# --- 3. SEARCH & MAP ---
st.sidebar.markdown("## 🔍 Find Site")
search_query = st.sidebar.text_input("Enter Ticket Number")

# Check if we have data to map
if df.empty:
    st.warning("No valid GPS data found in your CSV.")
    st.stop()

# Initialize Map
m = folium.Map()

if search_query:
    match = df[df['Ticket'].astype(str).str.contains(search_query, na=False)]
    if not match.empty:
        st.session_state.selected_id = str(match.iloc[0]['Ticket'])
        m = folium.Map(location=[match.iloc[0]['lat'], match.iloc[0]['lon']], zoom_start=18)
    else:
        # Fallback if search doesn't find a match
        sw, ne = df[['lat', 'lon']].min().values.tolist(), df[['lat', 'lon']].max().values.tolist()
        m.fit_bounds([sw, ne])
else:
    # Auto-zoom to all pins
    sw, ne = df[['lat', 'lon']].min().values.tolist(), df[['lat', 'lon']].max().values.tolist()
    m.fit_bounds([sw, ne])

folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri', name='Satellite', overlay=False
).add_to(m)

for _, row in df.iterrows():
    t_id = str(row['Ticket'])
    is_sel = (t_id == str(st.session_state.selected_id))
    color = "orange" if is_sel else ("green" if row['status'] == 'Completed' else "blue")
    icon_type = "star" if is_sel else ("check" if row['status'] == 'Completed' else "camera")
    folium.Marker(
        [row['lat'], row['lon']], 
        popup=f"ID:{t_id}", 
        icon=folium.Icon(color=color, icon=icon_type)
    ).add_to(m)

# RENDER
map_data = st_folium(m, width=None, height=450, returned_objects=["last_object_clicked_popup"], key="pro_map")

# --- 4. SELECTION & SIDEBAR ---
if map_data and map_data.get("last_object_clicked_popup"):
    clicked_id = map_data["last_object_clicked_popup"].split(":")[1]
    if st.session_state.selected_id != clicked_id:
        st.session_state.selected_id = clicked_id
        st.rerun()

if st.session_state.selected_id:
    t_id = st.session_state.selected_id
    # Get the row safely
    row_match = df[df['Ticket'].astype(str) == t_id]
    if not row_match.empty:
        sel_row = row_match.iloc[0]
        st.sidebar.markdown(f"### 📍 Site: {t_id}")
        
        # DISPLAY NOTES
        st.sidebar.markdown("#### 📝 Field Notes:")
        st.sidebar.info(sel_row['Notes'])

        nav_url = f"https://www.google.com/maps/dir/?api=1&destination={sel_row['lat']},{sel_row['lon']}&travelmode=driving"
        st.sidebar.link_button("🚗 Start Google Maps Nav", nav_url, use_container_width=True)
        
        photos = st.sidebar.file_uploader("Upload From Gallery", accept_multiple_files=True, key=f"p_up_{t_id}")
        if photos:
            st.session_state.all_photos[t_id] = photos

        if st.sidebar.button("✅ Confirm Completion", use_container_width=True):
            st.session_state.df.loc[st.session_state.df['Ticket'].astype(str) == t_id, 'status'] = 'Completed'
            st.session_state.selected_id = None
            save_progress()
            st.rerun()

        if st.sidebar.button("🔙 Deselect / Go Back", use_container_width=True):
            st.session_state.selected_id = None
            st.rerun()

# --- 5. EXPORT ---
st.sidebar.markdown("---")
total_photos = sum(len(v) for v in st.session_state.all_photos.values())
if total_photos > 0:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for ticket, files in st.session_state.all_photos.items():
            for i, f in enumerate(files):
                ext = f.name.split('.')[-1]
                z.writestr(f"{ticket}_{i+1}.{ext}", f.getvalue())
    st.sidebar.download_button("📥 Download ZIP", data=buf.getvalue(), file_name="Field_Photos.zip", use_container_width=True)

if st.sidebar.button("🗑️ Reset Day"):
    if os.path.exists(SAVED_DATA): os.remove(SAVED_DATA)
    st.session_state.clear()
    st.rerun()
