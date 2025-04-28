# This script modifies parcel-level parking data.
# Parcels obtain aggregate parking costs from 4K ensembles.

import pandas as pd


def main(state):
    parcel_file = r"outputs/landuse/parcels_urbansim.txt"

    # Load data
    df_parcels = pd.read_csv(parcel_file, delim_whitespace=True)
    df_parking_zones = pd.read_sql("SELECT * FROM parking_zones", con=state.conn)
    df_parking_cost = pd.read_sql(
        "SELECT * FROM parking_costs WHERE year==" + state.input_settings.model_year, con=state.conn
    )
    df_parcels = pd.merge(
        left=df_parcels, right=df_parking_zones, left_on="taz_p", right_on="TAZ", how="left"
    )

    # Log parcel data before edits
    df_summary = df_parcels[["ppricdyp", "pprichrp", "parkdy_p", "parkhr_p"]].describe()
    df_summary.loc['sum',:] = df_parcels[["ppricdyp", "pprichrp", "parkdy_p", "parkhr_p"]].sum(axis=0)
    df_summary['source'] = 'before update_parking.py'

    # Join daily costs with parcel data
    df_parking_cost = pd.merge(df_parcels, df_parking_cost, on="ENS", how="left")

    # Clean up the results and store in same format as original parcel.txt file
    df = pd.DataFrame(df_parking_cost)
    drop_columns = ["ppricdyp", "pprichrp"]
    df = df.drop(drop_columns, axis=1)

    for column_title in drop_columns:
        df = df.rename(columns={"DAY_COST": "ppricdyp", "HR_COST": "pprichrp"})


    # For parcels in regions with non-zero parking costs, ensure each parcel parking spaces available to meet Daysim requirements.
    # NOTE:
    # Applying average number of paid spaces for parcels within paid parking zones to all parcels with zero parking spaces.
    # This overpredicts the number of parking spaaces and this value should be modeled by urbansim or a preprocessor. 
    # Daysim does use the number of parking spaces in logsums but testing suggests it has little effect on results
    avg_daily_spaces = df[df["ppricdyp"] > 0]["parkdy_p"].mean()
    avg_hourly_spaces = df[df["pprichrp"] > 0]["parkhr_p"].mean()

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

    # Log parcel data before edits
    df_summary_update = df[["ppricdyp", "pprichrp", "parkdy_p", "parkhr_p"]].describe()
    df_summary_update.loc['sum',:] = df[["ppricdyp", "pprichrp", "parkdy_p", "parkhr_p"]].sum(axis=0)
    df_summary_update['source'] = 'after update_parking.py'

    df_summary = pd.concat([df_summary, df_summary_update], axis=0)
    df_summary.to_csv("outputs/landuse/parcel_summary.csv")

    # Save results to text file
    df.to_csv(parcel_file, sep=" ", index=False)

    # End the script
    print(
        "Parcel file updated with aggregate parking costs and lot numbers. "
        + str(len(replace_daily_parking_spaces))
        + " parcels were updated."
    )
