import numpy as np
from sqlalchemy import create_engine
import polars as pl
import pandas as pd
from pathlib import Path
import toml
import plotly.express as px

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

# landuse
county = {1: "King",
          2: "Kitsap",
          3: "Pierce",
          4: "Snohomish"}

transit_modes = ['WALK_LOC','WALK_COM','WALK_FRY','WALK_LR','DRIVE_TRN']
all_modes_transit_agg = ["DRIVEALONEFREE", "SHARED2FREE", "SHARED3FREE", "BIKE","WALK","ALL_TRANSIT","SCH_BUS","TNC","Other"]

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
        join(pl.read_csv("R:/e2projects_two/activitysim/estimation/2017_2019_data/validation_data/auto_ownership/maz_bg_lookup.csv")[['MAZ', 'block_group_id']], 
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

def get_person_data(summary_config, uncloned=True, get_cdap=False):
        
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

        # get tour direction
        pl.col("outbound").replace_strict(outbound_cat, default=None)
        .cast(pl.Enum(['outbound','inbound']), strict=False)
        .alias("tour_direction"),

        # clean up purpose labels
        pl.when(pl.col("purpose") == "Home").then(pl.lit("home"))
        .otherwise(pl.col("purpose"))
        .alias("purpose"),

        # aggregate transit modes
        pl.when(pl.col("trip_mode").is_in(transit_modes))
        .then(pl.lit("ALL_TRANSIT"))
        .otherwise(pl.col("trip_mode"))
        .cast(pl.Enum(all_modes_transit_agg), strict=False)
        .alias("trip_mode_transit_agg"),

        # only transit modes
        pl.when(pl.col("trip_mode").is_in(transit_modes))
        .then(pl.col("trip_mode"))
        .otherwise(None)
        .alias("trip_mode_transit_only")
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
    tour_data = tour_data.with_columns(
        # reassign tour category to mandatory vs non-mandatory
        pl.when(pl.col("tour_type").is_in(["work", "school"]))
        .then(pl.lit("mandatory"))
        .otherwise(pl.lit("non_mandatory"))
        .alias("tour_cat_reassign")
    )

    tour_data = tour_data.with_columns(
        # number of stops in outbound and inbound direction
        pl.col("stop_frequency").cast(pl.String).str.slice(0, 1).alias("stop_frequency_out"),
        pl.col("stop_frequency").cast(pl.String).str.slice(-3, 1).alias("stop_frequency_in")
    )
    
    tour_data = tour_data.with_columns(
        # total stops
        (pl.col("stop_frequency_out").cast(pl.Int32) + pl.col("stop_frequency_in").cast(pl.Int32)).alias("stop_frequency_total")
    )
    
    tour_data = tour_data.with_columns(
        # aggregate transit modes
        pl.when(pl.col("tour_mode").is_in(transit_modes))
        .then(pl.lit("ALL_TRANSIT"))
        .otherwise(pl.col("tour_mode"))
        .cast(pl.Enum(all_modes_transit_agg), strict=False)
        .alias("tour_mode_transit_agg"),

        # only transit modes
        pl.when(pl.col("tour_mode").is_in(transit_modes))
        .then(pl.col("tour_mode"))
        .otherwise(None)
        .alias("tour_mode_transit_only")
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

    # data manipulation
    landuse_data = landuse_data.with_columns(

        pl.col("county_id")
        .replace_strict(county, default=None)
        .alias("county_label")

    )

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
        .cast(pl.Enum(["dist_0_1", "dist_1_2", "dist_2_5", "dist_5_15", "dist_15_up"]), strict=False)
    )

# Create bins: bins of 2 miles up to 60 miles
def create_distance_bin_60mi(col):
    max_bin = 60
    bin_size = 2
    return (
        pl.col(col).cut(np.arange(bin_size, max_bin, bin_size), labels=[str(i) for i in np.arange(0, max_bin, bin_size)])
    )

# plotting functions

def plot_share_barchart(data, weight, share_col, 
                        title, height=400, width=700):
    """
    simple bar chart showing share
    """
    # calculate sample size and percentages
    df_plot = data.groupby(['source', share_col], observed=True).\
        agg(sample_size=(weight, 'size'),
            weighted_sum=(weight, 'sum')).reset_index()
    df_plot['percentage'] = df_plot.groupby('source', group_keys=False, observed=True)['weighted_sum']. \
        apply(lambda x: x / float(x.sum()))

    fig = px.bar(df_plot, x=share_col, y="percentage", color="source",barmode="group",
                hover_data=["sample_size"],
                title=title)
    fig.for_each_annotation(lambda a: a.update(text = a.text.split("=")[-1]))
    fig.update_layout(height=height, width=width, yaxis=dict(tickformat=".1%"))
    fig.show()

def plot_share_facetbar(data, weight, share_col, title, 
                        facet_col, facet_col_wrap=3,
                        height=400, orientation='h'):
    """
    faceted bar chart showing share by segment
    """

    if orientation == 'h':
        x = "percentage"
        y = share_col
    else:
        x = share_col
        y = "percentage"
    
    # calculate sample size and percentages
    df_plot = data.groupby(['source', facet_col, share_col], observed=True).\
        agg(sample_size=(weight, 'size'),
            weighted_sum=(weight, 'sum')).reset_index()
    df_plot['percentage'] = df_plot.groupby(['source',facet_col], group_keys=False, observed=True)['weighted_sum']. \
        apply(lambda x: x / float(x.sum()))

    fig = px.bar(df_plot, x=x, y=y, color="source",barmode="group",
                hover_data=["sample_size"],
                 facet_col=facet_col, facet_col_wrap=facet_col_wrap, orientation=orientation,
                 title=title)
    fig.for_each_annotation(lambda a: a.update(text = a.text.split("=")[-1]))
    fig.update_layout(height=height, width=750)

    if orientation == 'h':
        fig.update_layout(xaxis1=dict(tickformat=".0%"), xaxis2=dict(tickformat=".0%"))
    else:
        fig.update_layout(yaxis1=dict(tickformat=".0%"), yaxis2=dict(tickformat=".0%"))

    fig.show()
