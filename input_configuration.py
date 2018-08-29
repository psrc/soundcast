import os
# This file contains model input parameters imported by SoundCast scripts.

# CONFIGURATION TO RUN SOUNDCAST
# Note there are many other configuration files for specific model steps in their respective directories, such as Daysim, or skimming.

# Scenario and input paths
#####################################################################
base_year = '2014'  # This should always be 2014 unless the base year changes
scenario_name = '2014'
model_year = '2014'
main_inputs_folder = 'R:/SoundCast/Inputs/lodes/vision'
#####################################################################

######Set up:######
run_accessibility_calcs = True
run_copy_daysim_code = True
run_setup_emme_project_folders = True
run_setup_emme_bank_folders = True
run_copy_scenario_inputs = True
run_import_networks = True
#only run_daysim_zone_inputs in the base year currently
run_daysim_zone_inputs = True
run_integrated = False

# to get the first iteration of skims:
run_skims_and_paths_free_flow = True

##### Shadow prices now copied and are always used after the first time they have been created for a year.
#### This only needs to be turned off if they haven't been made for that year yet.

should_build_shadow_price = False

###### Models to Run:######
run_skims_and_paths = True
run_truck_model = True
run_supplemental_trips = True
run_daysim = True
run_supplemental_generation = True
###########################

#Summaries to run:######
run_input_summary = True
run_network_summary = True
run_grouped_summary = False
run_soundcast_summary = False
run_truck_summary = False
########################

###### Specific reports to run######
run_daysim_report = False
run_day_pattern_report = False
run_mode_choice_report = False
run_dest_choice_report = False
run_long_term_report = False
run_time_choice_report = False
####################################

delete_banks = False

###### Distance-based pricing######
add_distance_pricing = False
# rate below includes 3.5 cent carbon tax
distance_rate_dict = {'am' : 13.5, 'md' : 8.5, 'pm' : 13.5, 'ev' : 8.5, 'ni' : 8.5}
# HOT Lanes
add_hot_lane_tolls = False
hot_rate_dict = {'am' : 35, 'md' : 10, 'pm' : 35, 'ev' : 10, 'ni' : 10}

###### Model iterations, population sampling, log files, etc.######
pop_sample = [1, 1, 1, 1, 1, 1, 1, 1, 1]
# Assignment Iterations (must be same length as pop_sample:
max_iterations_list = [10, 100, 100, 100, 100, 100, 100, 100, 100]
min_pop_sample_convergence_test = 10
# start building shadow prices - only run work locations
shadow_work = [2, 1, 1, 1]
shadow_con = 30 #%RMSE for shadow pricing to consider being converged
####################################

# These files generally do not change and don't need to be toggled here usually
parcel_decay_file = 'inputs/buffered_parcels.txt' #File with parcel data to be compared to
# run daysim and assignment in feedback until convergence
main_log_file = 'soundcast_log.txt'
master_project = 'LoadTripTables'
network_summary_files = ['6to7_transit', '7to8_transit', '8to9_transit', '9to10_transit',
                         'counts_output', 'network_summary']

#This is what you get if the model runs cleanly, but it's random:
good_thing = ["cookie", "run", "puppy", "seal sighting",  "beer", "sunshine", "nap","world peace"]

base_inputs = os.path.join(main_inputs_folder, base_year)
scenario_inputs = os.path.join(main_inputs_folder, scenario_name)

# Integrated Run Settings
#################################
# Only required for integrated Urbans runs; leave as default for standard runs

# Root dir for all Soundcast runs
urbansim_skims_dir = r'E:\soundcast_root'

# Urbansim outputs dir
urbansim_outputs_dir = r'E:\opusgit\urbansim_data\data\psrc_parcel\2014SoundCastData\urbansim_outputs'