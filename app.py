import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
from itertools import combinations

st.set_page_config(page_title="Land Run Auswertung", layout="centered")
st.title("🏁 Land Run Auswertung")
st.markdown("Berechne die optimale Höhenstrategie zur Maximierung der Dreiecksfläche.")

uploaded_file = st.file_uploader("📤 Winddaten hochladen (.csv)", type=["csv"])
col1, col2 = st.columns(2)
with col1:
    flight_time_min = st.number_input("Flugdauer [min]", min_value=5, max_value=90, value=45, step=5)
with col2:
    climb_rate = st.number_input("Steig-/Sinkrate [m/s]", min_value=0.1, max_value=10.0, value=1.0, step=0.1)

def wind_vector(direction_deg, speed_kmh):
    direction_rad = math.radians(direction_deg)
    speed_ms = speed_kmh / 3.6
    dx = speed_ms * math.sin(direction_rad)
    dy = speed_ms * math.cos(direction_rad)
    return np.array([dx, dy])

def interpolate_wind_profile(df, alt_ft):
    df = df.sort_values('Altitude_ft')
    return np.interp(alt_ft, df['Altitude_ft'], df['Direction_deg']), \
           np.interp(alt_ft, df['Altitude_ft'], df['Speed_kmh'])

def simulate_landrun(df, duration_sec, climb_rate):
    altitudes = df['Altitude_ft'].unique()
    altitudes.sort()
    results = []
    for h1, h2 in combinations(altitudes, 2):
        climb_time = abs(h2 - h1) * 0.3048 / climb_rate
        cruise_time = duration_sec - climb_time
        if cruise_time <= 0:
            continue
        for frac in np.linspace(0.1, 0.9, 9):
            t1 = cruise_time * frac
            t2 = cruise_time * (1 - frac)
            def integrate_motion(alt, time_sec):
                direction, speed = interpolate_wind_profile(df, alt)
                return wind_vector(direction, speed) * time_sec
            p0 = np.array([0, 0])
            p1 = p0 + integrate_motion(h1, t1)
            p2 = p1 + integrate_motion(h2, t2)
            area = 0.5 * abs((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])) / 1e6
            results.append({
                'h1': h1, 'h2': h2,
                'Speed_h1': round(interpolate_wind_profile(df, h1)[1], 1),
                'Speed_h2': round(interpolate_wind_profile(df, h2)[1], 1),
                'T1': f"{int(t1//60)}:{int(t1%60):02d}",
                'T2': f"{int(t2//60)}:{int(t2%60):02d}",
                'Climb': f"{int(climb_time//60)}:{int(climb_time%60):02d}",
                'Area_km2': round(area, 2),
                'p0': p0, 'p1': p1, 'p2': p2
            })
    return sorted(results, key=lambda x: -x['Area_km2'])[:10]

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("✅ Winddaten erfolgreich geladen.")
    results = simulate_landrun(df, flight_time_min * 60, climb_rate)
    if results:
        st.subheader("🏆 Top 10 Höhenkombinationen")
        table = pd.DataFrame([{
            'h1': r['h1'],
            'Speed_h1': r['Speed_h1'],
            'h2': r['h2'],
            'Speed_h2': r['Speed_h2'],
            'T1': r['T1'],
            'T2': r['T2'],
            'Climb': r['Climb'],
            'Fläche [km²]': r['Area_km2']
        } for r in results])
        st.dataframe(table, use_container_width=True)

        st.subheader("📍 Flugbahn der besten Variante")
        best = results[0]
        x, y = zip(best['p0'], best['p1'], best['p2'])
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.plot(x, y, marker='o', linestyle='-', color='blue')
        ax.set_title("Flugbahn")
        ax.set_xlabel("Ostverschiebung [m]")
        ax.set_ylabel("Nordverschiebung [m]")
        ax.grid(True)
        st.pyplot(fig)
