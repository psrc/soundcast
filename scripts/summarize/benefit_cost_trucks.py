import numpy as np
import pandas as pd
import time
import h5py
import math
import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import multiprocessing as mp
import subprocess
import os,sys
from multiprocessing import Pool
from EmmeProject import *
from summary_functions import *


# where are your files?
# this should be a run or config parameter
model_dir = 'C:/bca_test'
truck_time_periods = ['a', 'p', 'e', 'm', 'n']
report_output_location = 'C:/truck_benefits.csv'
base_truck_model_bank= r"R:\SoundCast\releases\soundcast_beta3\Banks\TruckModel\emmebank"
alt_truck_model_bank = r"E:\Driverless4Round2\Banks\TruckModel\emmebank"
zone_dim = 4000



def emmeMatrix_to_numpyMatrix(matrix_name, emmebank, np_data_type, multiplier, max_value = None):
     matrix_id = emmebank.matrix(matrix_name).id
     emme_matrix = emmebank.matrix(matrix_id)
     matrix_data = emme_matrix.get_data()
     np_matrix = np.matrix(matrix_data.raw_data) 
     print np_matrix.max()

     np_matrix = np_matrix * multiplier
    
     if np_data_type == 'uint16':
        max_value = np.iinfo(np_data_type).max
        np_matrix = np.where(np_matrix > max_value, max_value, np_matrix)
    
     if np_data_type <> 'float32':
        np_matrix = np.where(np_matrix > np.iinfo(np_data_type).max, np.iinfo(np_data_type).max, np_matrix)
     
     return np_matrix    



def calculate_tot_diffs(benefits_base, benefits_alt):
    time_diff = (scen_travel_time - base_travel_time)
    trips_total = (scen_trips + base_trips)/2

    tot_time_diff_matrix = time_diff*trips_total
    tot_time_diff_matrix[np.isnan(tot_time_diff_matrix)] =0
    return tot_time_diff_matrix

def calculate_ave_diffs(benefits_base, benefits_alt):
    time_diff = (scen_travel_time - base_travel_time)
    trips_total = (scen_trips + base_trips)/2

    ave_time_diff_matrix = time_diff/trips_total
    ave_time_diff_matrix[np.isnan(ave_time_diff_matrix)] =0
    return ave_time_diff_matrix

def write_results(tot_time_diff_matrix, ave_time_diff_matrix):
    taz_labels = np.array(range(1, zone_dim + 1))
    ave_time_by_origin = np.array(np.mean(ave_time_diff_matrix, axis = 1, dtype=np.float64)).flatten()
    ave_time_by_destination = np.array(np.mean(ave_time_diff_matrix, axis = 0, dtype=np.float64)).flatten()
    total_time_by_origin = np.array(np.sum(tot_time_diff_matrix, axis = 1, dtype=np.float64)).flatten()
    total_time_by_destination = np.array(np.sum(tot_time_diff_matrix, axis = 0, dtype=np.float64)).flatten()
    all_colls = zip(taz_labels, ave_time_by_origin, ave_time_by_destination, total_time_by_origin, total_time_by_destination)
    results = pd.DataFrame(data=all_colls, columns=['taz', 'origin_ave_time_diff', 'destination_ave_time_diff',
                                                    'origin_total_time_diff', 'destination_total_time_diff'])
    results.to_csv(report_output_location)


def calculate_tot_times(base_bank, alt_bank):

    trips_matrix_name = "mfalttrk"
    cost_matrix_name = "mfblgtcs"
    light_truck_trips_base= np.matrix(base_bank.matrix(trips_matrix_name).raw_data)
    light_cost_base=  np.matrix(base_bank.matrix(trips_matrix_name).raw_data)
    light_truck_trips_alt= np.matrix(alternative_bank.matrix(trips_matrix_name).raw_data)
    light_cost_alt=  np.matrix(alternative_bank.matrix(trips_matrix_name).raw_data)

    tot_diff_matrix = (light_cost_alt - light_cost_base)*(light_truck_trips_base+light_truck_trips_alt)

    tot_diff_matrix[np.isnan(tot_diff_matrix)] =0

    return tot_diff_matrix

def calculate_ave_times(base_bank, alt_bank):

    trips_matrix_name = "mfalttrk"
    cost_matrix_name = "mfblgtcs"
    light_truck_trips_base= np.matrix(base_bank.matrix(trips_matrix_name).raw_data)
    light_cost_base=  np.matrix(base_bank.matrix(trips_matrix_name).raw_data)
    light_truck_trips_alt= np.matrix(alt_bank.matrix(trips_matrix_name).raw_data)
    light_cost_alt=  np.matrix(alt_bank.matrix(trips_matrix_name).raw_data)

    ave_diff_matrix = (light_cost_alt - light_cost_base)/((light_truck_trips_base+light_truck_trips_alt)/2)

    ave_diff_matrix[np.isnan(ave_diff_matrix )] =0

    return ave_diff_matrix



def main():

    base_bank = _eb.Emmebank(base_truck_model_bank)
    alternative_bank = _eb.Emmebank(alt_truck_model_bank)
 
    #make a dictionary of matrices by time period and truck class
    all_benefits = dict()

    for each time period:
          for each truck class:

            tot_time_diff_matrix =  calculate_tot_times(base_bank, alternative_bank)
            ave_time_diff_matrix =  calculate_ave_times(base_bank, alternative_bank)

    write_results(tot_time_diff_matrix, ave_time_diff_matrix)

if __name__ == "__main__":
    main()

