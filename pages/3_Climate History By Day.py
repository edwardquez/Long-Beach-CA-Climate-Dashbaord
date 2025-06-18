import streamlit as st
import pandas as pd
import duckdb 
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import calendar


# Page config
st.set_page_config(
    page_title="Select a Date",
    layout="wide"
)

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv("updated_data.csv", skiprows=1, parse_dates=["Date"])
    df.columns = df.columns.str.strip() # Normalize column names
    df = df[df["Date"] >= "1949-01-01"]
    return df
df = load_data()


# Helper function for custom date formatting like "January 25th 2002"
def format_date_readable(date_obj):
    day = date_obj.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return date_obj.strftime(f"%B {day}{suffix} %Y")

# Helper function for highest monthly precipitation recorded fact.
def format_precip_fact(row):
    date = pd.to_datetime(row["Date"])
    month_name = calendar.month_name[date.month]
    suffix = 'th' if 11 <= date.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(date.day % 10, 'th')
    rain = round(row["Rain"], 2)
    return f"**Did you know?** On {month_name} {date.day}{suffix}, {date.year}, Long Beach recorded {rain} inches of rain — the wettest {month_name} day on record!"

# Helper function for drought ending days fact.
def format_dry_streak_fact(row):
    end_date = pd.to_datetime(row["EndDate"])
    month = calendar.month_name[end_date.month]
    day = end_date.day
    year = end_date.year
    rain_amt = round(row["Rain"], 2)
    return f"**Did you know?** After {row['streak_length']} consecutive dry days, it finally rained on {month} {day}, {year} — {rain_amt} inches fell."


df["Year"] = df["Date"].dt.year
df["Decade"] = (df["Year"] // 10) * 10
duckdb.register("weather", df) 

# Add month/day columns
df["Month"] = df["Date"].dt.month
df["Day"] = df["Date"].dt.day
duckdb.register("weather", df)


# Selects month and day
selected_month = st.selectbox("Select Month", list(calendar.month_name)[1:], index=6)
selected_day = st.number_input("Select Day", min_value=1, max_value=31, value=15)

# Convert month name to number
month_num = list(calendar.month_name).index(selected_month)

# Query
day_summary = duckdb.query(f"""
    WITH filtered_data AS (
        SELECT 
            Date,
            EXTRACT(MONTH FROM Date) AS Month,
            EXTRACT(DAY FROM Date) AS Day,
            "TAVG (Degrees Fahrenheit)" AS TAVG,
            "TMAX (Degrees Fahrenheit)" AS TMAX,
            "TMIN (Degrees Fahrenheit)" AS TMIN,
            "PRCP (Inches)" AS PRCP
        FROM weather
        WHERE EXTRACT(MONTH FROM Date) = {month_num} AND EXTRACT(DAY FROM Date) = {selected_day}
    ),
    summary AS (
        SELECT
            ROUND(AVG(TAVG), 1) AS "Avg Temp",
            ROUND(AVG(TMAX), 1) AS "Avg High Temp",
            ROUND(AVG(TMIN), 1) AS "Avg Low Temp",
            ROUND(SUM(CASE WHEN PRCP > 0.01 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS "Chance of Rain (%)",
            MAX(TMAX) AS "Record High",
            MIN(TMIN) AS "Record Low"
        FROM filtered_data
    ),
    high_date AS (
        SELECT Date AS "Record High Date"
        FROM filtered_data
        WHERE TMAX = (SELECT MAX(TMAX) FROM filtered_data)
        LIMIT 1
    ),
    low_date AS (
        SELECT Date AS "Record Low Date"
        FROM filtered_data
        WHERE TMIN = (SELECT MIN(TMIN) FROM filtered_data)
        LIMIT 1
    ),
    biggest_swing AS (
        SELECT 
            Date,
            TMAX,
            TMIN,
            (TMAX - TMIN) AS swing
        FROM filtered_data
        ORDER BY swing DESC
        LIMIT 1
    )
    SELECT * FROM summary
    CROSS JOIN high_date
    CROSS JOIN low_date
    CROSS JOIN biggest_swing
""").to_df()


# Query for the highest precipitation day per month
wettest_days = duckdb.query("""
    SELECT DISTINCT ON (EXTRACT(MONTH FROM Date)) 
        EXTRACT(MONTH FROM Date) AS Month,
        Date,
        "PRCP (Inches)" AS Rain
    FROM weather
    WHERE "PRCP (Inches)" IS NOT NULL
    ORDER BY Month, "PRCP (Inches)" DESC
""").to_df()

dry_streaks = duckdb.query("""
    WITH weather_clean AS (
        SELECT 
            Date,
            "PRCP (Inches)" AS PRCP,
            CASE 
                WHEN "PRCP (Inches)" IS NULL OR "PRCP (Inches)" = 0 THEN 1
                ELSE 0
            END AS is_dry
        FROM weather
        WHERE Date IS NOT NULL
        ORDER BY Date
    ),
    runs AS (
        SELECT *,
            SUM(CASE WHEN is_dry = 0 THEN 1 ELSE 0 END) OVER (ORDER BY Date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS wet_group
        FROM weather_clean
    ),
    streaks AS (
        SELECT 
            wet_group,
            MIN(Date) AS StartDate,
            MAX(Date) AS EndDate,
            COUNT(*) AS StreakDays
        FROM runs
        WHERE is_dry = 1
        GROUP BY wet_group
        HAVING COUNT(*) >= 150
    ),
    rain_on_next_day AS (
        SELECT 
            s.*,
            w.Date AS RainDate,
            w."PRCP (Inches)" AS Rain
        FROM streaks s
        JOIN weather w ON w.Date = s.EndDate + INTERVAL 1 DAY
        WHERE w."PRCP (Inches)" > 0.01
    )
    SELECT 
        RainDate AS EndDate,
        StartDate,
        StreakDays AS streak_length,
        Rain
    FROM rain_on_next_day
""").to_df()


st.subheader(f"Weather on {selected_month} {selected_day}")

if not day_summary.empty:
    row = day_summary.iloc[0]

    # Format dates nicely
    record_high_date = format_date_readable(row['Record High Date'])
    record_low_date = format_date_readable(row['Record Low Date'])

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Temp", f"{row['Avg Temp']} °F")
    col2.metric("Avg High", f"{row['Avg High Temp']} °F")
    col3.metric("Avg Low", f"{row['Avg Low Temp']} °F")
    st.metric("Chance of Rain", f"{row['Chance of Rain (%)']} %")
    st.metric("Record High", f"{row['Record High']} °F on {record_high_date}")
    st.metric("Record Low", f"{row['Record Low']} °F on {record_low_date}")
    
 # ---------- SPECIAL FACT: Dry Streak > Rainiest > Temp Swing ----------

# Match dry streak ending
    dry_row = dry_streaks[pd.to_datetime(dry_streaks["EndDate"]).dt.month == month_num]
    dry_row = dry_row[pd.to_datetime(dry_row["EndDate"]).dt.day == selected_day]

    # Match wettest day
    wettest_row = wettest_days[wettest_days["Month"] == month_num]
    wettest_date = None
    if not wettest_row.empty:
        wettest_date = pd.to_datetime(wettest_row.iloc[0]["Date"])

    # Priority 1: Dry Streak
    if not dry_row.empty:
        st.markdown(format_dry_streak_fact(dry_row.iloc[0]))

    # Priority 2: Wettest Day
    elif wettest_date is not None and wettest_date.day == selected_day:
        st.markdown(format_precip_fact(wettest_row.iloc[0]))

    # Priority 3: Temperature Swing
    elif row['swing'] > 25:
        swing_date = format_date_readable(row['Date'])
        st.markdown(
            f"**Did you know?** On {swing_date}, Long Beach experienced a massive temperature swing of "
            f"{row['swing']}°F — going from {row['TMIN']}°F to {row['TMAX']}°F!"
        )
else: 
    st.warning(" No historical data available for this date. Does this date exist?")




