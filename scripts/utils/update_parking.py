# This script modifies parcel-level parking data. 
# Parcels obtain aggregate parking costs from 4K ensembles. 
# Parcels with parking cost but zero parking spaces are given the average number of parking spaces. 
# Currently this average is for the entire region, but should be updated to properly model number of spaces
# by building type, location, or local code. This is just a placeholder to remove coding errors in DaySim
# when zero-parking space parcels cause divide-by-zero errors. 
#
# Run this script from the same location as the parcels.txt file
# Parcels.txt can be converted from .dbf format with ArcGIS.

import pandas as pd
import h5py
import numpy as np
from input_configuration import *


daily_parking_cost = "inputs\\parcel_buffer\\daily_parking_costs.csv"
hourly_parking_cost = "inputs\\parcel_buffer\\hourly_parking_costs.csv"
input_ensemble = "inputs\\parking_gz.csv"
input_parcels = "inputs\\parcel_buffer\\parcels_urbansim.txt"

# Combine data columns
df_parcels = pd.read_csv(input_parcels, delim_whitespace=True)
df_ensemble = pd.read_csv(input_ensemble, low_memory = False)
df_daily_parking_cost = pd.DataFrame(pd.read_csv(daily_parking_cost, low_memory = False))
df_hourly_parking_cost = pd.DataFrame(pd.read_csv(hourly_parking_cost, low_memory = False))
join_ensemble_to_parcel = pd.merge(left = df_parcels, right=df_ensemble,left_on="TAZ_P",right_on="TAZ")
# Join daily costs with parcel data 
merged_df = pd.merge(left=join_ensemble_to_parcel,
                                right=df_daily_parking_cost, 
                                left_on="ENS",
                                right_on="ENS")
# Join hourly costs with parcel data
merged_df = pd.merge(left = merged_df,
                                right = df_hourly_parking_cost,
                                left_on="ENS",
                                right_on="ENS")


# Clean up the results and store in same format as original parcel.txt file
df = pd.DataFrame(merged_df)
#drop_columns = ['PARKDY_P', 'PARKHR_P', 'PPRICDYP', 'PPRICHRP']
drop_columns = ['PPRICDYP', 'PPRICHRP']
df = df.drop(drop_columns, 1)

for column_title in drop_columns:
    df = df.rename(columns = {'DAY_COST':'PPRICDYP',
                              'HR_COST':'PPRICHRP'})


# For parcels in regions with non-zero parking costs, ensure each parcel has some minumum parking spaces available
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
# check if any lines have zero costs and more than zero paid parking spaces
#check_day = df[df['PPRICDYP'] > 0]['PARKDY_P']
#check_hour = df[df['PPRICHRP'] > 0]['PARKHR_P']
#if check_day.sum()/check_day.count() != check_day.mean():
#    print "Warning. Some parcels may have zero daily parking spaces but non-zero price."
#if check_hour.sum()/check_hour.count() != check_hour.mean():
#    print "Warning. Some parcels may have zero hourly parking spaces but non-zero price."

# Delete TAZ and ENS columns to restore file to original form. 
df = df.drop(['ENS', 'TAZ'], 1)

# Save results to text file
df.to_csv(input_parcels, sep = ' ', index = False)

# End the script
print "Parcel file updated with aggregate parking costs and lot numbers. " + str(len(replace_daily_parking_spaces)) + " parcels were updated." 
