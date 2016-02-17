﻿##################################### NETWORK IMPORTER ####################################
project = 'Projects/LoadTripTables/LoadTripTables.emp'
network_summary_project = 'Projects/LoadTripTables/LoadTripTables.emp'
tod_networks = ['am', 'md', 'pm', 'ev', 'ni']
sound_cast_net_dict = {'5to6' : 'ni', '6to7' : 'am', '7to8' : 'am', '8to9' : 'am', 
                       '9to10' : 'md', '10to14' : 'md', '14to15' : 'md', 
                       '15to16' : 'pm', '16to17' : 'pm', '17to18' : 'pm', 
                       '18to20' : 'ev', '20to5' : 'ni'}
load_transit_tod = ['6to7', '7to8', '8to9', '9to10', '10to14', '14to15']

mode_crosswalk_dict = {'b': 'bp', 'bwl' : 'bpwl', 'aijb' : 'aimjbp', 'ahijb' : 'ahdimjbp', 
                      'ashijtuvb': 'asehdimjvutbp', 'r' : 'rc', 'br' : 'bprc', 
                      'ashijtuvbwl' : 'asehdimjvutbpwl', 'ashijtuvbfl' : 'asehdimjvutbpfl', 
                      'asbw' : 'asehdimjvutbpwl', 'ashijtuvbxl' : 'asehdimjvutbpxl', 
                      'ahijstuvbw' : 'asehdimjvutbpw'}
mode_file = 'modes.txt'
transit_vehicle_file = 'vehicles.txt' 
base_net_name = '_roadway.in'
turns_name = '_turns.in'
transit_name = '_transit.in'
shape_name = '_link_shape_1002.txt'
no_toll_modes = ['s', 'h', 'i', 'j']

################################### SKIMS AND PATHS ####################################
log_file_name = 'skims_log.txt'
STOP_THRESHOLD = 0.025
parallel_instances = 12   # Number of simultaneous parallel processes. Must be a factor of 12.
max_iter = 50             # Assignment Convergence Criteria
best_relative_gap = 0.01  # Assignment Convergence Criteria
relative_gap = .0001
normalized_gap = 0.01

MIN_EXTERNAL = 3733      #zone of externals (subtract 1 because numpy is zero-based)
MAX_EXTERNAL = 3750      #zone of externals (subtract 1 because numpy is zero-based)
HIGH_TAZ = 3700
LOW_PNR = 3751
HIGH_PNR = 4000

SPECIAL_GENERATORS = {"SeaTac":983,"Tacoma Dome":3110,"exhibition center":631, "Seattle Center":438}
feedback_list = ['Banks/7to8/emmebank','Banks/17to18/emmebank']

# Time of day periods
tods = ['5to6', '6to7', '7to8', '8to9', '9to10', '10to14', '14to15', '15to16', '16to17', '17to18', '18to20', '20to5' ]
project_list = ['Projects/' + tod + '/' + tod + '.emp' for tod in tods]

## HDF5 Groups and Subgroups
hdf5_maingroups = ["Daysim","Emme","Truck Model","UrbanSim"]
hdf5_emme_subgroups = tods
emme_matrix_subgroups = ["Highway", "Walk", "Bike", "Transit"]
hdf5_urbansim_subgroups = ["Households","Parcels","Persons"]
hdf5_freight_subgroups = ["Inputs","Outputs","Rates"]
hdf5_daysim_subgroups = ["Household","Person","Trip","Tour"]

# Skim for time, cost
skim_matrix_designation_all_tods = ['t','c']  # Time (t) and direct cost (c) skims
skim_matrix_designation_limited = ['d']    # Distance skim

# Skim for distance for only these time periods
distance_skim_tod = ['7to8', '17to18']
generalized_cost_tod = ['7to8', '17to18']
gc_skims = {'light_trucks' : 'lttrk', 'medium_trucks' : 'metrk', 'heavy_trucks' : 'hvtrk', 'sov' : 'svtl2'}

# Bike/Walk Skims
bike_walk_skim_tod = ['5to6']

# Transit Inputs:
transit_skim_tod = ['6to7', '7to8', '8to9', '9to10', '10to14', '14to15']
transit_submodes = ['b', 'c', 'f', 'p', 'r']
transit_node_attributes = {'headway_fraction' : {'name' : '@hdwfr', 'init_value': .5}, 
                           'wait_time_perception' :  {'name' : '@wait', 'init_value': 2},
                           'in_vehicle_time' :  {'name' : '@invt', 'init_value': 1}}
transit_node_constants = {'am':{'0888':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '0889':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '0892':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '0897':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}}}
transit_network_tod_dict = {'6to7' : 'am', '7to8' : 'am', '8to9' : 'am',
                            '9to10' : 'md', '10to14' : 'md', '14to15' : 'md'}                  

# Transit Fare:
zone_file = 'inputs/Fares/transit_fare_zones.grt'
peak_fare_box = 'inputs/Fares/am_fares_farebox.in'
peak_monthly_pass = 'inputs/Fares/am_fares_monthly_pass.in'
offpeak_fare_box = 'inputs/Fares/md_fares_farebox.in'
offpeak_monthly_pass = 'inputs/Fares/md_fares_monthly_pass.in'
fare_matrices_tod = ['6to7', '9to10']

# Intrazonals
intrazonal_dict = {'distance' : 'izdist', 'time auto' : 'izatim', 'time bike' : 'izbtim', 'time walk' : 'izwtim'}
taz_area_file = 'inputs/intrazonals/taz_acres.in'
origin_tt_file = 'inputs/intrazonals/origin_tt.in'
destination_tt_file = 'inputs/intrazonals/destination_tt.in'

# Zone Index
tazIndexFile = '/inputs/TAZIndex_5_28_14.txt'

# SUPPLEMENTAL#######################################################
#Trip-Based Matrices for External, Trucks, and Special Generator Inputs
supplemental_loc = 'outputs/supplemental/'
hdf_auto_filename = 'inputs/4k/auto.h5'
hdf_transit_filename = 'inputs/4k/transit.h5' 
group_quarters_trips = 'outputs/supplemental/group_quarters/'
ext_spg_trips = 'outputs/supplemental/ext_spg/'
supplemental_modes = ['svtl2', 'trnst', 'bike', 'h2tl2', 'h3tl2', 'walk', 'lttrk','metrk','hvtrk']
hh_trip_loc = '/supplemental/generation/rates/hh_triprates.in'
nonhh_trip_loc = '/supplemental/generation/rates/nonhh_triprates.in'
puma_taz_loc = '/supplemental/generation/ensembles/puma00.ens'
taz_data_loc = '/supplemental/generation/landuse/tazdata.in'
pums_data_loc = '/supplemental/generation/pums/' 
externals_loc = '/supplemental/generation/externals.csv'
# Special generator zones and demand (dictionary key is TAZ, value is demand)
spg_general = {3110: 1682,    
               631: 7567, 
               438: 14013}    
spg_airport = {983: 101838}

# Using one AM and one PM time period to represent AM and PM skims
am_skim_file_loc = 'inputs/7to8.h5'
pm_skim_file_loc = 'inputs/17to18.h5'
trip_table_loc = 'outputs/prod_att.csv'
output_dir = 'outputs/supplemental/'
ext_spg_dir = 'outputs/supplemental/ext_spg'
gq_directory = 'outputs/supplemental/group_quarters'
gq_trips_loc = 'outputs/gq_prod_att.csv'
supplemental_project = 'projects/supplementals/supplementals.emp'
# Iterations for fratar process in trip distribution
bal_iters = 5
# Define gravity model coefficients
autoop = 16.75    # Auto operation costs (in hundreds of cents per mile?)
avotda = 0.0303    # VOT

# Change modes for toll links
toll_modes_dict = {'asehdimjvutbpfl' : 'aedmvutbpfl', 'asehdimjvutbpwl' :	'aedmvutbpwl', 'ahdimjbp' : 'admbp'}