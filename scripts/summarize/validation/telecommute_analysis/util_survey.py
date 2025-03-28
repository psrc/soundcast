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


class ValidationData:
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

    # Read data for model and survey data
    def _get_data(self, df_name, uncloned=True):
        # survey data
        survey = pd.DataFrame()

        # read survey data in all sources
        for source_name in self.config["survey_directories"].keys():
            if uncloned:
                # get uncloned data
                survey_path = Path(
                    self.config["survey_directories"][source_name],
                    self.config["uncloned_folder"],
                )
            else:
                # get cloned data
                survey_path = self.config["survey_directories"][source_name]

            df = pd.read_csv(Path(survey_path, "_" + df_name + ".tsv"), sep="\t")
            df["source"] = source_name

            survey = pd.concat([survey, df])

        return survey

    def _get_hh_data(self, uncloned=True):
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
            Path(self.config["model_dir"], "outputs/landuse/buffered_parcels.txt"),
            delim_whitespace=True,
            # usecols=['parcelid','emptot_1','hh_1']
        )

        return df_parcel
