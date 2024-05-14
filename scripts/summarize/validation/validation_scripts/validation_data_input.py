import os
import toml
import pandas as pd
import numpy as np
import plotly.express as px

config = toml.load(os.path.join(os.getcwd(), r'../../../../configuration', 'validation_configuration.toml'))

# Read data for model and survey data
def get_data(df_name, survey_data_path, col_list=None):

    if col_list is None:
        model_cols = None
        survey_cols = None
    else:
        model_cols = col_list
        survey_cols = col_list

    # model data
    model = pd.read_csv(os.path.join(config['model_dir'], 'outputs', 'daysim', '_'+df_name+'.tsv'), sep='\t', usecols=model_cols)
    model['source'] = "model"

    # survey data
    survey = pd.read_csv(os.path.join(survey_data_path, '_'+df_name+'.tsv'), sep='\t', usecols=model_cols)
    survey['source'] = "survey"

    df = pd.concat([model, survey])

    return df