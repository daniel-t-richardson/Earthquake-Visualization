# Earthquake Visualization Project

## Overview
The goal of this project is to create an interactive dashboard visualizaing earthquakes around the world. The core functionallity lies in the interactive map. When a certain earthquake is selected, details like location, time, date, magnitude, and source are displayed. If the user selects the "Analyze selected earthquake" button, additional info is displayed. This additional info includes depth, aftershock predictions for the following day, week, and month, impact assessment, and visualization of historical earthquake data in close proximity to the selected earthquake. Aftershock predictions are based on the Gutenberg-Richter Law, describing the relationship between magnitude and aftershock frequency, combined wtih Omori's Law, describeing the decay of aftershock frequency. The visualization of regional historical earthquake data is useful for understanding a given areas susceptibility to earthquakes and noticing trends in earthquake frequency.

## Background
There are a few different projects made to visualize earthquakes, most notably the US Geological Survey quake map. I wanted to improve on these projects by combining Euro - Mediterranean Seismological Center with USGS data to create a more indepth analytical tool for earthquake analysis. 

## Technologies Used
This project is built purely in Python, utilizing the Streamlit library. Pandas and Geopy are used for data manipulation and Ploty and Altair are used for mapping and graphing. Additionally, ThreadPoolExecutor is used to improve data retrieval performance.

## Usage
This project is hosted on the Streamlit Community Cloud. The URL is earthquake-visualization.streamlit.app

