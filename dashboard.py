import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Dashboard PDAM - Subzona 215", layout="wide")

# --- HEADER ---
st.markdown("<h1 style='text-align: center;'>💧 DASHBOARD INTERAKTIF PDAM - SUBZONA 215</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>PENGEMBANGAN INTERAKTIF DASHBOARD BERBASIS STREAMLIT UNTUK ANALISIS SPASIO-TEMPORAL DAN SEGMENTASI PELANGGAN PDAM MENGGUNAKAN K-MEANS CLUSTERING</p>", unsafe_allow_html=True)
st.divider()

# --- LOAD DATA ---
@st.cache_data
def load_data():
    df = pd.read_csv("Hasil_Clustering_Subzona_215.csv")
    df['THBL'] = df['THBL'].astype(str)
    df['TAHUN'] = df['THBL'].str[:4] # Ekstraksi Tahun
    df['BULAN'] = df['THBL'].str[4:] # Ekstraksi Bulan
    
    # Efek Jittering untuk Peta
    df['Lat_Jitter'] = df['Latitude'] + np.random.uniform(-0.0005, 0.0005, len(df))
    df['Lon_Jitter'] = df['Longitude'] + np.random.uniform(-0.0005, 0.0005, len(df))
    return df

df = load_data()

# --- SIDEBAR (KONTROL PANEL) ---
st.sidebar.header("🕹️ Filter & Kontrol")

# 1. Filter Periode (Bisa Tahunan / Bulanan)
jenis_periode = st.sidebar.radio("Pilih Mode Waktu:", ["Rekap Tahunan", "Detail Bulanan"])

if jenis_periode == "Rekap Tahunan":
    pilih_waktu = st.sidebar.selectbox("Pilih Tahun:", sorted(df['TAHUN'].unique(), reverse=True))
    # Agregasi data jika tahunan (dijumlahkan per jalan)
    df_temp = df[df['TAHUN'] == pilih_waktu]
    df_filtered = df_temp.groupby(['JALAN', 'Latitude', 'Longitude', 'Lat_Jitter', 'Lon_Jitter']).agg({
        'TOTAL_PAKAI': 'sum',
        'TOTAL_RP': 'sum',
        'JUMLAH_PELANGGAN': 'mean',
        'CLUSTER': lambda x: x.mode()[0] # Ambil cluster yang paling sering muncul
    }).reset_index()
    label_waktu = f"Tahun {pilih_waktu}"
else:
    pilih_waktu = st.sidebar.selectbox("Pilih Bulan Tagihan (THBL):", sorted(df['THBL'].unique(), reverse=True))
    df_filtered = df[df['THBL'] == pilih_waktu]
    label_waktu = f"Bulan {pilih_waktu}"

st.sidebar.divider()

# 2. Filter Variabel Analisis
st.sidebar.markdown("**Target Analisis Utama**")
var_analisis = st.sidebar.radio("Fokuskan Metrik Pada:", ["Volume Air (m³)", "Pendapatan (Rp)"])

# 3. Mode Peta
mode_peta = st.sidebar.radio("Mode Tampilan Peta:", ["Cluster Markers", "Heatmap (Kepadatan)"])

# --- PENGATURAN WARNA & SATUAN ---
if var_analisis == "Volume Air (m³)":
    kolom_target = 'TOTAL_PAKAI'
    satuan = 'm³'
    warna_utama = '#3498db'
else:
    kolom_target = 'TOTAL_RP'
    satuan = 'Rp'
    warna_utama = '#2ecc71'

warna_cluster = {0: '#3498db', 1: '#2ecc71', 2: '#f1c40f', 3: '#e74c3c'}
warna_cluster_plotly = {'0': '#3498db', '1': '#2ecc71', '2': '#f1c40f', '3': '#e74c3c'}
df_filtered['CLUSTER_STR'] = df_filtered['CLUSTER'].astype(str) # Untuk Plotly

# --- TOP METRICS (ANGKA KINERJA) ---
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("💧 Total Volume Air", f"{int(df_filtered['TOTAL_PAKAI'].sum()):,} m³")
col_m2.metric("💰 Total Pendapatan", f"Rp {int(df_filtered['TOTAL_RP'].sum()):,}".replace(',', '.'))
col_m3.metric("👥 Rata-rata Pelanggan Aktif", f"{int(df_filtered['JUMLAH_PELANGGAN'].sum()):,}")
col_m4.metric(f"📊 Rata-rata {var_analisis} per Jalan", f"{int(df_filtered[kolom_target].mean()):,}".replace(',', '.') + f" {satuan}")

# --- PETA & TABEL TOP 10 ---
st.divider()
st.subheader(f"🗺️ Peta Distribusi {var_analisis} - {label_waktu}")

m = folium.Map(location=[-7.285, 112.796], zoom_start=14, tiles="CartoDB dark_matter")

if mode_peta == "Cluster Markers":
    for _, row in df_filtered.iterrows():
        # Dinamis: Ukuran lingkaran
        if kolom_target == 'TOTAL_PAKAI':
            radius_size = min(max(row['TOTAL_PAKAI'] / (1000 if jenis_periode=="Rekap Tahunan" else 200), 4), 20)
        else:
            radius_size = min(max(row['TOTAL_RP'] / (5000000 if jenis_periode=="Rekap Tahunan" else 1000000), 4), 20)
            
        rp_format = f"Rp {int(row['TOTAL_RP']):,}".replace(',', '.')
        folium.CircleMarker(
            location=[row['Lat_Jitter'], row['Lon_Jitter']],
            radius=radius_size,
            color=warna_cluster.get(row['CLUSTER'], 'white'),
            fill=True, fill_opacity=0.7,
            popup=f"<b>{row['JALAN']}</b><br>Pakai: {row['TOTAL_PAKAI']} m³<br>Tagihan: {rp_format}<br>Cluster: {row['CLUSTER']}"
        ).add_to(m)
else:
    max_val = df_filtered[kolom_target].max()
    heat_data = [[row['Latitude'], row['Longitude'], row[kolom_target]/max_val] for _, row in df_filtered.iterrows()]
    HeatMap(heat_data, radius=20, blur=15).add_to(m)

c1, c2 = st.columns([2.5, 1.5])
with c1:
    st_folium(m, width="100%", height=450)
with c2:
    st.write(f"🏆 **Top 10 Jalan Tertinggi ({label_waktu})**")
    df_top = df_filtered[['JALAN', 'TOTAL_PAKAI', 'TOTAL_RP']].sort_values(by=kolom_target, ascending=False).head(10)
    st.dataframe(df_top, hide_index=True, height=400)

# --- VISUALISASI INSIGHT MENDALAM ---
st.divider()
st.subheader("💡 Eksplorasi Insight & Statistik Mendalam")

# Baris Grafik 1
tab1, tab2 = st.columns(2)

with tab1:
    st.markdown("**1. Korelasi Volume Air vs Tagihan Rupiah**")
    st.caption("Melihat apakah tarif progresif berjalan normal atau ada anomali pencatatan.")
    fig_scatter = px.scatter(df_filtered, x='TOTAL_PAKAI', y='TOTAL_RP', 
                             color='CLUSTER_STR', size='JUMLAH_PELANGGAN', 
                             hover_name='JALAN', color_discrete_map=warna_cluster_plotly)
    fig_scatter.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_scatter, use_container_width=True)

with tab2:
    st.markdown(f"**2. Komposisi {var_analisis} per Cluster**")
    st.caption("Mengetahui klaster mana penyumbang beban/pendapatan terbesar.")
    fig_pie = px.pie(df_filtered, names='CLUSTER_STR', values=kolom_target, hole=0.4,
                     color='CLUSTER_STR', color_discrete_map=warna_cluster_plotly)
    fig_pie.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_pie, use_container_width=True)

# Baris Grafik 2
tab3, tab4 = st.columns(2)

with tab3:
    st.markdown("**3. Tren Historis Keseluruhan Subzona 215**")
    st.caption("Pergerakan tren dari waktu ke waktu.")
    # Agregasi berdasar THBL asli untuk Line chart
    df_trend = df.groupby('THBL')[kolom_target].sum().reset_index()
    fig_trend = px.line(df_trend, x='THBL', y=kolom_target, markers=True, color_discrete_sequence=[warna_utama])
    fig_trend.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_trend, use_container_width=True)

with tab4:
    st.markdown(f"**4. Distribusi Anomali (Outlier) {var_analisis}**")
    st.caption("Mendeteksi jalan yang pemakaian/tagihannya tidak wajar dalam klasternya.")
    fig_box = px.box(df_filtered, x='CLUSTER_STR', y=kolom_target, color='CLUSTER_STR', 
                     color_discrete_map=warna_cluster_plotly)
    fig_box.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_box, use_container_width=True)
