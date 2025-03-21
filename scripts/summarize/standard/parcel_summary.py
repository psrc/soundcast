import os
import pandas as pd
import sqlite3
import toml

def parcel_summary():
    """
    Summarize parcels for quick check of totals and means
    """

    input_config = toml.load('configuration/input_configuration.toml')

    # Load parcels_urbansim input
    load_cols = ["parcelid", "taz_p", "ppricdyp", "pprichrp", "parkdy_p", "parkhr_p"]
    df_input = pd.read_csv(
        "inputs/scenario/landuse/parcels_urbansim.txt", sep=" ", usecols=load_cols
    )

    df_output = pd.read_csv(
        "outputs/landuse/parcels_urbansim.txt", sep=" ", usecols=load_cols
    )

    # Check that future year parking costs are properly updated on parcel outputs file
    con = sqlite3.connect(os.path.join('inputs', 'db', 'soundcast_inputs_2023.db'))
    df_parking_costs = pd.read_sql_query("SELECT * FROM parking_costs WHERE year== "+input_config['model_year'], con)
    df_parking_zones = pd.read_sql_query("SELECT * FROM parking_zones", con)

    # Total number of parking spaces (hourly/daily should not change)


    # Merge parking costs to parcels
    df_input = df_input.merge(df_parking_zones, left_on="taz_p", right_on='TAZ', how="left")
    df_input = df_input.merge(df_parking_costs, on="ENS", how="left")

    # Summarize by parking ensemble area
    daily_parking_parcels = df_input[df_input['parkdy_p']>0]
    # Check that accessibilities are properly updated on buffered parcel file

    # Merge input and output parcels
    # df = df_input.merge(df_output, on="parcelid", suffixes=("_input", "_output"))
    df_input['source'] = 'input'
    df_output['source'] = 'output'
    df = pd.concat([df_input, df_output], axis=0)
    df = df.fillna(0)
    _df = df.groupby('source').sum()
    _df[load_cols]
    # Totals should be she same in base years and different in future years
    _df[load_cols].to_csv('outputs/landuse/parking_totals.csv', index=False)

    
    # Save results in flat text file
    # results_df = pd.DataFrame()

    # Calculate totals for jobs by sector, households, students, and parking spaces

    # _df = df[cols]
    # # Append results to results_df
    # results_df["value"] = _df.sum()
    # results_df["field"] = results_df.index
    # results_df.reset_index(inplace=True, drop=True)
    # results_df["measure"] = "sum"

    # # Calculate average parking price
    # _df = pd.DataFrame(df[parking_cols].mean(), columns=["value"])
    # _df["measure"] = "mean"
    # _df["field"] = _df.index
    # _df.reset_index(inplace=True, drop=True)
    # results_df = results_df.append(_df)

    # _df = pd.DataFrame(df[parking_cols].max(), columns=["value"])
    # _df["measure"] = "max"
    # _df["field"] = _df.index
    # _df.reset_index(inplace=True, drop=True)
    # results_df = results_df.append(_df)

    # results_df.to_csv(r"outputs/landuse/parcels_urbansim_summary.txt", index=False)


if __name__ == "__main__":
    parcel_summary()
