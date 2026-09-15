import numpy as np
from sqlalchemy import create_engine
import polars as pl
from pathlib import Path
import toml

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

