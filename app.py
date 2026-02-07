import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import zipfile
from io import BytesIO
from datetime import datetime

# --- SETTINGS ---
st.set_page_config(page_title="Field Mapper Pro", layout="wide")
PHOTO_DIR = "captured_photos"
LOG_FILE = "work_log.csv"

if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)

st.title("📸 Field Photo Mapper")

# --- HELPER FUNCTIONS ---
def load_initial_data(file):
    df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
    df.columns = [str(c).strip() for c in df.columns]
    rename_dict = {}
    for col in df.columns:
        low_col = col.lower()
        if low_col in ['lat', 'latitude', 'y']: rename_dict[col] = 'lat'
        if low_col in ['lon', 'long', 'longitude', 'x']: rename_dict[col] = 'lon'
        if 'ticket' in low_col or 'number' in low_col: rename_dict[col] = 'Ticket Numbers'
    df = df.rename(columns=rename_dict)
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    df = df.dropna(subset=['lat', 'lon'])
    if 'status' not in df.columns:
        df['status'] = 'Pending'
    return df

def create_zip_of_photos():
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for root, dirs, files in os.walk(PHOTO_DIR):
            for file in files:
                z.write(os.path.join(root, file), file)
    return buf.getvalue()

# --- 1. SESSION DATA ---
if os.path.exists(LOG_FILE) and 'df' not in st.session_state:
    st.session_state.df = pd.read_csv(LOG_FILE)

if 'df' not in st.session_state:
    uploaded_file = st.sidebar.file_uploader("Upload spreadsheet", type=["csv", "xlsx"])
    if uploaded_file:
        st.session_state.df = load_initial_data(uploaded_file)
        st.session_state.df.to_csv(LOG_FILE, index=False)
        st.rerun()
    st.info("👈 Upload your location list in the sidebar to start.")
    st.stop()

# --- 2. MAP ---
working_df = st.session_state.df
color_map = {"Pending": "blue", "En Route": "orange", "Completed": "green", "No Access": "red"}
m = folium.Map(location=[working_df['lat'].mean(), working_df['lon'].mean()], zoom_start=13)

for idx, row in working_df.iterrows():
    folium.Marker(
        [row['lat'], row['lon']],
        popup=f"Ticket: {row['Ticket Numbers']}",
        icon=folium.Icon(color=color_map.get(row['status'], "blue"), icon="camera")
    ).add_to(m)

map_data = st_folium(m, width="100%", height=500)

# --- 3. SIDEBAR CONTROLS ---
if map_data.get("last_object_clicked_popup"):
    ticket_id = str(map_data["last_object_clicked_popup"].split(": ")[1])
    st.sidebar.header(f"📍 Ticket: {ticket_id}")
    
    if st.sidebar.button("🚗 Set as Next (Yellow)"):
        st.session_state.df.loc[st.session_state.df['Ticket Numbers'].astype(str) == ticket_id, 'status'] = 'En Route'
        st.session_state.df.to_csv(LOG_FILE, index=False)
        st.rerun()

    st.sidebar.divider()
    
    # Photo Section
    photo = st.sidebar.camera_input("Take Photo")
    if photo:
        # Save photo immediately when taken
        ts = datetime.now().strftime("%H%M%S")
        fname = f"Ticket_{ticket_id}_{ts}.jpg"
        with open(os.path.join(PHOTO_DIR, fname), "wb") as f:
            f.write(photo.getbuffer())
        st.sidebar.success(f"Photo Saved!")

    col1, col2 = st.sidebar.columns(2)
    if col1.button("✅ Completed"):
        st.session_state.df.loc[st.session_state.df['Ticket Numbers'].astype(str) == ticket_id, 'status'] = 'Completed'
        st.session_state.df.to_csv(LOG_FILE, index=False)
        st.rerun()
    if col2.button("🚫 No Access"):
        st.session_state.df.loc[st.session_state.df['Ticket Numbers'].astype(str) == ticket_id, 'status'] = 'No Access'
        st.session_state.df.to_csv(LOG_FILE, index=False)
        st.rerun()

# --- 4. EXPORT UTILS ---
st.sidebar.divider()
st.sidebar.subheader("Export Data")

# Zip Download
if os.listdir(PHOTO_DIR):
    zip_data = create_zip_of_photos()
    st.sidebar.download_button(
        label="📥 Download All Photos (ZIP)",
        data=zip_data,
        file_name=f"Photos_{datetime.now().strftime('%Y-%m-%d')}.zip",
        mime="application/zip"
    )

if st.sidebar.button("🗑️ Reset All Data"):
    if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
    for f in os.listdir(PHOTO_DIR): os.remove(os.path.join(PHOTO_DIR, f))
    del st.session_state.df
    st.rerun()