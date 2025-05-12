import os
import pandas as pd
import h5py
import numpy as np
import toml
import sqlite3
from pathlib import Path

# from typing import Any


CONFIG = toml.load(Path("../../../../configuration") / "summary_configuration.toml")
INPUT_CONFIG = toml.load(Path("../../../../configuration") / "input_configuration.toml")

def _get_all_runs() -> dict:
    """
    a dictionary of soundcast runs, includes current run and any comparison runs
    """
    runs_dict = {CONFIG["sc_run_name"]: Path(CONFIG["sc_run_path"])}

    dict2 = CONFIG["comparison_runs_list"]
    for comparison_run, location in dict2.items():
        dict2[comparison_run] = Path(location)

    runs_dict.update(dict2)

    return runs_dict


ALL_RUNS = _get_all_runs()


def get_output_path(comparison_run: str) -> Path:
    """
    get output path for a run

    key argument:
        comparison_run: a key of an ALL_RUNS item (name of soundcast run directory)
    """
    return ALL_RUNS[comparison_run] / CONFIG["output_folder"]


def load_agg_data(file_path: str):
    """
    get aggregated summary tables for all runs.

    if `output_path == 'network/network_results.csv'`, the function will call `_process_network_summary()` to preprocess data

    key argument:
        output_path: file location relative to output folder
    """

    df = pd.DataFrame()
    for comparison_run in ALL_RUNS.keys():
        full_file_path = get_output_path(comparison_run) / file_path

        if file_path == "network/network_results.csv":
            df_run = _process_network_summary(comparison_run)
        else:
            if str(full_file_path).endswith(".csv"):
                df_run = pd.read_csv(full_file_path)
            # elif str(full_file_path).endswith('.h5'):
            #     df_run = h5py.File(full_file_path, 'r')

        df_run["source"] = comparison_run
        df = pd.concat([df, df_run])

    return df


def _process_network_summary(comparison_run: str):
    """
    preprocess network-level results
    """

    df = pd.read_csv(get_output_path(comparison_run) / "network/network_results.csv")

    # Exclude trips taken on non-designated facilities (facility_type == 0)
    # These are artificial (weave lanes to connect HOV) or for non-auto uses
    df = df[df["data3"] != 0]  # data3 represents facility_type

    # Define facility type
    df["facility_type"] = (
        df["data3"].astype("int32").astype("str").map(CONFIG["facility_type_dict"])
    )
    df["facility_type"].fillna("Other", inplace=True)
    # Define county type
    df["county"] = (
        df["@countyid"].astype("int32").astype("str").map(CONFIG["county_map"])
    )
    df["county"].fillna("Outside Region", inplace=True)
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


def load_landuse(output_path: str, usecols: list = None):
    """
    get land use data for all runs.

    key argument:
        output_path: file location relative to output folder
    """

    df = pd.DataFrame()
    for comparison_run in ALL_RUNS.keys():
        df_run = pd.read_csv(
            get_output_path(comparison_run) / output_path, sep=" ", usecols=usecols
        )

        # Ensure lower case column names
        df_run.columns = df_run.columns.str.lower()

        df_run["source"] = comparison_run
        df = pd.concat([df, df_run])

    return df


def load_sqlite(sql_query):
    df = pd.DataFrame()
    for comparison_run in ALL_RUNS.keys():
        con = sqlite3.connect(
            os.path.join(
                get_output_path(comparison_run),
                r"../inputs/db/soundcast_inputs_2023.db",
            )
        )
        df_run = pd.read_sql_query(sql_query, con)
        df_run["source"] = comparison_run
        df = pd.concat([df, df_run])

    return df
