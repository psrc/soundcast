import pandas as pd
from sqlalchemy import create_engine
import polars as pl
from pathlib import Path
import toml

equity_geog_dict = {"equity_focus_areas_2023__efa_poc": "People of Color",
                    "equity_focus_areas_2023__efa_pov200": "Income",
                    "equity_focus_areas_2023__efa_lep": "LEP",
                    "equity_focus_areas_2023__efa_dis": "Disability",
                    "equity_focus_areas_2023__efa_older": "Older Adults",
                    "equity_focus_areas_2023__efa_youth": "Youth"}


input_config = toml.load(Path.cwd() / '../../../../configuration/input_configuration.toml')
summary_config = toml.load(Path.cwd() / '../../../../configuration/summary_configuration.toml')

run_path = Path(summary_config['sc_run_path'])
output_path = run_path / summary_config["output_folder"]
input_path = run_path / 'inputs'


def read_sqlite_db(query):
    """get parcel geography data from sqlite database"""
        
    async_engine = create_engine('sqlite:///' + summary_config['sc_run_path'] + '/inputs/db/' + input_config['db_name'])
    df = pl.read_database(query= query,
                          connection=async_engine.connect()
                          ).to_pandas()

    return df

def get_parcel_geog():
    """get parcel geography data from sqlite database"""
    
    parcel_geog = read_sqlite_db("SELECT * FROM parcel_" + input_config["base_year"] + "_geography")

    # organize geographies
    parcel_geog['rgc_binary'] = parcel_geog['GrowthCenterName']
    parcel_geog.loc[parcel_geog['GrowthCenterName']!="Not in RGC",'rgc_binary'] = 'In RGC'

    rg_mapping = {'Core': 'Core Cities',
                  'Cities and Towns': 'Cities and Towns', 
                  'HCT': 'High Capacity Transit Communities',
                  'Metro': 'Metropolitan Cities',
                  'Rural': 'Rural Areas',
                  'Urban Unincorporated': 'Urban Unincorporated Areas'}
    parcel_geog['RegionalGeogName'] = parcel_geog['rg_proposed'].map(rg_mapping)

    parcel_geog[list(equity_geog_dict.values())] = parcel_geog[list(equity_geog_dict.keys())].\
        apply(lambda x: x.map({0.0: 'Below Regional Average', 
                               1.0: 'Above Regional Average', 
                               2.0: 'Higher Share of Equity Population'}
                               ))

    return parcel_geog

def get_parcels_urbansim_data(inc_geog=False):
    """get parcels_urbansim data from model output (merge with parcel geography if needed)"""
    
    # parcel land use data
    df_parcel = pl.read_csv(output_path / 'landuse/parcels_urbansim.txt', separator=' ').to_pandas()

    if inc_geog:
        df_parcel = df_parcel.merge(get_parcel_geog(), left_on='parcelid', right_on='ParcelID', how='left')     

    return df_parcel
    
def process_network_summary():
    """
    preprocess network-level results
    """

    df = pd.read_csv(output_path / "network/network_results.csv")

    # Exclude trips taken on non-designated facilities (facility_type == 0)
    # These are artificial (weave lanes to connect HOV) or for non-auto uses
    df = df[df["data3"] != 0].copy()  # data3 represents facility_type

    # Define facility type
    df["facility_type"] = (
        df["data3"].astype("int32").astype("str").map(summary_config["facility_type_dict"])
    )
    df["facility_type"] = df["facility_type"].fillna("Other").copy()
    # Define county type
    df["county"] = (
        df["@countyid"].astype("int32").astype("str").map(summary_config["county_map"])
    )
    df["county"] = df["county"].fillna("Outside Region").copy()
    # Define time of day period
    df["tod_period"] = df["tod"].map(summary_config["tod_dict"])

    # calculate total link VMT and VHT
    df["VMT"] = df["@tveh"] * df["length"]
    df["VHT"] = df["@tveh"] * df["auto_time"] / 60

    # Calculate delay
    # Select links from overnight time of day
    delay_df = df.loc[df["tod"] == "20to5"][["ij", "auto_time"]]
    delay_df.rename(columns={"auto_time": "freeflow_time"}, inplace=True)

    # Merge delay field back onto network link df
    df = pd.merge(df, delay_df, on="ij", how="left")

    # Calcualte hourly delay
    df["total_delay"] = (
        (df["auto_time"] - df["freeflow_time"]) * df["@tveh"]
    ) / 60  # sum of (volume)*(travtime diff from freeflow)

    return df
        
def get_is_rgc(df, from_col, to_col='is_rgc'):
    """Add a column 'is_rgc' to the dataframe based on the values in from_col."""

    df[to_col] = 'Not in RGC'
    df.loc[df[from_col] != 'Not in RGC', to_col] = 'In RGC'

    return df