import pandas as pd
import h5py
import os, shutil
import time
import polars as pl
from scripts.settings import run_args
from scripts.summarize.standard import parcelize_outputs

def create_dir(_dir):
    if os.path.exists(_dir):
        shutil.rmtree(_dir)
    os.makedirs(_dir)


def merge_geography(df, df_geog, df_geographic_lookup):
    for _index, _row in df_geog.iterrows():
        right_df = df_geographic_lookup[[_row.right_index, _row.right_column]]
        df = df.join(
            right_df, left_on=_row.left_index, right_on=_row.right_index, how="left"
        )
        df = df.rename({_row.right_column: _row.right_column_rename})

    return df


def h5_df(h5file, table, polars=True):
    """Load h5 file as pandas or polars dataframe."""
    df = pd.DataFrame()
    for col in h5file[table].keys():
        # Get dtype and store as dataframe columns
        col_type = type(h5file[table][col][0])
        df[col] = h5file[table][col][:].astype(col_type)

    if polars:
        df = pl.from_pandas(df)

    return df


def process_expressions(df, df_expr, table_name, survey):
    """Aggregate data according to each row of an expression file.
    Write CSV files to disk.
    """
    df_expr = df_expr[df_expr["table"] == table_name]
    for _index, _row in df_expr.iterrows():
        # Get list of aggregation fields and values
        agg_cols = [item.strip() for item in _row["agg_fields"].split(",")]
        values_cols = [item.strip() for item in _row["values"].split(",")]
        if _row.aggfunc == "sum":
            agg_df = df.group_by(agg_cols).agg(pl.col(values_cols).sum())
        elif _row.aggfunc == "mean":
            agg_df = df.group_by(agg_cols).agg(pl.col(values_cols).mean())
        elif _row.aggfunc == "median":
            agg_df = df.group_by(agg_cols).agg(pl.col(values_cols).median())
        elif  _row.aggfunc == "len":
            agg_df = df.group_by(agg_cols).len()
            # Rename len with values used for daysim for consistency
            agg_df = agg_df.rename({"len": _row["values"]})
        if survey:
            output_path = f"outputs/agg/{_row.output_dir}/survey/{_row.target}.csv"
        else:
            output_path = f"outputs/agg/{_row.output_dir}/{_row.target}.csv"
        agg_df.write_csv(output_path)

def process_variables(df, df_expr, table_name):
    """Load and apply variable expressions from CSV."""
    df_expr = df_expr[df_expr["table"] == table_name]
    
    for _index, _row in df_expr.iterrows():
        # CSV should contain: |new_variable|expression|table|
        # expression example: "((pl.col('hhincome') / 1000).round(0) * 1000).cast(pl.Int32)"
        
        expr = eval(_row["expression"], {"pl": pl})
        df = df.with_columns(**{_row["new_variable"]: expr})
    
    return df

def apply_labels(tablename, df, labels_df):
    """Convert model/survey data in integers to string labels."""
    labels_df = labels_df.filter(pl.col("table") == tablename)
    for field in labels_df["field"].unique():
        label_df = labels_df.filter(pl.col("field") == field)[["value", "text"]]
        # pl_df = pl.DataFrame(label_df)
        df = df.with_columns(pl.col(field).cast(pl.String))
        df = df.join(label_df, left_on=field, right_on="value", how="left")
        df = df.drop(field)
        df = df.rename({"text": field})

    return df


def create_agg_outputs(state, path_dir_base, model, survey=False):
    geography_lookup = pd.read_csv(
        f"inputs/model/{model}/summaries/geography_lookup.csv"
    )

    expr_df = pd.read_csv(
        os.path.join(
            os.getcwd(), f"inputs/model/{model}/summaries/agg_expressions.csv"
        )
    )

    if os.path.exists(os.path.join(f"inputs/model/{model}/lookup/variable_labels.csv")):
        labels_df = pl.read_csv(
            os.path.join(f"inputs/model/{model}/lookup/variable_labels.csv")
        )
    else:
        labels_df = pl.DataFrame()

    parcel_geog = pl.read_database(
        query=f"SELECT * FROM parcel_{state.input_settings.base_year}_geography",
        connection=state.conn,
    )

    # Load data
    buffered_parcels = pl.read_csv(
        os.path.join(os.getcwd(), r"outputs/landuse/buffered_parcels.txt"),
        separator=" ",
    )

    if survey:
        hh_df = pl.read_csv("inputs/base_year/survey/_household.tsv", separator="\t")
        person_df = pl.read_csv("inputs/base_year/survey/_person.tsv", separator="\t")
        trip_df = pl.read_csv("inputs/base_year/survey/_trip.tsv", separator="\t")
        tour_df = pl.read_csv("inputs/base_year/survey/_tour.tsv", separator="\t")
    elif state.input_settings.abm_model == "daysim":
        daysim_h5 = h5py.File(os.path.join(path_dir_base, "daysim_outputs.h5"), "r")
        hh_df = h5_df(daysim_h5, "Household")
        person_df = h5_df(daysim_h5, "Person")
        trip_df = h5_df(daysim_h5, "Trip")
        tour_df = h5_df(daysim_h5, "Tour")
    else:
        # Parcelize MAZ-level outputs from Activitysim
        parcelize_outputs.main(state, output_dir=run_args.args.output_dir)

        hh_df = pl.read_parquet(os.path.join(run_args.args.output_dir, "final_households.parquet"))
        person_df = pl.read_parquet(os.path.join(run_args.args.output_dir, "final_persons_with_parcels.parquet"))
        trip_df = pl.read_parquet(os.path.join(run_args.args.output_dir, "final_trips_with_parcels.parquet"))
        tour_df = pl.read_parquet(os.path.join(run_args.args.output_dir, "final_tours_with_parcels.parquet"))

        # Ensure parcels are stored as int
        # FIXME: use datatypes
        trip_df = trip_df.with_columns(pl.col("origin_parcel").cast(pl.Int64))
        trip_df = trip_df.with_columns(pl.col("destination_parcel").cast(pl.Int64))
        tour_df = tour_df.with_columns(pl.col("origin_parcel").cast(pl.Int64))
        tour_df = tour_df.with_columns(pl.col("destination_parcel").cast(pl.Int64))
        person_df = person_df.with_columns(pl.col("workplace_parcel").cast(pl.Int64))
        person_df = person_df.with_columns(pl.col("school_parcel").cast(pl.Int64))
        hh_df = hh_df.with_columns(pl.col("hhparcel").cast(pl.Int64))

    # Add labels to data
    if labels_df.shape[0] > 0:
        labels_df = labels_df.with_columns(pl.col("value").cast(pl.String))

        hh_df = apply_labels("Household", hh_df, labels_df)
        person_df = apply_labels("Person", person_df, labels_df)
        trip_df = apply_labels("Trip", trip_df, labels_df)
        tour_df = apply_labels("Tour", tour_df, labels_df)
        

    # Join parcel lookup and buffered parcels data
    for geog_file_name, geog_file in {
        "parcel_geog": parcel_geog,
        "buffered_parcels": buffered_parcels,
    }.items():
        hh_df = merge_geography(
            hh_df,
            geography_lookup[
                (geography_lookup.right_table == geog_file_name)
                & (geography_lookup.left_table == "Household")
            ],
            geog_file,
        )

        person_df = merge_geography(
            person_df,
            geography_lookup[
                (geography_lookup.right_table == geog_file_name)
                & (geography_lookup.left_table == "Person")
            ],
            geog_file,
        )

        trip_df = merge_geography(
            trip_df,
            geography_lookup[
                (geography_lookup.right_table == geog_file_name)
                & (geography_lookup.left_table == "Trip")
            ],
            geog_file,
        )

        tour_df = merge_geography(
            tour_df,
            geography_lookup[
                (geography_lookup.right_table == geog_file_name)
                & (geography_lookup.left_table == "Tour")
            ],
            geog_file,
        )

    # Calculate variables
    var_expr_df = pd.read_csv(
        os.path.join(
            os.getcwd(), f"inputs/model/{model}/summaries/variables.csv"
        )
    )
    hh_df = process_variables(hh_df, var_expr_df, "household")
    person_df = process_variables(person_df, var_expr_df, "person")
    trip_df = process_variables(trip_df, var_expr_df, "trip")
    tour_df = process_variables(tour_df, var_expr_df, "tour")

    # Merge data across tables; drop and duplicated columns after each merge
    if state.input_settings.abm_model == "activitysim":
        household_id_col = "household_id"
        pno_col = "PNUM"
        person_hh_df = person_df.join(hh_df, on=household_id_col, how="left", suffix="_right")
        person_hh_df = person_hh_df.drop([col for col in person_hh_df.columns if col.endswith("_right")])
        trip_df = trip_df.join(person_hh_df, on="person_id", how="left", suffix="_right")
        trip_df = trip_df.drop([col for col in trip_df.columns if col.endswith("_right")])
        trip_df = trip_df.join(tour_df, on="tour_id", how="left", suffix="_right")
        trip_df = trip_df.drop([col for col in trip_df.columns if col.endswith("_right")])
        tour_df = tour_df.join(person_hh_df, on="person_id", how="left", suffix="_right")
        tour_df = tour_df.drop([col for col in tour_df.columns if col.endswith("_right")])
    else:
        # Merge tour columns to trips
        tour_cols = ["hhno", "pno", "tour", "tmodetp", "pdpurp"]

        # When we add geography we can drop the parcel level on which is was joined
        person_hh_df = person_df.join(hh_df, on="hhno", how="left")
        # Join tour to trip
        trip_df = trip_df.join(tour_df[tour_cols], on=["hhno", "pno", "tour"], how="left")
        trip_df = trip_df.join(person_hh_df, on=["hhno", "pno"], how="left")
        tour_df = tour_df.join(person_hh_df, on=["hhno", "pno"], how="left")

    # Iterate through the agg_expressions file
    process_expressions(hh_df, expr_df, "household", survey)
    process_expressions(person_hh_df, expr_df, "person", survey)
    process_expressions(trip_df, expr_df, "trip", survey)
    process_expressions(tour_df, expr_df, "tour", survey)


def main(state):
    start_time = time.time()
    for folder in ["dash", "census"]:
        create_dir(os.path.join(os.getcwd(), f"outputs/agg/{folder}"))
        create_dir(os.path.join(os.getcwd(), f"outputs/agg/{folder}/survey"))

    create_agg_outputs(
        state,
        path_dir_base=os.path.join(os.getcwd(), r"outputs/daysim"),
        model=state.input_settings.abm_model,
        survey=False,
    )

    # Use daysim definitions for survey data for now
    # create_agg_outputs(
    #     state,
    #     path_dir_base=os.path.join(os.getcwd(), r"inputs/base_year/survey"),
    #     model="daysim",
    #     survey=True,
    # )

    print("--- %s seconds ---" % (time.time() - start_time))


if __name__ == "__main__":
    main()
