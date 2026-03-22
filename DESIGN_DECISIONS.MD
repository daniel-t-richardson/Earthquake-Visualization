## Design Decisions

### Why use Streamlit?

I used the streamlit library because I wanted to focus on data processing and visualization as opposed to front end design.

### Why use USGS and EMSC data?

I used USGS and EMSC data for seperate purposes. USGS data mostly covers major global earthquakes and earthquakes on the pacific coast. EMSC data covers earthquakes globally. EMSC data makes up the bulk of the earthquakes mapped, but USGS data allows for the impact assessment of major earthquakes.

### How do you ensure no duplicate earthquakes are added when using two data sources?

To prevent duplicate earthquakes being mapped, I used a dictionary of dictionaries of lists. The primary key is an earthquakes rounded magnitude and rounded hour time, and the secondary key is an earthquakes rounded latitude and longitude. When checking for duplicates, if an earthquakes rounded magnitude, rounded hour time, rounded latitude, and rounded longitude appear in the dictionary, similar coordinate dictionary entries are iterated through to ensure no earthquake with roughly the same magnitude, hour time, latitude, and longitude appear in the dictionary.

### Why is depth not shown in the main details of an earthquake?

Depth is not shown immediately because USGS does not include depth in its main API. If the selected earthquake is of USGS origin, another USGS api is called upon clicking the "analyze selected earthquake" button to retrieve depth details.
