import numpy as np
import pandas as pd
import h5py
import os, shutil
import re
import time
import polars as pl


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

        if survey:
            output_path = f"outputs/agg/{_row.output_dir}/survey/{_row.target}.csv"
        else:
            output_path = f"outputs/agg/{_row.output_dir}/{_row.target}.csv"
        agg_df.write_csv(output_path)


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


def create_agg_outputs(state, path_dir_base, base_output_dir, survey=False):
    geography_lookup = pd.read_csv(
        f"{state.model_input_dir}/summaries/geography_lookup.csv"
    )

    expr_df = pd.read_csv(
        os.path.join(
            os.getcwd(), f"{state.model_input_dir}/summaries/agg_expressions.csv"
        )
    )

    labels_df = pl.read_csv(
        os.path.join(f"{state.model_input_dir}/lookup/variable_labels.csv")
    )

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
    else:
        daysim_h5 = h5py.File(os.path.join(path_dir_base, "daysim_outputs.h5"), "r")

        hh_df = h5_df(daysim_h5, "Household")
        person_df = h5_df(daysim_h5, "Person")
        trip_df = h5_df(daysim_h5, "Trip")
        tour_df = h5_df(daysim_h5, "Tour")

    # Add labels to data
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

    # FIXME: This used to be taken care of from the variables CSV
    # How can we specify these outside of code?
    hh_df = hh_df.with_columns(
        hhincome_thousands=((pl.col("hhincome") / 1000).round(0) * 1000).cast(pl.Int32)
    )
    hh_df = hh_df.with_columns(
        quarter_mile_transit=pl.when(pl.col("hh_dist_transit") <= 0.25)
        .then(1)
        .otherwise(0)
    )
    hh_df = hh_df.with_columns(
        quarter_mile_hct=pl.when(pl.col("hh_dist_hct") <= 0.25).then(1).otherwise(0)
    )

    # Person
    person_df = person_df.with_columns(
        pwaudist_wt=pl.col("pwaudist") * pl.col("psexpfac")
    )
    person_df = person_df.with_columns(
        psaudist_wt=pl.col("psaudist") * pl.col("psexpfac")
    )
    person_df = person_df.with_columns(
        pwautime_wt=pl.col("pwautime") * pl.col("psexpfac")
    )
    person_df = person_df.with_columns(
        psautime_wt=pl.col("psautime") * pl.col("psexpfac")
    )
    person_df = person_df.with_columns(
        quarter_mile_transit_work=pl.when(pl.col("work_dist_transit") <= 0.25)
        .then(1)
        .otherwise(0)
    )
    person_df = person_df.with_columns(
        quarter_mile_hct_work=pl.when(pl.col("work_dist_hct") <= 0.25)
        .then(1)
        .otherwise(0)
    )

    # Trip
    trip_df = trip_df.with_columns(deptm_hr=pl.col("deptm").floordiv(60))
    trip_df = trip_df.with_columns(arrtm_hr=pl.col("arrtm").floordiv(60))
    trip_df = trip_df.with_columns(
        travdist_bin=pl.col("travdist").floordiv(1).cast(pl.Int32)
    )
    trip_df = trip_df.with_columns(
        travcost_bin=pl.col("travcost").floordiv(1).cast(pl.Int32)
    )
    trip_df = trip_df.with_columns(
        travtime_bin=pl.col("travtime").floordiv(1).cast(pl.Int32)
    )
    trip_df = trip_df.with_columns(travdist_wt=pl.col("travdist") * pl.col("trexpfac"))
    trip_df = trip_df.with_columns(travcost_wt=pl.col("travcost") * pl.col("trexpfac"))
    trip_df = trip_df.with_columns(travtime_wt=pl.col("travtime") * pl.col("trexpfac"))
    trip_df = trip_df.with_columns(
        sov_ff_time_wt=pl.col("sov_ff_time") / 100.0 * pl.col("trexpfac")
    )

    # Tour
    tour_df = tour_df.with_columns(tlvorg_hr=pl.col("tlvorig").floordiv(60))
    tour_df = tour_df.with_columns(tardest_hr=pl.col("tardest").floordiv(60))
    tour_df = tour_df.with_columns(tlvdest_hr=pl.col("tlvdest").floordiv(60))
    tour_df = tour_df.with_columns(tarorig_hr=pl.col("tarorig").floordiv(60))
    tour_df = tour_df.with_columns(
        tautotime_bin=pl.col("tautotime").floordiv(1).cast(pl.Int32)
    )
    tour_df = tour_df.with_columns(
        tautocost_bin=pl.col("tautocost").floordiv(1).cast(pl.Int32)
    )
    tour_df = tour_df.with_columns(
        tautodist_bin=pl.col("tautodist").floordiv(1).cast(pl.Int32)
    )
    tour_df = tour_df.with_columns(tour_duration=pl.col("tarorig") - pl.col("tlvorig"))

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
        base_output_dir=os.path.join(os.getcwd(), f"outputs/agg/{folder}"),
        survey=False,
    )

    create_agg_outputs(
        state,
        path_dir_base=os.path.join(os.getcwd(), r"inputs/base_year/survey"),
        base_output_dir=os.path.join(os.getcwd(), f"outputs/agg/{folder}/survey"),
        survey=True,
    )

    print("--- %s seconds ---" % (time.time() - start_time))


if __name__ == "__main__":
    main()
