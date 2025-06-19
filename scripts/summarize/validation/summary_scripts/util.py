import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import polars as pl
from pathlib import Path


class ValidationData:
    def __init__(self, config, input_config, get_data: list =['hh','person','person_day','tour','trip','land_use','parcel_geog']) -> None:
        self.config = config
        self.input_config = input_config
        self.get_data = get_data
        # get uncloned hh data
        self.hh = self._get_hh_data()
        # get uncloned person data
        self.person = self._get_person_data()
        self.person_day = self._get_person_day_data(False)
        self.tour = self._get_tour_data(False)
        self.trip = self._get_trip_data(False)
        self.land_use = self._get_parcel_landuse_data()
        self.parcel_geog = self._get_parcel_geog()


    # Read data for model and survey data
    def _get_data(self, df_name, uncloned=True):
        # model data
        model = pl.read_csv(
            Path(self.config["model_dir"], "outputs/daysim", "_" + df_name + ".tsv"),
            # Path("outputs/daysim", "_" + df_name + ".tsv"),
            separator="\t",
        )

        # Apply expected data types to data when read in

        # model["source"] = "model"
        # model.drop_in_place('fraction_with_jobs_outside')
        wt_col = model.select(pl.col("^.*expfac.*$")).columns[0]
        model = model.with_columns(
            source = pl.lit("model"),
            **{wt_col: pl.col(wt_col).cast(pl.Float64)}
        )

        # Generate a placeholder column for worker type
        # model["worker_type"] = "commuter"
        if df_name == "person":
            model = model.with_columns(
                worker_type = pl.lit("null")
            )

        # survey data
        # survey = pd.DataFrame()
        survey_list = []

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

            df = pl.read_csv(Path(survey_path, "_" + df_name + ".tsv"), separator="\t")
            # df["source"] = source_name
            df = df.with_columns(
                source = pl.lit(source_name)
            )
            # df = df[model.columns]
            col_list = np.intersect1d(df.columns, model.columns)
            df = df[col_list]
            # model_schema = model[col_list].collect_schema()
            model_schema = model[col_list].schema
            # Apply the new schema
            df = df.with_columns([
                pl.col(col_name).cast(new_type) for col_name, new_type in model_schema.items()
            ])
            # survey = pl.concat([survey, df])
            survey_list.append(df)

        data = pl.concat(survey_list+[model[col_list]])

        return data

    def _get_hh_data(self, uncloned=True):
        
        if 'hh' in self.get_data:
            hh_data = self._get_data("household", uncloned)
            return hh_data

    def _get_person_data(self, uncloned=True):
        
        if 'person' in self.get_data:
            per_data = self._get_data("person", uncloned)
            return per_data

    def _get_person_day_data(self, uncloned=True):
        
        if 'person_day' in self.get_data:
            per_day_data = self._get_data("person_day", uncloned)
            return per_day_data

    def _get_tour_data(self, uncloned=True):
            
        if 'tour' in self.get_data:
            tour_data = self._get_data("tour", uncloned)
            return tour_data

    def _get_trip_data(self, uncloned=True):
        
        if 'trip' in self.get_data:
            trip_data = self._get_data("trip", uncloned)
            return trip_data

    def _get_parcel_landuse_data(self):
        
        if 'land_use' in self.get_data:
            # parcel land use data
            df_parcel = pl.read_csv(
                Path(self.config["model_dir"], "outputs/landuse/buffered_parcels.txt"),
                separator=" ",
            )

            return df_parcel

    def _get_parcel_geog(self):

        if 'parcel_geog' in self.get_data:
            
            # conn = create_engine("sqlite:///"+ self.config["model_dir"]+ "/inputs/db/"+ self.input_config["db_name"])
            async_engine = create_engine("sqlite:///../../../../inputs/db/"+ self.input_config["db_name"])
            parcel_geog = pl.read_database(
                query=
                    "SELECT * FROM "
                    + "parcel_"
                    + self.input_config["base_year"]
                    + "_geography"
                ,
                connection=async_engine.connect()
            )

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