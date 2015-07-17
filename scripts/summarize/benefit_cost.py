import numpy as np
import pandas as pd
import time
import h5py
import math
from summary_functions import *


# where are your files?
# this should be a run or config parameter
model_dir = 'C:/soundcast615/'

h5_base_file = 'outputs/daysim_outputs.h5'
h5_base_name = 'Base'
h5_scen_file = 'outputs/daysim_outputs2040luv.h5'
h5_scen_name = 'Scenario'
report_output_location = 'outputs/time_zone.csv'
guidefile = 'scripts/summarize/CatVarDict.xlsx'
zone_dim = 4000 #hard code should be in the config
#output

##################################

# Construct file location names
h5_base_file = model_dir + h5_base_file
h5_scen_file =  model_dir + h5_scen_file
guidefile = model_dir + guidefile
report_output_location = model_dir + report_output_location

         
def read_in_data(file_name, data_names):
    my_store = h5py.File(file_name, "r+")
    trips_base = my_store['Trip']
    var_dict = {}

    for name in data_names:
        var_dict[name]= np.asarray(trips_base[name])

    return var_dict

def fill_trip_matrices(output):

    trips=np.zeros((zone_dim,zone_dim), np.float64)

    for trip in range (0, len(output['otaz'])-1):
        this_otaz =  output['otaz'][trip]
        this_dtaz = output['dtaz'][trip]
        trips[this_otaz, this_dtaz] =  trips[this_otaz, this_dtaz] + 1
    
    return trips


def fill_time_matrices(output):
    travel_times =np.zeros((zone_dim,zone_dim), np.float64)

    for trip in range (0, len(output['otaz'])-1):
        this_otaz =  output['otaz'][trip]
        this_dtaz = output['dtaz'][trip]
        this_time = output['travtime'][trip]
        travel_times[this_otaz, this_dtaz] =  travel_times[this_otaz, this_dtaz] + this_time

    return travel_times

def calculate_ave_diffs(base_trips, base_travel_time, scen_trips, scen_travel_time):
    time_diff = (scen_travel_time - base_travel_time)
    trips_total = (scen_trips + base_trips)

    avg_time_diff_matrix = time_diff/trips_total
    avg_time_diff_matrix[np.isnan(avg_time_diff_matrix)] =0
    return avg_time_diff_matrix


def calculate_tot_diffs(base_trips, base_travel_time, scen_trips, scen_travel_time):
    time_diff = (scen_travel_time - base_travel_time)
    trips_total = (scen_trips + base_trips)

    tot_time_diff_matrix = time_diff*trips_total
    tot_time_diff_matrix[np.isnan(avg_time_diff_matrix)] =0
    return tot_time_diff_matrix


def write_results(avg_time_diff_matrix, tot_time_diff_matrix):
    taz_labels = np.array(range(1, zone_dim + 1))
    time_by_origin = np.mean(avg_time_diff_matrix, axis = 1, dtype=np.float64)
    time_by_destination = np.mean(avg_time_diff_matrix, axis = 0, dtype=np.float64)
    total_time_by_origin = np.sum(tot_time_diff_matrix, axis = 1, dtype=np.float64)
    total_time_by_destination = np.sum(tot_time_diff_matrix, axis = 0, dtype=np.float64)
    all_colls = zip(taz_labels,time_by_origin, time_by_destination, 'total_time_by_origin', 'total_time_by_destination')
    results = pd.DataFrame(data=all_colls, columns=['taz','origin_avg_time_diff', 'destination_avg_time_diff', 'origin_total_time_diff', 'destination_total_time_diff'])
    results.to_csv(report_output_location)

def main():
    variables_to_read =['otaz', 'dtaz', 'travtime']
    matrices_to_fill = ['trips', 'travtime']
    outputs_base = {}
    outputs_scenario = {}
    matrices_base = {}
    matrices_scenario = {}

    outputs_base =read_in_data(h5_base_file,variables_to_read)
    outputs_scenario = read_in_data(h5_scen_file,variables_to_read)
    base_trips = fill_trip_matrices(outputs_base)
    base_trav_times = fill_time_matrices(outputs_base)
    scen_trips = fill_trip_matrices(outputs_scen)
    scen_trav_times = fill_time_matrices(outputs_scen)

    time_diff_matrix = calculate_ave_diffs(base_trips, base_travel_times, scen_trips, scen_trav_time)
    time_diff_matrix = calculate_tot_diffs(base_trips, base_travel_times, scen_trips, scen_trav_time)
    write_results(time_diff_matrix, total_diff_matrix)

if __name__ == "__main__":
    main()