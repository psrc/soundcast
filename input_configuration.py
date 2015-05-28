# This file contains model input parameters imported by SoundCast scripts.   

#################################### RUN SOUNDCAST ####################################

# Scenario and input paths
base_year = '2010'
scenario_name = '2010'
daysim_code = 'R:/soundcast/daysim' 
master_project = 'LoadTripTables'
base_inputs = 'R:/soundcast/inputs/' + scenario_name
network_buffer_inputs = 'R:/soundcast/inputs/parcel_buffering_network/parcel_buff_network_inputs.7z'
network_buffer_code = 'R:/SoundCast/util/parcel_buffering/'

recipients = []

# Script and subprocess controls
 
# Only update parking for future-year analysis!
run_update_parking = False
run_convert_hhinc_2000_2010 = True
run_parcel_buffering = True
run_copy_daysim_code = True
run_setup_emme_project_folders = True
run_setup_emme_bank_folders = True
run_copy_large_inputs = True
run_import_networks = True
run_skims_and_paths_seed_trips = True
should_build_shadow_price =True
run_skims_and_paths = True
run_truck_model =True
run_supplemental_trips = True
run_daysim = True
run_parcel_buffer_summary = True
run_network_summary = True
run_soundcast_summary = True
run_travel_time_summary = True
run_create_daily_bank = True


# Model iterations, population sampling, log files, etc.
pop_sample = [10, 5, 1]
# start building shadow prices - only run work locations
shadow_work = [2, 1, 1]
shadow_con = 10 #%RMSE for shadow pricing to consider being converged
parcel_decay_file = 'inputs/buffered_parcels.dat' #File with parcel data to be compared to
# run daysim and assignment in feedback until convergence


main_log_file = 'soundcast_log.txt'
network_summary_files = ['6to7_transit', '7to8_transit', '8to9_transit', '9to10_transit',
                         'counts_output', 'network_summary']
good_thing = ["cookie", "run", "puppy", "beer", "snack", "nap","venti cinnamon dolce latte"]

# These files are often missing from a run.  We want to check they are present and warn if not.
# Please add to this list as you find files that are missing.
commonly_missing_files = ['buffered_parcels.dat', 'tazdata.in']

#################################### SKIMS AND PATHS ####################################
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
                          '0892':{'@hdwfr': '.1', '@wait' : '1', '@invt' : '.70'}}}
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


#################################### NETWORK IMPORTER ####################################
project = 'Projects/LoadTripTables/LoadTripTables.emp'
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
                         '@ovol' : 'observed volume', 
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
uc_list = ['@svtl1', '@svtl2', '@svtl3', '@svnt1', '@svnt2', '@svnt3', '@h2tl1', '@h2tl2', '@h2tl3',
           '@h2nt1', '@h2nt2', '@h2nt3', '@h3tl1', '@h3tl2', '@h3tl3', '@h3nt1', '@h3nt2', '@h3nt3', '@lttrk', '@mveh', '@hveh', '@bveh']


#################################### TRUCK MODEL ####################################
truck_model_project = 'Projects/TruckModel/TruckModel.emp'
#hh_employment_file = 'tazdata.in'
districts_file = 'districts19_ga.ens'
truck_trips_h5_filename = 'inputs/4k/auto.h5'
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
					
#################################### SOUNDCAST SUMMARY ####################################
h5_results_file = 'outputs/daysim_outputs.h5'
h5_results_name = 'DaysimOutputs'
h5_comparison_file = 'scripts/summarize/survey.h5'
h5_comparison_name = 'Survey'
guidefile = 'scripts/summarize/CatVarDict.xlsx'
districtfile = 'scripts/summarize/TAZ_TAD_County.csv'
report_output_location = 'outputs'

travel_time_file = 'inputs/ObservedTravelTimes.xlsx'

topsheet = 'outputs/Topsheet.xlsx'

# Specific reports to run
run_daysim_report = True
run_day_pattern_report = True
run_mode_choice_report = True
run_dest_choice_report = True
run_long_term_report = True
run_time_choice_report = True
run_district_summary_report = True

output_list = ['prod_att.csv', 'gq_prod_att.csv', 'network_summary.csv', 'counts_output.csv', 'daysim_outputs.h5',
               'screenline_volumes', 'Topsheet.xlsx']