import numpy as np
from sqlalchemy import create_engine
import polars as pl
import pandas as pd
from pathlib import Path
import toml

from scripts.summarize.notebook_styling import psrc_theme
from scripts.settings.state import InputSettings, SummarySettings

# person
ptype_cat = {1: "1: Full-Time Worker",
             2: "2: Part-Time Worker",
             3: "3: University Student",
             4: "4: Non-Working Adult Age <65",
             5: "5: Non-Working Adult Age 65+",
             6: "6: High School Student Age 16+",
             7: "7: Child Age 5-15",
             8: "8: Child Age 0-4"}
telecommute_frequency_cat = {"No_Telecommute": "0 day",
                             "1_day_week": "1 day",
                             "2_3_days_week": "2-3 days",
                             "4_days_week": "4 days"}
work_from_home_cat = {True: "wfh worker",
                      False: "on-site worker"}

# trip
outbound_cat = {True: "outbound",
                False: "inbound"}

def get_validation_data(summary_config, df_name, weight_col, uncloned=True):

    summary_settings = SummarySettings(**summary_config)
    run_path = summary_settings.sc_run_path

    # model data
    model = pl.read_parquet(Path(run_path) / f"final_{df_name}.parquet")
    
    model = model.with_columns(
        pl.lit("model").alias("source"),
        pl.lit(1.0).alias(weight_col)
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

        df = pl.read_csv(survey_path/ f"override_{df_name}.csv", 
                         # TODO: clean or remove prev_home_notwa_zip column in household table/ clean or remove string values in tour_type_id
                         schema_overrides={'prev_home_notwa_zip': pl.String,
                                           'tour_type_id': pl.String})

        # Add source column
        df = df.with_columns(
            pl.lit(source_name).alias("source")
        )

        survey_list.append(df)
    
    survey_data = pl.concat(survey_list)
    
    if df_name == "tours":
        survey_data = survey_data.rename({
            "survey_tour_id": "tour_id",
            "tour_distance": "tour_distance_one_way"})
    
    if df_name == "trips":
        survey_data = survey_data.rename({
            "trip_distance": "od_dist_drive",
            "survey_tour_id": "tour_id"
            })

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

def get_hh_data(summary_config, uncloned=True):
        
    hh_data = get_validation_data(summary_config, 
                                  "households", 
                                  "hh_weight", 
                                  uncloned)
    
    # data manipulation
    # add vehicle counts with 2+
    hh_data = hh_data.with_columns(
        [
            pl.when(pl.col('auto_ownership') >= 2).then(pl.lit("2+"))
            .otherwise(pl.col('auto_ownership'))
            .alias("auto_ownership_2+")
        ]
    )

    # add counts with 4+
    hh_data = hh_data.with_columns(
        [
            pl.when(pl.col(col) >= 4).then(pl.lit("4+"))
            .otherwise(pl.col(col))
            .alias(col + "_4+")
            for col in ['auto_ownership','hhsize','num_workers','num_drivers']
        ]
    )
    
    # add auto availability
    hh_data = hh_data.with_columns(
        [
            
            pl.when(pl.col(f"num_{col}s") <= 0).then(pl.lit(f"no {col}"))
            .when(pl.col('auto_ownership') <= 0).then(pl.lit("no car"))
            .when((pl.col('auto_ownership') - pl.col(f"num_{col}s")) < 0).then(pl.lit("cars fewer than drivers"))
            .otherwise(pl.lit("enough cars"))
            .alias("auto_available_" + col)
            for col in ['driver','worker']
        ]
    )

    # income groups
    hh_data = hh_data.with_columns(
        [
            pl.when(pl.col("source") != "model").then(None)
            .otherwise(pl.col("income"))
            .alias("income_model")
        ]
        )
    hh_data = hh_data.with_columns(
        [
            pl.when(pl.col("income") < 0).then(None)
            .when(pl.col("income") < pl.col("income_model").quantile(.25)).then(pl.lit("low"))
            .when(pl.col("income") < pl.col("income_model").quantile(.5)).then(pl.lit("medium"))
            .when(pl.col("income") < pl.col("income_model").quantile(.75)).then(pl.lit("medium-high"))
            .otherwise(pl.lit("high"))
            .alias("income_group")
        ]
    )
    hh_data = hh_data.with_columns(
        pl.col("income_group").cast(pl.Enum(["low","medium","medium-high","high"]), strict=False)
    )
    
    hh_data = hh_data.drop(["income_model"])

    # get quantile groups for specified columns
    col_list = ['log_emptot_1','log_hh_1']

    hh_data = hh_data.\
        join(get_landuse_data(summary_config, to_pandas=False).select(['zone_id','log_emptot_1','log_hh_1']), 
            how="left",left_on='home_zone_id',right_on='zone_id').\
        join(pl.read_csv(summary_config['p_maz_bg_lookup'])[['MAZ', 'block_group_id']], 
            how="left",left_on='home_zone_id',right_on='MAZ')

    # create landuse variable with only model values
    hh_data = hh_data.with_columns(
        [
            pl.when(pl.col("source") != "model").then(None)
            .otherwise(pl.col(col))
            .alias(col+"_model")
            for col in col_list
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
            .alias(col+"_group")
            for col in col_list
        ]        
    )
    hh_data = hh_data.with_columns(
        [
            pl.col(col+"_group").cast(pl.Enum(["very low","low","medium","medium-high","high"]), strict=False)
            for col in col_list
        ]
    
    )

    hh_data = hh_data.drop([col+"_model" for col in col_list])

    return hh_data.to_pandas()

def get_person_data(summary_config, uncloned=True):
        
    per_data = get_validation_data(summary_config, 
                                   "persons", 
                                   "person_weight", 
                                   uncloned)
    
    # data manipulation
    per_data = per_data.with_columns(

        pl.col("ptype")
        .replace_strict(ptype_cat, default=None)
        .alias("ptype_label"),

        pl.col("telecommute_frequency").
        replace_strict(telecommute_frequency_cat, default=None)
        .alias("telecommute_frequency_label"),

        pl.col("work_from_home")
        .replace_strict(work_from_home_cat, default=None)
        .alias("work_from_home_label")

    )
    # distance bins
    per_data = per_data.with_columns(
        [
            create_distance_bin(col)  
            .alias(col+'_bin')
            for col in ['distance_to_school','distance_to_work']
        ]
        
    )
    per_data = per_data.with_columns(
        [
            create_distance_bin_60mi(col)  
            .alias(col+'_bin_60mi')
            for col in ['distance_to_school','distance_to_work']
        ]
        
    )


    return per_data.to_pandas()

def get_trip_data(summary_config, uncloned=False):
        
    trip_data = get_validation_data(summary_config, 
                                    "trips", 
                                    "trip_weight", 
                                    uncloned)
    
    # data manipulation
    trip_data = trip_data.with_columns(
        pl.col("outbound").replace_strict(outbound_cat, default=None).alias("tour_direction")
    )

    trip_data = trip_data.with_columns(
        pl.when(pl.col("purpose") == "Home").then(pl.lit("home"))
        .otherwise(pl.col("purpose"))
        .alias("purpose")
    )

    # distance bins
    trip_data = trip_data.with_columns(
        create_distance_bin('od_dist_drive')
        .alias('trip_distance_bin'),

        create_distance_bin_60mi('od_dist_drive')
        .alias('trip_distance_bin_60mi')  
    )

    return trip_data.to_pandas()

def get_tour_data(summary_config, uncloned=False):
        
    tour_data = get_validation_data(summary_config, 
                                    "tours", 
                                    "tour_weight", 
                                    uncloned)
    
    # data manipulation

    # number of stops in outbound and inbound direction
    tour_data = tour_data.with_columns(
        pl.col("stop_frequency").cast(pl.String).str.slice(0, 1).alias("stop_frequency_out"),
        pl.col("stop_frequency").cast(pl.String).str.slice(-3, 1).alias("stop_frequency_in")
    )

    # distance bins
    tour_data = tour_data.with_columns(
        create_distance_bin('tour_distance_one_way')
        .alias('tour_distance_bin'),

        create_distance_bin_60mi('tour_distance_one_way')
        .alias('tour_distance_bin_60mi')  
    )

    return tour_data.to_pandas()

def get_landuse_data(summary_config, to_pandas=True):
    
    summary_settings = SummarySettings(**summary_config)
    run_path = summary_settings.sc_run_path
        
    landuse_data = pl.read_parquet(Path(run_path)/ "final_land_use.parquet")
    if to_pandas:
        landuse_data = landuse_data.to_pandas()
    return landuse_data
    
# create distance bins for distance columns
def create_distance_bin(col):
    return (
        pl.when(pl.col(col) < 0).then(None)
        .when(pl.col(col) < 1).then(pl.lit("dist_0_1"))
        .when(pl.col(col) < 2).then(pl.lit("dist_1_2"))
        .when(pl.col(col) < 5).then(pl.lit("dist_2_5"))
        .when(pl.col(col) < 15).then(pl.lit("dist_5_15"))
        .otherwise(pl.lit("dist_15_up"))
    )

# Create bins: bins of 2 miles up to 60 miles
def create_distance_bin_60mi(col):
    max_bin = 60
    bin_size = 2
    return (
        pl.col(col).cut(np.arange(bin_size, max_bin, bin_size), labels=[str(i) for i in np.arange(0, max_bin, bin_size)])
    )