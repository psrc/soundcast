import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import polars as pl
from pathlib import Path


class SummaryData:
    def __init__(self, config, summary_config, get_data: list =['parcel_geog', 'parcels_urbansim'], inc_geog=False) -> None:
        self.config = config
        self.summary_config = summary_config
        self.get_data = get_data
        self.equity_geog_dict = {"equity_focus_areas_2023__efa_poc": "People of Color",
                                "equity_focus_areas_2023__efa_pov200": "Income",
                                "equity_focus_areas_2023__efa_lep": "LEP",
                                "equity_focus_areas_2023__efa_dis": "Disability",
                                "equity_focus_areas_2023__efa_older": "Older Adults",
                                "equity_focus_areas_2023__efa_youth": "Youth"}
        self.parcel_geog = self._get_parcel_geog()
        self.parcels_urbansim = self._get_parcels_urbansim_data(inc_geog)

    def _get_parcel_geog(self):

        if ('parcel_geog' in self.get_data) | ('parcels_urbansim' in self.get_data):
            
            # conn = create_engine("sqlite:///"+ self.config["model_dir"]+ "/inputs/db/"+ self.input_config["db_name"])
            async_engine = create_engine("sqlite:///../../../../inputs/db/"+ self.config["db_name"])
            parcel_geog = pl.read_database(
                query=
                    "SELECT * FROM "
                    + "parcel_"
                    + self.config["base_year"]
                    + "_geography"
                ,
                connection=async_engine.connect()
            ).to_pandas()

            # organize geographies
            parcel_geog['rgc_binary'] = parcel_geog['GrowthCenterName']
            parcel_geog.loc[parcel_geog['GrowthCenterName']!="Not in RGC",'rgc_binary'] = 'In RGC'

            rg_mapping = {'Core': 'Core Cities',
                          'Cities and Towns': 'Cities and Towns', 
                          'HCT': 'High Capacity Transit Communities',
                          'Metro': 'Metropolitan Cities',
                          'Rural': 'Rural Areas',
                          'Urban Unincorporated': 'Urban Unincorporated Areas'}
            parcel_geog['RegionalGeogName'] = parcel_geog['rg_proposed'].map(rg_mapping)

            
            parcel_geog[list(self.equity_geog_dict.values())] = parcel_geog[list(self.equity_geog_dict.keys())].\
                apply(lambda x: x.map({0.0: 'Below Regional Average', 
                                       1.0: 'Above Regional Average', 
                                       2.0: 'Higher Share of Equity Population'}
                                       ))

            return parcel_geog

    def _get_parcels_urbansim_data(self, inc_geog=False):
        
        if 'parcels_urbansim' in self.get_data:
            # parcel land use data
            OUTPUT_PATH = Path(self.summary_config['sc_run_path']) / self.summary_config["output_folder"]
            df_parcel = pl.read_csv(OUTPUT_PATH / 'landuse/parcels_urbansim.txt', separator=' ').to_pandas()

            if inc_geog:
                df_parcel = df_parcel.merge(self.parcel_geog, left_on='parcelid', right_on='ParcelID', how='left')     
    
        return df_parcel
        