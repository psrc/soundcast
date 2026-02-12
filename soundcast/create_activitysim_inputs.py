import pandas as pd
import numpy as np
import h5py
import os

from sqlalchemy import Join
from settings import run_args

# Supply a base
# land_use_dir = r"R:\e2projects_two\SoundCast\Inputs\dev\landuse\2018\new_emp"
parcel_area_file = r"R:\e2projects_two\activitysim\conversion\parcel_area.csv"

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
    "COUNTY": "first"     # FIXME: use mode for this?
}

def integerize_id_columns(df, table_name):
    columns = ['MAZ', 'OMAZ', 'DMAZ', 'TAZ', 'zone_id', 'household_id', 'HHID']
    for c in df.columns:
        if c in columns:
            print(f"converting {table_name}.{c} to int")
            if df[c].isnull().any():
                print(df[c][df[c].isnull()])
            df[c] = df[c].astype(int)

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
                except Exception:
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


def process_households(parcel_geog):
    """Convert Daysim-formatted household data to Activitysim format at the MAZ level.
    """

    hh_persons = h5py.File("inputs/scenario/landuse/hh_and_persons.h5", "r")
    df_psrc = pd.DataFrame()
    for col in hh_persons["Household"].keys():
        df_psrc[col] = hh_persons["Household"][col][:]

    df_psrc_person = pd.DataFrame()
    for col in hh_persons["Person"].keys():
        df_psrc_person[col] = hh_persons["Person"][col][:]
    hh_persons.close()

    df_psrc.rename(
        columns={
            "hhno": "household_id",
            "hhtaz": "TAZ",
            "hhincome": "income",
            # "hhsize": "PERSONS",
        },
        inplace=True,
    )

    df_psrc_person.rename(
        columns={
            "hhno": "household_id"
        },
        inplace=True
    )

    # FIXME: REMOVE from models
    df_psrc["HHT"] = 1
    # df_psrc["HHID"] = df_psrc["hhno"].copy()

    # Household income 
    df_psrc["income"] = np.where(df_psrc["income"] < 0, 0, df_psrc["income"])

    # Workers
    _df = (
        df_psrc_person[df_psrc_person["pwtyp"] > 0]
        .groupby("household_id")
        .count()[["psexpfac"]]
        .reset_index()
    )
    _df.rename(columns={"psexpfac": "num_workers"}, inplace=True)
    df_psrc = df_psrc.merge(_df, on="household_id", how="left")
    df_psrc["num_workers"] = df_psrc["num_workers"].fillna(0).astype("int")

    # Get MAZ from hhparcel
    df_psrc = df_psrc.merge(parcel_geog[["ParcelID", "maz_id"]], left_on="hhparcel", right_on="ParcelID", how="left")
    df_psrc.rename(columns={"maz_id": "home_zone_id"}, inplace=True)

    hh_col_list = ["household_id", "home_zone_id", "income", "hhsize", "num_workers", "HHT"]
    df_psrc = df_psrc[hh_col_list]
    
    return df_psrc, df_psrc_person


def process_persons(df):
    """Convert Daysim-formatted data to MTC TM1 format for activitysim."""

    df["age"] = df["pagey"].copy()
    df["sex"] = df["pgend"].copy()

    # worker type
    df.loc[df["pwtyp"] == 1, "pemploy"] = 1
    df.loc[df["pwtyp"] == 2, "pemploy"] = 2
    df.loc[df["pwtyp"] == 0, "pemploy"] = 3
    df.loc[df["age"] < 16, "pemploy"] = 4
    df["pemploy"] = df["pemploy"].astype("int")

    # student type
    df["pstudent"] = 3
    df.loc[df["pptyp"].isin([7, 6]), "pstudent"] = 1
    df.loc[df["pptyp"] == 5, "pstudent"] = 2

    # person type
    df["ptype"] = df["pptyp"]
    df.loc[df["pptyp"] == 3, "ptype"] = 5
    df.loc[df["pptyp"] == 5, "ptype"] = 3
    df["PNUM"] = df["pno"]
    df["person_id"] = range(len(df))

    person_col_list = ["person_id","household_id", "age", "sex", "PNUM", "pemploy", "pstudent", "ptype"]
    df = df[person_col_list]

    return df


def process_buffered_landuse(df_psrc, parcel_geog, aggregate_dict):
    """
    Generate MAZ-level land use and synthetic population data for Activitysim.
    """

    df_parcel = pd.read_csv("outputs/landuse/buffered_parcels.txt", sep=" ")
    df_parcel.rename(columns={"taz_p": "TAZ"}, inplace=True)

    df_parcel = df_parcel.merge(parcel_geog, left_on="parcelid", right_on="ParcelID", how="left")
    df_parcel.rename(columns={"maz_id": "MAZ"}, inplace=True)

    # DROP ANY PARCELS MISSING MAZs (coded as -1)
    df_parcel = df_parcel[~df_parcel.MAZ.isnull()]
    df_parcel = df_parcel[df_parcel.MAZ > -1]

    assert df_parcel.MAZ.isnull().values.any() == False

    county_map = {
    "King": 1,
    "Kitsap": 2,
    "Pierce": 3,
    "Snohomish": 4,
        }

    df_parcel["COUNTY"] = df_parcel["CountyName"].map(county_map)
    df_parcel = df_parcel[~df_parcel["COUNTY"].isnull()]
    df_parcel["COUNTY"] = df_parcel["COUNTY"].astype("int")

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
            "empfoo_p": "FOOEMPN",  # food employ
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

    # FIXME: assert all college students are full-time for now...
    # No data on this in parcels
    df_lu["COLLPTE"] = 0

    # Total population by TAZ
    df = df_psrc.groupby("home_zone_id").sum()["hhsize"].reset_index()
    df.rename(columns={"hhsize": "TOTPOP"}, inplace=True)
    df_lu = df_lu.merge(df, left_on="MAZ", right_on="home_zone_id", how="left")  # Retain all zones with left join

    # GET AREA FROM BLOCK GEOG?

    # Total acres, based on parcel size
    df_parcel_area = pd.read_csv(parcel_area_file)
    # df_parcel_area['parcel_id'] = df_parcel_area['pin'].astype(int)
    df_parcel = df_parcel.merge(df_parcel_area, how="left", left_on='parcelid', right_on="parcel_id")
    df_parcel["area"] = df_parcel["area"].fillna(0)
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

    # FIXME: remove TOPOLOGY from models
    df_lu["TOPOLOGY"] = 1

    # Terminal Times
    df_tt = pd.read_csv(
        "inputs/model/activitysim/intrazonals/destination_tt.in", sep="\s+", skiprows=4
    )

    df_tt.columns = ["taz_p", "TERMINAL"]
    df_tt["taz_p"] = df_tt["taz_p"].apply(lambda i: i.split(":")[0]).astype("int")
    df_lu = df_lu.merge(df_tt, left_on="TAZ", right_on="taz_p", how="left")

    # mixed use variable from buffered parcels:
    df_lu["mixed_use2_1"] = log2(df_lu, "hh_1", "emptot_1", 0.0001)
    df_lu["mixed_use2_2"] = log2(df_lu, "hh_2", "emptot_2", 0.0001)
    df_lu["mixed_use3_1"] = log3(df_lu, "hh_1", "empret_1", "empsvc_1", 0.0001)

    # df_lu["TAZ"] = df_lu["taz"]
    
    # create the MAZ and TAZ lookup files
    df_lu[["MAZ", "TAZ"]] = df_lu[["MAZ", "TAZ"]].astype("int")

    # Do some other clean up
    cols = [
        "TOTPOP",
        "access_dist_transit",
    ]
    df_lu[cols] = df_lu[cols].fillna(0)
    df_lu[cols] = df_lu[cols].replace(-1, 0)

    # make sure we have some HSENROLL and COLLFTE, even for very for small samples
    if df_lu['HSENROLL'].sum() == 0:
        "land_use['HSENROLL'] is 0 for full sample!"
        df_lu['HSENROLL'] = df_lu['AGE0519']
        print(f"\nWARNING: land_use.HSENROLL is 0, so backfilled with AGE0519\n")

    if df_lu['COLLFTE'].sum() == 0:
        "land_use['COLLFTE'] is 0 for full sample!"
        df_lu['COLLFTE'] = df_lu['HSENROLL']
        print(f"\nWARNING: land_use.COLLFTE is 0, so backfilled with HSENROLL\n")

    # move MAZ and TAZ columns to front
    df_lu = df_lu[['MAZ', 'TAZ'] + [c for c in df_lu.columns if c not in ['MAZ', 'TAZ']]]

    return df_lu

def run(state):
    
    # Write to outputs where results are stored
    output_dir = run_args.args.data_dir
    
    # Get parcel MAZ ID from inputs database
    parcel_geog = pd.read_sql(
        f"SELECT ParcelID, maz_id, CountyName FROM parcel_{state.input_settings.base_year}_geography",
        con=state.conn,
    )

    df_hh, df_person = process_households(parcel_geog)
    df_person = process_persons(df_person)
    df_lu = process_buffered_landuse(
            df_hh, parcel_geog, lu_aggregate_dict
        )
    
    df_maz = df_lu[["MAZ", "TAZ"]].sort_values(['MAZ', 'TAZ'])

    # Generate TAZ file from TAZ index file
    df_taz = pd.read_csv(
        "inputs/scenario/networks/TAZIndex.txt",
        sep="\s+",
        usecols=["Zone_id"],
    )
    df_taz.rename(columns={"Zone_id": "TAZ"}, inplace=True)

    # df_taz = df_taz[df_taz["TAZ"].isin(df_lu.TAZ)]
    integerize_id_columns(df_taz, 'taz')

    assert (df_lu.TAZ.isin(df_taz.TAZ).all())

    df_maz = df_maz[df_maz["MAZ"].isin(df_lu.MAZ)]
    integerize_id_columns(df_maz, 'maz')

    assert (df_lu.MAZ.isin(df_maz.MAZ).all())
    assert (df_lu.TAZ.isin(df_maz.TAZ).all())
    assert (df_maz.TAZ.isin(df_lu.TAZ).all())

    assert (df_lu.TAZ.isin(df_taz.TAZ).all())

    # Check data
    # Households
    orphan_households = df_hh[~df_hh.home_zone_id.isin(df_lu.home_zone_id)]
    print(f"{len(orphan_households)} orphan_households")

    df_hh = df_hh[df_hh["home_zone_id"].isin(df_maz.MAZ)]
    integerize_id_columns(df_hh, 'households')

    # Persons
    df_person = df_person[df_person["household_id"].isin(df_hh.household_id)]
    integerize_id_columns(df_person, 'persons')

    if not df_lu.MAZ.isin(df_maz.MAZ).all():
        print(f"land_use.MAZ not in maz.MAZ\n{df_lu.MAZ[~df_lu.MAZ.isin(df_maz.MAZ)]}")
        raise RuntimeError(f"land_use.MAZ not in maz.MAZ")

    if not df_maz.MAZ.isin(df_lu.MAZ).all():
        print(f"maz.MAZ not in land_use.MAZ\n{df_maz.MAZ[~df_maz.MAZ.isin(df_lu.MAZ)]}")

    # ### FATAL ###
    if not df_lu.TAZ.isin(df_maz.TAZ).all():
        print(f"land_use.TAZ not in maz.TAZ\n{df_lu.TAZ[~df_lu.TAZ.isin(df_maz.TAZ)]}")
        raise RuntimeError(f"land_use.TAZ not in maz.TAZ")

    if not df_maz.TAZ.isin(df_lu.TAZ).all():
        print(f"maz.TAZ not in land_use.TAZ\n{df_maz.TAZ[~df_maz.TAZ.isin(df_lu.TAZ)]}")
        
    df_hh.to_csv(os.path.join(output_dir, "households.csv"), index=False)
    df_person.to_csv(os.path.join(output_dir, "persons.csv"), index=False)
    df_lu.to_csv(os.path.join(output_dir, "land_use.csv"), index=False)
    df_maz.to_csv(os.path.join(output_dir, "maz.csv"), index=False)
    df_taz.to_csv(os.path.join(output_dir, "taz.csv"), index=False)
    # orphan_households.to_csv(os.path.join(output_dir, "orphan_households.csv"), index=False)