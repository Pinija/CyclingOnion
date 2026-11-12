"""Streamlit application for CyclingOnion."""

from html import escape
from pathlib import Path

import streamlit as st

from outfitter import OutfitError, get_optimized_outfit
from weather import WeatherError, get_weather_forecast

# Set page config with icon
st.set_page_config(page_title="CyclingOnion", page_icon="🚴‍♀️", layout="centered")

# ---- HEADER ----
col1, col2 = st.columns([1, 4])  # small left col for icon, big right col for title

with col1:
    st.image(str(Path(__file__).parent / "data" / "CyclingOnion_Icon_V2.png"), width=130)

with col2:
    st.markdown(
        """
        <h1 style='margin-bottom:0; color:#333;'>CyclingOnion</h1>
        <h4 style='margin-top:0; color:#777;'>Be perfectly dressed for your ride!</h4>
    """,
        unsafe_allow_html=True,
    )

st.write("---")

# ---- USER INPUTS ----
col1, col2 = st.columns(2)

with col1:
    st.subheader("Terrain")
    terrain = st.segmented_control(
        "Select Terrain",
        options=["Flat", "Hilly", "Mountain", "Alpine"],
        selection_mode="single",
        default="Flat",
        key="terrain",
    )

with col2:
    st.subheader("Intensity")
    intensity = st.segmented_control(
        "Select Intensity",
        options=["Easy", "Medium", "Tempo", "Extreme"],
        selection_mode="single",
        default="Medium",
        key="intensity",
    )

st.write("---")

# ---- LOCATION & DURATION ----
st.subheader("Ride Details")
location = st.text_input("Location (City or Place)", placeholder="e.g. Freiburg, Innsbruck..")
duration = st.slider("Ride Duration (hours)", 1, 6, 2)

# ---- ACTION BUTTON ----
if st.button("Find a Matching Outfit for the Weather 🚴"):
    if not location.strip():
        st.warning("Please enter a location before continuing.")
    elif not terrain:
        st.warning("Please choose a terrain before continuing.")
    elif not intensity:
        st.warning("Please choose an intensity before continuing.")
    else:
        try:
            with st.spinner("Checking the weather and finding your outfit..."):
                weather = get_weather_forecast(
                    location, duration, terrain.lower(), intensity.lower()
                )
                outfit = get_optimized_outfit(duration, weather)
        except (WeatherError, OutfitError) as error:
            st.error(str(error))
            st.stop()
        effective_temp = weather.get_effective_temp_range()
        pro_tip = weather.get_pro_tip()

        # 🧅 RESULTS SECTION

        st.markdown(
            f"""
            <h2 style='margin-bottom:5px;'>Recommended outfit for the ride in <b>{escape(location.strip())}</b></h2>
            <p style='color:#555;'>Intensity: <b>{intensity}</b> | Duration: <b>{duration} h</b></p>
            """,
            unsafe_allow_html=True,
        )

        # --- Weather summary card ---
        with st.container():
            # Create two small columns for icon and condition
            icon_col, text_col = st.columns([1, 8])

            with icon_col:
                icon_url = weather.get_icon()
                if icon_url:
                    st.image(icon_url, width=60)
                else:
                    st.write("🌤️")

            with text_col:
                st.markdown(f"### {weather.condition}")

            # Weather details below
            st.markdown(
                f"""
                <p style='margin:0;'>🌡️ Temperature: <b>{weather.temp_min:.1f} – {weather.temp_max:.1f} °C</b></p>
                <p style='margin:0;'>🥶 Felt temperature: <b>{effective_temp[0]:.1f} – {effective_temp[1]:.1f} °C</b></p>
                <p style='margin:0;'>💨 Wind: <b>{weather.wind_max:.0f} km/h</b></p>
                <p style='margin:0;'>🌧️ Maximum hourly rain chance: <b>{weather.precipitation_prob:g}%</b></p>
                """,
                unsafe_allow_html=True,
            )

            st.write("---")

        icons = {"Head": "🧢", "Upper Body": "👕", "Lower Body": "👖", "Hands": "🧤", "Feet": "👟"}

        for part, item in outfit.items():
            st.markdown(
                f"""
                <div style='margin-bottom:10px;'>
                    <h4>{icons.get(part, "🧩")} {part.capitalize()}</h4>
                    <p style='margin-left:25px;color:#BBB;font-size:1.1em;font-weight:bold;'>
                        {escape(item.name)}
                    </p>
                    <p style='margin-left:25px;color:#555;font-size:0.95em;'>
                        Comfort range: {item.main_comfort_min}–{item.main_comfort_max}°C<br>
                        Windproof: {"✅" if item.windproof else "❌"} |
                        Waterproof: {"✅" if item.waterproof else "❌"} |
                        Removable: {"✅" if item.removable else "❌"}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.write("")
        st.caption(f"Bonus tip: {pro_tip} 🏔️")

st.write("---")
st.caption("Built with ❤️ for Helen.")
