import os
import toml
import pandas as pd
import numpy as np
import plotly.express as px

config = toml.load(
    os.path.join(
        os.getcwd(), r"../../../../configuration", "validation_configuration.toml"
    )
)


# Read data for model and survey data
def get_data(df_name, col_list=None, source=None, max_rows=None):
    if col_list is None:
        model_cols = None
        survey_cols = None
    else:
        model_cols = col_list
        survey_cols = col_list

    # model data
    if not source or "model" in source:
        model = pd.read_csv(
            os.path.join(
                config["model_dir"], "outputs", "daysim", "_" + df_name + ".tsv"
            ),
            sep="\t",
            usecols=model_cols,
            nrows=max_rows,
        )
        model["source"] = "model"
    else:
        model = pd.DataFrame()

    # survey data
    if df_name in ["tour", "trip", "person_day"]:
        # get cloned data
        # TODO: check trips?
        survey_path = config["tour_survey_dir"]
        survey_update_path = config["tour_survey_update_dir"]
        survey_2017_path = config["tour_survey_2017_dir"]
    else:
        # get uncloned data
        survey_path = config["survey_dir"]
        survey_update_path = config["survey_update_dir"]
        survey_2017_path = config["survey_2017_dir"]

    if not source or "survey" in source:
        survey = pd.read_csv(
            os.path.join(survey_path, "_" + df_name + ".tsv"),
            sep="\t",
            usecols=model_cols,
            nrows=max_rows,
        )
        survey["source"] = "survey"
    else:
        survey = pd.DataFrame()

    # survey (2017/2019) data
    if config["include_2017_2019"]:
        if not source or "survey (2017/2019)" in source:
            survey_2017 = pd.read_csv(
                os.path.join(survey_2017_path, "_" + df_name + ".tsv"),
                sep="\t",
                usecols=model_cols,
                nrows=max_rows,
            )
            survey_2017["source"] = "survey (2017/2019)"
        else:
            survey_2017 = pd.DataFrame()
    else:
        survey_2017 = pd.DataFrame()

    # 2024/12/10 updated survey data
    if config["include_update"]:
        if not source or "survey (update)" in source:
            survey_update = pd.read_csv(
                os.path.join(survey_update_path, "_" + df_name + ".tsv"),
                sep="\t",
                usecols=model_cols,
                nrows=max_rows,
            )
            survey_update["source"] = "survey (update)"
        else:
            survey_update = pd.DataFrame()
    else:
        survey_update = pd.DataFrame()

    df = pd.concat([model, survey, survey_update, survey_2017])

    return df
