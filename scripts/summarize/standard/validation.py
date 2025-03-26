# Validation for observed data

import os, sys, shutil
import pandas as pd
from sqlalchemy import create_engine, text

# output directory
validation_output_dir = "outputs/validation"

# Create a clean output directory
if os.path.exists(validation_output_dir):
    shutil.rmtree(validation_output_dir)
os.makedirs(validation_output_dir)

### FIXME: move to a config file
agency_lookup = {
    1: "King County Metro",
    2: "Pierce Transit",
    3: "Community Transit",
    4: "Kitsap Transit",
    5: "Washington Ferries",
    6: "Sound Transit",
    7: "Everett Transit",
}
# List of route IDs to separate for analysis
# special_route_list = [6998,6999,1997,1998,6995,6996,1973,1975,
#                         4200,4201,4202,4203,4204,1671,1672,1673,1674,1675,1676,1040,1007,6550,
#                         5001,5002,5003,5004,5005,5006,5007]


facility_type_lookup = {
    1: "Freeway",  # Interstate
    2: "Freeway",  # Ohter Freeway
    3: "Freeway",  # Expressway
    4: "Ramp",
    5: "Arterial",  # Principal arterial
    6: "Arterial",  # Minor Arterial
    7: "Collector",  # Major Collector
    8: "Collector",  # Minor Collector
    9: "Collector",  # Local
    10: "Busway",
    11: "Non-Motor",
    12: "Light Rail",
    13: "Commuter Rail",
    15: "Ferry",
    16: "Passenger Only Ferry",
    17: "Connector",  # centroid connector
    18: "Connector",  # facility connector
    19: "HOV",  # HOV Only Freeway
    20: "HOV",  # HOV Flag
}

county_lookup = {33: "King", 35: "Kitsap", 53: "Pierce", 61: "Snohomish"}

tod_lookup = {
    0: "20to5",
    1: "20to5",
    2: "20to5",
    3: "20to5",
    4: "20to5",
    5: "5to6",
    6: "6to7",
    7: "7to8",
    8: "8to9",
    9: "9to10",
    10: "10to14",
    11: "10to14",
    12: "10to14",
    13: "10to14",
    14: "14to15",
    15: "15to16",
    16: "16to17",
    17: "17to18",
    18: "18to20",
    19: "18to20",
    20: "20to5",
    21: "20to5",
    22: "20to5",
    23: "20to5",
    24: "20to5",
}


def main(state):

    ########################################
    # Transit Boardings by Line
    ########################################

    # Load observed data for given base year
    df_obs = pd.read_sql(
        text(
            "SELECT * FROM observed_transit_boardings WHERE year IN (2023, 2024)"
        ),
        con=state.conn.connect(),
    )
    df_obs["route_id"] = df_obs["route_id"].astype("int")
    df_obs_pivot = df_obs.pivot_table(index='route_id', columns='year', values='observed_daily', aggfunc='sum').reset_index()
    df_obs = df_obs_pivot.merge(df_obs[['route_id','agency']].drop_duplicates(), on='route_id', how='left')
    df_line_obs = df_obs.copy()
    
    # Load model results and calculate modeled daily boarding by line
    df_transit_line = pd.read_csv(r"outputs\transit\transit_line_results.csv")
    df_model = df_transit_line.copy()
    df_model_daily = (
        df_model.groupby(["route_code", "mode"])
        .agg({"description": "first", "boardings": "sum"})
        .reset_index()
    )

    # Merge modeled with observed boarding data
    df_model_daily["route_code"] = df_model_daily["route_code"].astype("int")
    df = df_model_daily.merge(
        df_obs, left_on="route_code", right_on="route_id", how="left"
    )
    df.rename(
        columns={
            "boardings": "model_boardings",
            "observed_daily": "observed_boardings",
        },
        inplace=True,
    )
    # Write to file
    df.to_csv(
        os.path.join(validation_output_dir, "daily_boardings_by_line.csv"), index=False
    )

    # Boardings by agency
    df_agency = df.groupby(["agency"]).sum().reset_index()
    df_agency.to_csv(
        os.path.join(validation_output_dir, "daily_boardings_by_agency.csv"),
        index=False,
        columns=[
            "agency",
            "model_boardings",
            2023,
            2024
        ],
    )

    # Boardings by mode
    df_mode = df.groupby(["mode"]).sum().reset_index()
    df_mode.to_csv(
        os.path.join(validation_output_dir, "daily_boardings_by_mode.csv"),
        index=False,
        columns=["mode", "model_boardings", 2023, 2024],
    )

    # Boardings for special lines
    df_special = df[
        df["route_code"]
        .astype("str")
        .isin(state.summary_settings.special_route_lookup.keys())
    ]
    df_special.to_csv(
        os.path.join(validation_output_dir, "daily_boardings_key_routes.csv"),
        index=False,
        columns=[
            "description",
            "route_code",
            "agency",
            "model_boardings",
            2023,
            2024
        ],
    )

    ########################################
    # Transit Boardings by Stop
    ########################################

    # Light Rail
    df_obs = pd.read_sql(
        "SELECT * FROM light_rail_station_boardings WHERE year="
        + str(state.input_settings.base_year),
        con=state.conn,
    )
    df_obs.rename(columns={"boardings": "observed_boardings"}, inplace=True)

    df = pd.read_csv(r"outputs\transit\boardings_by_stop.csv")
    df = df[df["i_node"].isin(df_obs["emme_node"])]
    df = df.merge(df_obs, left_on="i_node", right_on="emme_node")
    df.rename(columns={"total_boardings": "model_boardings"}, inplace=True)
    df["observed_boardings"] = df["observed_boardings"].astype("float")
    df.index = df["station_name"]
    df_total = df.copy()[["observed_boardings", "model_boardings"]]
    df_total.loc["Total", ["observed_boardings", "model_boardings"]] = (
        df[["observed_boardings", "model_boardings"]].sum().values
    )
    df_total.to_csv(r"outputs\validation\light_rail_boardings.csv", index=True)

    # Light Rail Transfers
    df_transfer = df.copy()
    df_transfer["observed_transfer_rate"] = (
        df_transfer["observed_transfer_rate"].fillna(-99).astype("float")
    )
    df_transfer["modeled_transfer_rate"] = (
        df_transfer["transfers"] / df_transfer["model_boardings"]
    )
    df_transfer["diff"] = (
        df_transfer["modeled_transfer_rate"] - df_transfer["observed_transfer_rate"]
    )
    df_transfer["percent_diff"] = (
        df_transfer["diff"] / df_transfer["observed_transfer_rate"]
    )
    df_transfer = df_transfer[
        ["modeled_transfer_rate", "observed_transfer_rate", "diff", "percent_diff"]
    ]
    df_transfer.to_csv(r"outputs\validation\light_rail_transfers.csv", index=True)

    ########################################
    # Traffic Volumes
    ########################################

    # Count data

    # Model results
    df_network = pd.read_csv(r"outputs\network\network_results.csv")
    model_vol_df = df_network.copy()
    model_vol_df["@facilitytype"] = model_vol_df["@facilitytype"].map(
        facility_type_lookup
    )

    # Get daily and model volumes
    # daily_counts = counts.groupby('flag').sum()[['vehicles']].reset_index()
    daily_counts = pd.read_sql(
        "SELECT * FROM daily_counts WHERE year=" + str(state.input_settings.base_year), con=state.conn
    )
    df_daily = (
        model_vol_df.groupby(["@countid"])
        .agg({"@tveh": "sum", "@facilitytype": "first"})
        .reset_index()
    )

    # Merge observed with model
    df_daily = df_daily.merge(daily_counts, left_on="@countid", right_on="flag")

    # Merge with attributes
    df_daily.rename(columns={"@tveh": "modeled", "vehicles": "observed"}, inplace=True)
    df_daily["diff"] = df_daily["modeled"] - df_daily["observed"]
    df_daily["perc_diff"] = df_daily["diff"] / df_daily["observed"]
    df_daily[["modeled", "observed"]] = df_daily[["modeled", "observed"]].astype("int")
    df_daily["county"] = df_daily["countyid"].map(county_lookup)
    df_daily.to_csv(
        os.path.join(validation_output_dir, "daily_volume.csv"),
        index=False,
        columns=[
            "@countid",
            "@countid",
            "county",
            "@facilitytype",
            "modeled",
            "observed",
            "diff",
            "perc_diff",
        ],
    )

    # Counts by county and facility type
    df_county_facility_counts = (
        df_daily.groupby(["county", "@facilitytype"])
        .sum()[["observed", "modeled"]]
        .reset_index()
    )
    df_county_facility_counts.to_csv(
        os.path.join(validation_output_dir, "daily_volume_county_facility.csv")
    )

    # hourly counts
    # Create Time of Day (TOD) column based on start hour, group by TOD
    hr_counts = pd.read_sql(
        "SELECT * FROM hourly_counts WHERE year=" + str(state.input_settings.base_year), con=state.conn
    )
    hr_counts["tod"] = hr_counts["start_hour"].map(tod_lookup)
    counts_tod = hr_counts.groupby(["tod", "flag"]).sum()[["vehicles"]].reset_index()

    # Account for bi-directional links or links that include HOV volumes
    hr_model = (
        model_vol_df.groupby(["@countid", "tod"])
        .agg(
            {
                "@tveh": "sum",
                "@facilitytype": "first",
                "@countyid": "first",
                "i_node": "first",
                "j_node": "first",
                "auto_time": "first",
                "type": "first",
            }
        )
        .reset_index()
    )

    # Join by time of day and flag ID
    df = pd.merge(
        hr_model, counts_tod, left_on=["@countid", "tod"], right_on=["flag", "tod"]
    )
    df.rename(columns={"@tveh": "modeled", "vehicles": "observed"}, inplace=True)
    df["county"] = df["@countyid"].map(county_lookup)
    df.to_csv(os.path.join(validation_output_dir, "hourly_volume.csv"), index=False)

    # Roll up results to assignment periods
    df["time_period"] = df["tod"].map(state.network_settings.sound_cast_net_dict )

    ########################################
    # Ferry Boardings by Bike
    ########################################
    df_transit_seg = pd.read_csv(r"outputs\transit\transit_segment_results.csv")
    df_transit_seg = df_transit_seg[df_transit_seg["tod"] == "7to8"]
    df_transit_seg = df_transit_seg.drop_duplicates(["i_node", "line_id"])
    df_transit_line = df_transit_line[df_transit_line["tod"] == "7to8"]

    _df = df_transit_line.merge(df_transit_seg, on="line_id", how="left")
    _df = _df.drop_duplicates("line_id")

    df_ij = _df.merge(df_network, left_on="i_node", right_on="i_node", how="left")
    # select only ferries
    df_ij = df_ij[df_ij["@facilitytype"].isin([15, 16])]
    # both link and transit line modes should only include passenger (p) or general ferries (f)
    for colname in ["modes", "mode"]:
        df_ij["_filter"] = df_ij[colname].apply(
            lambda x: 1 if "f" in x or "p" in x else 0
        )
        df_ij = df_ij[df_ij["_filter"] == 1]

    df_total = df_ij.groupby("route_code").sum()[["@bvol"]].reset_index()
    df_total = df_total.merge(
        df_ij[["description", "route_code"]], on="route_code"
    ).drop_duplicates("route_code")
    df_total.to_csv(r"outputs\validation\bike_ferry_boardings.csv", index=False)

    ########################################
    # Vehicle Screenlines
    ########################################

    # Screenline is defined in "type" field for network links, all values other than 90 represent a screenline

    # Daily volume screenlines
    # df = model_vol_df.merge(model_vol_df[['i_node','j_node','type']], on=['i_node','j_node'], how='left').drop_duplicates()
    # df = model_vol_df.copy()
    # df = df.groupby('type').sum()[['@tveh']].reset_index()

    # Observed screenline data
    df_obs = pd.read_sql(
        "SELECT * FROM observed_screenline_volumes WHERE year="
        + str(state.input_settings.base_year),
        con=state.conn,
    )
    df_obs["observed"] = df_obs["observed"].astype("float")

    # df_model = pd.read_csv(r'outputs\network\network_results.csv')
    df_model = model_vol_df.copy()
    df_model["screenline_id"] = df_model["type"].astype("str")
    # Auburn screenline is the combination of 14 and 15, change label for 14 and 15 to a combined label
    df_model.loc[
        df_model["screenline_id"].isin(["14", "15"]), "screenline_id"
    ] = "14/15"
    # _df = df_model.groupby('screenline_id').sum()[['@tveh']].reset_index()
    _df = (
        df_model[["@tveh", "screenline_id"]]
        .groupby("screenline_id")
        .sum()[["@tveh"]]
        .reset_index()
    )
    _df = _df.merge(df_obs, on="screenline_id")
    _df.rename(columns={"@tveh": "modeled"}, inplace=True)
    _df = _df[["name", "observed", "modeled", "county"]]
    _df["diff"] = _df["modeled"] - _df["observed"]
    _df = _df.sort_values("observed", ascending=False)
    _df.to_csv(r"outputs\validation\screenlines.csv", index=False)

    ########################################
    # External Volumes
    ########################################

    # External stations
    external_stations = range(
        state.emme_settings.MIN_EXTERNAL, state.emme_settings.MAX_EXTERNAL + 1
    )
    df_model = model_vol_df.copy()
    _df = df_model[
        (df_model["i_node"].isin(external_stations))
        | (df_model["j_node"].isin(external_stations))
    ]
    _df_i = _df.groupby("i_node").sum()[["@tveh"]].reset_index()
    _df_j = _df.groupby("j_node").sum()[["@tveh"]].reset_index()
    _df = _df_i.merge(_df_j, left_on="i_node", right_on="j_node")
    _df["@tveh"] = _df[["@tveh_x", "@tveh_y"]].sum(axis=1)
    _df = _df[["i_node", "@tveh"]]
    _df.rename(columns={"i_node": "external_station"}, inplace=True)
    _df = _df[_df["external_station"].isin(external_stations)]

    # Join to observed
    df_obs = pd.read_sql(
        "SELECT * FROM observed_external_volumes WHERE year="
        + str(state.input_settings.base_year),
        con=state.conn,
    )
    newdf = _df.merge(df_obs, on="external_station")
    newdf.rename(columns={"@tveh": "modeled", "AWDT": "observed"}, inplace=True)
    newdf["observed"] = newdf["observed"].astype("float")
    newdf["diff"] = newdf["modeled"] - newdf["observed"]
    newdf = newdf[
        ["external_station", "location", "county", "observed", "modeled", "diff"]
    ].sort_values("observed", ascending=False)
    newdf.to_csv(r"outputs\validation\external_volumes.csv", index=False)
    newdf

    ########################################
    # Corridor Speeds
    ########################################

    df_model = model_vol_df.copy()
    df_model["@corridorid"] = df_model["@corridorid"].astype("int")

    df_obs = pd.read_sql_table("observed_corridor_speed", state.conn)

    # Average  6 and 7 pm observed data
    df_obs["6pm_spd_7pm_spd_avg"] = (df_obs["6pm_spd"] + df_obs["7pm_spd"]) / 2.0

    df_obs[["Flag 1", "Flag 2", "Flag 3", "Flag 4", "Flag 5", "Flag 6"]] = (
        df_obs[["Flag 1", "Flag 2", "Flag 3", "Flag 4", "Flag 5", "Flag 6"]]
        .fillna(-1)
        .astype("int")
    )

    tod_cols = [
        "ff_spd",
        "5am_spd",
        "6am_spd",
        "7am_spd",
        "8am_spd",
        "9am_spd",
        "3pm_spd",
        "4pm_spd",
        "5pm_spd",
        "6pm_spd_7pm_spd_avg",
    ]

    _df_obs = pd.melt(
        df_obs,
        id_vars="Corridor_Number",
        value_vars=tod_cols,
        var_name="tod",
        value_name="observed_speed",
    )
    _df_obs = _df_obs[_df_obs["tod"] != "ff_spd"]

    # Set TOD
    tod_dict = {
        # hour of observed data represents start hour
        "5am_spd": "5to6",
        "6am_spd": "6to7",
        "7am_spd": "7to8",
        "8am_spd": "8to9",
        "9am_spd": "9to10",
        "3pm_spd": "15to16",
        "4pm_spd": "16to17",
        "5pm_spd": "17to18",
        "6pm_spd_7pm_spd_avg": "18to20",
    }
    _df_obs["tod"] = _df_obs["tod"].map(tod_dict)

    _df = _df_obs.merge(df_obs, on=["Corridor_Number"])
    _df.drop(tod_cols, axis=1, inplace=True)

    # Get the corridor number from the flag file
    flag_lookup_df = pd.melt(
        df_obs[
            ["Corridor_Number", "Flag 1", "Flag 2", "Flag 3", "Flag 4", "Flag 5", "Flag 6"]
        ],
        id_vars="Corridor_Number",
        value_vars=["Flag 1", "Flag 2", "Flag 3", "Flag 4", "Flag 5", "Flag 6"],
        var_name="flag_number",
        value_name="flag_value",
    )

    df_speed = df_model.merge(
        flag_lookup_df, left_on="@corridorid", right_on="flag_value"
    )

    # Note that we need to separate out the Managed HOV lanes
    df_speed = df_speed[df_speed["@is_managed"] == 0]

    df_speed = (
        df_speed.groupby(["Corridor_Number", "tod"])
        .sum()[["auto_time", "length"]]
        .reset_index()
    )
    df_speed["model_speed"] = (df_speed["length"] / df_speed["auto_time"]) * 60
    df_speed = df_speed[
        (df_speed["model_speed"] < 80) & ((df_speed["model_speed"] > 0))
    ]

    # Join to the observed data
    df_speed = df_speed.merge(_df, on=["Corridor_Number", "tod"])

    # df_speed.plot(kind='scatter', y='model_speed', x='observed_speed')
    df_speed.to_csv(r"outputs\validation\corridor_speeds.csv", index=False)

    ########################################
    # ACS Comparisons
    ########################################

    # Auto Ownership
    df_obs = pd.read_sql(
        "SELECT * FROM observed_auto_ownership_acs_block_group WHERE year="
        + str(state.input_settings.model_year),
        con=state.conn,
    )
    if int(state.input_settings.base_year) < 2020:
        geocol = "GEOID10"
    else:
        geocol = "GEOID20"
    df_obs[geocol] = df_obs[geocol].astype("int64")
    df_obs.index = df_obs[geocol]
    df_obs.rename(
        columns={
            "cars_none_control": 0,
            "cars_one_control": 1,
            "cars_two_or_more_control": 2,
        },
        inplace=True,
    )
    df_obs = df_obs[[0, 1, 2]]
    df_obs_sum = df_obs.sum()
    df_obs_sum = pd.DataFrame(df_obs_sum, columns=["census"])
    df_obs = df_obs.unstack().reset_index()
    df_obs.rename(columns={"level_0": "hhvehs", 0: "census"}, inplace=True)

    df_model = pd.read_csv(r"outputs\agg\census\auto_ownership_block_group.csv")
    # Record categories to max of 2+
    df_model.loc[df_model["hhvehs"] >= 2, "hhvehs"] = 2
    df_model = (
        df_model.groupby(["hhvehs", "hh_block_group"]).sum()[["hhexpfac"]].reset_index()
    )
    df_model["hhvehs"] = df_model["hhvehs"].astype("int")

    df_model_sum = df_model.pivot_table(
        index="hh_block_group", columns="hhvehs", aggfunc="sum", values="hhexpfac"
    )
    df_model_sum = df_model_sum.fillna(0)
    df_model_sum = df_model_sum.sum()
    df_model_sum = pd.DataFrame(df_model_sum.reset_index(drop=True), columns=["model"])
    df_sum = df_obs_sum.merge(df_model_sum, left_index=True, right_index=True)
    df = df_model.merge(
        df_obs,
        left_on=["hh_block_group", "hhvehs"],
        right_on=[geocol, "hhvehs"],
        how="left",
    )
    df.rename(columns={"hhexpfac": "modeled"}, inplace=True)
    df.to_csv(r"outputs\validation\auto_ownership_block_group.csv", index=False)

    # compare vs survey
    df_survey = pd.read_csv(r"outputs\agg\census\survey\auto_ownership_block_group.csv")

    df_survey.loc[df_survey["hhvehs"] >= 2, "hhvehs"] = 2
    df_survey = (
        df_survey.groupby(["hhvehs", "hh_block_group"])
        .sum()[["hhexpfac"]]
        .reset_index()
    )

    df_survey_sum = df_survey.pivot_table(
        index="hh_block_group", columns="hhvehs", aggfunc="sum", values="hhexpfac"
    )
    df_survey_sum = df_survey_sum.fillna(0)
    df_survey_sum = df_survey_sum.sum()
    df_survey_sum = pd.DataFrame(
        df_survey_sum.reset_index(drop=True), columns=["survey"]
    )
    df_sum.merge(df_survey_sum, left_index=True, right_index=True).to_csv(
        r"outputs\validation\auto_ownership_census_totals.csv", index=False
    )

    # Commute Mode Share by Workplace Geography
    # Model Data
    df_model = pd.read_csv(r"outputs\agg\census\tour_place.csv")
    df_model = df_model[df_model["pdpurp"] == "Work"]
    df_model = (
        df_model.groupby(["t_o_place", "t_d_place", "tmodetp"])
        .sum()[["toexpfac"]]
        .reset_index()
    )
    # rename columns
    df_model.loc[df_model["tmodetp"] == "SOV", "mode"] = "auto"
    df_model.loc[df_model["tmodetp"] == "HOV2", "mode"] = "auto"
    df_model.loc[df_model["tmodetp"] == "HOV3+", "mode"] = "auto"
    df_model.loc[df_model["tmodetp"] == "Transit", "mode"] = "transit"
    df_model.loc[df_model["tmodetp"] == "Walk", "mode"] = "walk_and_bike"
    df_model.loc[df_model["tmodetp"] == "Bike", "mode"] = "walk_and_bike"
    df_model = df_model.groupby(["mode", "t_d_place"]).sum()[["toexpfac"]].reset_index()

    # Observed Data
    df = pd.read_sql(
        "SELECT * FROM acs_commute_mode_by_workplace_geog WHERE year="
        + str(state.input_settings.base_year),
        con=state.conn,
    )
    df = df[df["geography"] == "place"]
    df = df[df["mode"] != "worked_at_home"]
    df["geog_name"] = df["geog_name"].apply(lambda row: row.split(" city")[0])

    # FIXME:
    # no HOV modes - is SOV including all auto trips?
    df.loc[df["mode"] == "sov", "mode"] = "auto"

    # Merge modeled and observed
    df = df.merge(
        df_model, left_on=["geog_name", "mode"], right_on=["t_d_place", "mode"]
    )
    df.rename(
        columns={"trips": "observed", "toexpfac": "modeled", "geog_name": "work_place"},
        inplace=True,
    )
    df = df[["work_place", "mode", "modeled", "observed"]]
    df["percent_diff"] = (df["modeled"] - df["observed"]) / df["observed"]
    df["diff"] = df["modeled"] - df["observed"]

    df.to_csv(
        r"outputs\validation\acs_commute_share_by_workplace_geog.csv", index=False
    )

    # Commute Mode Share by Home Tract
    df_model = pd.read_csv(r"outputs\agg\census\tour_dtract.csv")

    df_model[["to_tract", "td_tract"]] = df_model[["to_tract", "td_tract"]].astype(
        "str"
    )
    df_model["to_tract"] = df_model["to_tract"].apply(lambda row: row.split(".")[0])
    df_model["td_tract"] = df_model["td_tract"].apply(lambda row: row.split(".")[0])

    df_model = df_model[df_model["pdpurp"] == "Work"]
    df_model = (
        df_model.groupby(["to_tract", "tmodetp"]).sum()[["toexpfac"]].reset_index()
    )

    # # Group all HOV together
    df_model["mode"] = df_model["tmodetp"]
    df_model.loc[df_model["tmodetp"] == "HOV2", "mode"] = "HOV"
    df_model.loc[df_model["tmodetp"] == "HOV3+", "mode"] = "HOV"
    df_model = df_model.groupby(["to_tract", "mode"]).sum().reset_index()

    df_model["to_tract"] = df_model["to_tract"].astype("int64")
    df_model["modeled"] = df_model["toexpfac"]

    # Load the census data
    df_acs = pd.read_sql(
        "SELECT * FROM acs_commute_mode_home_tract WHERE year="
        + str(state.input_settings.base_year),
        con=state.conn,
    )

    # Select only tract records
    df_acs = df_acs[df_acs["place_type"] == "tr"]

    # Only include modes for people that travel to work (exclude telecommuters and others)
    mode_map = {
        "Drove Alone": "SOV",
        "Carpooled": "HOV",
        "Walked": "Walk",
        "Other": "Other",
        "Transit": "Transit",
    }

    df_acs["mode"] = df_acs["mode"].map(mode_map)
    df_acs = df_acs[-df_acs["mode"].isnull()]

    # Drop the Other mode for now
    df_acs = df_acs[df_acs["mode"] != "Other"]

    # Merge the model and observed data
    df = df_acs[["mode", "geoid", "place_name", "estimate"]].merge(
        df_model, left_on=["geoid", "mode"], right_on=["to_tract", "mode"]
    )
    df.rename(columns={"estimate": "observed", "trexpfac": "modeled"}, inplace=True)
    df[["observed", "modeled"]] = df[["observed", "modeled"]].astype("float")

    # Add geography columns based on tract
    parcel_geog = pd.read_sql(
        "SELECT * FROM parcel_" + str(state.input_settings.base_year) + "_geography", con=state.conn
    )

    tract_geog = (
        parcel_geog.groupby("Census2020Tract")
        .first()[
            [
                "CountyName",
                "rg_proposed",
                "CityName",
                "GrowthCenterName",
                "TAZ",
                "District",
            ]
        ]
        .reset_index()
    )
    tract_geog["Census2020Tract"] = (
        tract_geog["Census2020Tract"].replace("nan", -1).astype("int64")
    )
    # tract_geog['Census2020Tract'] = tract_geog['Census2020Tract'].replace('nan', -1)
    df = df.merge(tract_geog, left_on="geoid", right_on="Census2020Tract", how="left")
    df.to_csv(r"outputs\validation\acs_commute_share_by_home_tract.csv", index=False)

    # Copy select results to dash directory    # Copy existing CSV files for topsheet
    dash_table_list = [
        "daily_volume_county_facility",
        "external_volumes",
        "screenlines",
        "daily_volume",
        "daily_boardings_by_agency",
        "daily_boardings_key_routes",
        "light_rail_boardings",
    ]
    for fname in dash_table_list:
        shutil.copy(
            os.path.join(r"outputs/validation", fname + ".csv"), r"outputs/agg/dash"
        )


if __name__ == "__main__":
    main()
