# Long Beach Climate Dashboard

## A Streamlit web app that analyzes 75 years of historical weather data in Long Beach, CA. 

This interactive weather analysis dashboard explores climate trends using historical data from 1949 to the present. Users can explore extremes, analyze major holidays, and look up climate summaries for any day of the year. 

 Key Features Include:

### Snapshot View:
Explore Long Beach’s most extreme weather observations with:  
- **Warmest and coldest days** (TMAX, TMIN) and **wettest days** (PRCP)  
- **Warmest, coldest, and wettest months** by averages  


### Holiday Outlook:
Get historical weather insights for major U.S. holidays:  
- **Year-by-year breakdowns** of temperatures and precipitation  
- **Record highs, lows, and rainfall** highlighted for context  
- **Expandable sections** for quick overview or detailed exploration

### Climate History by Day:
Select any calendar day to receive a comprehensive statistical profile including:  
- **Long-term daily averages** for temperature and rainfall probability  
- **Record highs and lows with dates**  
- **Auto-generated “Did You Know?” facts** revealing notable weather events or extremes

### Did You Know? Facts Engine:
Unique, engaging weather trivia generated dynamically by:  
- **Comparing record-setting values against daily averages**  
- **Highlighting extreme fluctuations** such as temperature swings over 30°F  

## Live Demo:

Check out the app here: [Long Beach Climate Dashboard on Streamlit](https://longbeachclimate.streamlit.app)


## Installation Instructions for Local Use:

### Prerequisites:
- Python 3.8+

### Installation:

1. Clone the repository:
```sh
git clone https://github.com/your-username/longbeach_weather.git
cd longbeach_weather
``` 
2. Create and activate a virtual environment: 
```sh
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate
```
3. Install the dependencies: 
```sh
pip install -r requirements.txt
``` 
4. Run the app on Streamlit: 
```sh 
streamlit run Snapshot.py
```

## Contact

Edward Quezada - edwardq@alumni.stanford.edu
