# This script modifies parcel-level parking data. 
# Parcels obtain aggregate parking costs from 4K ensembles. 
# Parcels with parking cost but zero parking spaces are given the average number of parking spaces. 
# Currently this average is for the entire region, but should be updated to properly model number of spaces
# by building type, location, or local code. This is just a placeholder to remove coding errors in DaySim
# when zero-parking space parcels cause divide-by-zero errors. 
#
# Run this script from the same location as the parcels.txt file
# Parcels.txt can be converted from .dbf format with ArcGIS.

import os, sys
import pandas as pd
import h5py
import numpy as np
from sqlalchemy import create_engine
sys.path.append(os.getcwd())
# from input_configuration import *
import toml
config = toml.load(os.path.join(os.getcwd(), 'configuration/input_configuration.toml'))

db_path = r'inputs/db/soundcast_inputs.db'
input_parcels = r'inputs/scenario/landuse/parcels_urbansim.txt'

# Load data
conn = create_engine('sqlite:///'+db_path)
df_parcels = pd.read_csv(input_parcels, delim_whitespace=True)
df_parking_zones = pd.read_sql('SELECT * FROM parking_zones', con=conn)
df_parking_cost = pd.read_sql('SELECT * FROM parking_costs WHERE year=='+config['model_year'], con=conn)
df_parcels = pd.merge(left=df_parcels, right=df_parking_zones, left_on="TAZ_P", right_on="TAZ", how = 'left')

# Join daily costs with parcel data 
df_parking_cost = pd.merge(df_parcels, df_parking_cost, on='ENS', how='left')

# Clean up the results and store in same format as original parcel.txt file
df = pd.DataFrame(df_parking_cost)
drop_columns = ['PPRICDYP', 'PPRICHRP']
df = df.drop(drop_columns, 1)

for column_title in drop_columns:
    df = df.rename(columns = {'DAY_COST':'PPRICDYP',
                              'HR_COST':'PPRICHRP'})


# For parcels in regions with non-zero parking costs, ensure each parcel has some minumum parking spaces available
# FIXME:
# For now, replacing all zero-parking locations with region-wide average number of parking spots. 
# We can update this with an ensemble-wide average from GIS analysis later.

avg_daily_spaces = df[df['PARKDY_P'] > 0]['PARKDY_P'].mean()
avg_hourly_spaces = df[df['PARKHR_P'] > 0]['PARKHR_P'].mean()

daily_parking_spaces = df[df['PPRICDYP'] > 0]['PARKDY_P']
hourly_parking_spaces = df[df['PPRICHRP'] > 0]['PARKHR_P']

replace_daily_parking_spaces= daily_parking_spaces[daily_parking_spaces == 0]
replace_hourly_parking_spaces= hourly_parking_spaces[hourly_parking_spaces == 0]
f_dy = lambda x : avg_daily_spaces
f_hr = lambda x : avg_hourly_spaces
replace_daily_parking_spaces = replace_daily_parking_spaces.apply(f_dy)
replace_daily_parking_spaces = pd.DataFrame(replace_daily_parking_spaces)
replace_hourly_parking_spaces = replace_hourly_parking_spaces.apply(f_hr)
replace_hourly_parking_spaces = pd.DataFrame(replace_hourly_parking_spaces)

# merge results back in to main data
if len(replace_daily_parking_spaces) > 0:
    df = df.join(replace_daily_parking_spaces, lsuffix = '_left', rsuffix = '_right')
    df = df.rename(columns = {'PARKDY_P_right':'PARKDY_P'})
    if 'PARKDY_P_left' in df:
        df = df.drop('PARKDY_P_left', 1)
    df = df.join(replace_hourly_parking_spaces, lsuffix = '_left', rsuffix = '_right')
    df = df.rename(columns = {'PARKHR_P_right':'PARKHR_P'})
    if 'PARKHR_P_left' in df:
        df = df.drop('PARKHR_P_left', 1)

# Delete TAZ and ENS (parking zone) columns to restore file to original form. 
df = df.drop(['ENS', 'TAZ'], 1)

#Make sure there are no Na's
df.fillna(0, inplace=True)

# Save results to text file
df.to_csv(input_parcels, sep = ' ', index=False)

# End the script
print("Parcel file updated with aggregate parking costs and lot numbers. " + str(len(replace_daily_parking_spaces)) + " parcels were updated.")
