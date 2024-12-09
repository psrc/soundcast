import os
import toml
import pandas as pd
import numpy as np
import plotly.express as px

config = toml.load(os.path.join(os.getcwd(), r'../../../../configuration', 'validation_configuration.toml'))

# Read data for model and survey data
def get_data(df_name, col_list=None, source=None, max_rows=None):

    if col_list is None:
        model_cols = None
        survey_cols = None
    else:
        model_cols = col_list
        survey_cols = col_list

    if not source or "model" in source:
        # print(f"read {df_name} model")
        model = pd.read_csv(os.path.join(config['model_dir'], 'outputs', 'daysim', '_'+df_name+'.tsv'),
                            sep='\t', usecols=model_cols, nrows=max_rows)
        model['source'] = "model"
    else:
        # print("don't read model")
        model = pd.DataFrame()

    # survey data
    if df_name in ['tour','person_day']:
        survey_path = config['tour_survey_dir']
        survey_2017_path = config['tour_survey_2017_dir']
    else:
        survey_path = config['survey_dir']
        survey_2017_path = config['survey_2017_dir']

    if not source or "survey" in source:
        # print(f"read {df_name} survey")
        survey = pd.read_csv(os.path.join(survey_path, '_'+df_name+'.tsv'),
                            sep='\t', usecols=model_cols, nrows=max_rows)
        survey['source'] = "survey"
    else:
        # print("don't read survey")
        survey = pd.DataFrame()

    if config['include_2017_2019']:
        if not source or "survey (2017/2019)" in source:
            # print(f"read {df_name} survey (2017/2019)")
            # 2017 survey data
            survey_2017 = pd.read_csv(os.path.join(survey_2017_path, '_'+df_name+'.tsv'),
                                    sep='\t', usecols=model_cols, nrows=max_rows)
            survey_2017['source'] = "survey (2017/2019)"
        else:
            # print("don't read survey (2017/2019)")
            survey_2017 = pd.DataFrame()
        df = pd.concat([model, survey, survey_2017])

    else:
        df = pd.concat([model, survey])

    return df