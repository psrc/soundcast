import pandas as pd
import numpy as np 
import h5py
import glob, os
import os
import sys
from sqlalchemy import create_engine
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
from emme_configuration import *
from input_configuration import *
from EmmeProject import *

### FIXME: do we need this?
pd.set_option('display.float_format', lambda x: '%.3f' % x)

def build_df(h5file, h5table, var_dict, nested):
    ''' Convert H5 into dataframe '''
    data = {}
    if nested:
        # survey h5 have nested data structure, different than daysim_outputs
        for col_name, var in var_dict.iteritems():
            data[col_name] = [i[0] for i in h5file[h5table][var][:]]
    else:
        for col_name, var in var_dict.iteritems():
            data[col_name] = [i for i in h5file[h5table][var][:]]
    return pd.DataFrame(data)

def daysim_sort(daysim):
        ###
    ### FIXME: remove magic number
    ###
    hhdict={'Household ID': 'hhno',
        'Household Size': 'hhsize',
        'Household TAZ': 'hhtaz',
        'Expansion Factor': 'hhexpfac'}
    daysim_df = build_df(h5file=daysim, h5table='Household', var_dict = hhdict, nested=False)
    daysim_sorted = pd.DataFrame(daysim_df.groupby('Household TAZ').sum()['Household Size'])
    del daysim_sorted.index.name
    daysim_sorted['TAZ'] = daysim_sorted.index
    daysim_sorted['pop_trip'] = daysim_sorted['Household Size']*0.02112
    return daysim_sorted

def parcel_sort(parcel):
    ###
    ### FIXME: remove magic number
    ###
    parcel['Employment Size'] = parcel['EMPTOT_P'] - parcel['EMPEDU_P'] + parcel['EMPGOV_P']
    parcel['emp_trip'] = parcel['Employment Size']*0.01486
    parcel_sorted = pd.DataFrame(parcel.groupby('TAZ_P').sum()[['emp_trip','Employment Size']])
    del parcel_sorted.index.name
    parcel_sorted['TAZ'] = parcel_sorted.index
    return parcel_sorted

# estimated trips
def trips_estimation(parcel_sorted, daysim_sorted):
    trips = pd.DataFrame.merge(parcel_sorted, daysim_sorted, on='TAZ')
    trips['est_trips'] = trips['pop_trip'] + trips['emp_trip']
    return trips

# Adjust estimated trips by appling observed control total 
def trips_adjustment(trips, control_total):
    ###
    ### FIXME: remove magic number
    ###
    est_trips = trips['est_trips'].sum()
    adj_factor = control_total/est_trips
    trips['adj_trips'] = trips['est_trips']*adj_factor

    cols = ['TAZ', 'adj_trips']
    airport_trips = trips[cols]
    airport_trips['SeaTac_Taz'] = 983
    return airport_trips


#open shares for hbo:
def create_demand_matrix(airport_trips, org_zones, dest_zones, dict_zone_lookup):
  
    demand_matrix = np.zeros((org_zones, dest_zones), np.float16) #IndexError: index 3868 is out of bounds for axis 0 with size 3868
    
    #convert to matrix
    for rec in airport_trips.iterrows():
        demand = rec[1].adj_trips
        origin = dict_zone_lookup[rec[1].TAZ]
        destination = dict_zone_lookup[rec[1].SeaTac_Taz]
        demand_matrix[origin, destination] = demand
    return demand_matrix


# Input the mode choice ratio matrices
def apply_ratio_to_trips(trip_table, ratio_table):
    result = trip_table * ratio_table
    return result


# split and output trip tables by mode and directions
def split_trips_into_modes(direction_trips, mode_dict, hbo_ratio):
    table_dict = {}
    for mode, ratio in mode_dict.iteritems():
        ratio = hbo_ratio['hbo'][ratio][:]
        mod_trip = apply_ratio_to_trips(direction_trips, ratio) 
        # convert hov to vehicle trips (/2, /3.5)
        if mode == 'hov2':
            mod_trip = mod_trip / 2
        if mode == 'hov3':
            mod_trip = mod_trip / 3.5
        table_dict[mode] = mod_trip
    return table_dict


# Split trips into time of a day: apply time of the day factors to internal trips
def split_tod_internal(airport_trips, tod_factors_df):
    matrix_dict = {}
    #for tod, dict in test.iteritems():
    for tod in tod_factors_df.time_of_day.unique():
        #open work externals:
        tod_dict = {}
        tod_df = tod_factors_df[tod_factors_df['time_of_day'] == tod]

        ixxi_work_store = h5py.File('outputs/supplemental/external_work_' + tod + '.h5', 'r')

        tod_dict['sov'] = np.array(airport_trips['sov']) * tod_df[tod_df['mode'] == 'sov']['value'].values[0] + np.array(ixxi_work_store['sov'])
        tod_dict['hov2'] = np.array(airport_trips['hov2']) * tod_df[tod_df['mode'] == 'hov']['value'].values[0] + np.array(ixxi_work_store['hov2'])
        tod_dict['hov3'] = np.array(airport_trips['hov3']) * tod_df[tod_df['mode'] == 'hov']['value'].values[0] + np.array(ixxi_work_store['hov3'])
        ixxi_work_store.close()

        tod_dict['litrat'] = np.array(airport_trips['litrat']) * tod_df[tod_df['mode'] == 'transit']['value'].values[0]
        tod_dict['trnst'] = np.array(airport_trips['trnst']) * tod_df[tod_df['mode'] == 'transit']['value'].values[0]
        tod_dict['walk'] = np.array(airport_trips['walk']) * tod_df[tod_df['mode'] == 'sov']['value'].values[0]
        tod_dict['bike'] = np.array(airport_trips['bike']) * tod_df[tod_df['mode'] == 'sov']['value'].values[0]
        matrix_dict[tod] = tod_dict

    return matrix_dict

# Output trips
def output_trips(path, matrix_dict):
    for tod in matrix_dict.iterkeys():
        print("Exporting supplemental trips for time period: " + str(tod))
        my_store = h5py.File(path + str(tod) + '.h5', "w")
        for mode, value in matrix_dict[tod].iteritems():
            my_store.create_dataset(str(mode), data=value)
        my_store.close()
        
def main():

    DAYSIM = 'inputs/scenario/landuse/hh_and_persons.h5'
    PARCEL = 'inputs/scenario/landuse/parcels_urbansim.txt'
    OUT_PUT = 'outputs/supplemental/AIRPORT_TRIPS.csv'
    daysim = h5py.File(DAYSIM,'r+')
    parcel = pd.read_csv(PARCEL, ' ')
    my_project = EmmeProject('projects/Supplementals/Supplementals.emp')
    zonesDim = len(my_project.current_scenario.zone_numbers)
    zones = my_project.current_scenario.zone_numbers
    # returns the ordinal (0-based, sequential) numpy index for our zone system
    dict_zone_lookup = dict((value,index) for index,value in enumerate(zones))
    # apply mode shares
    hbo_ratio = h5py.File('outputs/supplemental/hbo_ratio.h5', 'r')

    mode_dict = {'walk':'nwshwk', 
                 'bike':'nwshbk',
                 'trnst':'nwshtw',
                 'litrat':'nwshrw',
                 'sov': 'nwshda', 
                 'hov2':'nwshs2', 
                 'hov3':'nwshs3'}
    
    # Document source of TOD factors; consider calculating these from last iteration of soundcast via daysim outputs?
    conn = create_engine('sqlite:///inputs/db/soundcast_inputs.db')
    tod_factors_df = pd.read_sql('SELECT * FROM time_of_day_factors', con=conn)

    output_dir = r'outputs/supplemental/'

    # Get airport trip table  (all-in-one table) 
    daysim_sorted = daysim_sort(daysim)
    parcel_sorted = parcel_sort(parcel)
    trips = trips_estimation(parcel_sorted, daysim_sorted)
    airport_trips = trips_adjustment(trips, airport_control_total[model_year])
    demand_matrix = create_demand_matrix(airport_trips, zonesDim, zonesDim, dict_zone_lookup)

    # split airport trips into different modes, by applying HBO ratios
    # we would like to seperate airport trips by two directions, since the mode choice ratio are different between 'to' and 'from airport'
    to_airport = demand_matrix/2
    from_airport = to_airport.transpose()
    all = to_airport+from_airport
    airport_trips_by_mode = split_trips_into_modes(all, mode_dict, hbo_ratio)

    #open external trip tables:
    ixxi_non_work_store = h5py.File('outputs/supplemental/external_non_work.h5', 'r')
    external_modes = ['sov', 'hov2', 'hov3']
    ext_trip_table_dict = {}
    ext_tod_dict = {}
    # get the non work external trips
    for mode in external_modes:
        ext_trip_table_dict[mode] = np.array(ixxi_non_work_store[mode])

    # add external non work to airport trips
    airport_trips_by_mode['sov'] = airport_trips_by_mode['sov'] + ext_trip_table_dict['sov']
    airport_trips_by_mode['hov2'] = airport_trips_by_mode['hov2'] + ext_trip_table_dict['hov2']
    airport_trips_by_mode['hov3'] = airport_trips_by_mode['hov3'] + ext_trip_table_dict['hov3']

    #apply time of day factors:
    airport_matrix_dict = split_tod_internal(airport_trips_by_mode, tod_factors_df)

    ## Output final trip tables, which are by time of the day and trip mode. 
    output_trips(output_dir, airport_matrix_dict)

if __name__ == '__main__':
    main()