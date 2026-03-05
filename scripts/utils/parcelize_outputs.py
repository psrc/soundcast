import pandas as pd
import geopandas as gpd
import numpy as np
import warnings
import time

# suppress pandas warnings
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

# load parquet output of Activitysim
person_df = pd.read_parquet(r"C:\workspace\sc_20251118\outputs_new\final_persons.parquet")
hh_df = pd.read_parquet(r"C:\workspace\sc_20251118\outputs_new\final_households.parquet")
tour_df = pd.read_parquet(r"C:\workspace\sc_20251118\outputs_new\final_tours.parquet")
trip_df = pd.read_parquet(r"C:\workspace\sc_20251118\outputs_new\final_trips.parquet")

##### TEMP FOR TESTING!!!!!!!!!!!
################
# Select sample of persons and their tours/trips for testing
person_df = person_df.sample(1000, random_state=1)
hh_df = hh_df[hh_df.index.isin(person_df["household_id"])]
tour_df = tour_df[tour_df["person_id"].isin(person_df.index)]
trip_df = trip_df[trip_df["person_id"].isin(person_df.index)]

# Calculate weights as a function of size terms and jobs/hh

# Load size terms from model
df_size_terms = pd.read_csv(r"C:\Workspace\sc_asim_01_15_26\inputs\model\activitysim\configs\destination_choice_size_terms.csv")


# Load parcel data
df_parcel = pd.read_csv(r"C:\workspace\sc_asim_01_15_26\outputs\landuse\parcels_urbansim.txt", sep=" ")

# covnert to geodataframe
df_parcel["geometry"] = gpd.points_from_xy(df_parcel["xcoord_p"], df_parcel["ycoord_p"])
df_parcel.crs = "EPSG:2285"
gdf_parcel = gpd.GeoDataFrame(df_parcel, geometry="geometry")

# MAZ shape from Census
import psrcelmerpy
eg_conn = psrcelmerpy.ElmerGeoConn()
gdf = eg_conn.read_geolayer('block2010')
gdf.to_crs("EPSG:2285", inplace=True)

# Intersect parcel points with gdf to get maz_id on parcels
# FIXME: add this as standard geography available in db or on the parcel file itself
df_parcel = gpd.sjoin(gdf_parcel, gdf[["maz_id","geometry"]], how="left", predicate="within")

parcel_col_dict = {
        "hh_p": "TOTHH",
        "emptot_p": "TOTEMP",
        "stugrd_p": "GSENROLL",
        "stuhgh_p": "HSENROLL",
        "stuuni_p": "COLLFTE",
        "empfoo_p": "FOOEMPN",  # food employ
        "empgov_p": "OTHEMPN",  # government: other employment
        "empind_p": "MWTEMPN",  # industrial: manufacturing, wholesale trade, and transport
        "empofc_p": "FPSEMPN",  # other office: financial and professional services
        "empret_p": "RETEMPN",  # retail: retail
        "empsvc_p": "OTHEMPN",  # other service: other employment
        "empoth_p": "AGREMPN",  # construction, mining, and other: natural resources
    }

for urbansim_col, activitysim_col in parcel_col_dict.items():
    df_parcel[activitysim_col] = df_parcel[urbansim_col].copy()

# HEREMPN is defined by MTC as "Health, educational and recreational service employment"
# Since we have separate categories for education (empedu) and medical (empmed), we will compute HEREMPN as the sum of these two
df_parcel["HEREMPN"] = df_parcel["empedu_p"] + df_parcel["empmed_p"]

def assign_parcels(df, df_size_terms, segment, model_selector, target_col):
    """Assign parcels to tours/trips based on size terms and jobs/hh in the parcels.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing tours, trips, or persons with attributes to be assigned to parcels.

    df_size_terms (pd.DataFrame): DataFrame containing size terms for different segments and models.

    segment (str): The segment to select from size terms (e.g., "social" or "shopping" for trips).

    model_selector (str): The model to select from size terms (e.g., "non_mandatory" for non-mandatory tours).

    target_col (str): The column name in df that contains the target MAZ IDs (e.g., "destination" for tours or trips, "workplace_zone_id" for persons with usual workplace).

    """
    
    start_time = time.time()
    
    #################################
    # Size Terms
    #################################
    # Select size terms for the tour type
    df_size_terms = df_size_terms[(df_size_terms["segment"]==segment) &
                                    (df_size_terms["model_selector"]==model_selector)].copy()

    df_size_terms.drop(['segment','model_selector'], axis=1, inplace=True)
    # Select columns with greater than 0 values
    df_size_terms = df_size_terms.loc[:, (df_size_terms > 0).any()]
    
    #################################
    # Tours by Type and MAZ
    #################################

    df_to_maz = assign_to_maz(df, df_size_terms, target_col)

    elapsed_time = time.time() - start_time
    print(f"\nassign_parcels for '{segment}' completed in {elapsed_time:.2f} seconds")
    
    return df_to_maz


def assign_to_maz(df, df_size_terms, target_col):
    """Assign tours/trips/persons to parcels within MAZs based on size terms and jobs/hh in the parcels.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing tours, trips, or persons with attributes to be assigned to parcels.

    df_size_terms (pd.DataFrame): DataFrame containing size terms for different segments and models.

    target_col (str): The column name in df that contains the target MAZ IDs (e.g., "destination" for tours or trips, "workplace_zone_id" for persons with usual workplace).
    
    """

    # Loop through each MAZ chosen and proportionally assign choices in target_col to parcels
    results_df = pd.DataFrame()

    for maz_id in df[target_col].unique():
        
        # Select data with in target_col for the MAZ
        df_to_maz = df[df[target_col]==maz_id]

        # Get parcels in that MAZ; values from df_to_maz will be distributed to these parcels
        parcels_in_maz = df_parcel[df_parcel["maz_id"]==maz_id].copy()      

        # Randomly distribute df_to_maz to those parcels, weighted by size terms and jobs/hh in the parcels
        # Calculate weights by multiplying size terms by land use field (e.g., households, retail jobs)
        for col in df_size_terms.columns:
            if col in parcels_in_maz.columns:
                parcels_in_maz[col+"_weighted"] = parcels_in_maz[col] * df_size_terms[col].values[0]
            else:
                print(f"Column {col} not found in parcels_in_maz")

        weighted_col_list = [col+"_weighted" for col in df_size_terms.columns]

        # Calculate a weight for each parcel as the sum of the weighted size terms, normalized by the total weighted size terms in the MAZ 
        parcels_in_maz["weight"] = parcels_in_maz[weighted_col_list].sum(axis=1)/parcels_in_maz[weighted_col_list].sum(axis=1).sum(axis=0)

        # Ensure that all parcels have weights
        # If no data for size terms, try total jobs or households as weight
        # FIXME: we should use households as a criteria if the size terms include it
        if parcels_in_maz["weight"].sum() == 0:
            if "TOTEMP" in parcels_in_maz.columns and parcels_in_maz["TOTEMP"].sum() > 0:
                parcels_in_maz["weight"] = parcels_in_maz["TOTEMP"] / parcels_in_maz["TOTEMP"].sum()
            else:
                # If no data for size terms, total jobs, or households, assign equal weight to all parcels
                parcels_in_maz["weight"] = 1 / len(parcels_in_maz)

        # assign df_to_maz to parcels based on weight
        df_to_maz["assigned_parcel"] = np.random.choice(parcels_in_maz["parcelid"], size=len(df_to_maz), p=parcels_in_maz["weight"])

        results_df = pd.concat([results_df, df_to_maz])

    return results_df

tour_results_df = pd.DataFrame
trip_results_df = pd.DataFrame()

########################################
# Usual Work Location
########################################

# Locate parcels for those with usual workplace MAZ
df_workers = person_df[person_df["workplace_zone_id"]>-1].copy()

# Merge income from df_hh to segment workers by income for size terms
df_workers = df_workers.merge(hh_df[["income_segment"]], left_on="household_id", right_index=True, how="left")

df_assigned_workers = pd.DataFrame()

# Segment by income to use size terms
for segment_label, segment_value in {
    "work_low": 1, 
    "work_med": 2, 
    "work_high": 3, 
    "work_veryhigh": 4
    }.items():
    print("Assigning usual workplace parcels for segment:", segment_label)
    df = df_workers[df_workers["income_segment"]==segment_value]
    df = assign_parcels(df, df_size_terms, segment_label, "workplace", "workplace_zone_id")
    df_assigned_workers = pd.concat([df_assigned_workers, df])

df_assigned_workers.rename(columns={"assigned_parcel": "workplace_parcel"}, inplace=True)

# Merge assigned workers back to person_df
person_df = person_df.merge(df_assigned_workers[["workplace_parcel"]], left_index=True, right_index=True, how="left")

# Make sure no workers with workplace_zone_id > -1 have null workplace_parcel
assert person_df[person_df["workplace_zone_id"]>-1]["workplace_parcel"].isnull().sum() == 0, "Some workers with workplace_zone_id > -1 have null workplace_parcel"
person_df["workplace_parcel"].fillna(-1, inplace=True)

########################################
# School Location
########################################

df_students = person_df[person_df["school_zone_id"]>-1].copy()

df_assigned_students = pd.DataFrame()

# FIXME: labels and filtering
for segment_label, segment_value in {
    "presechool": "is_preschool", 
    "gradeschool": "is_gradeschool",
    "highshool": "is_highschool",
    "college": "is_university"
    }.items():
    print("Assigning usual school parcels for segment:", segment_label)
    df = df_students[df_students[segment_value]==True]
    df = assign_parcels(df, df_size_terms, segment_label, "school", "school_zone_id")
    df_assigned_students = pd.concat([df_assigned_students, df])

df_assigned_students.rename(columns={"assigned_parcel": "school_parcel"}, inplace=True)

# Merge assigned students back to person_df
person_df = df_students.merge(df_assigned_students[["school_parcel"]], left_index=True, right_index=True, how="left")
# Make sure no students with school_zone_id > -1 have null school_parcel
assert person_df[person_df["school_zone_id"]>-1]["school_parcel"].isnull().sum() == 0, "Some students with school_zone_id > -1 have null school_parcel"

person_df["school_parcel"].fillna(-1, inplace=True)

########################################
# Mandatory Tours (work and school) 
########################################

df_processed_work_tours = pd.DataFrame()

# If work tour is to usual work location MAZ, assume the tour is assigned to the usual work parcel. 
tour_df = tour_df.merge(df_assigned_workers[["income_segment", "workplace_zone_id", "workplace_parcel"]], left_on="person_id", right_index=True, how="left")
df_work_tours = tour_df[tour_df["tour_type"]=="work"]

df_work_tours.loc[df_work_tours["destination"]==df_work_tours["workplace_zone_id"], "destination_parcel"] = df_work_tours["workplace_parcel"]

# If work tour is not to usual workplace, assign the destiation to parcels in the destination MAZ using the size terms for workplace choice by income
df_work_tours_to_assign = df_work_tours[df_work_tours["destination_parcel"].isnull()]

for segment_label, segment_value in {
    "work_low": 1, 
    "work_med": 2, 
    "work_high": 3, 
    "work_veryhigh": 4
    }.items():
    print("Assigning work tours not to usual workplace for segment:", segment_label)
    df = df_work_tours_to_assign[df_work_tours_to_assign["income_segment"]==segment_value]
    df = assign_parcels(df, df_size_terms, segment_label, "workplace", "workplace_zone_id")
    df_processed_work_tours = pd.concat([df_processed_work_tours, df])

df_processed_work_tours.rename(columns={"assigned_parcel": "destination_parcel"}, inplace=True)

# Non mandatory tours
# for purpose in ["escort", "shopping", "eatout", "othmaint", "social", "othdiscr"]:
    # df = tour_df[tour_df["tour_type"]==tour_type].copy()
#     tours_to_maz = assign_parcels(df, df_size_terms, purpose, "non_mandatory", "destination")
#     results_df = pd.concat([results_df, tours_to_maz])

########################################
# Trips
########################################


########################################
# At-work tours and trips
########################################

# atwork size terms are shared across tours and trips
# process these separately from other tours/trips

# atwork tours
tours_to_maz = assign_parcels(tour_df, df_size_terms, "atwork", "atwork")
tour_results_df = pd.concat([tour_results_df, tours_to_maz])

# atwork trips
trips_to_maz = assign_parcels(trip_df, df_size_terms, "atwork", "atwork")
trip_results_df = pd.concat([trip_results_df, trips_to_maz])

########################################
# Household location
########################################

# Get household parcels from input synthetic population file
