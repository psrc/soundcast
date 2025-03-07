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

config = toml.load(os.path.join(os.getcwd(), "configuration/input_configuration.toml"))

db_path = os.path.join("inputs/db", config["db_name"])
input_parcels = r"outputs/landuse/parcels_urbansim.txt"

# Load data
conn = create_engine("sqlite:///" + db_path)
df_parcels = pd.read_csv(input_parcels, delim_whitespace=True)
df_parking_zones = pd.read_sql("SELECT * FROM parking_zones", con=conn)
df_parking_cost = pd.read_sql(
    "SELECT * FROM parking_costs WHERE year==" + config["model_year"], con=conn
)
df_parcels = pd.merge(
    left=df_parcels, right=df_parking_zones, left_on="taz_p", right_on="TAZ", how="left"
)

# Join daily costs with parcel data
df_parking_cost = pd.merge(df_parcels, df_parking_cost, on="ENS", how="left")

# Clean up the results and store in same format as original parcel.txt file
df = pd.DataFrame(df_parking_cost)
drop_columns = ["ppricdyp", "pprichrp"]
df = df.drop(drop_columns, axis=1)

for column_title in drop_columns:
    df = df.rename(columns={"DAY_COST": "ppricdyp", "HR_COST": "pprichrp"})


# For parcels in regions with non-zero parking costs, ensure each parcel has some minumum parking spaces available
# FIXME:
# For now, replacing all zero-parking locations with region-wide average number of parking spots.
# We can update this with an ensemble-wide average from GIS analysis later.

avg_daily_spaces = df[df["parkdy_p"] > 0]["parkdy_p"].mean()
avg_hourly_spaces = df[df["parkhr_p"] > 0]["parkhr_p"].mean()

daily_parking_spaces = df[df["ppricdyp"] > 0]["parkdy_p"]
hourly_parking_spaces = df[df["pprichrp"] > 0]["parkhr_p"]

replace_daily_parking_spaces = daily_parking_spaces[daily_parking_spaces == 0]
replace_hourly_parking_spaces = hourly_parking_spaces[hourly_parking_spaces == 0]
f_dy = lambda x: avg_daily_spaces
f_hr = lambda x: avg_hourly_spaces
replace_daily_parking_spaces = replace_daily_parking_spaces.apply(f_dy)
replace_daily_parking_spaces = pd.DataFrame(replace_daily_parking_spaces)
replace_hourly_parking_spaces = replace_hourly_parking_spaces.apply(f_hr)
replace_hourly_parking_spaces = pd.DataFrame(replace_hourly_parking_spaces)

# merge results back in to main data
if len(replace_daily_parking_spaces) > 0:
    df = df.join(replace_daily_parking_spaces, lsuffix="_left", rsuffix="_right")
    df = df.rename(columns={"parkdy_p_right": "parkdy_p"})
    if "parkdy_p_left" in df:
        df = df.drop("parkdy_p_left", axis=1)
    df = df.join(replace_hourly_parking_spaces, lsuffix="_left", rsuffix="_right")
    df = df.rename(columns={"parkhr_p_right": "parkhr_p"})
    if "parkhr_p_left" in df:
        df = df.drop("parkhr_p_left", axis=1)

# Delete TAZ and ENS (parking zone) columns to restore file to original form.
df = df.drop(["ENS", "TAZ"], axis=1)

# Make sure there are no Na's
df.fillna(0, inplace=True)

# Save results to text file
df.to_csv(input_parcels, sep=" ", index=False)

# End the script
print(
    "Parcel file updated with aggregate parking costs and lot numbers. "
    + str(len(replace_daily_parking_spaces))
    + " parcels were updated."
)
