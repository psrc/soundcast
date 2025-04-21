import pandas as pd
import numpy as np
import h5py
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "scripts"))
sys.path.append(os.path.join(os.getcwd(), "scripts/trucks"))
sys.path.append(os.getcwd())
# from scripts.emme_project import *


def network_importer(EmmeProject, state):
    for scenario in list(EmmeProject.bank.scenarios()):
        EmmeProject.bank.delete_scenario(scenario)
    # create scenario
    EmmeProject.bank.create_scenario(1002)
    EmmeProject.change_scenario()
    EmmeProject.delete_links()
    EmmeProject.delete_nodes()
    EmmeProject.process_modes("inputs/scenario/networks/modes.txt")
    EmmeProject.process_base_network(
        "inputs/scenario/networks/roadway/" + state.network_settings.truck_base_net_name
    )


def h5_to_data_frame(h5_file, group_name):
    col_dict = {}
    for col in h5_file[group_name].keys():
        my_array = np.asarray(h5_file[group_name][col])
        col_dict[col] = my_array
    return pd.DataFrame(col_dict)


def remove_employment_by_taz(df, taz_list, col_list):
    for taz in taz_list:
        for col in col_list:
            df.loc[df["taz_p"] == taz, col] = 0
    return df


def main(state):
    """
    Add internal-external (ix) and external-internal (xi) distribution for work purpose.
    Spatial distribution of work trips is based off observed LEHD LODES commute flows from/to PSRC region to/from surrounding counties.
    The distribution (share) of ixxi work trips is scaled up based on the shares calculated from this script.
    """

    # Load network for supplemental trip calculations
    my_project = state.main_project
    my_project.change_active_database("Supplementals")
    network_importer(my_project, state)

    # Load input data from DB and CSVs
    # conn = create_engine("sqlite:///inputs/db/" + state.input_settings.db_name)

    parcels_military = pd.read_sql(
        "SELECT * FROM enlisted_personnel WHERE year=="
        + state.input_settings.model_year,
        con=state.conn,
    )
    parcels_urbansim = pd.read_csv(
        "inputs/scenario/landuse/parcels_urbansim.txt", sep=" "
    )
    parcels_urbansim.index = parcels_urbansim["parcelid"]

    # Load time of day factors from inputs database
    tod_factors_df = pd.read_sql(f"SELECT * FROM time_of_day_factors WHERE model=='{state.input_settings.abm_model}'", con=state.conn)
    tod_factors_df = tod_factors_df.loc[tod_factors_df["mode"]=="sov"].copy()

    ########################################
    # Add military jobs to parcel employment
    ########################################

    # Take sum of jobs across parcels; take first value for the parcel's TAZ ID
    parcels_military = (
        parcels_military.groupby("ParcelID")
        .agg({"military_jobs": "sum", "Zone": "first"})
        .reset_index()
    )
    parcels_military.index = parcels_military["ParcelID"].astype("int")

    # Update parcels with enlisted jobs, for Government employment (empgov_p) category and Total employment (EMPTOT_P)
    parcels_urbansim["military_jobs"] = 0
    parcels_urbansim.update(parcels_military)

    for col in ["empgov_p", "emptot_p"]:
        parcels_urbansim[col] = (
            parcels_urbansim[col] + parcels_urbansim["military_jobs"]
        )

    # Log summary of jobs per TAZ added for verification
    parcels_urbansim[parcels_urbansim["military_jobs"] > 0].groupby("taz_p").sum()[
        ["military_jobs"]
    ].to_csv(r"outputs\supplemental\military_jobs_added.csv")

    # Drop military jobs column
    parcels_urbansim.drop("military_jobs", axis=1, inplace=True)

    #####################################################################################
    # Calculate Trip Distribution for Internal-External and External-Internal Work Trips
    #####################################################################################

    # Get Zone Index
    zonesDim = len(my_project.current_scenario.zone_numbers)
    zones = my_project.current_scenario.zone_numbers
    dictZoneLookup = dict((value, index) for index, value in enumerate(zones))

    # Load commute pattern data for workers in/out of PSRC region; keep only the needed columns
    # DB table "external_trip_distribution" generated from LEHD LODES data, 2014
    work = pd.read_sql("SELECT * FROM external_trip_distribution", con=state.conn)
    ixxi_cols = [
        "Total_IE",
        "Total_EI",
        "SOV_Veh_IE",
        "SOV_Veh_EI",
        "HOV2_Veh_IE",
        "HOV2_Veh_EI",
        "HOV3_Veh_IE",
        "HOV3_Veh_EI",
    ]
    work = work[["PSRC_TAZ", "External_Station"] + ixxi_cols]

    # Scale this based on forecasted employment growth between model and base year
    base_year_scaling = pd.read_sql("SELECT * FROM base_year_scaling", con=state.conn)

    # Base year employment
    base_year_totemp = base_year_scaling[
        (base_year_scaling["year"] == int(state.input_settings.base_year))
        & (base_year_scaling["field"] == "emptot_p")
    ]["value"].values[0]
    model_year_totemp = parcels_urbansim["emptot_p"].sum()
    emp_scaling = model_year_totemp / base_year_totemp
    # work[ixxi_cols] = work[ixxi_cols]*emp_scaling
    # externals_dont_grow=[3733]
    for col in work[ixxi_cols]:
        work[col] = np.where(
            (work["PSRC_TAZ"].isin(state.emme_settings.EXTERNALS_DONT_GROW))
            | (work["External_Station"].isin(state.emme_settings.EXTERNALS_DONT_GROW)),
            work[col],
            work[col] * emp_scaling,
        )

    # group trips by O-D TAZ's (trips from external stations to internal TAZs)
    w_grp = work.groupby(["PSRC_TAZ", "External_Station"]).sum()

    # FIXME: add some logging here to verify the results are as expected

    # Create empty numpy matrices for SOV, HOV2 and HOV3, populate with results
    w_SOV = np.zeros((zonesDim, zonesDim), np.float64)
    w_HOV2 = np.zeros((zonesDim, zonesDim), np.float16)
    w_HOV3 = np.zeros((zonesDim, zonesDim), np.float16)

    # Populate the numpy trips matrices; iterate through each internal TAZ (i) and External Station (j)
    for i in work["PSRC_TAZ"].value_counts().keys():
        for j in (
            work.groupby("PSRC_TAZ")
            .get_group(i)["External_Station"]
            .value_counts()
            .keys()
        ):  # all the external stations for each internal PSRC_TAZ
            # SOV
            w_SOV[dictZoneLookup[i], dictZoneLookup[j]] = w_grp.loc[
                (i, j), "SOV_Veh_IE"
            ]
            w_SOV[dictZoneLookup[j], dictZoneLookup[i]] = w_grp.loc[
                (i, j), "SOV_Veh_EI"
            ]
            # HOV2
            w_HOV2[dictZoneLookup[i], dictZoneLookup[j]] = w_grp.loc[
                (i, j), "HOV2_Veh_IE"
            ]
            w_HOV2[dictZoneLookup[j], dictZoneLookup[i]] = w_grp.loc[
                (i, j), "HOV2_Veh_EI"
            ]
            # HOV3
            w_HOV3[dictZoneLookup[i], dictZoneLookup[j]] = w_grp.loc[
                (i, j), "HOV3_Veh_IE"
            ]
            w_HOV3[dictZoneLookup[j], dictZoneLookup[i]] = w_grp.loc[
                (i, j), "HOV3_Veh_EI"
            ]
    # Get return trips (internal->external) by transposing external->internal trip table
    sov = w_SOV + w_SOV.transpose()
    hov2 = w_HOV2 + w_HOV2.transpose()
    hov3 = w_HOV3 + w_HOV3.transpose()

    matrix_dict = {"sov": sov, "hov2": hov2, "hov3": hov3}

    # Create h5 files for export
    if not os.path.exists("outputs/supplemental"):
        os.makedirs("outputs/supplemental")

    # Get time of day factors
    tod_factors_df.index = tod_factors_df.time_of_day
    tod_factors = tod_factors_df[['value']].to_dict()['value']

    for tod, factor in tod_factors.items():
        my_store = h5py.File(os.path.join("outputs/supplemental", f"external_work_{tod}.h5"), "w")
        for mode, matrix in matrix_dict.items():
            matrix = matrix * factor
            my_store.create_dataset(str(mode), data=matrix)
        my_store.close()

    ##################################################
    # Create "psrc_worker_ixxifractions" file
    # Update numworkers per TAZ
    ##################################################

    w_grp.reset_index(inplace=True)
    w_grp.reset_index(inplace=True)
    observed_ixxi = w_grp.groupby("PSRC_TAZ").sum()
    observed_ixxi = observed_ixxi.reindex(zones, fill_value=0)
    observed_ixxi.reset_index(inplace=True)

    # Remove jobs from JBLM Military zones so they are NOT available in Daysim choice models
    # These jobs are assumed "locked" and not available to civilian uses so are excluded from choice sets
    parcel_emp_cols = parcel_attributes = [
        "empmed_p",
        "empofc_p",
        "empedu_p",
        "empfoo_p",
        "empgov_p",
        "empind_p",
        "empsvc_p",
        "empoth_p",
        "emptot_p",
        "empret_p",
    ]
    parcels_urbansim = remove_employment_by_taz(
        parcels_urbansim, state.emme_settings.jblm_taz_list, parcel_emp_cols
    )
    hh_persons = h5py.File(r"inputs/scenario/landuse/hh_and_persons.h5", "r")
    parcel_grouped = parcels_urbansim.groupby("taz_p")
    emp_by_taz = pd.DataFrame(parcel_grouped["emptot_p"].sum())
    emp_by_taz.reset_index(inplace=True)

    # Update the total number of workers per TAZ to account for removed military jobs
    person_df = h5_to_data_frame(hh_persons, "Person")
    person_df = person_df.loc[(person_df.pwtyp > 0)]
    hh_df = h5_to_data_frame(hh_persons, "Household")
    merged = person_df.merge(hh_df, how="left", on="hhno")
    merged_grouped = merged.groupby("hhtaz")
    workers_by_taz = pd.DataFrame(merged_grouped["pno"].count())
    workers_by_taz.rename(columns={"pno": "workers"}, inplace=True)
    workers_by_taz.reset_index(inplace=True)

    # Calculate fraction of workers that do not work in the region, for each zone
    # Calculate fraction of jobs in each zone that are occupied by workers from external regions
    # These data are used to modify workplace location choices
    final_df = emp_by_taz.merge(
        workers_by_taz, how="left", left_on="taz_p", right_on="hhtaz"
    )
    final_df = observed_ixxi.merge(
        final_df, how="left", left_on="PSRC_TAZ", right_on="taz_p"
    )
    final_df["Worker_IXFrac"] = final_df.Total_IE / final_df.workers
    final_df["Jobs_XIFrac"] = final_df.Total_EI / final_df.emptot_p

    final_df.loc[final_df["Worker_IXFrac"] > 1, "Worker_IXFrac"] = 1
    final_df.loc[final_df["Jobs_XIFrac"] > 1, "Jobs_XIFrac"] = 1

    final_df = final_df.replace([np.inf, -np.inf], np.nan)
    final_df = final_df.fillna(0)
    final_cols = ["PSRC_TAZ", "Worker_IXFrac", "Jobs_XIFrac"]

    for col_name in final_df.columns:
        if col_name not in final_cols:
            final_df.drop(col_name, axis=1, inplace=True)
    final_df = final_df.round(3)

    final_df.to_csv(
        r"outputs/landuse/psrc_worker_ixxifractions.dat",
        sep="\t",
        index=False,
        header=False,
    )
    parcels_urbansim.to_csv(
        r"outputs/landuse/parcels_urbansim.txt", sep=" ", index=False
    )


if __name__ == "__main__":
    main()
