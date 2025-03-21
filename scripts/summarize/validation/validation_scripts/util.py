import os
import toml
import pandas as pd
import numpy as np
import plotly.express as px
from shapely import wkt
from sqlalchemy import create_engine, text
import urllib
import pyodbc
from pathlib import Path

class ValidationData():
    def __init__(self, config, input_config) -> None:
        self.config = config
        self.input_config = input_config
        # get uncloned hh data
        self.hh = self._get_hh_data()
        # get uncloned person data
        self.person = self._get_person_data()
        self.person_day = self._get_person_day_data(False)
        self.tour = self._get_tour_data(False)
        self.trip = self._get_trip_data(False)
        self.land_use = self._get_parcel_landuse_data()
        self.parcel_geog = self._get_parcel_geog()
        # self.hh_elmer = self._get_elmer_data("v_households_labels")
        # self.person_elmer = self._get_elmer_data("v_persons_labels")
        

    # Read data for model and survey data
    def _get_data(self, df_name, uncloned = True):

        # model data
        model = pd.read_csv(
            Path(self.config["model_dir"], "outputs/daysim", "_" + df_name + ".tsv"),
            sep="\t"
        )
        model["source"] = "model"

        # survey data
        survey = pd.DataFrame()

        # read survey data in all sources
        for source_name in self.config['survey_directories'].keys():
            if uncloned:
                # get uncloned data
                survey_path = Path(self.config["survey_directories"][source_name], self.config['uncloned_folder'])
            else:
                # get cloned data
                survey_path = self.config["survey_directories"][source_name]

            df = pd.read_csv(
                Path(survey_path, "_" + df_name + ".tsv"),
                sep="\t"
            )
            df["source"] = source_name

            survey = pd.concat([survey,df])


        data = pd.concat([model, survey])

        return data

    def _get_hh_data(self, uncloned = True):

        hh_data = self._get_data("household", uncloned)

        return hh_data
    
    def _get_person_data(self, uncloned=True):

        per_data = self._get_data("person", uncloned)

        return per_data
    
    def _get_person_day_data(self, uncloned=True):

        per_day_data = self._get_data("person_day", uncloned)

        return per_day_data
    
    def _get_tour_data(self, uncloned=True):

        tour_data = self._get_data("tour", uncloned)

        return tour_data

    def _get_trip_data(self, uncloned=True):

        trip_data = self._get_data("trip", uncloned)

        return trip_data
    
    def _get_parcel_landuse_data(self):

        # parcel land use data
        df_parcel = pd.read_csv(
            Path(self.config['model_dir'], 'outputs/landuse/buffered_parcels.txt'),
            delim_whitespace=True,
            # usecols=['parcelid','emptot_1','hh_1']
            )

        return df_parcel

    def _get_parcel_geog(self):
        # Load parcel geography lookups
        conn = create_engine('sqlite:///'+self.config['model_dir']+'/inputs/db/' + self.input_config['db_name'])
        parcel_geog = pd.read_sql(text("SELECT * FROM " + 'parcel_'+self.input_config['base_year']+'_geography'), con=conn.connect())

        return parcel_geog
    
    # def _get_elmer_data(self, table_name):

    #     def load_elmer_table(table_name, sql=None):
    #         conn_string = "DRIVER={ODBC Driver 17 for SQL Server}; SERVER=SQLserver; DATABASE=Elmer; trusted_connection=yes"
    #         sql_conn = pyodbc.connect(conn_string)
    #         params = urllib.parse.quote_plus(conn_string)
    #         engine = create_engine("mssql+pyodbc:///?odbc_connect=%s" % params)

    #         # if sql is None:
    #         #     sql = "SELECT * FROM " + table_name

    #         # df = pd.DataFrame(engine.connect().execute(text(sql)))
    #         with engine.begin() as connection:
    #             result = connection.execute(text(f"SELECT * FROM HHSurvey.{table_name} WHERE survey_year in ({self.input_config['base_year']})"))
    #             df = pd.DataFrame(result.fetchall())
    #             df.columns = result.keys()

    #         return df

    #     df_elmer = load_elmer_table(table_name)

    #     return df_elmer
