import pandas as pd
import numpy as np 
import h5py
import glob, os
pd.set_option('display.float_format', lambda x: '%.3f' % x)
import os
import sys
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
from emme_configuration import *
from input_configuration import *
from EmmeProject import *

DAYSIM = 'inputs/hh_and_persons.h5'
PARCEL = 'inputs/accessibility/parcels_urbansim.txt'
OUT_PUT = 'outputs/supplemental/AIRPORT_TRIPS.csv'
daysim = h5py.File(DAYSIM,'r+')
parcel = pd.read_csv(PARCEL, ' ')
my_project = EmmeProject('projects/Supplementals/Supplementals.emp')
zonesDim = len(my_project.current_scenario.zone_numbers)
zones = my_project.current_scenario.zone_numbers
# returns the ordinal (0-based, sequential) numpy index for our zone system
dictZoneLookup = dict((value,index) for index,value in enumerate(zones))
# apply mode shares
hbo_ratio = h5py.File('outputs/supplemental/hbo_ratio.h5', 'r')
mode_dict = {'walk':'nwshwk', 'bike':'nwshbk','trnst':'nwshtw', 'litrat':'nwshrw', 'sov': 'nwshda', 'hov2':'nwshs2', 'hov3':'nwshs3'}
#Time of the day factors
test = {'5to6' : {'sov' : .04, 'hov' : .035, 'transit' : .04}, '6to7' : {'sov' : .053, 'hov' : .056, 'transit' : .053}, '7to8' : {'sov' : .06, 'hov' : .061, 'transit' : .06}, 
        '8to9' : {'sov' : .057, 'hov' : .057, 'transit' : .057}, '9to10' : {'sov' : .055, 'hov' : .051, 'transit' : .055}, '10to14' : {'sov' : .2250, 'hov' : .1880, 'transit' : .2250}, 
        '14to15' : {'sov' : .061, 'hov' : .07, 'transit' : .061}, '15to16' : {'sov' : .061, 'hov' : .082, 'transit' : .061}, '16to17' : {'sov' : .06, 'hov' : .084, 'transit' : .06}, 
        '17to18' : {'sov' : .06, 'hov' : .08, 'transit' : .06}, '18to20' : {'sov' : .10, 'hov' : .108, 'transit' : .269}, '20to5' : {'sov' : .169, 'hov' : .125, 'transit' : 0.0}}

output_dir = r'outputs/supplemental/'

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
def trips_adjustion(trips, control_total):
    #obs_trips = 101838
    est_trips = trips['est_trips'].sum()
    print 'Total number of estimated trips is', est_trips
    adj_factor = control_total/est_trips
    print 'The adjusted factor of observe/estimate is:', adj_factor
    trips['adj_trips'] = trips['est_trips']*adj_factor

    # Trip number validation
    if  0 < (trips['adj_trips'].sum() - control_total) < 1:
        print 'Total number of adjusted trips is as same as observed trips '
    cols = ['TAZ', 'adj_trips']
    airport_trips = trips[cols]
    airport_trips['SeaTac_Taz'] = 983
    return airport_trips


#open shares for hbo:
def create_demand_matrix(airport_trips, org_zones, dest_zones):
  
    demand_matrix = np.zeros((org_zones, dest_zones), np.float16) #IndexError: index 3868 is out of bounds for axis 0 with size 3868
    
    #convert to matrix
    for rec in airport_trips.iterrows():
        demand = rec[1].adj_trips
        origin = dictZoneLookup[rec[1].TAZ]
        destination = dictZoneLookup[rec[1].SeaTac_Taz]
        print origin 
        print demand
        demand_matrix[origin, destination] = demand
    return demand_matrix


# Input the mode choice ratio matrices
def apply_ratio_to_trips(trip_table, ratio_table):
    result = trip_table * ratio_table
    return result


# split and output trip tables by mode and directions
def split_trips_into_modes(direction_trips):
    table_dict = {}
    for mode, ratio in mode_dict.iteritems():
        print mode
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
def split_tod_internal(airport_trips):
    matrix_dict = {}
    for tod, dict in test.iteritems():
        #open work externals:
        tod_dict = {}
        ixxi_work_store = h5py.File('outputs/supplemental/external_work_' + tod + '.h5', 'r')
        tod_dict['svtl'] = np.array(airport_trips['sov']) * float(test[tod]['sov']) + np.array(ixxi_work_store['svtl'])
        tod_dict['h2tl'] = np.array(airport_trips['hov2']) * float(test[tod]['hov']) + np.array(ixxi_work_store['h2tl'])
        tod_dict['h3tl'] = np.array(airport_trips['hov3']) * float(test[tod]['hov']) + np.array(ixxi_work_store['h3tl'])
        ixxi_work_store.close()
        ''' At this point, We determine to use SOV factors on transit, bike and walk '''
        tod_dict['litrat'] = np.array(airport_trips['litrat']) * float(test[tod]['transit'])
        tod_dict['trnst'] = np.array(airport_trips['trnst']) * float(test[tod]['transit'])
        tod_dict['walk'] = np.array(airport_trips['walk']) * float(test[tod]['sov'])
        tod_dict['bike'] = np.array(airport_trips['bike']) * float(test[tod]['sov'])
        matrix_dict[tod] = tod_dict
        #matrix_dict[tod]= {'svtl' : sov, 'h2tl' : hov2, 'h3tl' : hov3, 'litrat': litrat, 'trnst' : trnst, 'walk': walk, 'bike': bike}
    return matrix_dict


# Combine external and internal trips
def combine_IE_trips(path, matrix_dict1, matrix_dict2, matrix_dict):
    for tod in test.keys():
       print tod
       external_trips = h5py.File(path + tod + '.h5', 'r')
       print external_trip_dir + tod + '.h5'
       for mod in ['svtl', 'h2tl', 'h3tl']:
           matrix_dict1[tod][mod][0:3865, 0:3865] = matrix_dict1[tod][mod][0:3865, 0:3865] + np.array(external_trips[mod])
           matrix_dict2[tod][mod] += matrix_dict1[tod][mod]
    matrix_dict = matrix_dict2
    return matrix_dict


# Output trips
def output_trips(path, matrix_dict):
    for tod in matrix_dict.iterkeys():
        print tod
        print "Exporting supplemental trips for time period: " + str(tod)
        my_store = h5py.File(path + str(tod) + '.h5', "w")
        for mode, value in matrix_dict[tod].iteritems():
            my_store.create_dataset(str(mode), data=value)
        my_store.close()
        

########################### Calculation ##########################
# Get airport trip table  (all-in-one table) 
daysim_sorted = daysim_sort(daysim)
parcel_sorted = parcel_sort(parcel)
trips = trips_estimation(parcel_sorted, daysim_sorted)
airport_trips = trips_adjustion(trips, airport_control_total[model_year])
print zonesDim
demand_matrix = create_demand_matrix(airport_trips, zonesDim, zonesDim)
print 'create airport trip demand matrix, done'

# split airport trips into different modes, by appling HBO ratios
# we would like to seperate airport trips by two directions, since the mode choice ratio are different between 'to' and 'from airport'
to_airport = demand_matrix/2
from_airport = to_airport.transpose()
all = to_airport+from_airport
airport_trips_by_mode = split_trips_into_modes(all)
print 'split to_airport_trips into modes, done'
#airport_matrix_dict = {}

#open external trip tables:
ixxi_non_work_store = h5py.File('outputs/supplemental/external_non_work.h5', 'r')
external_modes = ['svtl', 'h2tl', 'h3tl']
ext_trip_table_dict = {}
ext_tod_dict = {}
# get the non work external trips
for mode in external_modes:
    ext_trip_table_dict[mode] = np.array(ixxi_non_work_store[mode])
# add external non work to airport trips
airport_trips_by_mode['sov'] = airport_trips_by_mode['sov'] + ext_trip_table_dict['svtl']
airport_trips_by_mode['hov2'] = airport_trips_by_mode['hov2'] + ext_trip_table_dict['h2tl']
airport_trips_by_mode['hov3'] = airport_trips_by_mode['hov3'] + ext_trip_table_dict['h3tl']

#apply time of day factors:
airport_matrix_dict = split_tod_internal(airport_trips_by_mode)
print 'split internal to airpoprt trips into time periods, done'

## Output final trip tables, which are by time of the day and trip mode. 
output_trips(output_dir, airport_matrix_dict)
#print 'congrats, your airport trip tables are ready at:', combined_bidir_airport_trip_dir



##*******************************************VALIDATION/Statistic *******************************************************


#to_airport2 = h5py.File('outputs/supplemental/mode_choice/trips_to_airport_am.h5', 'r')
#from_airport2 = h5py.File('outputs/supplemental/mode_choice/trips_from_airport_am.h5', 'r')


tot_trips = np.sum(airport_trips_by_mode.values())
for mode in ['sov', 'hov2', 'hov3', 'bike', 'walk', 'trnst', 'litrat']:
    print mode
    print airport_trips_by_mode[mode].sum()
    print airport_trips_by_mode[mode].sum()/tot_trips

print 'done'
    

