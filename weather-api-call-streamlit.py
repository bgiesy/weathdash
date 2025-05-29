#!/usr/bin/env python3
import requests
from datetime import datetime, timezone
import pytz
import csv
import os
import pandas as pd
import streamlit as st

API_KEY = os.getenv("OPENWEATHER_API_KEY")
LAT = 38.9222   # Example location
LON = -77.1379
WEATHER_URL = 'https://api.openweathermap.org/data/2.5/weather'
UV_URL = 'http://api.openweathermap.org/data/2.5/uvi'
AQ_URL = 'http://api.openweathermap.org/data/2.5/air_pollution'
UNITS = 'imperial'  # Fahrenheit
LOG_FILE = 'weather_log.csv'
local_timezone_name = 'America/New_York'
def utc_to_local(utc_epoch, local_tz_name):
    local_tz = pytz.timezone(local_tz_name)
    # Convert epoch to timezone-aware UTC datetime
    utc_dt = datetime.fromtimestamp(utc_epoch, tz=timezone.utc)
    # Convert to local timezone
    return utc_dt.astimezone(local_tz).strftime('%I:%M %p')

def dt_to_local_time(dt, local_tz_name):
    local_tz = pytz.timezone(local_tz_name)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(local_tz).strftime('%Y-%m-%d %I:%M %p')


params = {
    'lat': LAT,
    'lon': LON,
    'appid': API_KEY,
    'units': UNITS
}

weather_response = requests.get(WEATHER_URL, params=params)
data = weather_response.json()

uv_params = {
    'lat': LAT,
    'lon': LON,
    'appid': API_KEY
}

uv_response = requests.get(UV_URL, params=uv_params)
uv_data = uv_response.json()
uv_index = uv_data.get('value', 'N/A')

aq_params = {
    'lat': LAT,
    'lon': LON,
    'appid': API_KEY
}


def calc_us_aqi(conc, breakpoints):
    for bp in breakpoints:
        if bp[0] <= conc <= bp[1]:
            Clow, Chigh = bp[0], bp[1]
            Ilow, Ihigh = bp[2], bp[3]
            return round(((Ihigh - Ilow) / (Chigh - Clow)) * (conc - Clow) + Ilow)
    return None

# Breakpoints for U.S. EPA AQI
pm25_breakpoints = [
    [0.0, 12.0, 0, 50],
    [12.1, 35.4, 51, 100],
    [35.5, 55.4, 101, 150],
    [55.5, 150.4, 151, 200],
    [150.5, 250.4, 201, 300],
    [250.5, 350.4, 301, 400],
    [350.5, 500.4, 401, 500]
]

pm10_breakpoints = [
    [0, 54, 0, 50],
    [55, 154, 51, 100],
    [155, 254, 101, 150],
    [255, 354, 151, 200],
    [355, 424, 201, 300],
    [425, 504, 301, 400],
    [505, 604, 401, 500]
]

def aqi_health_category(aqi):
    if aqi is None: return "N/A"
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Moderate"
    elif aqi <= 150: return "Unhealthy for Sensitive Groups"
    elif aqi <= 200: return "Unhealthy"
    elif aqi <= 300: return "Very Unhealthy"
    else: return "Hazardous"

#Fetch air quality data
aq_data = requests.get(AQ_URL, params={'lat': LAT, 'lon': LON, 'appid': API_KEY}).json()
aq_list = aq_data.get('list', [{}])
components = aq_list[0].get('components', {}) if aq_list else {}

pm25 = components.get('pm2_5', None)
pm10 = components.get('pm10', None)
pm25_aqi = calc_us_aqi(pm25, pm25_breakpoints) if pm25 is not None else None
pm10_aqi = calc_us_aqi(pm10, pm10_breakpoints) if pm10 is not None else None
us_aqi = max(filter(None, [pm25_aqi, pm10_aqi])) if any([pm25_aqi, pm10_aqi]) else 'N/A'
us_aqi_health = aqi_health_category(us_aqi)


main = data.get('main', {})
weather = data.get('weather', [{}])[0]
wind = data.get('wind', {})
clouds = data.get('clouds', {})
sys = data.get('sys', {})
rain = data.get('rain', {})

def deg_to_compass(deg):
    directions = [
        'N', 'NNE', 'NE', 'ENE',
        'E', 'ESE', 'SE', 'SSE',
        'S', 'SSW', 'SW', 'WSW',
        'W', 'WNW', 'NW', 'NNW'
    ]
    idx = int((deg % 360) / 22.5 + 0.5) % 16
    return directions[idx]

def beaufort_category(mph):
    if mph < 1:
        return "Calm"
    elif mph < 4:
        return "Light air"
    elif mph < 8:
        return "Light breeze"
    elif mph < 13:
        return "Gentle breeze"
    elif mph < 19:
        return "Moderate breeze"
    elif mph < 25:
        return "Fresh breeze"
    elif mph < 32:
        return "Strong breeze"
    elif mph < 39:
        return "Near gale"
    elif mph < 47:
        return "Gale"
    elif mph < 55:
        return "Strong gale"
    elif mph < 64:
        return "Storm"
    elif mph < 73:
        return "Violent storm"
    else:
        return "Hurricane force"



# Handle sunrise and sunset timestamps in UTC
sunrise_raw = utc_to_local(sys['sunrise'], local_timezone_name) if 'sunrise' in sys else 'N/A'
sunset_raw  = utc_to_local(sys['sunset'],  local_timezone_name) if 'sunset'  in sys else 'N/A'

sunrise = sunrise_raw.lstrip('0') if sunrise_raw != 'N/A' else 'N/A'
sunset  = sunset_raw.lstrip('0')  if sunset_raw  != 'N/A' else 'N/A'

wind_deg_raw = wind.get('deg', None)
wind_deg = wind_deg_raw if wind_deg_raw is not None else 'N/A'
wind_compass = deg_to_compass(wind_deg_raw) if wind_deg_raw is not None else 'N/A'

wind_speed_mps = wind.get('speed', None)
wind_speed_mph = round(wind_speed_mps * 2.23694, 2) if wind_speed_mps is not None else 'N/A'
wind_speed = wind_speed_mph if wind_speed_mph != 'N/A' else 'N/A'
wind_beaufort = beaufort_category(wind_speed_mph) if wind_speed_mph != 'N/A' else 'N/A'

rain_1h = rain.get('1h', 0.0)  # mm

description = weather.get('description', 'N/A').capitalize()

timestamp = datetime.now(timezone.utc)
timestamp_local = dt_to_local_time(timestamp, local_timezone_name)

headers = ['timestamp', 'description', 'temp', 'feels_like', 'humidity', 'temp_min', 'temp_max',
           'wind_speed_mph', 'wind_deg', 'wind_compass', 'wind_desc', 'cloud_cover',
           'sunrise', 'sunset', 'rain_1h', 'uv_index', 'us_aqi', 'us_aqi_desc']

row = [
    timestamp_local,
    description,
    main.get('temp', 'N/A'),
    main.get('feels_like', 'N/A'),
    main.get('humidity', 'N/A'),
    main.get('temp_min', 'N/A'),
    main.get('temp_max', 'N/A'),
    wind_speed,
    wind_deg,
    wind_compass,
    wind_beaufort,
    clouds.get('all', 'N/A'),
    sunrise,
    sunset,
    rain_1h,
    uv_index,
    us_aqi,
    us_aqi_health
]

# Write to CSV file (append mode)
file_exists = os.path.isfile(LOG_FILE)

with open(LOG_FILE, 'a', newline='') as csvfile:
    writer = csv.writer(csvfile)
    if not file_exists:
        writer.writerow(headers)
    writer.writerow(row)

