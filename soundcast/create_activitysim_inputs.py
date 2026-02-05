import pandas as pd
import numpy as np
import h5py
import os

# Supply a base
# land_use_dir = r"R:\e2projects_two\SoundCast\Inputs\dev\landuse\2018\new_emp"
parcel_area_file = r"R:\e2projects_two\activitysim\conversion\parcel_area.csv"
syn_hh_file = r"R:\e2projects_two\SyntheticPopulation_2018\keep\2018\populationsim_files\output\synthetic_households.csv"
seed_hh_file = r"R:\e2projects_two\SyntheticPopulation_2018\keep\2018\populationsim_files\data\seed_households.csv"
# seed_person_file = r"R:\e2projects_two\SyntheticPopulation_2018\keep\2018\populationsim_files\data\seed_persons.csv"
# parcel_block_file = r'R:\e2projects_two\activitysim\conversion\parcel_taz_block_lookup.csv'
parcel_block_file = r"R:\e2projects_two\activitysim\conversion\geographic_crosswalks\parcel_taz_block_lookup.csv"
# raw_parcel_file = r'R:\e2projects_two\SoundCast\Inputs\dev\landuse\2018\new_emp\parcels_urbansim.txt'
# buffered_parcel_path = r'R:\e2projects_two\activitysim\conversion\land_use\buffered_parcels.csv'
# buffered_parcel_path = r"L:\RTP_2022\final_runs\sc_rtp_2018_final\soundcast\outputs\landuse\buffered_parcels.txt"
# \\modelstation2\c$\Workspace\sc_2018_rtp_final\soundcast\outputs\landuse

# parcels_file =
# hh_persons_file = os.path.join(land_use_dir, "hh_and_persons.h5")


# transit score
transit_score_file = r"R:\e2projects_two\activitysim\inputs\data\psrc\two_zone_maz\transit_index\block_transit_score2018.csv"

##### Outputs
output_dir = r"C:\Stefan"

# zone_types = ['TAZ','MAZ','parcel']
zone_types = ["MAZ"]

# If true, create new persons.csv and households.csv; otherwise load existing files from the output directory
##run_hh = True
##run_person = True
run_hh = True
run_person = True
use_buffered_parcels = True

lu_aggregate_dict = {
    "hh_p": "sum",
    "emptot_p": "sum",
    "stugrd_p": "sum",
    "stuhgh_p": "sum",
    "stuuni_p": "sum",
    "empedu_p": "sum",  # educational: health, education, and recreational
    "empfoo_p": "sum",  # retail trade: retail trade
    "empgov_p": "sum",  # government: other employment
    "empind_p": "sum",  # industrial: manufacturing, wholesale trade, and transport
    "empmed_p": "sum",  # medical: health, educational, and recreational
    "empofc_p": "sum",  # other office: financial and professional services
    "empret_p": "sum",  # retail: retail
    "empsvc_p": "sum",  # other service: other employment
    "empoth_p": "sum",  # construction, mining, and other: natural resources
    "hh_1": "mean",
    "hh_2": "mean",
    "emptot_1": "mean",
    "emptot_2": "mean",
    "empret_1": "mean",
    "empsvc_1": "mean",
    # "sfunits": "sum",
    # "mfunits": "sum",
    "TAZ": "first",
}

lu_rename_dict = {
    "hh_p": "TOTHH",
    "emptot_p": "TOTEMP",
    "stuhgh_p": "HSENROLL",
    "stuuni_p": "COLLFTE",
    "empedu_p": "HEREMPN",  # educational: health, education, and recreational
    "empfoo_p": "RETEMPN",  # retail trade: retail trade
    "empgov_p": "OTHEMPN",  # government: other employment
    "empind_p": "MWTEMPN",  # industrial: manufacturing, wholesale trade, and transport
    "empmed_p": "HEREMPN",  # medical: health, educational, and recreational
    "empofc_p": "FPSEMPN",  # other office: financial and professional services
    "empret_p": "RETEMPN",  # retail: retail
    "empsvc_p": "OTHEMPN",  # other service: other employment
    "empoth_p": "AGREMPN",  # construction, mining, and other: natural resources
}


def write_csv(df, control_df, output_dir, fname, additional_cols=[]):
    """Write modified dataframe to file using existing file columns as template."""

    # Find common set of columns
    df = df.loc[:, ~df.columns.duplicated()]
    df = df[list(np.intersect1d(control_df.columns, df.columns)) + additional_cols]

    # For missing columns, populate with -1
    for col in control_df.columns:
        if col not in df.columns:
            df[col] = -1

    # Make sure data types are consistent between two data sets
    for col in df.columns:
        if col not in additional_cols:
            if df[col].dtype != control_df[col].dtype:
                print(col)
                try:
                    df[col] = df[col].fillna(-1)
                except:
                    print("")
                df[col] = df[col].astype(control_df[col].dtype)

    df.to_csv(os.path.join(output_dir, fname), index=False)

    return df


def log2(df, col1, col2, min):
    total = df[col1] + df[col2]
    return np.where(
        ((df[col1] > min) & (df[col2] > min)),
        -1
        * (
            df[col1] / total * np.log(df[col1] / total)
            + df[col2] / total * np.log(df[col2] / total)
        )
        / np.log(2),
        0,
    )
    # 1 * (df[col1] / total * np.log1p(df[col1]/total) + df[col2]/total * np.log1p(df[col2]/total)) / np.log1p(2)
    # df['color'] = np.where(((df[col1] > min) & ((df[col2] > min)), 1 * (df[col1] / total * np.log1p(df[col1]/total) + df[col2]/total * np.log1p(df[col2]/total)) / np.log1p(2), 0)


def log3(df, col1, col2, col3, min):
    total = df[col1] + df[col2] + df[col3]
    return np.where(
        ((df[col1] > min) & (df[col2] > min) & (df[col3] > min)),
        -1
        * (
            df[col1] / total * np.log(df[col1] / total)
            + df[col2] / total * np.log(df[col2] / total)
            + df[col3] / total * np.log(df[col3] / total)
        )
        / np.log(3),
        0,
    )


def log4(df, col1, col2, col3, col4, min):
    total = df[col1] + df[col2] + df[col3] + df[col4]
    return np.where(
        ((df[col1] > min) & (df[col2] > min)),
        -1
        * (
            df[col1] / total * np.log(df[col1] / total)
            + df[col2] / total * np.log(df[col2] / total)
        )
        / np.log(4),
        0,
    )


def process_households(state):
    """Convert Daysim-formatted household data to Activitysim format at the MAZ level.
    """

    # Load MTC example as a data format template
    # df_mtc = pd.read_csv(
    #     "https://raw.githubusercontent.com/ActivitySim/activitysim/master/activitysim/examples/example_mtc/data/households.csv",
    #     nrows=10,
    # )
    # syn_hh = pd.read_csv(syn_hh_file)
    # seed_hh = pd.read_csv(
    #     seed_hh_file
    # )  # Some columns not available form synthetic files can be retrieved from the seed files used to build the synthetic households
    # seed_persons = pd.read_csv(seed_person_file)
    parcel_block = pd.read_csv(parcel_block_file)

    # raw_parcels_df = pd.read_csv(
    #     "outputs/landuse/parcels_urbansim.txt", sep=" "
    # )
    # raw_parcels_df = raw_parcels_df[["parcelid", "sfunits", "mfunits"]]

    hh_persons = h5py.File("inputs/scenario/landuse/hh_and_persons.h5", "r")
    df_psrc = pd.DataFrame()
    for col in hh_persons["Household"].keys():
        df_psrc[col] = hh_persons["Household"][col][:]

    df_psrc_person = pd.DataFrame()
    for col in hh_persons["Person"].keys():
        df_psrc_person[col] = hh_persons["Person"][col][:]
    hh_persons.close()

    # df_psrc = df_psrc.merge(raw_parcels_df, left_on="hhparcel", right_on="parcelid")
    # df_psrc["is_mf"] = np.where(df_psrc["mfunits"] > 0, 1, 0)

    # Join seed data to synthetic population based on the hhnum field
    # df_psrc = df_psrc.merge(
    #     syn_hh[["household_id", "hh_id"]], left_on="hhno", right_on="household_id"
    # )
    # # There are multiple instances of hhnum in the seed_hh
    # df_psrc = df_psrc.merge(seed_hh, left_on="hh_id", right_on="hhnum", how="left")

    df_psrc.rename(
        columns={
            "hhtaz": "TAZ",
            "hhincome": "income",
            "hhsize": "PERSONS",
            # "VEH": "VEHICL",
            # "TYPE": "UNITTYPE",
            # "BLD": "BLDGSZ",
            # "PUMA": "PUMA5",
            # "TEN": "TENURE",
            # "WIF": "hwrkrcat",
        },
        inplace=True,
    )
    df_psrc["HHID"] = df_psrc["hhno"].copy()

    # Household income categorization, coarse (1-4) and detailed (1-9)
    df_psrc["income"] = np.where(df_psrc["income"] < 0, 0, df_psrc["income"])
    # df_psrc["hinccat1"] = pd.cut(
    #     df_psrc["income"],
    #     [-1, 20000, 50000, 100000, 99999999999999],
    #     labels=[1, 2, 3, 4],
    # )

    # df_psrc["hinccat2"] = pd.cut(
    #     df_psrc["income"],
    #     [-1, 10000, 20000, 30000, 40000, 50000, 60000, 75000, 100000, 99999999999999],
    #     labels=[1, 2, 3, 4, 5, 6, 7, 8, 9],
    # )

    # Workers
    _df = (
        df_psrc_person[df_psrc_person["pwtyp"] > 0]
        .groupby("hhno")
        .count()[["psexpfac"]]
        .reset_index()
    )
    _df.rename(columns={"psexpfac": "workers"}, inplace=True)
    df_psrc = df_psrc.merge(_df, on="hhno", how="left")
    df_psrc["workers"].fillna(0, inplace=True)

    # # Houeshold size category, 1, 2, 3, 4+
    # df_psrc["hsizecat"] = df_psrc["PERSONS"].copy()
    # df_psrc.loc[df_psrc["hsizecat"] >= 4, "hsizecat"] = 4

    # # From person seed (PUMS) data
    # # hunittype
    # df_psrc["hunittype"] = df_psrc["UNITTYPE"].copy()

    # # hNOCcat (number of children category)
    # df_psrc["hNOCcat"] = 0
    # df_psrc.loc[df_psrc["NOC"] >= 1, "hhNOCcat"] = 1

    # # Age category
    # age_cols = [
    #     "h004",
    #     "h0511",
    #     "h1215",
    #     "h1617",
    #     "h1824",
    #     "h2534",
    #     "h3549",
    #     "h5064",
    #     "h6579",
    #     "h80up",
    # ]
    # df_psrc_person["age_category"] = pd.cut(
    #     df_psrc_person["pagey"],
    #     [-1, 4, 11, 15, 17, 24, 34, 49, 64, 79, 999],
    #     labels=age_cols,
    # )

    # df = df_psrc_person.groupby(["hhno", "age_category"]).size().reset_index()
    # for age_category in age_cols:
    #     _df = df.loc[df["age_category"] == age_category]
    #     df_psrc = df_psrc.merge(_df[["hhno", 0]], on="hhno", how="left")
    #     df_psrc[0] = df_psrc[0].fillna(0).astype("int")
    #     df_psrc.rename(columns={0: age_category}, inplace=True)

    # # Employment type
    # df_psrc_person["mtc_worker_type"] = df_psrc_person["pptyp"].copy()
    # df_psrc_person["mtc_worker_type"] = df_psrc_person["mtc_worker_type"].map(
    #     {
    #         1: "hwork_f",
    #         2: "hwork_p",
    #         5: "huniv",
    #         4: "hnwork",
    #         3: "hretire",
    #         8: "hpresch",
    #         7: "hschpred",
    #         6: "hschdriv",
    #     }
    # )

    # df = df_psrc_person.groupby(["hhno", "mtc_worker_type"]).size().reset_index()
    # mtc_worker_cats = [
    #     "hwork_f",
    #     "hwork_p",
    #     "huniv",
    #     "hnwork",
    #     "hretire",
    #     "hrpresch",
    #     "hschpred",
    #     "hschdriv",
    # ]

    # for worker_cat in mtc_worker_cats:
    #     _df = df.loc[df["mtc_worker_type"] == worker_cat]
    #     df_psrc = df_psrc.merge(_df[["hhno", 0]], how="left", on="hhno")
    #     df_psrc[0] = df_psrc[0].fillna(0).astype("int")
    #     df_psrc.rename(columns={0: age_category}, inplace=True)

    # # Home dwelling type (1 SFH detached, 2 duplex or apt, 3 mobile home etc)
    # df_psrc.loc[df_psrc["BLDGSZ"].isin([2, 3]), "htypdwel"] = 1
    # df_psrc.loc[df_psrc["BLDGSZ"].isin([4, 5, 6, 7, 8, 9]), "htypdwel"] = 2
    # df_psrc.loc[
    #     df_psrc["BLDGSZ"].isin([0, 1, 10]), "htypdwel"
    # ] = 3  # classify 0 values here

    # # student nonworker
    # df_psrc_person["hadnwst"] = 0
    # df_psrc_person.loc[
    #     (df_psrc_person["pstyp"] > 0) & (df_psrc_person["pwtyp"] == 0), "hadnwst"
    # ] = 1
    # # student worker
    # df_psrc_person["hadwpst"] = 0
    # df_psrc_person.loc[
    #     (df_psrc_person["pstyp"] > 0) & (df_psrc_person["pwtyp"] > 0), "hadwpst"
    # ] = 1

    # df = df_psrc_person.groupby("hhno").sum()[["hadwpst"]].reset_index()
    # df.loc[df["hadwpst"] > 0, "hadwpst"] = 1
    # df_psrc = df_psrc.merge(df[["hhno", "hadwpst"]], how="left", on="hhno")

    # df = df_psrc_person.groupby("hhno").sum()[["hadnwst"]].reset_index()
    # df.loc[df["hadnwst"] > 0, "hadnwst"] = 1
    # df_psrc = df_psrc.merge(df[["hhno", "hadnwst"]], how="left", on="hhno")

    # # hadkids
    # ###### FIXME###########
    # # Set to 0 for now
    # df_psrc["hadkids"] = 0

    # # bucketBin
    # df_psrc["bucketBin"] = 1

    # # originalPUMA
    # df_psrc["orginalPUMA"] = df_psrc["PUMA5"].copy()

    # # hmultiunit
    # df_psrc["hmultiunit"] = 1
    # df_psrc.loc[df_psrc["htypdwel"] == 1, "hmultiunit"] = 0

    # Use maz_id as the MAZ definition
    parcel_block = parcel_block[-parcel_block["maz_id"].isnull()]
    parcel_block["maz_id"] = parcel_block["maz_id"].astype("int")
    df_psrc = df_psrc.merge(
        parcel_block, left_on="hhparcel", right_on="parcel_id", how="left"
    )
    df_psrc.rename(columns={"maz_id": "MAZ"}, inplace=True)
    # df = write_csv(
    #     df_psrc,
    #     df_mtc,
    #     os.path.join(output_dir, "MAZ"),
    #     "households.csv",
    #     additional_cols=["MAZ", "is_mf"],
    # )
    

    return df_psrc, df_psrc_person


def process_persons(df_psrc_person):
    """Convert Daysim-formatted data to MTC TM1 format for activitysim."""

    # df_mtc_persons = pd.read_csv(
    #     "https://raw.githubusercontent.com/ActivitySim/activitysim/master/activitysim/examples/example_mtc/data/persons.csv",
    #     nrows=10,
    # )

    df_psrc_person["HHID"] = df_psrc_person["hhno"].copy()
    df_psrc_person["household_id"] = df_psrc_person["hhno"].copy()
    df_psrc_person["age"] = df_psrc_person["pagey"].copy()
    df_psrc_person["sex"] = df_psrc_person["pgend"].copy()

    # worker type
    df_psrc_person.loc[df_psrc_person["pwtyp"] == 1, "pemploy"] = 1
    df_psrc_person.loc[df_psrc_person["pwtyp"] == 2, "pemploy"] = 2
    df_psrc_person.loc[df_psrc_person["pwtyp"] == 0, "pemploy"] = 3
    df_psrc_person.loc[df_psrc_person["age"] < 16, "pemploy"] = 4
    df_psrc_person["pemploy"] = df_psrc_person["pemploy"].astype("int")

    # student type
    df_psrc_person["pstudent"] = 3
    df_psrc_person.loc[df_psrc_person["pptyp"].isin([7, 6]), "pstudent"] = 1
    df_psrc_person.loc[df_psrc_person["pptyp"] == 5, "pstudent"] = 2

    # person type
    df_psrc_person["ptype"] = df_psrc_person["pptyp"]
    df_psrc_person.loc[df_psrc_person["pptyp"] == 3, "ptype"] = 5
    df_psrc_person.loc[df_psrc_person["pptyp"] == 5, "ptype"] = 3
    df_psrc_person["PNUM"] = df_psrc_person["pno"]
    df_psrc_person["PERID"] = range(len(df_psrc_person))

    # df = write_csv(
    #     df_psrc_person,
    #     df_mtc_persons,
    #     os.path.join(output_dir, zone_type),
    #     "persons.csv",
    # )

    return df_psrc_person


def process_buffered_landuse(df_psrc, aggregate_dict):
    """
    Generate MAZ-level land use and synthetic population data for Activitysim.
    """

    # mtc_lu_path = "https://raw.githubusercontent.com/ActivitySim/activitysim/master/activitysim/examples/example_mtc/data/land_use.csv"
    # df_parcel_path = r'R:\e2projects_two\SoundCast\Inputs\dev\landuse\2018\vers2_july2020\parcels_urbansim.txt'
    # df_parcel_path = r'L:\RTP_2022\soundcast_rtp2050_tests_BASE\outputs\landuse\buffered_parcels.txt'
    # df_parcel_path = r'C:\Stefan\scratch\buffered_parcels.csv'

    # df_mtc_lu = pd.read_csv(mtc_lu_path)
    df_parcel = pd.read_csv("outputs/landuse/buffered_parcels.txt", sep=" ")
    df_parcel.rename(columns={"taz_p": "TAZ"}, inplace=True)

    # Load block to parcel lookup and join to parcels
    parcel_block = pd.read_csv(parcel_block_file)
    df_parcel = df_parcel.merge(
        parcel_block, left_on="parcelid", right_on="parcel_id", how="left"
    )
    df_parcel.rename(columns={"maz_id": "MAZ"}, inplace=True)

    ## FIXME!!!!!!!!!!!!!!!
    # DROP ANY PARCELS MISSING MAZs. 
    # We should fix this or check that its correct
    df_parcel = df_parcel[~df_parcel.MAZ.isnull()]

    assert df_parcel.MAZ.isnull().values.any() == False

    # units_df = df_psrc.groupby("parcel_id", as_index=False).agg(
    #     {"mfunits": sum, "sfunits": sum}
    # )
    # df_parcel = df_parcel.merge(units_df, how="left", on="parcel_id")
    df_lu = df_parcel.groupby("MAZ", as_index=False).agg(aggregate_dict)
    df_lu = df_lu.reset_index()

    df_lu.rename(
        columns={
            "hh_p": "TOTHH",
            "emptot_p": "TOTEMP",
            "stugrd_p": "GSENROLL",
            "stuhgh_p": "HSENROLL",
            "stuuni_p": "COLLFTE",
            "empedu_p": "HEREMPN",  # educational: health, education, and recreational
            "empfoo_p": "RETEMPN",  # retail trade: retail trade
            "empgov_p": "OTHEMPN",  # government: other employment
            "empind_p": "MWTEMPN",  # industrial: manufacturing, wholesale trade, and transport
            "empmed_p": "HEREMPN",  # medical: health, educational, and recreational
            "empofc_p": "FPSEMPN",  # other office: financial and professional services
            "empret_p": "RETEMPN",  # retail: retail
            "empsvc_p": "OTHEMPN",  # other service: other employment
            "empoth_p": "AGREMPN",  # construction, mining, and other: natural resources
        },
        inplace=True,
    )
    df_lu = df_lu.reset_index()

    # empoth	(construction, ag, mining, and any other):	AGREMPN	ag, natural resources

    # df_lu['ZONE'] = df_lu['TAZ']    # retain ZONE in addition to any other geographies

    # FIXME: assert all college students are full-time for now...
    # No data on this in parcels
    df_lu["COLLPTE"] = 0

    # Total population by TAZ
    df = df_psrc.groupby("MAZ").sum()["PERSONS"].reset_index()
    df.rename(columns={"PERSONS": "TOTPOP"}, inplace=True)
    df_lu = df_lu.merge(df, on="MAZ", how="left")  # Retain all zones with left join
    # df_lu["HHPOP"] = df_lu["TOTPOP"].copy()

    # # MPRES
    # # employed residents
    # df_psrc_person["household_id"] = df_psrc_person["household_id"].copy()
    # df_psrc_person["EMPRES"] = 0
    # df_psrc_person.loc[df_psrc_person["pemploy"].isin([1, 2]), "EMPRES"] = 1

    # df = df_psrc_person.groupby("household_id").sum()[["EMPRES"]].reset_index()
    # df_psrc = df_psrc.merge(df, left_on="HHID", right_on="household_id")
    # df_lu = df_lu.merge(
    #     df_psrc.groupby("MAZ").sum()[["EMPRES"]].reset_index(),
    #     on="MAZ",
    #     how="left",
    # )

    # # SFDU (single family dwelling units, not used)
    # df_lu["SFDU"] = -1
    # df_lu["MFDU"] = -1

    # # Households in the lowest income quartile (less than $30,000 annually in $2000)
    # for colname in ["HHINCQ1", "HHINCQ2", "HHINCQ3", "HHINCQ4"]:
    #     df_psrc[colname] = 0

    # df_psrc.loc[df_psrc["income"] < 30000, "HHINCQ1"] = 1
    # df_psrc.loc[
    #     (df_psrc["income"] >= 30000) & (df_psrc["income"] < 60000), "HHINCQ2"
    # ] = 1
    # df_psrc.loc[
    #     (df_psrc["income"] >= 60000) & (df_psrc["income"] < 100000), "HHINCQ3"
    # ] = 1
    # df_psrc.loc[df_psrc["income"] >= 100000, "HHINCQ4"] = 1

    # df = (
    #     df_psrc.groupby("MAZ")
    #     .sum()[["HHINCQ1", "HHINCQ2", "HHINCQ3", "HHINCQ4"]]
    #     .reset_index()
    # )
    # df_lu = df_lu.merge(df, on="MAZ", how="left")

    # Total acres, based on parcel size
    df_parcel_area = pd.read_csv(parcel_area_file)
    # df_parcel_area['parcel_id'] = df_parcel_area['pin'].astype(int)
    df_parcel = df_parcel.merge(df_parcel_area, how="left", on="parcel_id")
    df_parcel["area"].fillna(0, inplace=True)
    df_parcel["area"] = np.where(
        df_parcel["area"] < 1, df_parcel["area"].mean(), df_parcel["area"]
    )

    # df = (df_parcel.groupby("MAZ").sum()[['sqft_p']]/43560).reset_index()
    df = (df_parcel.groupby("MAZ").sum()[["area"]] / 43560).reset_index()
    df.rename(columns={"area": "TOTACRE"}, inplace=True)
    df_lu = df_lu.merge(df, on="MAZ", how="left")

    # Some TAZs have 0 TOTACRE fields.
    # Popuilate with regional average
    df_lu.loc[df_lu["TOTACRE"] == 0, "TOTACRE"] = df_lu.TOTACRE.mean()

    # # Acreage occupied by residential development;
    # df_lu["RESACRE"] = df_lu["TOTACRE"] * (
    #     df_lu["TOTPOP"] / (df_lu["TOTPOP"] + df_lu["TOTEMP"])
    # )
    # df_lu.loc[df_lu["TOTPOP"].isnull(), "RESACRE"] = df_lu["TOTACRE"] / 2.0

    # # commercial acreage
    # df_lu["CIACRE"] = df_lu["TOTACRE"] * (
    #     df_lu["TOTEMP"] / (df_lu["TOTPOP"] + df_lu["TOTEMP"])
    # )
    # df_lu.loc[df_lu["TOTPOP"].isnull(), "CIACRE"] = df_lu["TOTACRE"] / 2.0

    # Calculate density index as a check; should not be null
    df_lu["household_density"] = df_lu.TOTHH / df_lu.TOTACRE
    df_lu["employment_density"] = df_lu.TOTEMP / (df_lu.TOTACRE)

    df_lu["density_index"] = (df_lu.household_density * df_lu.employment_density) / (
        df_lu.household_density + df_lu.employment_density
    ).clip(lower=1)
    df_lu["density_index"] = df_lu["density_index"].replace(np.nan, 0)
    df_lu["buff_density_index"] = (df_lu.hh_1 * df_lu.emptot_1) / (
        df_lu.hh_1 + df_lu.emptot_1
    ).clip(lower=1)
    df_lu["buff_density_index"] = df_lu["buff_density_index"].replace(np.nan, 0)
    # df_lu['household_density'] = df_lu.TOTHH / (df_lu.RESACRE + df_lu.CIACRE)
    # df_lu['employment_density'] = df_lu.TOTEMP / (df_lu.RESACRE + df_lu.CIACRE)
    # df_lu['density_index'] = (df_lu['household_density'] *df_lu['employment_density']) / (df_lu['household_density'] + df_lu['employment_density']).clip(lower=1)

    # # Share of population 62 or older
    # df_psrc_person.loc[df_psrc_person["age"] >= 62, "SHPOP62P"] = 1
    # df = (
    #     df_psrc_person.groupby("household_id").sum()["SHPOP62P"].fillna(0).reset_index()
    # )
    # df_psrc = df_psrc.merge(df, left_on="HHID", right_on="household_id")
    # df = df_psrc.groupby("MAZ").sum()["SHPOP62P"].reset_index()
    # df_lu = df_lu.merge(df, on="MAZ", how="left")
    # df_lu["SHPOP62P"] = df_lu["SHPOP62P"] / df_lu["TOTPOP"]
    # df_lu["SHPOP62P"] = df_lu["SHPOP62P"].fillna(0)

    # # Age categories
    # df_psrc_person.loc[df_psrc_person["age"] < 5, "AGE0004"] = 1
    # df_psrc_person.loc[
    #     (df_psrc_person["age"] >= 5) & (df_psrc_person["age"] < 20), "AGE0519"
    # ] = 1
    # df_psrc_person.loc[
    #     (df_psrc_person["age"] >= 20) & (df_psrc_person["age"] < 45), "AGE2044"
    # ] = 1
    # df_psrc_person.loc[
    #     (df_psrc_person["age"] >= 45) & (df_psrc_person["age"] < 65), "AGE4564"
    # ] = 1
    # df_psrc_person.loc[df_psrc_person["age"] >= 65, "AGE65P"] = 1

    # for colname in ["AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P"]:
    #     df = (
    #         df_psrc_person.groupby("household_id")
    #         .sum()[colname]
    #         .fillna(0)
    #         .reset_index()
    #     )
    #     df_psrc = df_psrc.merge(df, left_on="HHID", right_on="household_id")
    #     df = df_psrc.groupby("MAZ").sum()[colname].reset_index()
    #     df_lu = df_lu.merge(df, on="MAZ", how="left")

    # PRKCST Hourly parking rate paid by long-term hours (8 hours)
    # Take the average for all parcels (weighted by number of spaces)
    df_parcel["weighted_daily_price"] = df_parcel["parkdy_p"] * df_parcel["ppricdyp"]
    df = (
        df_parcel.groupby("MAZ").sum()["weighted_daily_price"]
        / df_parcel.groupby("MAZ").sum()["parkdy_p"]
    )

    # Convert the daily total rate to hourly assuming 8 hours
    df = df / 8
    df = pd.DataFrame(df, columns=["PRKCST"]).reset_index().fillna(0)

    df_lu = df_lu.merge(df, on="MAZ", how="left")

    # OPRKCST Hourly parking rate paid by short-term parkers
    df_parcel["weighted_hourly_price"] = df_parcel["parkhr_p"] * df_parcel["pprichrp"]
    df = (
        df_parcel.groupby("MAZ").sum()["weighted_hourly_price"]
        / df_parcel.groupby("MAZ").sum()["parkhr_p"]
    )

    # Convert the daily total rate to hourly assuming 8 hours
    df = df / 8
    df = pd.DataFrame(df, columns=["OPRKCST"]).reset_index().fillna(0)

    df_lu = df_lu.merge(df, on="MAZ", how="left")

    # Distance to transit
    # Get average
    df_parcel['access_dist_transit'] = df_parcel['raw_dist_transit'].copy()
    df = df_parcel.groupby("MAZ")["access_dist_transit"].mean()
    df = df.reset_index()

    # recode greater than 5 miles to 0, which means no access to transit in ActivitySim
    df["access_dist_transit"] = np.where(
        df["access_dist_transit"] > 5, 0, df["access_dist_transit"]
    )
    df = df[["MAZ", "access_dist_transit"]]

    df_lu = df_lu.merge(df, on="MAZ", how="left")

    df_lu["density"] = (df_lu.TOTPOP + (2.5 * df_lu.TOTEMP)) / df_lu.TOTACRE
    # Fill zones with no residents/employment as 0
    df_lu["density"] = df_lu["density"].fillna(0)
    df_lu["area_type"] = pd.cut(
        df_lu.density, bins=[-1, 6, 30, 55, 100, 300, np.inf], labels=[5, 4, 3, 2, 1, 0]
    )

    # TERMINAL
    # get terminal times from file
    # df_tt = pd.read_csv(
    #     r"https://raw.githubusercontent.com/psrc/soundcast/dev/inputs/model/intrazonals/destination_tt.in",
    #     delim_whitespace=True,
    #     skiprows=4,
    # )
    df_tt = pd.read_csv(
        "inputs/model/activitysim/intrazonals/destination_tt.in", delim_whitespace=True, skiprows=4
    )

    df_tt.columns = ["taz_p", "TERMINAL"]
    df_tt["taz_p"] = df_tt["taz_p"].apply(lambda i: i.split(":")[0]).astype("int")
    df_lu = df_lu.merge(df_tt, left_on="TAZ", right_on="taz_p", how="left")

    # # TOPOLOGY
    # df_lu["TOPOLOGY"] = 1

    # # ZERO placeholder
    # df_lu["ZERO"] = 0

    # df_lu["SFTAZ"] = df_lu["TAZ"]

    # # Group quarters population
    # df_lu["GQPOP"] = 0

    # Add a county lookup
    ## FIXME: get this from soundcast input db
    #######################
    taz_geog = pd.read_csv(
        r"R:\e2projects_two\SoundCast\Inputs\db_inputs\taz_geography.csv"
    )
    # df_lu.columns
    # taz_geog.columns
    df_lu = df_lu.merge(
        taz_geog[["taz", "geog_name"]], left_on="TAZ", right_on="taz", how="left"
    )

    county_map = {
        "King County": 1,
        "Kitsap County": 2,
        "Pierce County": 3,
        "Snohomish County": 4,
    }
    df_lu["COUNTY"] = df_lu["geog_name"].map(county_map)

    # mixed use variable from buffered parcels:
    df_lu["mixed_use2_1"] = log2(df_lu, "hh_1", "emptot_1", 0.0001)
    df_lu["mixed_use2_2"] = log2(df_lu, "hh_2", "emptot_2", 0.0001)
    df_lu["mixed_use3_1"] = log3(df_lu, "hh_1", "empret_1", "empsvc_1", 0.0001)
    # df_lu['mixed_use2_maz'] = log2(df_lu, 'TOTHH', 'TOTEMP')

    # # transit index
    # transit_index_df = pd.read_csv(transit_score_file)
    # df_lu = df_lu.merge(transit_index_df, on="MAZ", how="left")
    # df_lu["transit_score"] = df_lu["score"]
    # df_lu["transit_score_scaled"] = df_lu["scaled_score"]

    # # sf and mf units:
    # total = df_lu["sfunits"] + df_lu["mfunits"]
    # df_lu["percent_mf"] = np.where(total > 0, df_lu["mfunits"] / total, 0)

    # for col in df_mtc_lu.columns:
    #     if col not in df_lu.columns:
    #         print("Missing col %s, setting to -1" % (col))
    #         df_lu[col] = -1
    df_lu["TAZ"] = df_lu["taz"]
    df_lu["zone_id"] = df_lu["taz"]

    # # if zone_type == "MAZ":
    # additional_cols = [
    #     "MAZ",
    #     "GSENROLL",
    #     "transit_score",
    #     "transit_score_scaled",
    #     "sfunits",
    #     "mfunits",
    #     "percent_mf",
    #     "mixed_use2_1",
    #     "density_index",
    #     "buff_density_index",
    #     "density",
    #     "mixed_use3_1",
    #     "hh_1",
    #     "emptot_1",
    #     "hh_2",
    #     "emptot_2",
    #     "access_dist_transit",
    # ]
    # create the MAZ and TAZ lookup files
    df_lu[["MAZ", "TAZ"]] = df_lu[["MAZ", "TAZ"]].astype("int")
    # df_lu[["MAZ", "TAZ"]].to_csv(
    #     os.path.join(output_dir, zone_type, "maz.csv"), index=False
    # )

    # Do some other clean up
    cols = [
        # "AGE0004",
        # "AGE0519",
        # "AGE2044",
        # "AGE4564",
        # "AGE65P",
        # "HHINCQ1",
        # "HHINCQ2",
        # "HHINCQ3",
        # "HHINCQ4",
        # "HHPOP",
        "TOTPOP",
        # "transit_score",
        # "transit_score_scaled",
        "access_dist_transit",
    ]
    df_lu[cols] = df_lu[cols].fillna(0)
    ### FIXME: do we actually need to replace with -1?
    df_lu[cols] = df_lu[cols].replace(-1, 0)

    return df_lu

def run(state):
    # pass

    df_hh, df_person = process_households(state)
    df_person = process_persons(df_person)
    df_lu = process_buffered_landuse(
            df_hh, lu_aggregate_dict
        )
    
    df_maz = df_lu[["MAZ", "TAZ"]]

    # Write TAZ file based on MAZ file