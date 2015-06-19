import numpy as np
import pandas as pd
import time
import h5py
import math
from summary_functions import *


# where are your files?
# this should be a run or config parameter
model_dir = 'C:/soundcast615/'

h5_base_file = 'outputs/daysim_outputs3.h5'
h5_base_name = 'Base'
h5_scen_file = 'outputs/daysim_outputs1.h5'
h5_scen_name = 'Scenario'
report_output_location = 'outputs/benefits_zone.csv'
guidefile = 'scripts/summarize/CatVarDict.xlsx'
zone_dim = 4050 #hard code should be in the config
#output

##################################

# Construct file location names
h5_base_file = model_dir + h5_base_file
h5_scen_file =  model_dir + h5_scen_file
guidefile = model_dir + guidefile
report_output_location = model_dir + report_output_location


#read in the data
my_store_base = h5py.File(h5_base_file, "r+")
my_store_scen = h5py.File(h5_scen_file, "r+")

trips_base = my_store_base['Trip']
trips_scen = my_store_scen['Trip']

otaz_base = np.asarray(trips_base["otaz"])
otaz_base = otaz_base.astype('int')

dtaz_base = np.asarray(trips_base["dtaz"])
dtaz_base = dtaz_base.astype('int')

vot_base = np.asarray(trips_base["vot"])
time_base = np.asarray(trips_base["travtime"])
cost_base =vot_base*time_base

otaz_scen = np.asarray(trips_scen["otaz"])
otaz_scen = otaz_scen.astype('int')

dtaz_scen = np.asarray(trips_scen["dtaz"])
dtaz_scen = dtaz_base.astype('int')

vot_scen = np.asarray(trips_scen["vot"])
time_scen = np.asarray(trips_scen["travtime"])
cost_scen =vot_scen*time_scen


trip_base_matrix = np.zeros((zone_dim,zone_dim), np.float64)
cost_base_matrix= np.zeros((zone_dim,zone_dim), np.float64)
trip_scen_matrix = np.zeros((zone_dim,zone_dim), np.float64)
cost_scen_matrix= np.zeros((zone_dim,zone_dim), np.float64)

# Fill up the base matrices from the arrays of data because they will be faster to work with
for trip in range (0, len(otaz_base)):
    this_otaz = otaz_base[trip]
    this_dtaz = dtaz_base[trip]
    this_cost = cost_base[trip]
    trip_base_matrix [this_otaz, this_dtaz] = trip_base_matrix[this_otaz, this_dtaz] + 1
    cost_base_matrix [this_otaz, this_dtaz] = cost_base_matrix[this_otaz, this_dtaz] + this_cost

# Fill up the scenario matrices
for trip in range (0, len(otaz_scen)):
    this_otaz = otaz_scen[trip]
    this_dtaz = dtaz_scen[trip]
    this_cost = cost_scen[trip]
    trip_scen_matrix [this_otaz, this_dtaz] = trip_scen_matrix[this_otaz, this_dtaz] + 1
    cost_scen_matrix [this_otaz, this_dtaz] = cost_scen_matrix[this_otaz, this_dtaz] + this_cost

cost_diff = (cost_scen_matrix - cost_base_matrix)
trips_total = (trip_scen_matrix + trip_base_matrix)/2

benefit_matrix = cost_diff*trips_total

taz_labels = np.array(range(1, zone_dim + 1))

#benefits by origin:
bens_by_origin = np.nansum(benefit_matrix , axis = 1, dtype=np.float64)
    
#benefits by destination:
bens_by_destination = np.nansum(benefit_matrix, axis = 0, dtype=np.float64)
    
#combine arrays:
all_colls = zip(taz_labels,bens_by_origin, bens_by_destination)
    
#convert to dataframe
results = pd.DataFrame(data=all_colls, columns=['taz','origin_benefit', 'destination_benefit'])

results.to_csv(report_output_location)
         


