import os, sys
import numpy as np
from sqlalchemy import create_engine
import polars as pl
import pandas as pd
from scipy import stats
from pathlib import Path
import toml
import plotly.express as px
from IPython.display import display

module_path = os.path.abspath(os.path.join('../../../..')) # or the path to your source code
sys.path.insert(0, module_path)

from scripts.summarize.notebook_styling import psrc_theme
from scripts.settings.state import InputSettings, SummarySettings


def read_sqlite_db(input_config, summary_config, query):
    """get parcel geography data from sqlite database"""
        
    input_settings = InputSettings(**input_config)
    summary_settings = SummarySettings(**summary_config)
    run_path = summary_settings.sc_run_path

    async_engine = create_engine('sqlite:///' + run_path + '/inputs/db/' + input_settings.db_name)
    df = pl.read_database(query= query,
                          connection=async_engine.connect()
                          )

    return df.to_pandas()

def get_parcel_geog(input_config, summary_config):
    """get parcel geography data from sqlite database"""
    
    input_settings = InputSettings(**input_config)

    parcel_geog = read_sqlite_db(input_config, summary_config, "SELECT * FROM parcel_" + input_settings.base_year + "_geography")

    return parcel_geog

def plot_observed_modeled_scatter(df_plot, observe_var, model_var, title, hover_vars =[], height=450, width=600):

    # get the max value for plot limit
    lim = df_plot[[observe_var, model_var]].max().max() * 1.05

    # build scatterplot
    fig = px.scatter(df_plot, 
                     x=observe_var, y=model_var, 
                     hover_data=hover_vars, 
                     trendline="ols",
                     title=title)

    # add x=y line
    fig.add_shape(
        type="line",
        x0=0, x1=lim, y0=0, y1=lim,
        line=dict(color="Red", width=2, dash="dash"),
    )

    fig.update_traces(marker=dict(size=4))
    fig.update_traces(selector=dict(mode="lines"), line_color="grey", line_width=2)
    fig.update_xaxes(range=[0, lim])
    fig.update_yaxes(range=[0, lim])
    fig.update_layout(height=height, width=width)
    fig.show()

    # calculate stats
    slope, intercept, r_value, p_value, std_err = stats.linregress(df_plot[observe_var],df_plot[model_var])

    summary_df = pd.DataFrame(
        {
            "Metric": [
                        "Slope (Sensitivity)",
                        "Intercept (Bias)",
                        "R-squared (R²)",
                        "p-value (Significance)",
                        "Std Error",
                    ],
                    "Value": [slope, intercept, r_value**2, p_value, std_err]
        }
    )

    # scientific notation for p-value, 4 decimals for others
    styled_summary = summary_df.style.format(
        {"Value": lambda x: f"{x:.4e}" if x < 0.001 and x > 0 else f"{x:.4f}"}
    ).hide(axis="index")

    # Display the styled table (just evaluate it at the end of a cell)
    display(styled_summary)

def table_observed_modeled_percent_diff(df_table: pd.DataFrame, 
                                        observe_vars: list, 
                                        model_var: str):

    target_cols = [model_var] + observe_vars
    other_cols = [col for col in df_table.columns if col not in target_cols]
    
    if other_cols:
        df_table = df_table.set_index(other_cols)

    final_df = df_table[[model_var] + observe_vars].copy()

    per_diff_vars = []
    for obs_var in observe_vars:
        per_diff_vars = per_diff_vars + [obs_var + '% diff']
        final_df.loc[:, obs_var + '% diff'] = (final_df[model_var] - final_df[obs_var]) / final_df[obs_var]


    format_dict = {model_var: "{:,.0f}"}
    for var in observe_vars:
        format_dict[var] = "{:,.0f}"
    for var in per_diff_vars:
        format_dict[var] = "{:+.1%}"

    
    styled_output = (
        final_df.style
        .format(format_dict)
        # Add the mid-aligned horizontal bars to the numeric values
        .bar(
            subset=per_diff_vars,
            align=0,
            color=["#91268F", "#00A7A0"], # Soft red for negative, soft green for positive
            vmin=min(-1, final_df[per_diff_vars].min().min()),  # lower bound for bar scaling
            vmax=max(1, final_df[per_diff_vars].min().min()),
            height=65,
            # props="border-left: 1.5px solid #d3d3d3; padding-left: 2px;"
        )
    )
    
    # Display in your notebook
    display(styled_output)