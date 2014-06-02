# This file contains model input parameters imported by SoundCast scripts.   

#################################### RUN SOUNDCAST ####################################

# Scenario and input paths
scenario_name = '2040'
daysim_code = 'R:/soundcast/daysim' 
master_project = 'LoadTripTables'
base_inputs = 'R:/soundcast/inputs/' + scenario_name

# Script and subprocess controls 
run_copy_daysim_code = False
run_setup_emme_project_folders = False
run_setup_emme_bank_folders = False
run_copy_inputs = False
run_import_networks = False 
run_skims_and_paths = False
run_truck_model = True
run_daysim = False
run_network_summary = False
run_r_summaries = False

# Model iterations, population sampling, log files, etc. 
num_iter = 1
pop_sample = [20, 20, 20, 20, 20, 20, 20, 20, 20]
main_log_file = 'soundcast_log.txt'
network_summary_files = ['6to7_transit', '7to8_transit', '8to9_transit', '9to10_transit',
                         'counts_output', 'network_summary']
good_thing = ["cookie", "pickle", "puppy", "beer", "snack"]


#################################### SKIMS AND PATHS ####################################
log_file_name = 'skims_log.txt'
STOP_THRESHOLD = 0.1
parallel_instances = 6    # Number of simultaneous parallel processes. Must be a factor of 12.
global_iterations = 1
max_iter = 50              # Assignment Convergence Criteria
b_rel_gap = 0.0001         # Assignment Convergence Criteria
MIN_EXTERNAL = 3733-1      #zone of externals (subtract 1 because numpy is zero-based)
MAX_EXTERNAL = 3749-1      #zone of externals (subtract 1 because numpy is zero-based)
SPECIAL_GENERATORS = {"SeaTac":982,"Tacoma Dome":3108,"exhibition center":630, "Seattle Center":437}
## HDF5 Groups and Subgroups
hdf5_maingroups = ["Daysim","Emme","Truck Model","UrbanSim"]
hdf5_emme_subgroups = ["5to6","6to7","7to8","8to9","9to10","10to14","14to15","15to16","16to17","17to18","18to20","20to5"]
emme_matrix_subgroups = ["Highway", "Walk", "Bike", "Transit"]
hdf5_urbansim_subgroups = ["Households","Parcels","Persons"]
hdf5_freight_subgroups = ["Inputs","Outputs","Rates"]
hdf5_daysim_subgroups = ["Household","Person","Trip","Tour"]

# Skim for time, cost
skim_matrix_designation_all_tods = ['t','c']
skim_matrix_designation_limited = ['d']

# Skim for distance for only these time periods
distance_skim_tod = ['7to8', '17to18']
generalized_cost_tod = ['7to8', '17to18']
gc_skims = {'light_trucks' : 'lttrk', 'medium_trucks' : 'metrk', 'heavy_trucks' : 'hvtrk'}

# Bike/Walk Skims
bike_walk_skim_tod = ['5to6']
bike_walk_matrix_dict = {'walk':{'time' : 'walkt', 'description' : 'walk time',
                                 'demand' : 'walk', 'modes' : ["w", "x"],
                                 'intrazonal_time' : 'izwtim'},
                         'bike':{'time' : 'biket', 'description' : 'bike time',
                                 'demand' : 'bike', 'modes' : ["k", "l", "q"],
                                 'intrazonal_time' : 'izbtim'}}

# Transit Inputs:
transit_skim_tod = ['6to7', '7to8', '8to9', '9to10', '10to14', '14to15']
transit_submodes = ['b', 'c', 'f', 'p', 'r']
transit_node_attributes = {'headway_fraction' : {'name' : '@hdwfr', 'init_value': .5}, 
                           'wait_time_perception' :  {'name' : '@wait', 'init_value': 2},
                           'in_vehicle_time' :  {'name' : '@invt', 'init_value': 1}}
transit_node_constants = {'am':{'0888':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.60'}, 
                          '0889':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.60'},
                          '0892':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.60'}}}
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
tazIndexFile = '/inputs/TAZIndex_wo_gaps.txt'

#Trip-Based Matrices for External, Trucks, and Special Generator Inputs
hdf_auto_filename = 'inputs/4k/trips_auto_4k.h5'
hdf_transit_filename = 'inputs/4k/trips_transit_4k.h5'

# Change modes for toll links
toll_modes_dict = {'asehdimjvutbpfl' : 'aedmvutbpfl', 'asehdimjvutbpwl' :	'aedmvutbpwl', 'ahdimjbp' : 'admbp'}


#################################### NETWORK IMPORTER ####################################
project = 'Projects/LoadTripTables/LoadTripTables.emp'
tod_networks = ['am', 'md', 'pm', 'ev', 'ni']
sound_cast_net_dict = {'5to6' : 'am', '6to7' : 'am', '7to8' : 'am', '8to9' : 'am', 
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


#################################### NETWORK SUMMARY ####################################
network_summary_project = 'Projects/LoadTripTables/LoadTripTables.emp'
fac_type_dict = {'highway' : 'ul3 = 1 or ul3 = 2',
                 'arterial' : 'ul3 = 3 or ul3 = 4 or ul3 = 6',
                 'connectors' : 'ul3 = 5'}
extra_attributes_dict = {'@tveh' : 'total vehicles', 
                         '@mveh' : 'medium trucks', 
                         '@hveh' : 'heavy trucks', 
                         '@vmt' : 'vmt',\
                         '@vht' : 'vht', 
                         '@trnv' : 'buses in auto equivalents', 
                         '@bveh' : 'number of buses'}
transit_extra_attributes_dict = {'@board' : 'total boardings', '@timtr' : 'transit line time'}
transit_tod = {'6to7' : {'4k_tp' : 'am', 'num_of_hours' : 1}, 
               '7to8' :  {'4k_tp' : 'am', 'num_of_hours' : 1}, 
               '8to9' :  {'4k_tp' : 'am', 'num_of_hours' : 1}, 
               '9to10' : {'4k_tp' : 'md', 'num_of_hours' : 1}, 
               '10to14' : {'4k_tp' : 'md', 'num_of_hours' : 4}, 
               '14to15' : {'4k_tp' : 'md', 'num_of_hours' : 1}}
# Input Files:
counts_file = 'TrafficCounts_Mid.txt'
# Output Files: 
net_summary_file = 'network_summary.csv'
counts_output_file = 'counts_output.csv'
screenlines_file = 'screenline_volumes.csv'
uc_list = ['@svtl1', '@svtl2', '@svtl3', '@svnt1', '@h2tl1', '@h2tl2', '@h2tl3',
           '@h2nt1', '@h3tl1', '@h3tl2', '@h3tl3', '@h3nt1', '@lttrk', '@mveh', '@hveh', '@bveh']


#################################### TRUCK MODEL ####################################
truck_model_project = 'Projects/TruckModel/TruckModel.emp'
#hh_employment_file = 'tazdata.in'
districts_file = 'districts19_ga.ens'
truck_trips_h5_filename = 'inputs/4k/trips_auto_4k.h5'
truck_base_net_name = 'am_roadway.in'
#TOD to create Bi-Dir skims (AM/EV Peak)
truck_generalized_cost_tod = {'7to8' : 'am', '17to18' : 'pm'}
#GC & Distance skims that get read in from Soundcast

# 4k time of day
tod_list = ['am','md', 'pm', 'ev', 'ni']
# External Magic Numbers
LOW_STATION = 3733
HIGH_STATION = 3750
EXTERNAL_DISTRICT = 'ga20'
					
