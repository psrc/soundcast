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
base_truck_model_bank= r"C:\soundcast\Banks\TruckModel\emmebank"
alt_truck_model_bank = r"R:\SoundCast\releases\soundcast_release_c1\Banks\TruckModel\emmebank"
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
    trips_total = (scen_trips + base_trips)

    tot_time_diff_matrix = time_diff*trips_total
    tot_time_diff_matrix[np.isnan(avg_time_diff_matrix)] =0
    return tot_time_diff_matrix

def write_results(tot_time_diff_matrix):
    taz_labels = np.array(range(1, zone_dim + 1))
    total_time_by_origin = np.sum(tot_time_diff_matrix, axis = 1, dtype=np.float64)
    total_time_by_destination = np.sum(tot_time_diff_matrix, axis = 0, dtype=np.float64)
    all_colls = zip(taz_labels, total_time_by_origin, total_time_by_destination)
    results = pd.DataFrame(data=all_colls, columns=['taz', 'origin_total_time_diff', 'destination_total_time_diff'])
    results.to_csv(report_output_location)


def calculate_times(bank):

    trips_matrix_name = "mfalttrk"
    cost_matrix_name = "mfblgtcs"
    light_truck_trips= np.matrix(base_bank.matrix(trips_matrix_name).raw_data)
    light_cost=  np.matrix(base_bank.matrix(trips_matrix_name).raw_data)
    total_cost = light_truck_trips * light_cost
    total_cost[np.isnan(total_cost)] =0

    return total_cost



def main():

    base_bank = _eb.Emmebank(base_truck_model_bank)
    alternative_bank = _eb.Emmebank(alt_truck_model_bank)
 
    times_base = calculate_times(base_bank)
    times_alt = calculate_times(alternative_bank)

    tot_time_diff_matrix =  times_base - times_alt
   

    write_results(tot_time_diff_matrix)

if __name__ == "__main__":
    main()

