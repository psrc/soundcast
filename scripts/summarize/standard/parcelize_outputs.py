import os
from timeit import main
import pandas as pd
import geopandas as gpd
import numpy as np
import warnings
import time

# suppress pandas warnings
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None


def prepare_inputs(state, use_sample, output_dir):
    """Load ActivitySim outputs and parcel geography needed for parcel assignment."""

    # load parquet output of Activitysim
    person_df = pd.read_parquet(os.path.join(output_dir, r"final_persons.parquet"))
    hh_df = pd.read_parquet(os.path.join(output_dir, r"final_households.parquet"))
    tour_df = pd.read_parquet(os.path.join(output_dir, r"final_tours.parquet"))
    trip_df = pd.read_parquet(os.path.join(output_dir, r"final_trips.parquet"))

    # Merge household parcel to trips
    trip_df = trip_df.merge(hh_df[["hhparcel","home_zone_id"]], left_on="household_id", right_index=True, how="left") 

    # Select sample of persons and their tours/trips for testing
    if use_sample:
        person_df = person_df.sample(10000, random_state=1)
        hh_df = hh_df[hh_df.index.isin(person_df["household_id"])]
        tour_df = tour_df[tour_df["person_id"].isin(person_df.index)]
        trip_df = trip_df[trip_df["person_id"].isin(person_df.index)]

    # Load size terms from model
    df_size_terms = pd.read_csv(
        r"inputs/model/activitysim/configs/destination_choice_size_terms.csv"
    )

    # Load parcel data
    df_parcel = pd.read_csv(r"outputs/landuse/parcels_urbansim.txt", sep=" ")

    # Get parcel MAZ ID from soundcast inputs database
    df_parcel_geog = pd.read_sql(
        f"SELECT ParcelID, maz_id FROM parcel_{state.input_settings.base_year}_geography",
        con=state.conn,
    )

    df_parcel = df_parcel.merge(df_parcel_geog, left_on="parcelid", right_on="ParcelID", how="left")
    # convert to geodataframe
    # df_parcel["geometry"] = gpd.points_from_xy(df_parcel["xcoord_p"], df_parcel["ycoord_p"])
    # df_parcel.crs = "EPSG:2285"
    # gdf_parcel = gpd.GeoDataFrame(df_parcel, geometry="geometry")

    # # MAZ shape from Census
    # eg_conn = psrcelmerpy.ElmerGeoConn()
    # gdf = eg_conn.read_geolayer("block2010")
    # gdf.to_crs("EPSG:2285", inplace=True)

    # # Intersect parcel points with gdf to get maz_id on parcels
    # # FIXME: add this as standard geography available in db or on the parcel file itself
    # df_parcel = gpd.sjoin(gdf_parcel, gdf[["maz_id", "geometry"]], how="left", predicate="within")

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

    # HEREMPN is defined by MTC as health, educational and recreational employment.
    df_parcel["HEREMPN"] = df_parcel["empedu_p"] + df_parcel["empmed_p"]

    return person_df, hh_df, tour_df, trip_df, df_size_terms, df_parcel


def add_parcel_weights_for_size_terms(df_size_terms, df_parcel):
    """Create purpose-specific parcel weights from size terms, normalized within each MAZ.

    For each (segment, model_selector) in the size-term table, a raw parcel score is
    computed as the linear combination of parcel employment/household fields and
    corresponding size-term coefficients. Raw scores are normalized to probabilities
    within each MAZ.
    """

    index_cols = ["segment", "model_selector"]
    coeff_cols = [
        col for col in df_size_terms.columns if col not in index_cols and col in df_parcel.columns
    ]

    weight_frames = []

    for _, term_row in df_size_terms.iterrows():
        raw_weight = np.zeros(len(df_parcel), dtype=float)

        for col in coeff_cols:
            coeff = term_row[col]
            if pd.notna(coeff) and coeff > 0:
                raw_weight += df_parcel[col].fillna(0).to_numpy() * coeff

        purpose_weights = df_parcel[["parcelid", "maz_id"]].copy()
        purpose_weights["raw_weight"] = raw_weight
        purpose_weights["TOTEMP"] = df_parcel["TOTEMP"].fillna(0)

        raw_sum = purpose_weights.groupby("maz_id")["raw_weight"].transform("sum")
        emp_sum = purpose_weights.groupby("maz_id")["TOTEMP"].transform("sum")
        parcel_count = purpose_weights.groupby("maz_id")["parcelid"].transform("count")

        purpose_weights["weight"] = np.where(
            raw_sum > 0,
            purpose_weights["raw_weight"] / raw_sum,
            np.where(emp_sum > 0, purpose_weights["TOTEMP"] / emp_sum, 1 / parcel_count),
        )

        purpose_weights["segment"] = term_row["segment"]
        purpose_weights["model_selector"] = term_row["model_selector"]
        weight_frames.append(
            purpose_weights[["segment", "model_selector", "parcelid", "maz_id", "weight"]]
        )

    return pd.concat(weight_frames, ignore_index=True)


def export_parcel_weight_diagnostics(
    df_parcel_weights,
    output_dir,
    tolerance=1e-6,
    export_csv=True,
):
    """Validate MAZ-level weight sums and optionally export diagnostics CSV."""

    diagnostics = (
        df_parcel_weights
        .groupby(["segment", "model_selector", "maz_id"], as_index=False)["weight"]
        .sum()
        .rename(columns={"weight": "weight_sum"})
    )
    diagnostics["abs_error_from_1"] = (diagnostics["weight_sum"] - 1.0).abs()
    diagnostics["passes"] = diagnostics["abs_error_from_1"] <= tolerance

    failed = (~diagnostics["passes"]).sum()
    if export_csv:
        os.makedirs(output_dir, exist_ok=True)
        diagnostics_path = os.path.join(output_dir, "parcel_weight_diagnostics.csv")
        diagnostics.to_csv(diagnostics_path, index=False)
        print(
            f"Parcel weight diagnostics exported to {diagnostics_path}. "
            f"Checked {len(diagnostics)} MAZ rows; failures={failed} (tolerance={tolerance})."
        )
    else:
        print(
            f"Parcel weight diagnostics computed (not exported). "
            f"Checked {len(diagnostics)} MAZ rows; failures={failed} (tolerance={tolerance})."
        )

    return diagnostics


def join_weights_to_parcels(df_parcel, df_parcel_weights):
    """Join purpose-specific parcel weights to the input parcel table.

    Weight columns are named `<purpose>_weight`. If a purpose appears in more than
    one model selector, columns are disambiguated as
    `<purpose>_<model_selector>_weight`.
    """

    model_selector_counts = (
        df_parcel_weights.groupby("segment")["model_selector"].nunique().to_dict()
    )

    weights_for_join = df_parcel_weights[["parcelid", "segment", "model_selector", "weight"]].copy()
    weights_for_join["purpose_name"] = np.where(
        weights_for_join["segment"].map(model_selector_counts).gt(1),
        weights_for_join["segment"] + "_" + weights_for_join["model_selector"],
        weights_for_join["segment"],
    )
    weights_for_join["weight_col"] = weights_for_join["purpose_name"] + "_weight"

    weights_wide = (
        weights_for_join
        .pivot_table(index="parcelid", columns="weight_col", values="weight", aggfunc="first")
        .reset_index()
    )
    weights_wide.columns.name = None

    return df_parcel.merge(weights_wide, on="parcelid", how="left")


def assign_parcels(df, df_parcel_weights, segment, model_selector, target_col, df_parcel):
    """Assign parcels to tours/trips/persons using precomputed purpose/model weights.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing tours, trips, or persons with attributes to be assigned to parcels.

    df_size_terms (pd.DataFrame): Kept for backward compatibility; not used directly.

    segment (str): The segment to select from size terms (e.g., "social" or "shopping" for trips).

    model_selector (str): The model to select from size terms (e.g., "non_mandatory" for non-mandatory tours).

    target_col (str): The column name in df that contains the target MAZ IDs (e.g., "destination" for tours or trips, "workplace_zone_id" for persons with usual workplace).

    """
    
    start_time = time.time()

    segment_weights = df_parcel_weights[
        (df_parcel_weights["segment"] == segment)
        & (df_parcel_weights["model_selector"] == model_selector)
    ][["parcelid", "maz_id", "weight"]]

    df_to_maz = assign_to_parcel(df, target_col, segment_weights, df_parcel)

    elapsed_time = time.time() - start_time
    print(f"\nassign_parcels for '{segment}' completed in {elapsed_time:.2f} seconds")
    
    return df_to_maz


def assign_to_parcel(df, target_col, segment_weights, df_parcel):
    """Assign records to parcels without iterating MAZ-by-MAZ in Python.

    For each MAZ, this computes how many records need assignment, samples exactly
    that many parcels using parcel weights, and joins sampled parcels back to the
    original rows by MAZ sequence position.
    """

    if df.empty:
        return df.copy()

    result_df = df.copy()
    result_df["assigned_parcel"] = np.nan

    if segment_weights is None:
        segment_weights = pd.DataFrame(columns=["maz_id", "parcelid", "weight"])

    valid_mask = result_df[target_col].notnull()
    if not valid_mask.any():
        return result_df

    assign_df = result_df.loc[valid_mask, [target_col]].copy()

    # Count records by MAZ and build one sampling request row per record.
    maz_counts = (
        assign_df[target_col]
        .value_counts(dropna=False)
        .rename_axis("maz_id")
        .reset_index(name="n")
    )
    sample_requests = maz_counts.loc[maz_counts.index.repeat(maz_counts["n"]), ["maz_id"]].copy()
    sample_requests["maz_id"] = pd.to_numeric(sample_requests["maz_id"], errors="coerce")
    sample_requests = sample_requests[sample_requests["maz_id"].notnull()].copy()
    sample_requests["maz_id"] = sample_requests["maz_id"].astype(np.int64)
    sample_requests["maz_seq"] = sample_requests.groupby("maz_id").cumcount()
    sample_requests["draw"] = np.random.random(len(sample_requests))

    # Build MAZ-specific CDF table used for weighted sampling.
    cdf = segment_weights[["maz_id", "parcelid", "weight"]].copy()
    cdf = cdf[cdf["maz_id"].notnull()].copy()
    cdf["maz_id"] = pd.to_numeric(cdf["maz_id"], errors="coerce")
    cdf = cdf[cdf["maz_id"].notnull()].copy()
    cdf["maz_id"] = cdf["maz_id"].astype(np.int64)
    cdf["weight"] = cdf["weight"].fillna(0)

    # If any requested MAZs are missing from segment weights, use TOTEMP/equal fallback.
    requested_maz = set(sample_requests["maz_id"].dropna().tolist())
    weighted_maz = set(cdf["maz_id"].dropna().tolist())
    missing_maz = requested_maz - weighted_maz
    if missing_maz:
        fallback = df_parcel[df_parcel["maz_id"].isin(missing_maz)][["maz_id", "parcelid", "TOTEMP"]].copy()
        fallback["maz_id"] = pd.to_numeric(fallback["maz_id"], errors="coerce")
        fallback = fallback[fallback["maz_id"].notnull()].copy()
        fallback["maz_id"] = fallback["maz_id"].astype(np.int64)
        fallback["TOTEMP"] = fallback["TOTEMP"].fillna(0)
        fallback["totemp_sum"] = fallback.groupby("maz_id")["TOTEMP"].transform("sum")
        fallback["parcel_count"] = fallback.groupby("maz_id")["parcelid"].transform("count")
        fallback["weight"] = np.where(
            fallback["totemp_sum"] > 0,
            fallback["TOTEMP"] / fallback["totemp_sum"],
            1 / fallback["parcel_count"],
        )
        cdf = pd.concat([cdf, fallback[["maz_id", "parcelid", "weight"]]], ignore_index=True)

    cdf["maz_id"] = cdf["maz_id"].astype(np.int64)

    # Also fallback MAZs that exist in weights but have no positive weight rows.
    positive_weight_maz = set(cdf.loc[cdf["weight"] > 0, "maz_id"].tolist())
    zero_weight_maz = requested_maz - positive_weight_maz
    if zero_weight_maz:
        fallback_zero = df_parcel[df_parcel["maz_id"].isin(zero_weight_maz)][["maz_id", "parcelid", "TOTEMP"]].copy()
        fallback_zero["maz_id"] = pd.to_numeric(fallback_zero["maz_id"], errors="coerce")
        fallback_zero = fallback_zero[fallback_zero["maz_id"].notnull()].copy()
        fallback_zero["maz_id"] = fallback_zero["maz_id"].astype(np.int64)
        fallback_zero["TOTEMP"] = fallback_zero["TOTEMP"].fillna(0)
        fallback_zero["totemp_sum"] = fallback_zero.groupby("maz_id")["TOTEMP"].transform("sum")
        fallback_zero["parcel_count"] = fallback_zero.groupby("maz_id")["parcelid"].transform("count")
        fallback_zero["weight"] = np.where(
            fallback_zero["totemp_sum"] > 0,
            fallback_zero["TOTEMP"] / fallback_zero["totemp_sum"],
            1 / fallback_zero["parcel_count"],
        )
        cdf = cdf[~cdf["maz_id"].isin(zero_weight_maz)].copy()
        cdf = pd.concat([cdf, fallback_zero[["maz_id", "parcelid", "weight"]]], ignore_index=True)

    cdf["weight"] = cdf["weight"].fillna(0)
    cdf = cdf[cdf["weight"] > 0].copy()
    cdf = cdf.sort_values(["maz_id", "parcelid"])
    cdf["cum_weight"] = cdf.groupby("maz_id")["weight"].cumsum()
    cdf["cum_weight"] = cdf["cum_weight"] / cdf.groupby("maz_id")["cum_weight"].transform("max")
    # Ensure each MAZ CDF reaches exactly 1.0 to avoid edge-case misses for high draws.
    cdf.loc[cdf.groupby("maz_id")["cum_weight"].idxmax(), "cum_weight"] = 1.0
    cdf = cdf.sort_values(["maz_id", "cum_weight"])

    # Weighted sample via CDF lookup. Use a composite monotonic key so merge_asof
    # works consistently across pandas versions while preserving within-MAZ matching.
    all_maz = np.union1d(sample_requests["maz_id"].unique(), cdf["maz_id"].unique())
    maz_to_code = pd.Series(np.arange(len(all_maz), dtype=np.int64), index=all_maz)

    sample_requests["maz_code"] = sample_requests["maz_id"].map(maz_to_code).astype(np.int64)
    cdf["maz_code"] = cdf["maz_id"].map(maz_to_code).astype(np.int64)

    sample_requests["asof_key"] = sample_requests["maz_code"] + sample_requests["draw"]
    cdf["asof_key"] = cdf["maz_code"] + cdf["cum_weight"]

    sampled = pd.merge_asof(
        sample_requests.sort_values(["asof_key"]),
        cdf[["asof_key", "parcelid", "maz_code"]]
        .rename(columns={"maz_code": "matched_maz_code"})
        .sort_values(["asof_key"]),
        left_on="asof_key",
        right_on="asof_key",
        direction="forward",
    )
    sampled.loc[sampled["maz_code"] != sampled["matched_maz_code"], "parcelid"] = np.nan

    # Map sampled parcels back to original rows by MAZ and sequence number.
    row_map = assign_df[[target_col]].copy()
    row_map["_row_id"] = assign_df.index
    row_map = row_map.rename(columns={target_col: "maz_id"})
    row_map["maz_id"] = pd.to_numeric(row_map["maz_id"], errors="coerce")
    row_map = row_map[row_map["maz_id"].notnull()].copy()
    row_map["maz_id"] = row_map["maz_id"].astype(np.int64)
    row_map["maz_seq"] = row_map.groupby("maz_id").cumcount()

    assigned = row_map.merge(
        sampled[["maz_id", "maz_seq", "parcelid"]],
        on=["maz_id", "maz_seq"],
        how="left",
    )

    # If sampling still missed within a MAZ, use first available parcel in that MAZ.
    if assigned["parcelid"].isnull().any():
        first_parcel_by_maz = cdf.groupby("maz_id")["parcelid"].first()
        assigned["parcelid"] = assigned["parcelid"].fillna(assigned["maz_id"].map(first_parcel_by_maz))

    result_df.loc[assigned["_row_id"], "assigned_parcel"] = assigned["parcelid"].to_numpy()
    return result_df

def main(state,output_dir):

    script_start_time = time.perf_counter()

    use_sample = False
    # output_dir = r"C:\workspace\sc_20251118\outputs_new"
    run_diagnostics = False
    export_diagnostics_csv = False
    export_parcel_weights_csv = False

    person_df, hh_df, tour_df, trip_df, df_size_terms, df_parcel = prepare_inputs(state, use_sample, output_dir)
    df_parcel_weights = add_parcel_weights_for_size_terms(df_size_terms, df_parcel)
    if run_diagnostics:
        parcel_weight_diagnostics = export_parcel_weight_diagnostics(
            df_parcel_weights,
            output_dir,
            export_csv=export_diagnostics_csv,
        )
    else:
        parcel_weight_diagnostics = None
        print("Parcel weight diagnostics skipped.")
    df_parcel = join_weights_to_parcels(df_parcel, df_parcel_weights)

    if export_parcel_weights_csv:
        os.makedirs(output_dir, exist_ok=True)
        enriched_parcel_path = os.path.join(output_dir, "parcels_with_purpose_weights.csv")
        df_parcel.to_csv(enriched_parcel_path, index=False)
        print(f"Enriched parcel table exported to {enriched_parcel_path}")
    else:
        print("Enriched parcel table export skipped.")

    tour_results_df = pd.DataFrame()
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
        df = assign_parcels(df, df_parcel_weights, segment_label, "workplace", "workplace_zone_id", df_parcel)
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

    for segment_label, segment_value in {
        "preschool": "is_preschool", 
        "gradeschool": "is_gradeschool",
        "highshool": "is_highschool",
        "college": "is_university"
        }.items():
        print("Assigning usual school parcels for segment:", segment_label)
        df = df_students[df_students[segment_value]==True]
        df = assign_parcels(df, df_parcel_weights, segment_label, "school", "school_zone_id", df_parcel)
        df_assigned_students = pd.concat([df_assigned_students, df])

    df_assigned_students.rename(columns={"assigned_parcel": "school_parcel"}, inplace=True)

    # Merge assigned students back to person_df
    person_df = person_df.merge(df_assigned_students[["school_parcel"]], left_index=True, right_index=True, how="left")
    # Make sure no students with school_zone_id > -1 have null school_parcel
    assert person_df[person_df["school_zone_id"]>-1]["school_parcel"].isnull().sum() == 0, "Some students with school_zone_id > -1 have null school_parcel"

    person_df["school_parcel"].fillna(-1, inplace=True)

    ########################################
    # Mandatory Tours (work and school) 
    ########################################

    ########################################
    # Work Tours
    ########################################
    df_processed_work_tours = pd.DataFrame()

    # If work tour is to usual work location MAZ, assume the tour is assigned to the usual work parcel. 
    tour_df = tour_df.merge(df_assigned_workers[["income_segment", "workplace_zone_id", "workplace_parcel"]], left_on="person_id", right_index=True, how="left")
    df_work_tours = tour_df[tour_df["tour_type"]=="work"]

    df_work_tours.loc[df_work_tours["destination"]==df_work_tours["workplace_zone_id"], "destination_parcel"] = df_work_tours["workplace_parcel"]

    # If work tour is not to usual workplace, assign the destiation to parcels in the destination MAZ using the size terms for workplace choice by income
    df_work_tours_complete = df_work_tours[~df_work_tours["destination_parcel"].isnull()]
    df_work_tours_to_assign = df_work_tours[df_work_tours["destination_parcel"].isnull()]

    if len(df_work_tours_to_assign) > 0:
        for segment_label, segment_value in {
            "work_low": 1, 
            "work_med": 2, 
            "work_high": 3, 
            "work_veryhigh": 4
            }.items():
            print("Assigning work tours not to usual workplace for segment:", segment_label)
            df = df_work_tours_to_assign[df_work_tours_to_assign["income_segment"]==segment_value]
            df = assign_parcels(df, df_parcel_weights, segment_label, "workplace", "workplace_zone_id", df_parcel)
            df_processed_work_tours = pd.concat([df_processed_work_tours, df])

        df_processed_work_tours.rename(columns={"assigned_parcel": "destination_parcel"}, inplace=True)
        tour_results_df = pd.concat([tour_results_df, df_processed_work_tours])
    tour_results_df = pd.concat([tour_results_df, df_work_tours_complete])

    ########################################
    # School Tours
    ########################################
    df_processed_school_tours = pd.DataFrame()

    tour_df = tour_df.merge(df_assigned_students[[ "school_zone_id", "school_parcel"]], left_on="person_id", right_index=True, how="left")

    # If school tour is to usual school location MAZ, assume the tour is assigned to the usual school parcel.
    df_school_tours = tour_df[tour_df["tour_type"]=="school"]
    df_school_tours.loc[df_school_tours["destination"]==df_school_tours["school_zone_id"], "destination_parcel"] = df_school_tours["school_parcel"]

    # If school tour is not to usual school location, assign the destination to parcels in the destination MAZ using the size terms for school choice by grade level
    df_school_tours_complete = df_school_tours[~df_school_tours["destination_parcel"].isnull()]
    df_school_tours_to_assign = df_school_tours[df_school_tours["destination_parcel"].isnull()]

    if len(df_school_tours_to_assign) > 0:
        for segment_label, segment_value in {
            "presechool": "is_preschool", 
            "gradeschool": "is_gradeschool",
            "highschool": "is_highschool",
            "college": "is_university"
            }.items():
            print("Assigning usual school parcels for segment:", segment_label)
            df = df_school_tours_to_assign[df_school_tours_to_assign[segment_value]==True]
            df = assign_parcels(df, df_parcel_weights, segment_label, "school", "school_zone_id", df_parcel)
            df_processed_school_tours = pd.concat([df_processed_school_tours, df])

        df_processed_school_tours.rename(columns={"assigned_parcel": "destination_parcel"}, inplace=True)

        tour_results_df = pd.concat([tour_results_df, df_processed_school_tours])
    tour_results_df = pd.concat([tour_results_df, df_school_tours_complete])

    ########################################
    # Non-mandatory tours
    ########################################
    non_mandatory_tour_results = pd.DataFrame()
    for purpose in ["escort", "shopping", "eatout", "othmaint", "social", "othdiscr"]:
        df = tour_df[tour_df["tour_type"]==purpose].copy()
        tours_to_maz = assign_parcels(df, df_parcel_weights, purpose, "non_mandatory", "destination", df_parcel)
        non_mandatory_tour_results = pd.concat([non_mandatory_tour_results, tours_to_maz])

    tour_results_df = pd.concat([tour_results_df, non_mandatory_tour_results])

    ########################################
    # Trips
    ########################################

    trip_results_df = pd.DataFrame()
    for purpose in ["escort", "shopping", "eatout", "othmaint", "social", "othdiscr"]:
        df = trip_df[trip_df["purpose"]==purpose].copy()
        trips_to_maz = assign_parcels(df, df_parcel_weights, purpose, "trip", "destination", df_parcel)
        trip_results_df = pd.concat([trip_results_df, trips_to_maz])

    # For work trips, if the destination is the same as the workplace_zone_id, assign to the workplace parcel. 
    # If not, assign to parcels in the destination MAZ using trip size terms

    # If work tour is to usual work location MAZ, assume the tour is assigned to the usual work parcel. 
    trip_df = trip_df.merge(df_assigned_workers[["workplace_zone_id", "workplace_parcel"]], left_on="person_id", right_index=True, how="left")
    df_work_trips = trip_df[trip_df["purpose"]=="work"]
    df_work_trips.loc[df_work_trips["destination"]==df_work_trips["workplace_zone_id"], "destination_parcel"] = df_work_trips["workplace_parcel"]

    # If work tour is not to usual workplace, assign the destiation to parcels in the destination MAZ using the size terms for workplace choice by income
    df_work_trips_complete = df_work_trips[~df_work_trips["destination_parcel"].isnull()]
    df_work_trips_to_assign = df_work_trips[df_work_trips["destination_parcel"].isnull()]

    trips_to_maz = assign_parcels(df_work_trips_to_assign, df_parcel_weights, "work", "trip", "destination", df_parcel)
    trip_results_df = pd.concat([trip_results_df,df_work_trips_complete, trips_to_maz])

    # For school trips, if the destination is the same as the school_zone_id, assign to the school parcel.
    # If not, assign to parcels in the destination MAZ using trip size terms
    trip_df = trip_df.merge(df_assigned_students[["school_zone_id", "school_parcel"]], left_on="person_id", right_index=True, how="left")
    df_school_trips = trip_df[trip_df["purpose"].isin(["univ", "school"])]
    df_school_trips.loc[df_school_trips["destination"]==df_school_trips["school_zone_id"], "destination_parcel"] = df_school_trips["school_parcel"]

    # If school tour is not to usual school location, assign the destination to parcels in the destination MAZ using the size terms for school choice by grade level
    df_school_trips_complete = df_school_trips[~df_school_trips["destination_parcel"].isnull()]
    df_school_trips_to_assign = df_school_trips[df_school_trips["destination_parcel"].isnull()]

    trips_to_maz = assign_parcels(df_school_trips_to_assign, df_parcel_weights, "school", "trip", "destination", df_parcel)
    trip_results_df = pd.concat([trip_results_df,df_school_trips_complete, trips_to_maz])

    ########################################
    # At-work tours and trips
    ########################################

    # atwork size terms are shared across tours and trips
    # process these separately from other tours/trips
    df_atwork_tours = tour_df[tour_df["tour_category"]=="atwork"].copy()
    tours_to_maz = assign_parcels(df_atwork_tours, df_parcel_weights, "atwork", "atwork", "destination", df_parcel)
    tour_results_df = pd.concat([tour_results_df, tours_to_maz])

    # atwork trips
    df_atwork_trips = trip_df[trip_df["purpose"]=="atwork"].copy()
    trips_to_maz = assign_parcels(df_atwork_trips, df_parcel_weights, "atwork", "atwork", "destination", df_parcel)
    trip_results_df = pd.concat([trip_results_df, trips_to_maz])

    # Set trip parcel destination for trips to home as home parcel
    df_home_trips = trip_df[trip_df["purpose"]=="home"].copy()
    df_home_trips["assigned_parcel"] = df_home_trips["hhparcel"].copy()
    trip_results_df = pd.concat([trip_results_df, df_home_trips])

    # tour_results_df.rename(columns={"assigned_parcel": "destination_parcel"}, inplace=True)
    # trip_results_df.rename(columns={"assigned_parcel": "destination_parcel"}, inplace=True)
    tour_results_df["destination_parcel"].fillna(tour_results_df["assigned_parcel"], inplace=True)
    trip_results_df["destination_parcel"].fillna(trip_results_df["assigned_parcel"], inplace=True)

    # trip_results_df and tour_results_df should now be the same size as the original trip and tour tables
    assert len(trip_results_df) == len(trip_df), "Trip results table size mismatch"
    assert len(tour_results_df) == len(tour_df), "Tour results table size mismatch"

    ########################################
    # Origin parcels
    ########################################

    # For trips from same zone as home assume origin is home parcel
    trip_origin_home_mask = trip_results_df["origin"] == trip_results_df["home_zone_id"]
    trip_results_df.loc[trip_origin_home_mask, "origin_parcel"] = trip_results_df.loc[
        trip_origin_home_mask, "hhparcel"
    ].to_numpy()

    # For at-work trips set origin as workplace parcel
    # atwork_trip_mask = trip_results_df["purpose"]=="atwork"
    # trip_results_df.loc[atwork_trip_mask, "origin_parcel"] = trip_results_df.loc[atwork_trip_mask, "workplace_parcel"].to_numpy()

    # Tours
    tour_results_df = tour_results_df.merge(hh_df[["hhparcel","home_zone_id"]], left_on="household_id", right_index=True, how="left")

    # Tours are home-based except for at-work tours. 
    # For home-based tours, set origin as home parcel. 
    tour_home_mask = tour_results_df["origin"] == tour_results_df["home_zone_id"]
    tour_results_df.loc[tour_home_mask, "origin_parcel"] = tour_results_df.loc[tour_home_mask, "hhparcel"].to_numpy()

    # For at-work tours set origin as destination for parent tour_id
    tour_results_df = tour_results_df.merge(tour_results_df[["destination_parcel"]], how="left", left_on="parent_tour_id", right_index=True, suffixes=("", "_parent"))
    atwork_tour_mask = (tour_results_df["primary_purpose"]=="atwork")
    tour_results_df.loc[atwork_tour_mask, "origin_parcel"] = tour_results_df["destination_parcel_parent"]

    # Sort trips by trip_id
    trip_results_df = trip_results_df.sort_index()

    # Get origin destination for at-work trips from parent tour_id
    atwork_trip_mask = trip_results_df["purpose"]=="atwork"
    trip_results_df = trip_results_df.merge(tour_results_df[["destination_parcel_parent"]], how="left", left_on="tour_id", right_index=True, suffixes=("", "_tour"))

    # First trip in atwork tour has origin of destination_parcel_parent
    atwork_trip_mask = (trip_results_df["primary_purpose"]=="atwork") & (trip_results_df["trip_num"]==1) & (trip_results_df["outbound"]==True)
    trip_results_df.loc[atwork_trip_mask, "origin_parcel"] = trip_results_df.loc[atwork_trip_mask, "destination_parcel_parent"]

    # compute previous destination within each tour
    prev_dest = trip_results_df.groupby("tour_id")["destination_parcel"].shift()
    # only fill origins that are null
    missing_origin = trip_results_df["origin_parcel"].isna()
    trip_results_df.loc[missing_origin, "origin_parcel"] = prev_dest[missing_origin]

    ########################################
    # Q/C 
    ########################################

    # ensure parcel results are stored as integers
    for col in ["destination_parcel", "assigned_parcel"]:
        trip_results_df[col] = trip_results_df[col].fillna(-1).astype("int64")
        tour_results_df[col] = tour_results_df[col].fillna(-1).astype("int64")

    for col in ["workplace_parcel", "school_parcel"]:
        person_df[col] = person_df[col].fillna(-1).astype("int64")

    # Reconcile outputs to ensure exactly one row per original record index.
    tour_results_df = tour_results_df[~tour_results_df.index.duplicated(keep="first")]
    missing_tour_ids = tour_df.index.difference(tour_results_df.index)
    if len(missing_tour_ids) > 0:
        tour_results_df = pd.concat([tour_results_df, tour_df.loc[missing_tour_ids]], sort=False)
    tour_results_df = tour_results_df.reindex(tour_df.index)

    trip_results_df = trip_results_df[~trip_results_df.index.duplicated(keep="first")]
    missing_trip_ids = trip_df.index.difference(trip_results_df.index)
    if len(missing_trip_ids) > 0:
        trip_results_df = pd.concat([trip_results_df, trip_df.loc[missing_trip_ids]], sort=False)
    trip_results_df = trip_results_df.reindex(trip_df.index)

    # check that results have expected number of records
    assert len(tour_results_df) == len(tour_df), "Number of records in tour_results_df does not match original tour_df"
    assert len(trip_results_df) == len(trip_df), "Number of records in trip_results_df does not match original trip_df"

    # check that no origin_parcel or destination_parcel is null for tours/trips with non-null origin/destination
    assert tour_results_df.loc[tour_results_df["origin"].notnull(), "origin_parcel"].isnull().sum() == 0, "Some tours with non-null origin have null origin_parcel"
    assert tour_results_df.loc[tour_results_df["destination"].notnull(), "destination_parcel"].isnull().sum() == 0, "Some tours with non-null destination have null destination_parcel"
    assert trip_results_df.loc[trip_results_df["origin"].notnull(), "origin_parcel"].isnull().sum() == 0, "Some trips with non-null origin have null origin_parcel"
    assert trip_results_df.loc[trip_results_df["destination"].notnull(), "destination_parcel"].isnull().sum() == 0, "Some trips with non-null destination have null destination_parcel"

    script_elapsed_seconds = time.perf_counter() - script_start_time
    print(f"Total script runtime: {script_elapsed_seconds:.2f} seconds")
    print ("Parcel assignment completed.")

    # Write results to output directory as parquet file
    person_df.to_parquet(os.path.join(output_dir, "final_persons_with_parcels.parquet"), index=False)
    tour_cols = tour_df.columns.tolist() + ["destination_parcel", "origin_parcel"]
    trip_cols = trip_df.columns.tolist() + ["destination_parcel", "origin_parcel"]
    tour_results_df[tour_cols].to_parquet(os.path.join(output_dir, "final_tours_with_parcels.parquet"), index=False)
    trip_results_df[trip_cols].to_parquet(os.path.join(output_dir, "final_trips_with_parcels.parquet"), index=False)

if __name__ == "__main__":
    main(state, output_dir)