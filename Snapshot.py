import streamlit as st
import pandas as pd
import duckdb 
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import calendar

# Page configuration
st.set_page_config(
    page_title="Long Beach Weather Dashboard",
    layout = "wide"
)

# Title and intro
st.title("A Snapshot of Long Beach, California's Climate")
st.subheader(
    """
    Exploring 75 years of historical weather data (1949-2024)
    ---
    """
)

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv("updated_data.csv", skiprows=1, parse_dates=["Date"])
    df.columns = df.columns.str.strip() # Normalize column names
    df = df[df["Date"] >= "1949-01-01"]
    return df
df = load_data()


df["Year"] = df["Date"].dt.year
df["Decade"] = (df["Year"] // 10) * 10
duckdb.register("weather", df) 

# Query stays the same
monthly_temp_combined = duckdb.query("""
    SELECT 
        EXTRACT(MONTH FROM Date) AS Month,
        AVG("TMIN (Degrees Fahrenheit)") AS AvgLow,
        AVG("TMAX (Degrees Fahrenheit)") AS AvgHigh,
        MIN("TMIN (Degrees Fahrenheit)") AS MinLow,
        MAX("TMAX (Degrees Fahrenheit)") AS MaxHigh
    FROM weather
    WHERE "TMIN (Degrees Fahrenheit)" IS NOT NULL 
      AND "TMAX (Degrees Fahrenheit)" IS NOT NULL
    GROUP BY Month
    ORDER BY Month
""").to_df()

# Labels for temps 
monthly_temp_combined["MonthName"] = monthly_temp_combined["Month"].apply(lambda x: calendar.month_abbr[int(x)])
monthly_temp_combined["BelowTop"] = monthly_temp_combined["AvgLow"]
monthly_temp_combined["AvgTop"] = monthly_temp_combined["AvgHigh"]
monthly_temp_combined["AboveTop"] = monthly_temp_combined["MaxHigh"]

# Displaying monthly temp ranges and monthly avg precipitation side by side
col1, col2 = st.columns(2)
with col1: 
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly_temp_combined["MonthName"],
        y=monthly_temp_combined["MaxHigh"] - monthly_temp_combined["MinLow"],
        base=monthly_temp_combined["MinLow"],
        marker_color='lightgray',
        name='Extreme Range',
        hoverinfo='skip',
        opacity=0.3,
        showlegend=False
    ))

    # Below Avg Low (light blue)
    fig.add_trace(go.Bar(
        x=monthly_temp_combined["MonthName"],
        y=monthly_temp_combined["AvgLow"] - monthly_temp_combined["MinLow"],
        base=monthly_temp_combined["MinLow"],
        marker_color='lightblue',
        name='Below Avg Low',
        hovertemplate=(
            'Below Avg Low: %{base:.1f} to %{customdata:.1f}°F<extra></extra>'
        ),
        customdata=monthly_temp_combined["BelowTop"]
    ))

    # Average Range (whiteish)
    fig.add_trace(go.Bar(
        x=monthly_temp_combined["MonthName"],
        y=monthly_temp_combined["AvgHigh"] - monthly_temp_combined["AvgLow"],
        base=monthly_temp_combined["AvgLow"],
        marker_color='#E5ECF8',
        name='Average Range',
        hovertemplate=(
            'Avg Range: %{base:.1f} to %{customdata:.1f}°F<extra></extra>'
        ),
        customdata=monthly_temp_combined["AvgTop"]
    ))

    # Above Avg High (light red)
    fig.add_trace(go.Bar(
        x=monthly_temp_combined["MonthName"],
        y=monthly_temp_combined["MaxHigh"] - monthly_temp_combined["AvgHigh"],
        base=monthly_temp_combined["AvgHigh"],
        marker_color='#FF9999',
        name='Above Avg High',
        hovertemplate=(
            'Above Avg High: %{base:.1f} to %{customdata:.1f}°F<extra></extra>'
        ),
        customdata=monthly_temp_combined["AboveTop"]
    ))

    fig.update_layout(
        title="Monthly Temperature Ranges in Long Beach, CA (1949–2024)",
        xaxis_title="Month",
        yaxis_title="Temperature (°F)",
        barmode='overlay',
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)


# ---- Query for monthly average precipitation ---- 
monthly_avg_precip = duckdb.query("""
    SELECT
        EXTRACT(MONTH FROM Date) AS Month,
        SUM("PRCP (Inches)") / COUNT(DISTINCT EXTRACT(YEAR FROM Date)) AS "Average Precipitation"
    FROM weather
    WHERE "PRCP (Inches)" IS NOT NULL
    GROUP BY Month
    ORDER BY Month                                                                                                                                   
    """).to_df()

# Convert numeric month to full month name
monthly_avg_precip["Month"] = monthly_avg_precip["Month"].apply(lambda x: calendar.month_name[int(x)])

# Assign custom colors based on precipitation thresholds
def get_precip_color(value):
    if value >= 1.74:
        return 'lightblue'
    elif value >= 0.65:
        return '#E5ECF8'
    else:
        return '#FF9999'

monthly_avg_precip["Color"] = monthly_avg_precip["Average Precipitation"].apply(get_precip_color)

with col2:
    fig = go.Figure(data=[
        go.Bar(
            x=monthly_avg_precip["Month"],
            y=monthly_avg_precip["Average Precipitation"],
            marker_color=monthly_avg_precip["Color"],
            hovertemplate='%{x}<br>Avg Precipitation: %{y:.2f} inches',
            name='',
            showlegend= False
        )
    ])

    # Update layout
    fig.update_layout(
        title="Average Monthly Precipitation in Long Beach, CA (1949–2024)",
        xaxis_title="Month",
        yaxis_title="Avg Precip (inches)",
        height=600
    )

    # Show chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)


with col1: 

    # ---- Query for yearly annual average temp. ----
    annual_avg_sql = duckdb.query("""
        SELECT Year, AVG("TAVG (Degrees Fahrenheit)") AS avg_temp
        FROM weather
        WHERE YEAR < 2025
        GROUP BY Year
        ORDER BY Year
    """).to_df()

    # Figure for yearly annual average temp.
    fig = px.line(
        annual_avg_sql,
        x= "Year",
        y= "avg_temp",
        title= "Average Annual Temperature (1949–Present)",
        labels= {"avg_temp": "Avg Temp (°F)"},
        height = 600
    )
    fig.update_traces(
    hovertemplate='Year: %{x}<br>Avg Temp: %{y:.1f}°F<extra></extra>'
    )
    st.plotly_chart(fig, use_container_width=True)



with col2: 
    # ---- Query for Total Annual Precipitation ---- 
    annual_total_prcp = duckdb.query("""
        SELECT Year, SUM("PRCP (Inches)") AS "Total Precipitation (Inches)"
        FROM weather
        WHERE Year < 2025
        GROUP BY YEAR
        ORDER BY YEAR                                                     
    """).to_df()


    # Thresholds for rainiest/driest years in terms of precipitation
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=annual_total_prcp["Year"],
        y=annual_total_prcp["Total Precipitation (Inches)"],
        mode="lines",          # same stock blue
        name="Total Precipitation"
    ))

    fig.update_layout(
        title="Total Annual Precipitation in Long Beach, CA (1949–2024)",
        xaxis_title="Year",
        yaxis_title="Total Precipitation (Inches)",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)


# ---- Query for Monthly Average Temperature ---- 
monthly_avg_temp = duckdb.query("""
     SELECT 
        EXTRACT(MONTH FROM Date) AS Month,
        AVG("TAVG (Degrees Fahrenheit)") AS "Average Temperature"
     FROM weather
     WHERE "TAVG (Degrees Fahrenheit)" IS NOT NULL
     GROUP BY Month
     ORDER BY Month                                                                        
""").to_df()

# Replaces month numbers with month names
monthly_avg_temp["Month"] = monthly_avg_temp["Month"].apply(lambda x: calendar.month_name[int(x)])



# Historical Metric Queries

st.header("Historical Records:")

# ---- Top 10 Warmest Days ----
warmest_days = duckdb.query("""
    SELECT Date, "TMAX (Degrees Fahrenheit)" AS TMAX
    FROM weather
    WHERE "TMAX (Degrees Fahrenheit)" IS NOT NULL
    ORDER BY TMAX DESC
    LIMIT 10
""").to_df()
warmest_days['Date'] = pd.to_datetime(warmest_days['Date']).apply(lambda x: x.strftime('%B ') + str(x.day) + x.strftime(', %Y'))
warmest_days['TMAX'] = warmest_days['TMAX'].apply(lambda x: f"{x}°F")

# ---- Top 10 Coldest Days ----
coldest_days = duckdb.query("""
    SELECT Date, "TMIN (Degrees Fahrenheit)" AS TMIN
    FROM weather
    WHERE "TMIN (Degrees Fahrenheit)" IS NOT NULL
    ORDER BY TMIN ASC
    LIMIT 10
""").to_df()
coldest_days['Date'] = pd.to_datetime(coldest_days['Date']).apply(lambda x: x.strftime('%B ') + str(x.day) + x.strftime(', %Y'))
coldest_days['TMIN'] = coldest_days['TMIN'].apply(lambda x: f"{x}°F")

# ---- Top 10 Wettest Days ----
wettest_days = duckdb.query("""
    SELECT Date, "PRCP (Inches)" AS PRCP
    FROM weather
    WHERE "PRCP (Inches)" IS NOT NULL
    ORDER BY PRCP DESC
    LIMIT 10
""").to_df()
wettest_days['Date'] = pd.to_datetime(wettest_days['Date']).apply(lambda x: x.strftime('%B ') + str(x.day) + x.strftime(', %Y'))
wettest_days['PRCP'] = wettest_days['PRCP'].apply(lambda x: f"{x:.2f} in")

# ---- Top 10 Warmest Months ----
warmest_months = duckdb.query("""
    SELECT MIN(Date) AS SampleDate,
           ROUND(AVG("TAVG (Degrees Fahrenheit)"), 1) AS TAVG
    FROM weather
    WHERE "TAVG (Degrees Fahrenheit)" IS NOT NULL
    GROUP BY STRFTIME(Date, '%Y-%m')
    ORDER BY TAVG DESC
    LIMIT 10
""").to_df()
warmest_months['Date'] = pd.to_datetime(warmest_months['SampleDate']).dt.strftime('%B %Y')
warmest_months['TAVG'] = warmest_months['TAVG'].apply(lambda x: f"{x}°F")
warmest_months = warmest_months[['Date', 'TAVG']]

# ---- Top 10 Coldest Months ----
coldest_months = duckdb.query("""
    SELECT MIN(Date) AS SampleDate,
           ROUND(AVG("TAVG (Degrees Fahrenheit)"), 1) AS TAVG
    FROM weather
    WHERE "TAVG (Degrees Fahrenheit)" IS NOT NULL
    GROUP BY STRFTIME(Date, '%Y-%m')
    ORDER BY TAVG ASC
    LIMIT 10
""").to_df()
coldest_months['Date'] = pd.to_datetime(coldest_months['SampleDate']).dt.strftime('%B %Y')
coldest_months['TAVG'] = coldest_months['TAVG'].apply(lambda x: f"{x}°F")
coldest_months = coldest_months[['Date', 'TAVG']]

# ---- Top 10 Wettest Months ----
wettest_months = duckdb.query("""
    SELECT MIN(Date) AS SampleDate,
           SUM("PRCP (Inches)") AS PRCP
    FROM weather
    WHERE "PRCP (Inches)" IS NOT NULL
    GROUP BY STRFTIME(Date, '%Y-%m')
    ORDER BY PRCP DESC
    LIMIT 10
""").to_df()
wettest_months['Date'] = pd.to_datetime(wettest_months['SampleDate']).dt.strftime('%B %Y')
wettest_months['PRCP'] = wettest_months['PRCP'].apply(lambda x: f"{x:.2f} in")
wettest_months = wettest_months[['Date', 'PRCP']]

# ---- Display in Streamlit ----
col1, col2 = st.columns(2)

entry_style = "display: flex; justify-content: space-between; padding: 8px 0; margin-bottom: 2px; border-bottom: 1px solid rgba(128, 128, 128, 0.3);"
last_entry_style = "display: flex; justify-content: space-between; padding: 8px 0; margin-bottom: 2px;"

with col1:
    with st.expander("Warmest Days", expanded=False):
        for i, row in warmest_days.iterrows():
            style = last_entry_style if i == len(warmest_days) - 1 else entry_style
            st.markdown(f"<div style='{style}'><span>{row['Date']}</span><span>{row['TMAX']}</span></div>", unsafe_allow_html=True)

    with st.expander("Coldest Days", expanded=False):
        for i, row in coldest_days.iterrows():
            style = last_entry_style if i == len(coldest_days) - 1 else entry_style
            st.markdown(f"<div style='{style}'><span>{row['Date']}</span><span>{row['TMIN']}</span></div>", unsafe_allow_html=True)

    with st.expander("Wettest Days", expanded=False):
        for i, row in wettest_days.iterrows():
            style = last_entry_style if i == len(wettest_days) - 1 else entry_style
            st.markdown(f"<div style='{style}'><span>{row['Date']}</span><span>{row['PRCP']}</span></div>", unsafe_allow_html=True)

with col2:
    with st.expander("Warmest Months", expanded=False):
        for i, row in warmest_months.iterrows():
            style = last_entry_style if i == len(warmest_months) - 1 else entry_style
            st.markdown(f"<div style='{style}'><span>{row['Date']}</span><span>{row['TAVG']}</span></div>", unsafe_allow_html=True)

    with st.expander("Coldest Months", expanded=False):
        for i, row in coldest_months.iterrows():
            style = last_entry_style if i == len(coldest_months) - 1 else entry_style
            st.markdown(f"<div style='{style}'><span>{row['Date']}</span><span>{row['TAVG']}</span></div>", unsafe_allow_html=True)

    with st.expander("Wettest Months", expanded=False):
        for i, row in wettest_months.iterrows():
            style = last_entry_style if i == len(wettest_months) - 1 else entry_style
            st.markdown(f"<div style='{style}'><span>{row['Date']}</span><span>{row['PRCP']}</span></div>", unsafe_allow_html=True)
