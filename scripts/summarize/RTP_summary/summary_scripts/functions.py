import os
import pandas as pd
import h5py
import numpy as np
import toml
import sqlite3
from pathlib import Path


CONFIG = toml.load(Path("../../../../configuration") / "summary_configuration.toml")
INPUT_CONFIG = toml.load(Path("../../../../configuration") / "input_configuration.toml")

# Relative path between notebooks and goruped output directories
output_path = Path(CONFIG['sc_run_path']) / CONFIG["output_folder"]

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
        df["data3"].astype("int32").astype("str").map(CONFIG["facility_type_dict"])
    )
    df["facility_type"] = df["facility_type"].fillna("Other").copy()
    # Define county type
    df["county"] = (
        df["@countyid"].astype("int32").astype("str").map(CONFIG["county_map"])
    )
    df["county"] = df["county"].fillna("Outside Region").copy()
    # Define time of day period
    df["tod_period"] = df["tod"].map(CONFIG["tod_dict"])

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