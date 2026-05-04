import numpy as np
from sqlalchemy import create_engine
import polars as pl
from pathlib import Path
import toml

from scripts.summarize.notebook_styling import psrc_theme
from scripts.settings.state import InputSettings, SummarySettings


# config = toml.load(Path.cwd() / "../../../../configuration/input_configuration.toml")
# summary_config = toml.load(Path.cwd() / "../../../../configuration/summary_configuration.toml")

# input_settings = InputSettings(**config)
# summary_settings = SummarySettings(**summary_config)
# run_path = summary_settings.sc_run_path

# person
pptyp_cat = {1: "1: full time worker",
             2: "2: part time worker",
             3: "3: non-worker age 65+",
             4: "4: other non-working adult",
             5: "5: university student",
             6: "6: grade school student/child age 16+",
             7: "7: child age 5-15",
             8: "8: child age 0-4"}
# tour
tmodetp_cat = {1: "1: walk",
               2: "2: bike",
               3: "3: sov",
               4: "4: hov 2",
               5: "5: hov 3+",
               6: "6: walk to transit",
               7: "7: park-and-ride",
               8: "8: school bus",
               9: "9: tnc"}
pdpurp_cat = {1: "1: Work",
              2: "2: School",
              3: "3: Escort",
              4: "4: Personal Business",
              5: "5: Shop",
              6: "6: Meal",
              7: "7: Social"}

# trip
mode_cat = {1: "1: walk",
            2: "2: bike",
            3: "3: sov",
            4: "4: hov 2",
            5: "5: hov 3+",
            6: "6: transit",
            8: "8: school bus",
            9: "9: tnc"}


def get_validation_data(summary_config, df_name, uncloned=True):

    summary_settings = SummarySettings(**summary_config)
    run_path = summary_settings.sc_run_path
    
    # model data
    model = pl.read_csv(
        Path(run_path)/ f"outputs/daysim/_{df_name}.tsv",
        separator="\t"
    )

    # Add source column and apply expected data types to data when read in
    model = model.with_columns(
        pl.lit("model").alias("source"),
        pl.col("^.*expfac.*$").cast(pl.Float64)
    )

    # Generate a placeholder column for worker type
    if df_name == "person":
        model = model.with_columns(
            worker_type = pl.lit("null")
        )

    # survey data
    survey_list = []

    # read survey data in all sources
    for source_name in summary_settings.survey_directories.keys():
        
        if uncloned:
            # get uncloned data
            survey_path = Path(summary_settings.survey_directories[source_name])/ summary_settings.uncloned_folder
        else:
            # get cloned data
            survey_path = Path(summary_settings.survey_directories[source_name])

        df = pl.read_csv(survey_path/ f"_{df_name}.tsv", separator="\t")

        # Add source column
        df = df.with_columns(
            pl.lit(source_name).alias("source")
        )

        survey_list.append(df)
    
    survey_data = pl.concat(survey_list)
    
    col_list = np.intersect1d(survey_data.columns, model.columns)
    survey_data = survey_data[col_list]
    model = model[col_list]

    # align survey data to model schema
    model_schema = model.schema
    survey_data = survey_data.with_columns([
        pl.col(col_name).cast(new_type) for col_name, new_type in model_schema.items()
    ])

    data = pl.concat([survey_data,model])

    return data

def get_hh_data(summary_config, uncloned=True, quantile_groups=None):
    
    hh_data = get_validation_data(summary_config, "household", uncloned)

    # data manipulation
    hh_data = hh_data.with_columns(
        # hhwkrs is not always accurate; recalculate from part and full time workers
        (pl.col('hhftw') + pl.col('hhptw'))
        .alias('hhwkrs'),
        # Add column for (potential) drivers adults (all hh members 16 and above)
        (pl.col('hhsize') - pl.col('hh515') - pl.col('hhcu5'))
        .alias('drivers')
    )

    hh_data = hh_data.with_columns(
        [
            # add counts with 4+
            pl.when(pl.col(col) >= 4).then(pl.lit("4+"))
            .otherwise(pl.col(col))
            .alias(col + "_4+")
            for col in ['hhvehs','hhsize','hhwkrs','drivers']
        ]
    )

    hh_data = hh_data.with_columns(
        [
            # add auto availability
            pl.when(pl.col(col) <= 0).then(pl.lit("no driver"))
            .when(pl.col('hhvehs') <= 0).then(pl.lit("no car"))
            .when((pl.col('hhvehs') - pl.col(col)) < 0).then(pl.lit("cars fewer than drivers"))
            .otherwise(pl.lit("enough cars"))
            .alias("auto_available_" + col)
            for col in ['drivers','hhwkrs']
        ]
    )

    # get quantile groups for specified columns
    if quantile_groups:
        land_use = get_parcel_landuse_data(summary_config).select('parcelid','emptot_1','hh_1')
        hh_data = hh_data.join(land_use, left_on="hhparcel", right_on="parcelid", how="left")

        # create landuse variable with only model values
        hh_data = hh_data.with_columns(
            [
                pl.when(pl.col("source") != "model").then(None)
                .otherwise(pl.col(col))
                .alias(col+"_model")
                for col in quantile_groups
            ]
            )
        
        hh_data = hh_data.with_columns(
            [
                pl.when(pl.col(col) < 0).then(None)
                .when(pl.col(col) < pl.col(col+"_model").quantile(.125)).then(pl.lit("very low"))
                .when(pl.col(col) < pl.col(col+"_model").quantile(.25)).then(pl.lit("low"))
                .when(pl.col(col) < pl.col(col+"_model").quantile(.5)).then(pl.lit("medium"))
                .when(pl.col(col) < pl.col(col+"_model").quantile(.75)).then(pl.lit("medium-high"))
                .otherwise(pl.lit("high"))
                .alias(col+"_4group")
                for col in quantile_groups
            ]
        )

        hh_data = hh_data.drop([col+"_model" for col in quantile_groups])

    return hh_data

def get_person_data(summary_config, uncloned=True):
        
    per_data = get_validation_data(summary_config, "person", uncloned)
    
    # data manipulation
    per_data = per_data.with_columns(
        pl.col("pptyp").replace_strict(pptyp_cat, default=None).alias("pptyp_label")
    )

    return per_data

def get_person_day_data(summary_config, uncloned=True):
    
    per_day_data = get_validation_data(summary_config, "person_day", uncloned)
    return per_day_data

def get_tour_data(summary_config, uncloned=True):
        
    tour_data = get_validation_data(summary_config, "tour", uncloned)
    
    # data manipulation
    tour_data = tour_data.with_columns(

        # get tour mode labels
        pl.col("tmodetp").replace_strict(tmodetp_cat, default=None)
        .alias("tmodetp_label"),

        # get tour purpose labels
        pl.col("pdpurp").replace_strict(pdpurp_cat, default=None)
        .alias("pdpurp_label")
        )

    return tour_data

def get_trip_data(summary_config, uncloned=True):
    
    trip_data = get_validation_data(summary_config, "trip", uncloned)

    # data manipulation
    trip_data = trip_data.with_columns(

        # get trip mode labels
        pl.col("mode").replace_strict(mode_cat, default=None)
        .alias("mode_label")

    )

    return trip_data

def get_parcel_landuse_data(summary_config):
    
    summary_settings = SummarySettings(**summary_config)
    run_path = summary_settings.sc_run_path

    # parcel land use data
    df_parcel = pl.read_csv(
        Path(run_path)/"outputs/landuse/buffered_parcels.txt",
        separator=" ",
    )

    return df_parcel

def read_sqlite_db(input_config, summary_config, query):
    """get parcel geography data from sqlite database"""
        
    input_settings = InputSettings(**input_config)
    summary_settings = SummarySettings(**summary_config)
    run_path = summary_settings.sc_run_path

    async_engine = create_engine('sqlite:///' + run_path + '/inputs/db/' + input_settings.db_name)
    df = pl.read_database(query= query,
                          connection=async_engine.connect()
                          )

    return df

def get_parcel_geog(input_config, summary_config):
    """get parcel geography data from sqlite database"""
    
    input_settings = InputSettings(**input_config)

    parcel_geog = read_sqlite_db(input_config, summary_config, "SELECT * FROM parcel_" + input_settings.base_year + "_geography")

    return parcel_geog

