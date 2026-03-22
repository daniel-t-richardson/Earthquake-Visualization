import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from geopy.distance import geodesic
import altair as alt
import plotly.express as px
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Earthquake_Visualization", layout="wide")

st.markdown( # remove watermark on map
    """
    <style>
    .mapboxgl-ctrl-bottom-right, .mapboxgl-ctrl-bottom-left {
        display: none !important;
    }
    .deck-tooltip {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.title("Earthquake Visualization")

with st.sidebar:
    mag_filter = st.slider("Magnitude Range", # no rerun because data is in cache
                            min_value = 0, 
                            max_value= 10, 
                            value = (0, 10),
                            key = 'mag_filter')
    
    timeframe_filter = st.selectbox("Timeframe",
                                    ("Day", "Week", "Month")) # reruns data fetching, required data is not in the cache
    
    feelable_filter = st.checkbox("Only Show Feelable Earthquakes") # only show > 2.5 mag. no rerun, data in cache

# sample urls:
#https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson
#https://www.seismicportal.eu/fdsnws/event/1/query?minmagnitude=1.5&starttime=3-6-2026&format=json
def generate_urls(timeframe):
    # create urls to feed to fetch_data
    today = datetime.now()
    if timeframe == 'month':
        date = today - relativedelta(months=1)
    elif timeframe == 'week':
        date = today - relativedelta(weeks=1)
    else:
        date = today - relativedelta(days=1)
    
    formatted_date = date.strftime("%Y-%m-%d")
    usgs_url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={formatted_date}&minmagnitude=1.5"
    emsc_url = f"https://www.seismicportal.eu/fdsnws/event/1/query?minmagnitude=1.5&starttime={formatted_date}&format=json"
    return usgs_url, emsc_url

# if a mag is logged in the earthquake dict, calculate distance between prev and new coord. If dist < 20 km, duplication is probable.
def duplication_check(coord_tuple, earthquake_dictionary, mag, hour_time):
    # for every earthquake, check if mag and hour time is in the dictionary. if it is, check if similar coords have been stored. if any similar coords have a distance less than 
    # 20 km, do not add the earthquake to the earthquake dict
    lat, long = coord_tuple
    rounded_lat = int(float(lat))
    rounded_long = int(float(long))
    key = (mag, hour_time)
    rounded_coords = (rounded_lat, rounded_long)
    
    for i in range(rounded_lat - 1, rounded_lat + 2):
        for j in range(rounded_long - 1, rounded_long + 2):
            
            adj_coords = (i, j)
            prev_coords = earthquake_dictionary[key].get(adj_coords, [])
            
            for prev_coord_tuple in prev_coords:
                if geodesic(coord_tuple, prev_coord_tuple).km < 20: # 20 km is generally greater than the difference between emsc and usgs coords, indicating a duplicate if dist > 20
                    return False

    earthquake_dictionary[key][rounded_coords].append(coord_tuple)
    
    return True
    
def aftershock_prediction(mag, hours_since, window_days):
    # predict > 2.5 aftershocks using generalised constants. maybe add seperate constants for quakes on ring of fire.
    a = -1.67 # generalised productivity constant representing average crust productivity
    b = 0.91 # gutenberg-richter, 1 mag 7 = 9 mag 6s
    p = 1.08 # decay, how fast aftershocks fade
    c = 0.05 # offset due to detection delays
     
    productivity = 10**(a + b * (mag - 2.5)) # only factors mag > 2.5. if lower, zero
     
    start = hours_since / 24 # converting hour time to days
    end = start + window_days
     
    term1 = (start + c)**(1 - p)
    term2 = (end + c)**(1 - p)
    
    total = (productivity / (1 - p)) * (term2 - term1) # frequency of shocks decreases proportional to inverse of time follow mainshock
     
    return max(total, 0)
    
def historical_data(lat, long):
    # use emsc data, go back ten years, plot data
    base_url = "https://www.seismicportal.eu/fdsnws/event/1/query"
    end_time = datetime.now(timezone.utc)
    start_time = end_time - relativedelta(years=10)
    params = {
        "format": "json",
        "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "latitude": lat,
        "longitude": long,
        "maxradius": 2,
        "minmagnitude": 4.0, # historical data retrieval would be too time intensive without mag > 4
        "limit": 4000 # neccessary fail safe, > 4000 causes issues with json encoding. emsc issue.
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        quakes = data['features']
        
        # create dataframe for plotting data
        history = []
        for quake in quakes:
            properties = quake['properties']
            info = {
                'mag': properties['mag'],
                'depth': properties['depth'],
                'date': properties['time'].split("T")[0]
            }
            history.append(info)
            
        df = pd.DataFrame(history)
        return df 
    
    except requests.exceptions.RequestException:
        return None # if None, create chart function will write error message to user

def create_history_chart(df):
    # display historical data for any given earthquake
    if df is None: # there was an issue pulling data from emsc
        st.write("There was an error retrieving historical data.")
        return
    st.header("Regional Historic Data")
    st.caption("Past Earthquakes greater than magnitude 4 within ~138 miles")
    
    #plot data from historical_data()
    chart = (
        alt.Chart(df)
        .mark_circle()
        .encode(x="date:T",
                color = alt.Color("depth:Q", scale=alt.Scale(scheme="reds")),
                y=alt.Y("mag:Q", scale=alt.Scale(domainMin=4)),
                tooltip=["mag:Q", "depth:Q", "date:T"])
    )
    
    st.altair_chart(chart)

def quake_analysis(clicked_data):
    # process data to display when analayze quake button is pressed
    now = datetime.now(timezone.utc)
    date_format = "%Y-%m-%d %H:%M:%S" 
    quake_time = datetime.strptime(f"{clicked_data['date']} {clicked_data['time']}", date_format).replace(tzinfo=timezone.utc) # creates a datetime object of the selected date and time
    difference = now - quake_time
    hour_diff = difference.total_seconds() / 3600 # hour difference of current time and selected quake
    
    aftershocks_day = round(aftershock_prediction(clicked_data['mag'], hour_diff, 1)) # calculate all three aftershock time frames
    aftershocks_week = round(aftershock_prediction(clicked_data['mag'], hour_diff, 7))
    aftershocks_month = round(aftershock_prediction(clicked_data['mag'], hour_diff, 30))
    
    alert = clicked_data.get('alert') 
    # only usgs has alerts. because usgs is processed first,
    # any earthquake large enough to have a meaningful alert will be stored as a usgs quake. if there is 
    # not an alert, we know that usgs did not flag it and it is harmless.
    
    if not alert:
        impact_message = "This earthquake did not result in any casualties or damage."
        
    else:
        if alert == 'green':
            impact_message = "This earthquake is not likely to have caused any casualties or damage."
        
        elif alert == 'yellow':
            impact_message = "This earthquake is likely to have caused 1 - 10 million USD in damages and 1 - 10 casualties."
        
        elif alert == 'orange':
            impact_message = "This earthquake is likely to have caused 100 - 1,000 million USD in damages and 100 - 1,000 casualties."
        
        elif alert == "red":
            impact_message = "This earthquake is likely to have caused more than 10 billion dollars in damages and 10,000 casualties."       
        
    depth = "There was an error retrieving depth data." # assigning depth if source is somehow neither emsc or usgs
    
    if clicked_data['source'] == 'EMSC':
        depth = clicked_data['depth']
        
    elif clicked_data['source'] == 'USGS':
        # depth is not shown in first chart due to usgs not displaying depth with main details
        try:
            url = f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/{clicked_data['usgs_id']}.geojson"
            details_json = response_and_parse(url)
            depth = int(details_json['properties']['products']['origin'][0]['properties']['depth'].split(".")[0])
            
        except (requests.exceptions.RequestException, KeyError, IndexError):
            depth = "There was an error retrieving depth data."
            
    with st.container(border=True):
        aftershock_df = pd.DataFrame(
                {
                    "Predicted Aftershocks Greater than 2.5 Mag":
                        [aftershocks_day,
                        aftershocks_week,
                        aftershocks_month]
                },
                index=["Day", "Week", "Month"]
            )
        st.table(aftershock_df, border="horizontal")
        
    analysis_display(impact_message, depth, clicked_data) # display info
        
def analysis_display(impact_message, depth, clicked_data):
    # display info and feed data into create_history_chart
    with st.container(border=True):
        st.markdown("Impact Assessment")
        st.write(impact_message)
        
    with st.container(border=True):
        st.markdown("Earthquake Depth (KM)")
        st.markdown(depth)
    
    with st.spinner("Loading Historical Data"):
        historical_df = historical_data(clicked_data['latitude'], clicked_data['longitude'])
        create_history_chart(historical_df) # chart display is handled in create_chart
        
def response_and_parse(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

@st.cache_data(ttl=300)
def fetch_data(usgs_url, emsc_url):
    earthquake_dictionary = defaultdict(lambda: defaultdict(list)) # make a dictionary of dictionaries each containing an empty list.
    try:
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_usgs = executor.submit(response_and_parse, usgs_url)
            future_emsc = executor.submit(response_and_parse, emsc_url)
            
            usgs_json = future_usgs.result()
            emsc_json = future_emsc.result()
            
        usgs_earthquakes = usgs_json['features']
        data_list = []
        
        # iterate through data in json, add data to dataframe if not duplicate
        for quake in usgs_earthquakes:
            mag = quake['properties']['mag']
            if mag is None:
                continue
            timestamp = quake['properties']['time'] / 1000.0 # time is in unix
            date_time = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S').split()
            date = date_time[0]
            time = date_time[1]
            hour_time = time.split(":")[0]
            alert = quake['properties']['alert'] or None

            row_data = {'location': quake['properties']['place'], 
                        'latitude': quake['geometry']['coordinates'][1], 
                        'longitude': quake['geometry']['coordinates'][0],
                        'mag': mag,
                        'time': time,
                        'date': date,
                        'source': 'USGS',
                        'usgs_id': quake['id'],
                        'alert': alert,
                        }
            
            if not duplication_check((row_data['latitude'], row_data['longitude']), earthquake_dictionary, round(mag, 1), hour_time):
                continue

            data_list.append(row_data)
            
        emsc_earthquakes = emsc_json['features']
        
        for quake in emsc_earthquakes:
            full_timestamp = quake['properties']['time'].split("T")
            hours_time = full_timestamp[1]
            date = full_timestamp[0]
            time = hours_time.split(".")[0]
            hour_time = time.split(":")[0]
            mag = quake['properties']['mag']
            if mag is None:
                continue
            
            row_data = {'location': quake['properties']['flynn_region'],
                        'latitude': quake['properties']['lat'],
                        'longitude': quake['properties']['lon'],
                        'mag': mag,
                        'time': time,
                        'date': date,
                        'depth': quake['properties']['depth'],
                        'source': "EMSC",
                        'alert': None}

            if not duplication_check((row_data['latitude'], row_data['longitude']), earthquake_dictionary, round(mag, 1), hour_time):
                continue
            
            data_list.append(row_data)
            
        df = pd.DataFrame(data_list)
        
        return df
        
    except requests.exceptions.RequestException:
        st.write("United States Geological Survey or European Mediterranean Seismological Centre JSON data is unavailable")
        return None

usgs_url, emsc_url = generate_urls(timeframe = timeframe_filter.lower())
df = fetch_data(usgs_url, emsc_url)

if df is not None:
    magnitude_condition = (df['mag'] >= mag_filter[0]) & (df['mag'] <= mag_filter[1])

    if feelable_filter:
        feelable_condition = df['mag'] >= 2.5 # 2.5 is generally lowest mag felt
        filtered = df[magnitude_condition & feelable_condition]
    else:
        filtered = df[magnitude_condition]
        
    quake_count = len(filtered) # earthquakes in the given period

    fig = px.scatter_mapbox(
        filtered,
        lat="latitude",
        lon="longitude",
        size="mag",
        color="mag",
        color_continuous_scale=px.colors.sequential.YlOrRd,
        hover_name="source",
        hover_data={"mag": True, "date": True, "time": True, "latitude": False, "longitude": False},
        zoom=1,
        mapbox_style="carto-positron"
    )

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}) # removes padding

    map_event = st.plotly_chart( # for interaction
        fig,
        on_select="rerun",
        selection_mode="points",
        config={"scrollZoom": True}
    )

    st.divider()

    st.write(f"{quake_count} Earthquakes")

    if map_event and len(map_event.selection["point_indices"]) > 0: # if a plot is selected
        
        selected = map_event.selection["point_indices"][0]
        
        clicked_data = filtered.iloc[selected].to_dict() # change the selected point from dataframe row to dictionary
        
        if clicked_data:
            
            info = pd.DataFrame( # main info chart
                {   
                    "Details": [
                        clicked_data['location'],
                        f"{clicked_data['mag']:.1f}",
                        clicked_data['time'],
                        clicked_data['date'],
                        clicked_data['source']]
                },
                    index=["Location", "Magnitude", "Time (UTC)", "Date", "Source"]
            )
            st.dataframe(info, selection_mode="none")
            
            if st.button("Analyze Selected Earthquake", width="stretch"):
                
                quake_analysis(clicked_data)
                
    else:
        st.info("Click an earthquake marker to view information")
