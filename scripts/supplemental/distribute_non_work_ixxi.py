import array as _array
import os
import shutil
import json
import csv
import pandas as pd
import h5py
import numpy as np
import sys
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.path.join(os.getcwd(),"scripts/trucks"))
sys.path.append(os.getcwd())
from emme_configuration import *
from EmmeProject import *
from truck_configuration import *


def json_to_dictionary(dict_name):
    ''' Load supplemental input files as dictionary '''
    input_filename = os.path.join('inputs/model/supplementals', dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return my_dictionary

def init_dir(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.mkdir(directory)

def load_skims(skim_file_loc, mode_name, divide_by_100=False):
    ''' Loads H5 skim matrix for specified mode. '''
    with h5py.File(skim_file_loc, "r") as f:
        skim_file = f['Skims'][mode_name][:]
    # Divide by 100 since decimals were removed in H5 source file through multiplication
    if divide_by_100:
        return skim_file.astype(float)/100
    else:
        return skim_file

def calc_fric_fac(cost_skim, dist_skim, coeff):
    ''' Calculate friction factors for all trip purposes '''
    friction_fac_dic = {}
    for purpose, coeff_val in coeff.iteritems():
        friction_fac_dic[purpose] = np.exp((coeff[purpose])*(cost_skim + (dist_skim * autoop * avotda)))
        ## Set external zones to zero to prevent external-external trips
        friction_fac_dic[purpose][LOW_STATION:] = 0
        friction_fac_dic[purpose][:,[x for x in range(LOW_STATION, len(cost_skim))]] = 0

    return friction_fac_dic

def delete_matrices(my_project, matrix_type):
    ''' Deletes all Emme matrices of specified type in emmebank '''
    for matrix in my_project.bank.matrices():
        if matrix.type == matrix_type:
            my_project.delete_matrix(matrix)

def load_matrices_to_emme(trip_table_in, trip_purps, fric_facs, my_project):
    ''' Loads data to Emme matrices: Ps and As and friction factor by trip purpose.
        Also initializes empty trip distribution and O-D result tables. '''

    matrix_name_list = [matrix.name for matrix in my_project.bank.matrices()]
    zonesDim = len(my_project.current_scenario.zone_numbers)
    zones = my_project.current_scenario.zone_numbers

    # Create Emme matrices if they don't already exist
    for purpose in trip_purps:
        print(purpose)
        if purpose + 'pro' not in matrix_name_list:
            my_project.create_matrix(str(purpose)+ "pro" , str(purpose) + " productions", "ORIGIN")
        if purpose + 'att' not in matrix_name_list:
            my_project.create_matrix(str(purpose) + "att", str(purpose) + " attractions", "DESTINATION")
        if purpose + 'fri' not in matrix_name_list:
            my_project.create_matrix(str(purpose) + "fri" , str(purpose) + "friction factors", "FULL")
        if purpose + 'dis' not in matrix_name_list:
            my_project.create_matrix(str(purpose) + "dis" , str(purpose) + "distributed trips", "FULL")
        if purpose + 'od' not in matrix_name_list:
            my_project.create_matrix(str(purpose) + "od" , str(purpose) + "O-D tables", "FULL")

        for p_a in ['pro', 'att']:
            # Load zonal production and attractions from CSV (output from trip generation)
            
            trips = np.array(trip_table_in[purpose + p_a])
            trips = np.resize(trips, zonesDim)
            #code below does not work for GQs because there are only 3700 records in the csv file. Not sure if code above is ideal.
            #trips = np.array(trip_table_in.loc[0:zonesDim - 1][purpose + p_a])    # Less 1 because NumPy is 0-based\
            matrix_id = my_project.bank.matrix(purpose + p_a).id    
            emme_matrix = my_project.bank.matrix(matrix_id)  
            emme_matrix = ematrix.MatrixData(indices=[zones],type='f')    # Access Matrix API

             # Update Emme matrix data
            emme_matrix.raw_data = _array.array('f', trips)    # set raw matrix data equal to prod/attr data
            my_project.bank.matrix(matrix_id).set_data(emme_matrix, my_project.current_scenario)

        # Load friction factors by trip purpose
        fri_fac = fric_facs[purpose][0:zonesDim+1,0:zonesDim+1]
        emme_matrix = ematrix.MatrixData(indices=[zones,zones],type='f')    # Access Matrix API
        emme_matrix.raw_data = [_array.array('f',row) for row in fri_fac]
        matrix_id = my_project.bank.matrix(purpose + "fri").id    
        my_project.bank.matrix(matrix_id).set_data(emme_matrix, my_project.current_scenario)
                  
def balance_matrices(trip_purps, my_project):
    ''' Balances productions and attractions by purpose for all internal zones '''
    for purpose in trip_purps:
        # For friction factors, have to make sure 0s in Externals are actually 0, otherwise you will get intrazonal trips
        my_project.matrix_calculator(result = 'mf' + purpose + 'fri', expression = '0', 
                                 constraint_by_zone_destinations = str(LOW_STATION) + '-' + str(HIGH_STATION), 
                                 constraint_by_zone_origins = str(LOW_STATION) + '-' + str(HIGH_STATION))
        print("Balancing trips for purpose: " + str(purpose))
        my_project.matrix_balancing(results_od_balanced_values = 'mf' + purpose + 'dis', 
                                    od_values_to_balance = 'mf' + purpose + 'fri', 
                                    origin_totals = 'mo' + purpose + 'pro', 
                                    destination_totals = 'md' + purpose + 'att', 
                                    constraint_by_zone_destinations = '1-' + str(HIGH_STATION), 
                                    constraint_by_zone_origins = '1-' + str(HIGH_STATION))

def calculate_daily_trips_externals(trip_purps, my_project):
    # Accounting for out- and in-bound trips.
    # The distribution matrices (e.g. 'mfcoldis') are in PA format. Need to convert to OD format by transposing
    #Stefan- changing code for externals- we are sending half the daily trips from external to internal. Now we need add the transpose to get the other direction. 
    for purpose in trip_purps:
        my_project.matrix_calculator(result = 'mf' + purpose + 'od', 
                                     expression = 'mf' + purpose + 'dis + mf' + purpose + 'dis'+ "'")
  
def distribute_trips_externals(trip_table_in, trip_purps, fric_facs, my_project):
    ''' Load data in Emme, balance trips by purpose, and produce O-D trip tables '''
    #print 'in distribute trips function: ' + trip_purps
    # Clear all existing matrices
    delete_matrices(my_project, "ORIGIN")
    delete_matrices(my_project, "DESTINATION")
    delete_matrices(my_project, "FULL")

    # Load data into fresh Emme matrices
    load_matrices_to_emme(trip_table_in, trip_purps, fric_facs, my_project)

    # Balance matrices
    balance_matrices(trip_purps, my_project)

    # Calculate daily trips
    calculate_daily_trips_externals(trip_purps, my_project)

def ext_spg_selected(trip_purps, my_project):
    ''' Select only external and special generator zones '''
    total_sum_by_purp = {}
    for purpose in trip_purps:
        # Load Emme O-D total trip data by purpose
        matrix_id = my_project.bank.matrix(purpose + 'od').id    
        emme_matrix = my_project.bank.matrix(matrix_id)  
        emme_data = emme_matrix.get_data() # Access emme data as numpy matrix
        emme_data = np.array(emme_data.raw_data, dtype='float64')
        filtered = np.zeros_like(emme_data)

        # Add only external rows and columns
        filtered[3700:,:] = emme_data[3700:,:]
        filtered[:,3700:] = emme_data[:,3700:]

        total_sum_by_purp[purpose] = filtered
    return total_sum_by_purp

def main():

    # Load the trip productions and attractions
    trip_table = pd.read_csv(trip_table_loc, index_col="taz")  # total 4K Ps and As by trip purpose

    # Import JSON inputs as dictionaries
    ###
    ### FIXME: save table in database or in model inputs (part of github versioning)
    ###
    coeff = json_to_dictionary('gravity_model')
                               
    # All Non-work external trips assumed as HSP (home-based shopping trips)
    trip_purp_full = ['hsp']

    output_dir = os.path.join(os.getcwd(),r'outputs\supplemental')

    my_project = EmmeProject(r'projects\Supplementals\Supplementals.emp')

    global dictZoneLookup
    dictZoneLookup = dict((value,index) for index,value in enumerate(my_project.current_scenario.zone_numbers))
    
    # Load skim data
    am_cost_skim = load_skims('inputs/model/roster/7to8.h5', mode_name='sov_inc2g')
    am_dist_skim = load_skims('inputs/model/roster/7to8.h5', mode_name='sov_inc1d', divide_by_100=True)
    pm_cost_skim = load_skims('inputs/model/roster/17to18.h5', mode_name='sov_inc2g')
    pm_dist_skim = load_skims('inputs/model/roster/17to18.h5', mode_name='sov_inc1d', divide_by_100=True)
    # Average skims between AM and PM periods
    cost_skim = (am_cost_skim + pm_cost_skim) * .5
    dist_skim = (am_cost_skim + pm_dist_skim) * .5
   
    # Compute friction factors by trip purpose
    fric_facs = calc_fric_fac(cost_skim, dist_skim, coeff)

    # Create trip table for externals 
    distribute_trips_externals(trip_table, trip_purp_full, fric_facs, my_project)

    #removed special generators for now
    ext_spg_trimmed = ext_spg_selected(trip_purp_full, my_project)    # Include only external and special gen. zones

    #Just IXXI trips for now:
    ixxi_trips = ext_spg_trimmed['hsp']
    svtl = ixxi_trips * .8
    h2tl = ixxi_trips * .13
    h3tl = ixxi_trips * .07

    #write out trip table for now:
    my_store = h5py.File(output_dir + '/' + 'external_non_work' + '.h5', "w")
    my_store.create_dataset('svtl', data=svtl)
    my_store.create_dataset('h2tl', data=h2tl)
    my_store.create_dataset('h3tl', data=h3tl)

    my_store.close()

if __name__ == "__main__":
    main()
