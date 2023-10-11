import os, sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
import collections
import h5py
import re
import time
import pandas as pd
import numpy as np 
import pandana as pdna
import inro.emme.database.emmebank as _eb
from pyproj import Proj, transform
# from input_configuration import base_year
import toml
config = toml.load(os.path.join(os.getcwd(), 'configuration/input_configuration.toml'))

def get_transit_time(bank, max_time):
    '''Extract transit travel times from skim matrices, between all zones'''

    # Bus and rail travel times are the sum of access, wait time, and in-vehicle times; Bus and rail have separate paths
    bus_time = bank.matrix('auxwa').get_numpy_data() + bank.matrix('twtwa').get_numpy_data() + bank.matrix('ivtwa').get_numpy_data() 
    rail_time = bank.matrix('auxwr').get_numpy_data() + bank.matrix('twtwr').get_numpy_data() + bank.matrix('ivtwr').get_numpy_data() 
    ferry_time = bank.matrix('auxwf').get_numpy_data() + bank.matrix('twtwf').get_numpy_data() + bank.matrix('ivtwf').get_numpy_data()
    p_ferry_time = bank.matrix('auxwp').get_numpy_data() + bank.matrix('twtwp').get_numpy_data() + bank.matrix('ivtwp').get_numpy_data() 
    commuter_rail_time = bank.matrix('auxwc').get_numpy_data() + bank.matrix('twtwc').get_numpy_data() + bank.matrix('ivtwc').get_numpy_data() 
    # Take the shortest transit time between bus or rail
    #transit_time = np.minimum(bus_time, rail_time)
    transit_time = np.minimum.reduce([bus_time, rail_time, ferry_time, p_ferry_time, commuter_rail_time])
    transit_time = transit_time[0:3700, 0:3700]
    transit_time_df = pd.DataFrame(transit_time)
    transit_time_df['from'] = transit_time_df.index
    transit_time_df = pd.melt(transit_time_df, id_vars= 'from', value_vars=list(transit_time_df.columns[0:3700]), var_name = 'to', value_name='travel_time')

    # Join with parcel data; add 1 to get zone ID because emme matrices are indexed starting with 0
    transit_time_df['to'] = transit_time_df['to'] + 1 
    transit_time_df['from'] = transit_time_df['from'] + 1

    transit_time_df = transit_time_df[transit_time_df['travel_time']<=max_time]

    return transit_time_df

def get_auto_time(bank, max_time):
    auto_time = bank.matrix('sov_inc2t').get_numpy_data()

    auto_time = auto_time[0:3700, 0:3700]
    auto_time_df = pd.DataFrame(auto_time)
    auto_time_df['from'] = auto_time_df.index
    auto_time_df = pd.melt(auto_time_df, id_vars= 'from', value_vars=list(auto_time_df.columns[0:3700]), var_name = 'to', value_name='travel_time')

    auto_time_df['to'] = auto_time_df['to'] + 1 
    auto_time_df['from'] = auto_time_df['from'] + 1

    auto_time_df = auto_time_df[auto_time_df['travel_time']<=max_time]
    return auto_time_df

def aggregate_travel_time(travel_time_df, taz_df, mode):
    travel_time_df = travel_time_df.merge(taz_df, how = 'left', left_on = 'to', right_on = 'TAZ_P')
    travel_time_df = travel_time_df.groupby('from').aggregate({'EMPTOT_P' : sum, 'HH_P' : sum}).reset_index()
    travel_time_df = travel_time_df.rename(columns = {'EMPTOT_P' : 'EMPTOT_P' + '_' + mode, 'HH_P' : 'HH_P' + '_' + mode})
    return travel_time_df


output_dir = r'outputs/access'
parcel_df = pd.read_csv(r'inputs/scenario/landuse/parcels_urbansim.txt', delim_whitespace=True)
bank = _eb.Emmebank(os.path.join(os.getcwd(), r'Banks/7to8/emmebank'))
taz_data = parcel_df.groupby('TAZ_P').aggregate({'EMPTOT_P' : sum, 'HH_P' : sum}).reset_index()
auto_time_df = get_auto_time(bank, 30) 
transit_time_df = get_transit_time(bank, 45) 

auto_df = aggregate_travel_time(auto_time_df, taz_data, 'auto')
transit_df = aggregate_travel_time(transit_time_df, taz_data, 'transit')

taz_data = taz_data.merge(auto_df, how = 'left', left_on = 'TAZ_P', right_on = 'from')
taz_data = taz_data.merge(transit_df, how = 'left', left_on = 'TAZ_P', right_on = 'from')

taz_data = taz_data[['TAZ_P', 'EMPTOT_P', 'HH_P', 'from_x', 'EMPTOT_P_auto', 'HH_P_auto', 'EMPTOT_P_transit', 'HH_P_transit']]
taz_data.fillna(0, inplace = True)

taz_data['jh_ratio_transit'] = taz_data['EMPTOT_P_transit'] / taz_data['HH_P_transit']
taz_data['jh_ratio_auto'] = taz_data['EMPTOT_P_auto'] / taz_data['HH_P_auto']

taz_data.fillna(0, inplace = True)
taz_data.to_csv(os.path.join(output_dir,'jobs_housing.csv'))
print ('done')




