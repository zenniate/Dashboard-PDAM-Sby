import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Dashboard PDAM - Subzona 215", layout="wide")

st.markdown("<h1 style='text-align: center; color: #2c3e50;'>💧 Interaktif Dashboard PDAM - Subzona 215</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7f8c8d;'>Komparasi Geospasial: Volume Air (m³) vs Tagihan (Rp)</p>", unsafe_allow_html=True)
st.divider()

# ==========================================
# 2. LOAD DATA & FORMATTING
# ==========================================
@st.cache_data
def load_data():
    # Menggunakan file hasil pipeline terakhir
    # Pastikan file ini ada di direktori yang sama dengan skrip ini
    try:
        df = pd.read_csv("Data_Siap_Clustering_Final3.csv") 
    except FileNotFoundError:
        # Dummy data jika file tidak ditemukan untuk keperluan testing
        return pd.DataFrame()

    df['THBL'] = df['THBL'].astype(str)
    df['TAHUN'] = df['THBL'].str[:4]
    df['BULAN_ANGKA'] = df['THBL'].str[4:]
    
    bulan_indo = {
        '01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April',
        '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus',
        '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'
    }
    
    df['NAMA_BULAN'] = df['BULAN_ANGKA'].map(bulan_indo) + " " + df['TAHUN']
    
    df['Lat_Jitter'] = df['Latitude'] + np.random.uniform(-0.0005, 0.0005, len(df))
    df['Lon_Jitter'] = df['Longitude'] + np.random.uniform(-0.0005, 0.0005, len(df))
    return df

df = load_data()

# Proteksi jika dataframe kosong
if df.empty:
    st.error("File 'Data_Siap_Clustering_Final3.csv' tidak ditemukan. Pastikan file tersedia.")
    st.stop()

# ==========================================
# 3. SIDEBAR (LOGOS & FILTER)
# ==========================================

# --- LOGO ATAS (PDAM) ---
if os.path.exists("pdam-surabaya.png"):
    st.sidebar.image("pdam-surabaya.png", use_container_width=True)

st.sidebar.divider()

# --- KONTROL PANEL / FILTER ---
st.sidebar.header("🕹️ Filter Waktu")
jenis_periode = st.sidebar.radio("Pilih Mode Waktu:", ["Semua Waktu (Default)", "Filter per Tahun", "Filter per Bulan"])

if jenis_periode == "Semua Waktu (Default)":
    df_filtered = df.groupby(['JALAN', 'Latitude', 'Longitude', 'Lat_Jitter', 'Lon_Jitter']).agg({
        'TOTAL_PAKAI': 'sum',
        'TOTAL_RP': 'sum',
        'JUMLAH_PELANGGAN': 'mean'
    }).reset_index()
    label_waktu = "Semua Periode (2024 - 2026)"

elif jenis_periode == "Filter per Tahun":
    pilih_waktu = st.sidebar.selectbox("Pilih Tahun:", sorted(df['TAHUN'].unique(), reverse=True))
    df_temp = df[df['TAHUN'] == pilih_waktu]
    df_filtered = df_temp.groupby(['JALAN', 'Latitude', 'Longitude', 'Lat_Jitter', 'Lon_Jitter']).agg({
        'TOTAL_PAKAI': 'sum',
        'TOTAL_RP': 'sum',
        'JUMLAH_PELANGGAN': 'mean'
    }).reset_index()
    label_waktu = f"Tahun {pilih_waktu}"

else: 
    bulan_sorted = df[['THBL', 'NAMA_BULAN']].drop_duplicates().sort_values(by='THBL', ascending=False)['NAMA_BULAN']
    pilih_waktu = st.sidebar.selectbox("Pilih Bulan Tagihan:", bulan_sorted)
    df_filtered = df[df['NAMA_BULAN'] == pilih_waktu]
    label_waktu = f"{pilih_waktu}"

# Hitung Harga per m3 dinamis
df_filtered['HARGA_PER_M3'] = np.where(df_filtered['TOTAL_PAKAI'] > 0, df_filtered['TOTAL_RP'] / df_filtered['TOTAL_PAKAI'], 0)

# --- BAGIAN TIPS DENGAN HYPERLINK PDF ---
st.sidebar.info("💡 **Tips:**")
st.sidebar.markdown("""
- **Zoom:** Scroll mouse.
- **Geser:** Klik & tarik.
- <a href='https://drive.google.com/file/d/1uRwUfXgt6NNKbcfpRixEp9eV65G85XMG/view?usp=sharing' target='_blank' style='color: #0000FF; text-decoration: underline; font-weight: bold;'>Petunjuk Penggunaan</a>
""", unsafe_allow_html=True)

# --- LOGO BAWAH (ITS & STATISTIKA) ---
st.sidebar.markdown("<br><br>", unsafe_allow_html=True) 
col_l1, col_l2 = st.sidebar.columns(2)
with col_l1:
    if os.path.exists("Badge_ITS.png"):
        st.image("Badge_ITS.png", use_container_width=True)
with col_l2:
    if os.path.exists("logo-statistika-white-border.png"):
        st.image("logo-statistika-white-border.png", use_container_width=True)

# ==========================================
# 4. TOP METRICS
# ==========================================
total_pakai = df_filtered['TOTAL_PAKAI'].sum()
total_rp = df_filtered['TOTAL_RP'].sum()
rata_harga = total_rp / total_pakai if total_pakai > 0 else 0

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("💧 Total Volume Air", f"{int(total_pakai):,} m³".replace(',', '.'))
col_m2.metric("💰 Total Tagihan", f"Rp {int(total_rp):,}".replace(',', '.'))
col_m3.metric("👥 Rata-rata Pelanggan Aktif", f"{int(df_filtered['JUMLAH_PELANGGAN'].sum()):,}".replace(',', '.'))
col_m4.metric("🏷️ Harga Rata-rata / m³", f"Rp {int(rata_harga):,}".replace(',', '.'))

st.divider()

# ==========================================
# 5. DUAL MAPS (LIGHT MODE)
# ==========================================
st.subheader(f"🗺️ Peta Komparasi Interaktif ({label_waktu})")
map_col1, map_col2 = st.columns(2)

hover_konf = {"Lat_Jitter": False, "Lon_Jitter": False, "TOTAL_PAKAI": True, "TOTAL_RP": True, "HARGA_PER_M3": ":.0f"}

with map_col1:
    st.markdown("<h4 style='text-align: center; color: #3498db;'>💧 Distribusi Volume Air (m³)</h4>", unsafe_allow_html=True)
    fig_map1 = px.scatter_mapbox(df_filtered, lat="Lat_Jitter", lon="Lon_Jitter", color='TOTAL_PAKAI', size='TOTAL_PAKAI',
                                 color_continuous_scale=["#2ecc71", "#f1c40f", "#e74c3c"], hover_name="JALAN",          
                                 hover_data=hover_konf, zoom=13.5, center={"lat": -7.285, "lon": 112.796}, 
                                 mapbox_style="carto-positron", labels={'TOTAL_PAKAI': 'm³', 'HARGA_PER_M3': 'Rp/m³'})
    fig_map1.update_layout(separators=",.", margin={"r":0,"t":0,"l":0,"b":0}, 
                           coloraxis_colorbar=dict(title="<b>m³</b>", thickness=10, tickformat=",.0f"))
    st.plotly_chart(fig_map1, use_container_width=True, config={'scrollZoom': True})

with map_col2:
    st.markdown("<h4 style='text-align: center; color: #2ecc71;'>💰 Distribusi Tagihan (Rp)</h4>", unsafe_allow_html=True)
    fig_map2 = px.scatter_mapbox(df_filtered, lat="Lat_Jitter", lon="Lon_Jitter", color='TOTAL_RP', size='TOTAL_RP',
                                 color_continuous_scale=["#2ecc71", "#f1c40f", "#e74c3c"], hover_name="JALAN",          
                                 hover_data=hover_konf, zoom=13.5, center={"lat": -7.285, "lon": 112.796}, 
                                 mapbox_style="carto-positron", labels={'TOTAL_RP': 'Rp', 'HARGA_PER_M3': 'Rp/m³'})
    fig_map2.update_layout(separators=",.", margin={"r":0,"t":0,"l":0,"b":0}, 
                           coloraxis_colorbar=dict(title="<b>Rp</b>", thickness=10, tickformat=",.0f"))
    st.plotly_chart(fig_map2, use_container_width=True, config={'scrollZoom': True})

# ==========================================
# 6. TABEL & GRAFIK (TOP 10 & TOP 5)
# ==========================================
st.divider()
st.subheader(f"🏆 Peringkat Kinerja Jalan ({label_waktu})")

df_tabel = df_filtered.groupby('JALAN')[['TOTAL_PAKAI', 'TOTAL_RP']].sum().reset_index()
df_tabel['HARGA_PER_M3'] = np.where(df_tabel['TOTAL_PAKAI'] > 0, df_tabel['TOTAL_RP'] / df_tabel['TOTAL_PAKAI'], 0)

df_tabel_manusia = df_tabel.rename(columns={
    'JALAN': 'Nama Jalan',
    'TOTAL_PAKAI': 'Volume Air (m³)',
    'TOTAL_RP': 'Total Tagihan (Rp)',
    'HARGA_PER_M3': 'Harga per m³ (Rp)'
})

c1, c2, c3, c4 = st.columns([1, 1.5, 1, 1.5])

with c1:
    st.markdown("**Top 10 Volume Air**")
    df_top_p = df_tabel_manusia[['Nama Jalan', 'Volume Air (m³)']].sort_values(by='Volume Air (m³)', ascending=False).head(10)
    df_top_p_disp = df_top_p.copy()
    df_top_p_disp['Volume Air (m³)'] = df_top_p_disp['Volume Air (m³)'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
    st.dataframe(df_top_p_disp, hide_index=True, use_container_width=True)

with c2:
    fig_p = px.bar(df_tabel.sort_values(by='TOTAL_PAKAI', ascending=False).head(5).sort_values(by='TOTAL_PAKAI', ascending=True), 
                   x='TOTAL_PAKAI', y='JALAN', orientation='h', text='TOTAL_PAKAI', 
                   color_discrete_sequence=['#3498db'],
                   labels={'TOTAL_PAKAI': 'Volume Air (m³)', 'JALAN': 'Jalan'})
    fig_p.update_traces(texttemplate='%{text:,.0f} m³', textposition='inside')
    fig_p.update_layout(separators=",.", height=350, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="", xaxis_title="")
    st.plotly_chart(fig_p, use_container_width=True)

with c3:
    st.markdown("**Top 10 Total Tagihan**")
    df_top_r = df_tabel_manusia[['Nama Jalan', 'Total Tagihan (Rp)']].sort_values(by='Total Tagihan (Rp)', ascending=False).head(10)
    df_top_r_disp = df_top_r.copy()
    df_top_r_disp['Total Tagihan (Rp)'] = df_top_r_disp['Total Tagihan (Rp)'].apply(lambda x: f"Rp {int(x):,}".replace(',', '.'))
    st.dataframe(df_top_r_disp, hide_index=True, use_container_width=True)

with c4:
    fig_r = px.bar(df_tabel.sort_values(by='TOTAL_RP', ascending=False).head(5).sort_values(by='TOTAL_RP', ascending=True), 
                   x='TOTAL_RP', y='JALAN', orientation='h', text='TOTAL_RP', 
                   color_discrete_sequence=['#2ecc71'],
                   labels={'TOTAL_RP': 'Total Tagihan (Rp)', 'JALAN': 'Jalan'})
    fig_r.update_traces(texttemplate='Rp %{text:,.0f}', textposition='inside')
    fig_r.update_layout(separators=",.", height=350, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="", xaxis_title="")
    st.plotly_chart(fig_r, use_container_width=True)

st.markdown("<br><h4 style='color: #9b59b6;'>🏷️ Analisis Rasio: Harga Air per m³ Tertinggi</h4>", unsafe_allow_html=True)
col_t_h, col_b_h = st.columns([1, 1.5])

with col_t_h:
    st.markdown("**Top 10 Harga per m³**")
    df_top_h = df_tabel_manusia[['Nama Jalan', 'Harga per m³ (Rp)']].sort_values(by='Harga per m³ (Rp)', ascending=False).head(10)
    df_top_h_disp = df_top_h.copy()
    df_top_h_disp['Harga per m³ (Rp)'] = df_top_h_disp['Harga per m³ (Rp)'].apply(lambda x: f"Rp {int(x):,}".replace(',', '.'))
    st.dataframe(df_top_h_disp, hide_index=True, use_container_width=True)

with col_b_h:
    fig_h = px.bar(df_tabel.sort_values(by='HARGA_PER_M3', ascending=False).head(5).sort_values(by='HARGA_PER_M3', ascending=True), 
                   x='HARGA_PER_M3', y='JALAN', orientation='h', text='HARGA_PER_M3', 
                   color_discrete_sequence=['#9b59b6'],
                   labels={'HARGA_PER_M3': 'Harga per m³ (Rp)', 'JALAN': 'Jalan'})
    fig_h.update_traces(texttemplate='Rp %{text:,.0f}', textposition='inside')
    fig_h.update_layout(separators=",.", height=350, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="", xaxis_title="")
    st.plotly_chart(fig_h, use_container_width=True)

# ==========================================
# 7. TREN HISTORIS
# ==========================================
st.divider()
st.subheader("💡 Eksplorasi Tren Historis")
df_tr = df.groupby('THBL')[['TOTAL_PAKAI', 'TOTAL_RP']].sum().reset_index()
df_tr['Bulan_Tahun'] = pd.to_datetime(df_tr['THBL'], format='%Y%m')
fig_tr = make_subplots(specs=[[{"secondary_y": True}]])
fig_tr.add_trace(go.Scatter(x=df_tr['Bulan_Tahun'], y=df_tr['TOTAL_PAKAI'], name="Volume Air (m³)", mode='lines+markers', line=dict(color='#3498db', width=3)), secondary_y=False)
fig_tr.add_trace(go.Scatter(x=df_tr['Bulan_Tahun'], y=df_tr['TOTAL_RP'], name="Tagihan (Rp)", mode='lines+markers', line=dict(color='#2ecc71', width=3)), secondary_y=True)
fig_tr.update_layout(separators=",.", height=400, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified", xaxis=dict(dtick="M3", tickformat="%b %Y"))
fig_tr.update_yaxes(title_text="Volume Air (m³)", secondary_y=False, tickformat=",.0f")
fig_tr.update_yaxes(title_text="Tagihan (Rp)", secondary_y=True, tickformat=",.0f")
st.plotly_chart(fig_tr, use_container_width=True)
