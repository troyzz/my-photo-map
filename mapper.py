import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import zipfile
from io import BytesIO

st.set_page_config(page_title="Field Mapper PRO", layout="wide")

# --- 1. PERSISTENT STORAGE ---
SAVED_DATA = "permanent_work_log.csv"

# Initialize photo storage if not exists
if 'all_photos' not in st.session_state:
    st.session_state.all_photos = {}
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

def save_progress():
    st.session_state.df.to_csv(SAVED_DATA, index=False)

# --- 2. DATA LOADING ---
if 'df' not in st.session_state:
    if os.path.exists(SAVED_DATA):
        st.session_state.df = pd.read_csv(SAVED_DATA)
    else:
        uploaded_file = st.sidebar.file_uploader("Upload CSV to Start", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            df.columns.values[0], df.columns.values[1], df.columns.values[2] = "Ticket", "lat", "lon"
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df = df.dropna(subset=['lat', 'lon'])
            df['status'] = 'Pending'
            st.session_state.df = df
            save_progress()
            st.rerun()
        st.stop()

df = st.session_state.df

# --- 3. SEARCH & DYNAMIC ZOOM ---
st.sidebar.markdown("## 🔍 Find Site")
search_query = st.sidebar.text_input("Enter Ticket Number")

m = folium.Map()
if search_query:
    match = df[df['Ticket'].astype(str).str.contains(search_query, na=False)]
    if not match.empty:
        st.session_state.selected_id = str(match.iloc[0]['Ticket'])
        m = folium.Map(location=[match.iloc[0]['lat'], match.iloc[0]['lon']], zoom_start=18)
else:
    sw, ne = df[['lat', 'lon']].min().values.tolist(), df[['lat', 'lon']].max().values.tolist()
    m.fit_bounds([sw, ne])

folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                 attr='Esri', name='Satellite', overlay=False).add_to(m)

for _, row in df.iterrows():
    t_id = str(row['Ticket'])
    is_sel = (t_id == str(st.session_state.selected_id))
    color = "orange" if is_sel else ("green" if row['status'] == 'Completed' else "blue")
    folium.Marker([row['lat'], row['lon']], popup=f"ID:{t_id}", icon=folium.Icon(color=color, icon="camera")).add_to(m)

map_data = st_folium(m, width=None, height=450, returned_objects=["last_object_clicked_popup"], key="pro_map")

# --- 4. SELECTION LOGIC ---
if map_data and map_data.get("last_object_clicked_popup"):
    new_id = map_data["last_object_clicked_popup"].split(":")[1]
    if st.session_state.selected_id != new_id:
        st.session_state.selected_id = new_id
        st.rerun()

# --- 5. THE SIDEBAR PHOTO HANDLER ---
if st.session_state.selected_id:
    t_id = st.session_state.selected_id
    sel_row = df[df['Ticket'].astype(str) == t_id].iloc[0]
    
    st.sidebar.markdown(f"### 📍 Site: {t_id}")
    nav_url = f"https://www.google.com/maps/dir/?api=1&destination={sel_row['lat']},{sel_row['lon']}&travelmode=driving"
    st.sidebar.link_button("🚗 Start Nav", nav_url)
    
    # Check for existing photos
    if t_id in st.session_state.all_photos:
        st.sidebar.write(f"✅ {len(st.session_state.all_photos[t_id])} photos uploaded.")

    # REFINED UPLOADER
    new_photos = st.sidebar.file_uploader("Upload From Gallery", accept_multiple_files=True, key=f"p_up_{t_id}")
    
    # Immediately store them if they exist
    if new_photos:
        st.session_state.all_photos[t_id] = new_photos

    if st.sidebar.button("✅ Confirm Completion"):
        st.session_state.df.loc[st.session_state.df['Ticket'].astype(str) == t_id, 'status'] = 'Completed'
        st.session_state.selected_id = None
        save_progress()
        st.rerun()

# --- 6. EXPORT ---
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
