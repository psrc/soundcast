# import os
import pandas as pd
import numpy as np
import toml
from pathlib import Path
# from typing import Any

class SummaryData():
    def __init__(self, config) -> None:
        self.config = config
        self.network_summary = self._load_network_summary()

    def _load_network_summary(self):
        """Load network-level results using a standard procedure. """

        df = pd.read_csv(Path(self.config['output_path'])/'network/network_results.csv')

        # Congested network components by time of day
        df.columns

        # Get freeflow from 20to5 period

        # Exclude trips taken on non-designated facilities (facility_type == 0)
        # These are artificial (weave lanes to connect HOV) or for non-auto uses 
        df = df[df['data3'] != 0]    # data3 represents facility_type

        # Define facility type
        df['facility_type'] =df['data3'].astype('int32').astype('str').map(self.config['facility_type_dict'])
        df['facility_type'].fillna('Other', inplace=True)
        # Define county type
        df['county'] =df['@countyid'].astype('int32').astype('str').map(self.config['county_map'])
        df['county'].fillna('Outside Region', inplace=True)
        # Define time of day period
        df['tod_period'] =df['tod'].map(self.config['tod_dict'])


        # calculate total link VMT and VHT
        df['VMT'] = df['@tveh']*df['length']
        df['VHT'] = df['@tveh']*df['auto_time']/60

        # Calculate delay
        # Select links from overnight time of day
        delay_df = df.loc[df['tod'] == '20to5'][['ij','auto_time']]
        delay_df.rename(columns={'auto_time':'freeflow_time'}, inplace=True)

        # Merge delay field back onto network link df
        df = pd.merge(df, delay_df, on='ij', how='left')

        # Calcualte hourly delay
        df['total_delay'] = ((df['auto_time']-df['freeflow_time'])*df['@tveh'])/60    # sum of (volume)*(travtime diff from freeflow)

        
        return df
