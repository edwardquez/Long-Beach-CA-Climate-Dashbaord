import streamlit as st
import pandas as pd
import duckdb 
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import calendar
import holidays as pyholidays
from datetime import datetime
import platform

# Page configuration
st.set_page_config(
    page_title="Holiday Weather",
    layout="wide"
)

# Title and header
st.title("Temperature Trends on Major U.S. Holidays")
'---'

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv("updated_data.csv", skiprows=1, parse_dates=["Date"])
    df.columns = df.columns.str.strip()
    df = df[df["Date"] >= "1949-01-01"]
    return df

weather_df = load_data()
weather_df["Year"] = weather_df["Date"].dt.year
weather_df["Decade"] = (weather_df["Year"] // 10) * 10

# Fill null TMAX with TAVG and PRCP with 0
weather_df["TMAX (Degrees Fahrenheit)"] = weather_df["TMAX (Degrees Fahrenheit)"].fillna(weather_df["TAVG (Degrees Fahrenheit)"])
weather_df["PRCP (Inches)"] = weather_df["PRCP (Inches)"].fillna(0)

# Register dataframe in DuckDB
duckdb.sql("DROP VIEW IF EXISTS weather")
duckdb.register("weather", weather_df)

# Define fixed holidays
holiday_names = {
    "New Year's Day": (1, 1),
    "Independence Day": (7, 4),
    "Christmas": (12, 25)
}

# Define variable holidays
def get_variable_holiday_dates():
    years = range(1949, datetime.now().year + 1)
    holiday_dates = {
        "Memorial Day": [],
        "Labor Day": [],
        "Thanksgiving": []
    }
    for year in years:
        memorial = max(pd.date_range(start=f"{year}-05-01", end=f"{year}-05-31").to_series()[lambda x: x.dt.dayofweek == 0])
        labor = min(pd.date_range(start=f"{year}-09-01", end=f"{year}-09-07").to_series()[lambda x: x.dt.dayofweek == 0])
        thursdays = pd.date_range(start=f"{year}-11-01", end=f"{year}-11-30").to_series()[lambda x: x.dt.dayofweek == 3]
        thanksgiving = thursdays.iloc[3]

        holiday_dates["Memorial Day"].append(memorial.strftime("%Y-%m-%d"))
        holiday_dates["Labor Day"].append(labor.strftime("%Y-%m-%d"))
        holiday_dates["Thanksgiving"].append(thanksgiving.strftime("%Y-%m-%d"))

    return holiday_dates

variable_holidays = get_variable_holiday_dates()

# Collect holiday stats using SQL queries
summary_rows = []

for name, (month, day) in holiday_names.items():
    query = f"""
        SELECT 
            Date,
            "TMAX (Degrees Fahrenheit)" AS TMAX,
            "TMIN (Degrees Fahrenheit)" AS TMIN,
            "TAVG (Degrees Fahrenheit)" AS TAVG,
            "PRCP (Inches)" AS PRCP
        FROM weather
        WHERE EXTRACT(month FROM Date) = {month} AND EXTRACT(day FROM Date) = {day}
    """
    df = duckdb.query(query).to_df()
    df['Holiday'] = name
    summary_rows.append(df)

for name, dates in variable_holidays.items():
    date_list = "', '".join(dates)
    query = f"""
        SELECT 
            Date,
            "TMAX (Degrees Fahrenheit)" AS TMAX,
            "TMIN (Degrees Fahrenheit)" AS TMIN,
            "TAVG (Degrees Fahrenheit)" AS TAVG,
            "PRCP (Inches)" AS PRCP
        FROM weather
        WHERE Date IN ('{date_list}')
    """
    df = duckdb.query(query).to_df()
    df['Holiday'] = name
    summary_rows.append(df)

all_holidays_df = pd.concat(summary_rows)
all_holidays_df["Date"] = pd.to_datetime(all_holidays_df["Date"])
all_holidays_df["Year"] = all_holidays_df["Date"].dt.year

# Custom order for displaying holidays
holiday_order = [
    "New Year's Day", "Memorial Day", "Independence Day",
    "Labor Day", "Thanksgiving", "Christmas"
]

entry_style = "display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #ddd;"
last_entry_style = "display: flex; justify-content: space-between; padding: 5px 0;"

# Determine correct date format string based on platform
if platform.system() == "Windows":
    date_format_str = "%B %#d, %Y"
else:
    date_format_str = "%B %-d, %Y"

# Display each holiday summary in a dashboard style
for holiday in holiday_order:
    holiday_df = all_holidays_df[all_holidays_df['Holiday'] == holiday].copy()
    holiday_df.sort_values("Year", inplace=True)

    avg_temp = holiday_df["TAVG"].mean()
    avg_high = holiday_df["TMAX"].mean()
    avg_low = holiday_df["TMIN"].mean()
    max_temp = holiday_df["TMAX"].max()
    max_temp_year = holiday_df.loc[holiday_df["TMAX"].idxmax(), "Year"]
    min_temp = holiday_df["TMIN"].min()
    min_temp_year = holiday_df.loc[holiday_df["TMIN"].idxmin(), "Year"]
    precip_chance = (holiday_df["PRCP"] > 0).mean() * 100

    st.markdown(f"## {holiday}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Temp", f"{avg_temp:.1f} °F")
    col2.metric("Avg High", f"{avg_high:.1f} °F")
    col3.metric("Avg Low", f"{avg_low:.1f} °F")

    col4, col5, col6 = st.columns(3)
    col4.metric("Chance of Rain", f"{precip_chance:.1f} %")
    col5.metric("Record High", f"{max_temp:.1f} °F ({int(max_temp_year)})")
    col6.metric("Record Low", f"{min_temp:.1f} °F ({int(min_temp_year)})")

    graph_col1, graph_col2 = st.columns(2)

    with graph_col1:
        temp_fig = px.line(
            holiday_df,
            x="Year",
            y="TMAX",
            title=f"Annual High Temperature on {holiday}",
            markers=True,
            labels={"TMAX": "High Temperature"}
        )
        st.plotly_chart(temp_fig, use_container_width=True)

    with graph_col2:
        precip_fig = px.line(
            holiday_df,
            x="Year",
            y="PRCP",
            title=f"Annual Precipitation on {holiday}",
            markers=True,
            labels={"PRCP": "Precipitation"}
        )
        st.plotly_chart(precip_fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.expander("Warmest Days", expanded=False):
            warmest_days = holiday_df.sort_values("TMAX", ascending=False).head(5)
            for i, row in warmest_days.iterrows():
                style = last_entry_style if i == len(warmest_days) - 1 else entry_style
                formatted_date = row['Date'].strftime(date_format_str)
                st.markdown(f"<div style='{style}'><span>{formatted_date}</span><span>{row['TMAX']:.1f} °F</span></div>", unsafe_allow_html=True)

    with col2:
        with st.expander("Coldest Days", expanded=False):
            coldest_days = holiday_df.sort_values("TMIN").head(5)
            for i, row in coldest_days.iterrows():
                style = last_entry_style if i == len(coldest_days) - 1 else entry_style
                formatted_date = row['Date'].strftime(date_format_str)
                st.markdown(f"<div style='{style}'><span>{formatted_date}</span><span>{row['TMIN']:.1f} °F</span></div>", unsafe_allow_html=True)

    with col3:
        with st.expander("Wettest Days", expanded=False):
            wettest_days = holiday_df.sort_values("PRCP", ascending=False).head(5)
            for i, row in wettest_days.iterrows():
                style = last_entry_style if i == len(wettest_days) - 1 else entry_style
                formatted_date = row['Date'].strftime(date_format_str)
                st.markdown(f"<div style='{style}'><span>{formatted_date}</span><span>{row['PRCP']:.2f} in</span></div>", unsafe_allow_html=True)

    st.markdown("---")
