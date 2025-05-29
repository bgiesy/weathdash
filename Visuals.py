import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# Load data
df = pd.read_csv("weather_log.csv", parse_dates=['timestamp'])
df.sort_values("timestamp", inplace=True)

# Calculate rolling 7-day rainfall average
df['rain_7d_avg'] = df.set_index('timestamp')['rain_1h'].rolling('7D').mean().reset_index(drop=True)

# Combines date from timestamp field with sunset and sunrise dates
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Function to combine date and time strings into datetime objects
def combine_date_time(row):
    # Handle both string or Timestamp safely
    if isinstance(row["timestamp"], pd.Timestamp):
        date_only = row["timestamp"].date()
    else:
        date_only = datetime.strptime(row["timestamp"], "%Y-%m-%d %I:%M %p").date()

    sunrise_time = datetime.strptime(row["sunrise"], "%I:%M %p").time()
    sunset_time = datetime.strptime(row["sunset"], "%I:%M %p").time()
    sunrise_dt = datetime.combine(date_only, sunrise_time)
    sunset_dt = datetime.combine(date_only, sunset_time)
    return pd.Series([sunrise_dt, sunset_dt])

# Create new datetime columns
df[["sunrise_dt", "sunset_dt"]] = df.apply(combine_date_time, axis=1)


# Layout
st.title("Weather Dashboard")

# Summary stats
latest = df.iloc[-1]
weather_keywords = ["storm", "thunderstorm", "rain"]
description_text = str(latest["description"]).lower()

if any(keyword in description_text for keyword in weather_keywords):
    st.markdown(
        "<h1 style='color: red; text-align: center;'>⚠️ It is raining ⚠️</h1>",
        unsafe_allow_html=True
    )

st.subheader("At a Glance")
col1, col2, col3 = st.columns([1,1,2])
col1.metric("Temp", f"{int(latest['temp'])} °F")
col2.metric("Feels Like", f"{int(latest['temp'])} °F")
col3.metric("Weather", f"{latest['description']}")

st.subheader("Current Conditions")
col1, col2, col3, col4 = st.columns([1,1,1,2])
col1.metric("High", f"{int(latest['temp_max'])} °F")
col2.metric("Low", f"{int(latest['temp_min'])} °F")
col3.metric("Cloud Cover", f"{latest['cloud_cover']}%")
col4.metric("Wind Speed", f"{latest['wind_desc']}")

# Shading on Time

def add_night_shading(fig, df):
    # First, group by date and get one sunrise/sunset per day
    df['date'] = df['timestamp'].dt.date
    daily_sun = df.groupby('date').agg({
        'sunrise_dt': 'first',
        'sunset_dt': 'first'
    }).reset_index()

    for i in range(len(daily_sun)):
        sunset = daily_sun.loc[i, 'sunset_dt']

        if i + 1 < len(daily_sun):
            next_sunrise = daily_sun.loc[i + 1, 'sunrise_dt']
        else:
            # fallback: assume next sunrise is 12 hours later
            next_sunrise = sunset + timedelta(hours=12)

        # Now add shaded rectangle from sunset to next sunrise
        fig.add_shape(
            type="rect",
            xref="x",
            yref="paper",
            x0=sunset,
            x1=next_sunrise,
            y0=0,
            y1=1,
            fillcolor="LightBlue",
            opacity=0.25,
            layer="below",
            line_width=0,
        )

    return fig


# Time series plots
st.subheader("Weather Trends")
col1, col2 = st.columns(2)

with col1:
    fig_temp = px.line(df, x="timestamp", y=["temp", "feels_like"],
                       labels={"value": "Temperature (°F)", "timestamp": "DateTime"},
                       title="Temperature Over Time")
    fig_temp = add_night_shading(fig_temp, df)
    st.plotly_chart(fig_temp, use_container_width=True)

    fig_humidity = px.line(df, x="timestamp", y="uv_index",
                           labels={"uv_index": "UV Index", "timestamp": "DateTime"},
                          title="UV Index Over Time")
    st.plotly_chart(fig_humidity, use_container_width=True)

with col2:
    fig_wind = px.line(df,x="timestamp", y="wind_speed_mph", 
                       labels={"wind_speed_mph": "Wind Speed (mph)", "timestamp": "DateTime"},
                       title="Wind Speed")
    fig_wind = add_night_shading(fig_wind, df)
    st.plotly_chart(fig_wind, use_container_width=True)
   
    fig_rain = go.Figure()
    fig_rain.add_trace(go.Scatter(x=df['timestamp'], y=df['rain_1h'],
                                  mode='lines',
                                  name='Hourly Rainfall',
                                  line=dict(color='blue', width=2),
                                  opacity=0.4))
    fig_rain.add_trace(go.Scatter(x=df['timestamp'], y=df['rain_7d_avg'],
                                  mode='lines',
                                  name='7-Day Avg Rainfall',
                                  line=dict(color='darkblue', width=3)))
    fig_rain.update_layout(title="Rainfall Trends",
                           xaxis_title="DateTime",
                           yaxis_title="Rainfall (mm)")
    fig_rain = add_night_shading(fig_rain, df)
    st.plotly_chart(fig_rain, use_container_width=True)