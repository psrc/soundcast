from input_configuration import *
##################################### NETWORK IMPORTER ####################################
import_shape = False    # use network shape
master_project = 'LoadTripTables'
project = 'Projects/LoadTripTables/LoadTripTables.emp'
network_summary_project = 'Projects/LoadTripTables/LoadTripTables.emp'
tod_networks = ['am', 'md', 'pm', 'ev', 'ni']
sound_cast_net_dict = {'5to6' : 'am', '6to7' : 'am', '7to8' : 'am', '8to9' : 'am', 
                       '9to10' : 'md', '10to14' : 'md', '14to15' : 'md', 
                       '15to16' : 'pm', '16to17' : 'pm', '17to18' : 'pm', 
                       '18to20' : 'ev', '20to5' : 'ni'}
load_transit_tod = ['5to6', '6to7', '7to8', '8to9', '9to10', '10to14', '14to15', '15to16', '16to17', '17to18', '18to20']

mode_crosswalk_dict = {'b': 'bp', 'bwl' : 'bpwl', 'aijb' : 'aimjbp', 'ahijb' : 'ahdimjbp', 
                      'ashijtuvb': 'asehdimjvutbp', 'r' : 'rc', 'br' : 'bprc', 
                      'ashijtuvbwl' : 'asehdimjvutbpwl', 'ashijtuvbfl' : 'asehdimjvutbpfl', 
                      'asbw' : 'asehdimjvutbpwl', 'ashijtuvbxl' : 'asehdimjvutbpxl', 
                      'ahijstuvbw' : 'asehdimjvutbpw'}
###### Distance-based pricing######
add_distance_pricing = True
# rate below includes 3.5 cent carbon tax
distance_rate_dict = {'am' : 13.5, 'md' : 8.5, 'pm' : 13.5, 'ev' : 8.5, 'ni' : 8.5}
# HOT Lanes
add_hot_lane_tolls = True
hot_rate_dict = {'am' : 35, 'md' : 10, 'pm' : 35, 'ev' : 10, 'ni' : 10}
mode_file = 'modes.txt'
transit_vehicle_file = 'vehicles.txt' 
base_net_name = '_roadway.in'
shape_name = '_link_shape.txt'
turns_name = '_turns.in'
transit_name = '_transit.in'
no_toll_modes = ['s', 'h', 'i', 'j']
unit_of_length = 'mi'    # units of miles in Emme
rdly_factor = .25
coord_unit_length = 0.0001894    # network links measured in feet, converted to miles (1/5280)
headway_file = 'headways.csv'

# in the junctions shapefile in the inputs/networks folder, this is the
# minimum scene_node value where facility type = 99
min_hov_node = {'2014' : 199203, '2025' : 199026, '2040' : 199205, '2040' : 199205}
###################################
################################### SKIMS AND PATHS ####################################
log_file_name = 'outputs/logs/skims_log.txt'
STOP_THRESHOLD = 0.026
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
emme_matrix_subgroups = ["Highway", "Walk", "Bike", "Transit", 'LightRail']
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
transit_skim_tod = ['5to6', '6to7', '7to8', '8to9', '9to10', '10to14', '14to15', '15to16', '16to17', '17to18', '18to20']
transit_submodes = ['b', 'c', 'f', 'p', 'r']
transit_node_attributes = {'headway_fraction' : {'name' : '@hdwfr', 'init_value': .5}, 
                           'wait_time_perception' :  {'name' : '@wait', 'init_value': 2},
                           'in_vehicle_time' :  {'name' : '@invt', 'init_value': 1}}
transit_node_constants = {'2014':{'4943':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '4944':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '4945':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '4952':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '4960':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '4961':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}},
                          '2025':{'5165':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '5166':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '5167':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '5168':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '5670':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '5671':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}},
                          '2040':{'0041':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '0042':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '0043':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '0044':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '0055':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '0056':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '0057':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '0058':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}},
                          '2050':{'0041':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '0042':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '0043':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}, 
                          '0044':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '0055':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '0056':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '0057':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'},
                          '0058':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}}}

transit_network_tod_dict = {'5to6' : 'am', '6to7' : 'am', '7to8' : 'am', '8to9' : 'am',
                            '9to10' : 'md', '10to14' : 'md', '14to15' : 'md',
                            '15to16' : 'pm', '16to17' : 'pm', '17to18' : 'pm',
                            '18to20' : 'ev'}                  

transit_tod = {'5to6' : {'4k_tp' : 'am', 'num_of_hours' : 1},
               '6to7' : {'4k_tp' : 'am', 'num_of_hours' : 1}, 
               '7to8' :  {'4k_tp' : 'am', 'num_of_hours' : 1}, 
               '8to9' :  {'4k_tp' : 'am', 'num_of_hours' : 1}, 
               '9to10' : {'4k_tp' : 'md', 'num_of_hours' : 1}, 
               '10to14' : {'4k_tp' : 'md', 'num_of_hours' : 4}, 
               '14to15' : {'4k_tp' : 'md', 'num_of_hours' : 1},
               '15to16' : {'4k_tp' : 'pm', 'num_of_hours' : 1},
               '16to17' : {'4k_tp' : 'pm', 'num_of_hours' : 1},
               '17to18' : {'4k_tp' : 'pm', 'num_of_hours' : 1},
               '18to20' : {'4k_tp' : 'ev', 'num_of_hours' : 2}}
                

# Transit Fare:
fares_dir = 'inputs/scenario/networks/fares/'
zone_file = 'inputs/scenario/networks/fares/transit_fare_zones.grt'
peak_fare_box = 'inputs/scenario/networks/fares/am_fares_farebox.in'
peak_monthly_pass = 'inputs/scenario/networks/fares/am_fares_monthly_pass.in'
offpeak_fare_box = 'inputs/scenario/networks/fares/Fares/md_fares_farebox.in'
offpeak_monthly_pass = 'inputs/scenario/networks/fares/md_fares_monthly_pass.in'
fare_matrices_tod = ['6to7', '9to10']

# Intrazonals
intrazonal_dict = {'distance' : 'izdist', 'time auto' : 'izatim', 'time bike' : 'izbtim', 'time walk' : 'izwtim'}
taz_area_file = 'inputs/model/intrazonals/taz_acres.in'
origin_tt_file = 'inputs/model/intrazonals/origin_tt.in'
destination_tt_file = 'inputs/model/intrazonals/destination_tt.in'

# Zone Index
#tazIndexFile = '/inputs/TAZIndex_5_28_14.txt'

# SUPPLEMENTAL#######################################################
#Trip-Based Matrices for External, Trucks, and Special Generator Inputs
supplemental_loc = 'outputs/supplemental/'
hdf_auto_filename = 'outputs/supplemental/auto.h5'
hdf_transit_filename = 'outputs/supplemental/transit.h5' 
group_quarters_trips = 'outputs/supplemental/group_quarters/'
ext_spg_trips = 'outputs/supplemental/ext_spg/'
supplemental_modes = ['svtl2', 'trnst', 'bike', 'h2tl2', 'h3tl2', 'walk', 'lttrk','metrk','hvtrk']
special_gen_trips = 'inputs/scenario/supplemental/generation/special_generators.csv'
airport_zone_list = [983] # zone numbers for airport special generator

# Using one AM and one PM time period to represent AM and PM skims
am_skim_file_loc = 'outputs/skims/7to8.h5'
pm_skim_file_loc = 'outputs/skims/17to18.h5'
trip_table_loc = 'inputs/scenario/supplemental/generation/prod_att.csv'
output_dir = 'outputs/supplemental/'
ext_spg_dir = 'outputs/supplemental/ext_spg'
gq_directory = 'outputs/supplemental/group_quarters'
gq_trips_loc = 'inputs/scenario/supplemental/generation/gq_prod_att.csv'
supplemental_project = 'projects/supplementals/supplementals.emp'
# Iterations for fratar process in trip distribution
bal_iters = 5
# Define gravity model coefficients
autoop = 16.75    # Auto operation costs (in hundreds of cents per mile?)
avotda = 0.0303    # VOT
airport_control_total = {'2014' : 101838, '2020' : 130475, '2025' : 149027, '2030' : 170216, '2035' : 189617, '2040' : 211228, '2050' : 257500} 

# Change modes for toll links
toll_modes_dict = {'asehdimjvutbpfl' : 'aedmvutbpfl', 'asehdimjvutbpwl' :	'aedmvutbpwl', 'ahdimjbp' : 'admbp'}