import numpy as np
import pandas as pd
import h5py
import os, shutil
import re
import time
import polars as pl


# Define relationships between daysim files
daysim_merge_fields = {
    "Trip": {
        "Tour": ["hhno", "pno", "tour"],
        "Person": ["hhno", "pno"],
        "Household": ["hhno"],
    },
    "Person": {"Household": ["hhno"]},
    "Tour": {"Person": ["hhno", "pno"], "Household": ["hhno"]},
}


dash_table_list = [
    "vmt_facility",
    "vht_facility",
    "delay_facility",
    "vmt_user_class",
    "vht_user_class",
    "delay_user_class",
]


def get_dict_values(d):
    """Return unique dictionary values for a 2-level dictionary"""

    _list = []
    for k, v in d.iteritems():
        if isinstance(v, dict):
            for _k, _v in v.iteritems():
                _list += _v
        else:
            _list += v
        _list = list(np.unique(_list))

    return _list


def create_dir(_dir):
    if os.path.exists(_dir):
        shutil.rmtree(_dir)
    os.makedirs(_dir)


def get_row_col_list(row, full_col_list):
    row_list = ["agg_fields", "values"]
    for field_type in ["filter_fields"]:
        if type(row[field_type]) != float:
            row_list += [field_type]
    col_list = list(row[row_list].values)
    col_list = [i.split(",") for i in col_list]
    col_list = list(
        np.unique([item.strip(" ") for sublist in col_list for item in sublist])
    )

    # Identify column values from query field with regular expressions
    if type(row["query"]) != float:
        # query_fields_cols = [i.strip() for i in re.split(',|>|==|>=|<|<=|!=|&',row['query'])]
        regex = re.compile("[^a-zA-Z]")
        query_fields_cols = [
            regex.sub("", i).strip()
            for i in re.split(",|>|==|>=|<|<=|!=|&", row["query"])
        ]
        for query in query_fields_cols:
            if query in full_col_list and query not in col_list:
                col_list += [query]

    return col_list


def merge_geography(df, df_geog, df_geographic_lookup):
    for _index, _row in df_geog.iterrows():

        right_df = df_geographic_lookup[[_row.right_index,_row.right_column]]
        df = df.join(right_df, left_on=_row.left_index, 
                    right_on=_row.right_index,
                    how='left')
        df = df.rename({_row.right_column: _row.right_column_rename})
        
    return df


def execute_eval(df, row, col_list, fname):
    print(fname)
    # Process query field
    query = ""
    if type(row["query"]) != float:
        query = """.query('""" + str(row["query"]) + """')"""

    agg_fields_cols = [i.strip() for i in row["agg_fields"].split(",")]
    values_cols = [i.strip() for i in row["values"].split(",")]

    if type(row["filter_fields"]) == float:
        expr = (
            "df["
            + str(col_list)
            + "]"
            + query
            + ".groupby("
            + str(agg_fields_cols)
            + ")."
            + row["aggfunc"]
            + "()["
            + str(values_cols)
            + "]"
        )

        # Write results to target output
        df_out = pd.eval(expr, engine="python").reset_index()
        _labels_df = labels_df[labels_df["field"].isin(df_out.columns)]
        for field in _labels_df["field"].unique():
            _df = _labels_df[_labels_df["field"] == field]
            local_series = pd.Series(_df["text"].values, index=_df["value"])
            df_out[field] = df_out[field].map(local_series)

        df_out.to_csv(fname + ".csv", index=False)
    else:
        filter_cols = np.unique([i.strip() for i in row["filter_fields"].split(",")])
        for _filter in filter_cols:
            unique_vals = np.unique(df[_filter].values.astype("str"))
            for filter_val in unique_vals:
                expr = (
                    "df["
                    + str(col_list)
                    + "][df['"
                    + str(_filter)
                    + "'] == '"
                    + str(filter_val)
                    + "']"
                    + ".groupby("
                    + str(agg_fields_cols)
                    + ")."
                    + row["aggfunc"]
                    + "()["
                    + str(values_cols)
                    + "]"
                )

                # Write results to target output
                df_out = pd.eval(expr, engine="python").reset_index()

                # # Apply labels
                _labels_df = labels_df[labels_df["field"].isin(df_out.columns)]
                for field in _labels_df["field"].unique():
                    _df = _labels_df[_labels_df["field"] == field]
                    local_series = pd.Series(_df["text"].values, index=_df["value"])
                    df_out[field] = df_out[field].map(local_series)

                df_out.to_csv(
                    fname + "_" + str(_filter) + "_" + str(filter_val) + ".csv",
                    index=False,
                )


def h5_df(h5file, table, col_list):
    df = pd.DataFrame()
    for col in h5file[table].keys():
        if col in col_list:
            print(col)
            # Get dtype
            col_type = type(h5file[table][col][0]) 
            df[col] = h5file[table][col][:].astype(col_type)

    df = pl.from_pandas(df)

    return df


def create_agg_outputs(state, path_dir_base, base_output_dir, survey=False):
    # # Load the expression file
    # expr_df = pd.read_csv(
    #     os.path.join(os.getcwd(), f"{state.model_input_dir}/summaries/agg_expressions.csv")
    # )
    # expr_df = expr_df.fillna('__remove__')    # Fill NA with string signifying data to be ignored
    geography_lookup = pd.read_csv(
        "inputs/model/daysim/summaries/geography_lookup.csv")
    
    # variables_df = pd.read_csv(
    #     os.path.join(os.getcwd(), f"{state.model_input_dir}/summaries/variables.csv")
    # )
    # global labels_df
    # labels_df = pd.read_csv(
    #     os.path.join(os.getcwd(), f"{state.model_input_dir}/lookup/variable_labels.csv")
    # )

    # geog_cols = list(
    #     np.unique(
    #         geography_lookup[geography_lookup.right_table == "parcel_geog"][
    #             ["right_column", "right_index"]
    #         ].values
    #     )
    # )
    # # Add geographic lookups at parcel level; only load relevant columns

    # #######remove or fix!
    # geog_cols = [col for col in geog_cols if col != "place_name"]
    # #################
    # parcel_geog = pd.read_sql_table(
    #     "parcel_2023_geography",
    #     state.conn,
    # )
    parcel_geog = pl.read_database(
        query="SELECT * FROM parcel_2023_geography",
        connection=state.conn,
    )
    # buffered_parcels_cols = list(
    #     np.unique(
    #         geography_lookup[geography_lookup.right_table == "buffered_parcels"][
    #             ["right_column", "right_index"]
    #         ]
    #     )
    # )

    # Load data
    buffered_parcels = pl.read_csv(
        os.path.join(os.getcwd(), r"outputs/landuse/buffered_parcels.txt"),
        separator=" ",
    )

  

    # Create output folder for flattened output
    if survey:
        survey_str = "survey"
        # Get a list of headers for all daysim records so we can load data in as needed

    else:
        survey_str = ""
        # create h5 table of daysim outputs
        daysim_h5 = h5py.File(os.path.join(path_dir_base, "daysim_outputs.h5"), "r")
        # daysim_h5 = h5py.File()

    # only load in specified columns
    # hh_col_list = ["hhno","hhexpfac","hhsize","hh515","hhcu5","hhftw","hhhsc","hhincome","hhparcel",
    #                 "hhptw", "hhtaz","hhuni","hhvehs","hhwkrs"]
    # person_col_list = ["hhno","pagey","pgend","pno","psexpfac","ptpass","pwpcl","pwtyp"]
    # trip_col_list = ["hhno","pno","dorp","opcl","dpcl","trexpfac"]
    # tour_col_list = ["hhno","pno","pdpurp","topcl","tdpcl","tautocost","tautodist","tautotime","toexpfac"]

    
    hh_full_col_list = pd.read_csv(
        os.path.join(path_dir_base, "_household.tsv"), sep="\t", nrows=0
    )
    person_full_col_list = pd.read_csv(
        os.path.join(path_dir_base, "_person.tsv"), sep="\t", nrows=0
    )
    trip_full_col_list = pd.read_csv(
        os.path.join(path_dir_base, "_trip.tsv"), sep="\t", nrows=0
    )
    tour_full_col_list = pd.read_csv(
        os.path.join(path_dir_base, "_tour.tsv"), sep="\t", nrows=0
    )

    hh_df = h5_df(daysim_h5, "Household", hh_full_col_list)
    person_df = h5_df(daysim_h5, "Person", person_full_col_list)
    trip_df = h5_df(daysim_h5, "Trip", trip_full_col_list)
    tour_df = h5_df(daysim_h5, "Tour", tour_full_col_list)

    
    # Merge to geography lookup
    # Use geography_lookup.csv to create new geographic variables, depending on the table
    # Do this before merging household, person etc files
    # household
    # df = geography_lookup[(geography_lookup['left_table']=='Household') & 
    #                         (geography_lookup['right_table']=='parcel_geog')]
    # FIXME: do this join as an index, join on multiple columns?

    # Merge parel lookup data
    # hh_df = merge_geography(
    #             hh_df,
    #             geography_lookup[
    #                 (geography_lookup.right_table == "parcel_geog")
    #                 & (geography_lookup.left_table == "Household")
    #             ],
    #             parcel_geog
    #         )

    # Join parcel lookup and buffered parcels data
    for geog_file_name, geog_file in {
        "parcel_geog": parcel_geog, 
        "buffered_parcels": buffered_parcels}.items():
        hh_df = merge_geography(
                    hh_df,
                    geography_lookup[
                        (geography_lookup.right_table == geog_file_name)
                        & (geography_lookup.left_table == "Household")
                    ],
                    geog_file
                )

        person_df = merge_geography(
                    person_df,
                    geography_lookup[
                        (geography_lookup.right_table == geog_file_name)
                        & (geography_lookup.left_table == "Person")
                    ],
                    geog_file
                )

        trip_df = merge_geography(
                    trip_df,
                    geography_lookup[
                        (geography_lookup.right_table == geog_file_name)
                        & (geography_lookup.left_table == "Trip")
                    ],
                    geog_file
                )

        tour_df = merge_geography(
                    tour_df,
                    geography_lookup[
                        (geography_lookup.right_table == geog_file_name)
                        & (geography_lookup.left_table == "Tour")
                    ],
                    geog_file
                )

    # FIXME: This used to be taken care of from the variables CSV
    # How can we specify these outside of code?
    hh_df = hh_df.with_columns(
        hhincome_thousands = ((pl.col('hhincome')/1000).round(0)*1000).cast(pl.Int32)
        )
    hh_df = hh_df.with_columns(
        quarter_mile_transit = pl.when(pl.col("hh_dist_transit") <= 0.25).then(1).otherwise(0)
    )
    hh_df = hh_df.with_columns(
        quarter_mile_hct = pl.when(pl.col("hh_dist_hct") <= 0.25).then(1).otherwise(0)
    )

    # Person
    person_df = person_df.with_columns(
        pwaudist_wt = pl.col("pwaudist") * pl.col("psexpfac")
        )
    person_df = person_df.with_columns(
            psaudist_wt = pl.col("psaudist") * pl.col("psexpfac")
            )
    person_df = person_df.with_columns(
        pwautime_wt = pl.col("pwautime") * pl.col("psexpfac")
        )
    person_df = person_df.with_columns(
        psautime_wt = pl.col("psautime") * pl.col("psexpfac")
        )
    person_df = person_df.with_columns(
        quarter_mile_transit_work = pl.when(pl.col("work_dist_transit") <= 0.25).then(1).otherwise(0)
    )
    person_df = person_df.with_columns(
        quarter_mile_hct_work = pl.when(pl.col("work_dist_hct") <= 0.25).then(1).otherwise(0)
    )

    # Trip
    trip_df = trip_df.with_columns(
        deptm_hr = pl.col("deptm").floordiv(60)
        )
    trip_df = trip_df.with_columns(
        arrtm_hr = pl.col("arrtm").floordiv(60)
        )
    # trip,travdist_bin,travdist,trip['travdist'].floordiv(1).astype('int'),
    # trip,travcost_bin,travcost,trip['travcost'].floordiv(1).astype('int'),
    # trip,travtime_bin,travtime,trip['travtime'].floordiv(1).astype('int'),
    # trip,travdist_wt,travdist,trip['travdist']*trip['trexpfac'],
    # trip,travcost_wt,travcost,trip['travcost']*trip['trexpfac'],
    # trip,travtime_wt,travtime,trip['travtime']*trip['trexpfac'],
    # trip,sov_ff_time_wt,sov_ff_time,(trip['sov_ff_time']/100.0)*trip['trexpfac'],

    # Tour
    # tour,tlvorg_hr,tlvorig,(tour['tlvorig']).floordiv(60),
    # tour,tardest_hr,tardest,(tour['tardest']).floordiv(60),
    # tour,tlvdest_hr,tlvdest,(tour['tlvdest']).floordiv(60),
    # tour,tarorig_hr,tarorig,(tour['tlvdest']).floordiv(60),
    # tour,tautotime_bin,tautotime,tour['tautotime'].floordiv(1).astype('int'),
    # tour,tautocost_bin,tautocost,tour['tautocost'].floordiv(1).astype('int'),
    # tour,tautodist_bin,tautodist,tour['tautodist'].floordiv(1).astype('int'),
    # tour,tour_duration,tlvorig,tour['tarorig'] - tour['tlvorig'],

    # When we add geogrpahy we can drop the parcel level on which is was joined  
    person_hh_df = person_df.join(hh_df, on='hhno', how='left')
    trip_df = trip_df.join(person_hh_df, on=['hhno','pno'], how='left')
    tour_df = tour_df.join(person_hh_df, on=['hhno','pno'], how='left')


    # Iterate through the agg_expressions file
    expr_df = pd.read_csv(
        os.path.join(os.getcwd(), f"{state.model_input_dir}/summaries/agg_expressions.csv")
    )

    ##############################
    # Household
    ##############################
    hh_expr_df = expr_df[expr_df['table']=='household']
    # Also select where we're aggregating by sum
    for _index, _row in hh_expr_df.iterrows():
        agg_cols = [item.strip() for item in  _row['agg_fields'].split(',')]
        df = hh_df.group_by(agg_cols).agg(pl.col(_row['values']).sum())  
        df.write_csv('outputs/agg/dash/{_row.target}.csv')

    ##############################
    # Person
    ##############################
    person_expr_df = expr_df[expr_df['table']=='person']
    # Also select where we're aggregating by sum
    for _index, _row in person_expr_df.iterrows():
        agg_cols = [item.strip() for item in  _row['agg_fields'].split(',')]
        df = person_hh_df.group_by(agg_cols).agg(pl.col(_row['values']).sum())  
        df.write_csv('outputs/agg/dash/{_row.target}.csv')

    ##############################
    # Trip
    ##############################


    ##############################
    # Tour
    ##############################


def main(state):
    start_time = time.time()
    output_dir_base = os.path.join(os.getcwd(), "outputs/agg/dash")
    create_dir(output_dir_base)

    input_dir = os.path.join(os.getcwd(), r"outputs/daysim")
    create_agg_outputs(state, input_dir, output_dir_base, survey=False)

    print("--- %s seconds ---" % (time.time() - start_time))
    print('test')

    # survey_input_dir = os.path.join(os.getcwd(), r"inputs/base_year/survey")
    # create_agg_outputs(state, survey_input_dir, output_dir_base, survey=True)

    # copy_dash_tables(dash_table_list)


if __name__ == "__main__":
    start_time = time.time()
    main()
    print("--- %s seconds ---" % (time.time() - start_time))
