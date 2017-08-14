import os
from input_configuration_simple import *

# This file contains model input parameters imported by SoundCast scripts.   

# If you are using the simple configuration, in the file input_configuration_simple, you will set use_simple_configuration = True, and
# the values of variables to run will be set in that file.  Otherwise the values can be over-ridden below.

# CONFIGURATION TO RUN SOUNDCAST
# Note there are many other configuration files for specific model steps in their respective directories, such as Daysim, or skimming.


####################################################################
#If you need to have more detailed control, fill in these variables

if not(use_simple_configuration):
    
    # Scenario and input paths
    base_year = '2014'  # This should always be 2014 unless the base year changes
    scenario_name = '2014'
    model_year = '2014'
    daysim_code = 'R:/SoundCast/daysim_2016' 
    master_project = 'LoadTripTables'
    main_inputs_folder =  'R:/SoundCast/Inputs'
    base_inputs = os.path.join(main_inputs_folder, base_year)
    scenario_inputs = os.path.join(main_inputs_folder, scenario_name)
    # For Overriding the simple configuration, when you want to run things in more detail:
    
    ###### Only Convert 2010 hhinc if using 2010 base year!######
    run_convert_hhinc_2000_2010 = False
    #############################################################
    
    ###### Distance-based pricing######
    add_distance_pricing = False
    # rate below includes 3.5 cent carbon tax
    distance_rate_dict = {'am' : 13.5, 'md' : 8.5, 'pm' : 13.5, 'ev' : 8.5, 'ni' : 8.5}
    # HOT Lanes
    add_hot_lane_tolls = False
    hot_rate_dict = {'am' : 35, 'md' : 10, 'pm' : 35, 'ev' : 10, 'ni' : 10}
    # in the junctions shapefile in the inputs/networks folder, this is the minimum scene_node value where facility type = 99
    min_hov_node = 199203
    ###################################
    
    ######Set up:######
    run_accessibility_calcs = True
    run_copy_daysim_code = True
    run_setup_emme_project_folders = True
    run_setup_emme_bank_folders = True
    run_copy_large_inputs = True
    run_import_networks = True
    ###################

    ###### Only one of the following should be Tru!!!!!!######
    run_copy_seed_skims = False
    run_skims_and_paths_seed_trips = False
    run_skims_and_paths_free_flow = True
    ##########################################################
    
    ##### Shadow prices now copied and are always used. Only Run this if building shadow prices from scratch!
    should_build_shadow_price = False
    ##########################################################
    
    ###### Models to Run:######
    run_skims_and_paths = True
    run_truck_model = True
    run_supplemental_trips = True
    run_daysim = True
    ###########################

    ###### Additional skims for Benefit Cost:######
    should_run_reliability_skims = True
    ###########################
    
    #Summaries to run:######
    run_accessibility_summary = True
    run_network_summary = True
    run_grouped_summary = True
    run_soundcast_summary = True
    run_truck_summary = True
    run_landuse_summary = False
    ########################

    ###### Specific reports to run######
    run_daysim_report = True
    run_day_pattern_report = True
    run_mode_choice_report = True
    run_dest_choice_report = True
    run_long_term_report = True
    run_time_choice_report = True
    run_district_summary_report = False
    ####################################
    

    ###### Model iterations, population sampling, log files, etc.######
    pop_sample = [1, 1, 1, 1, 1, 1, 1, 1, 1]
    # Assignment Iterations (must be same length as pop_sample:
    max_iterations_list = [10, 100, 100, 100, 100, 100, 100, 100, 100]
    min_pop_sample_convergence_test = 10
    # start building shadow prices - only run work locations
    shadow_work = [2, 1, 1, 1]
    shadow_con = 30 #%RMSE for shadow pricing to consider being converged
    ###################################################################

 

else:

    create_no_toll_network = False

    min_pop_sample_convergence_test = 10
    
    if run_setup:
        if base_year == scenario_name:
            run_update_parking = False
        else:
            run_update_parking = True

        if base_year == '2010':
            run_convert_hhinc_2000_2010 = True
        else:
            run_convert_hhinc_2000_2010 = False

        run_accessibility_calcs = True
        run_accessibility_summary = True
        run_copy_daysim_code = True
        run_setup_emme_project_folders = True
        run_setup_emme_bank_folders = True
        run_copy_large_inputs = True
        run_landuse_summary = True
    else:
        run_update_parking = False
        run_convert_hhinc_2000_2010 = False
        run_accessibility_calcs = False
        run_accessibility_summary = False
        run_copy_daysim_code = False
        run_setup_emme_project_folders = False
        run_setup_emme_bank_folders = False
        run_copy_large_inputs = False
        run_landuse_summary = False

        
    if run_daysim:
        run_soundcast_summary = True
        run_daysim_report = True
        run_day_pattern_report = True
        run_mode_choice_report = True
        run_dest_choice_report = True
        run_long_term_report = True
        run_time_choice_report = True
        run_district_summary_report = False
    else:
        run_soundcast_summary = False
        run_daysim_report = False
        run_day_pattern_report = False
        run_mode_choice_report = False
        run_dest_choice_report = False
        run_long_term_report = False
        run_time_choice_report = False
        run_district_summary_report = False

    if should_build_shadow_price:
        shadow_work = [2, 1]
        shadow_con = 30 #%RMSE for shadow pricing to consider being converged
        feedback_iterations = feedback_iterations - 1 # when building shadow prices a final iteration happens automatically

    if start_with_seed_skims:
        run_copy_seed_skims = True
        run_skims_and_paths_seed_trips = False
    else:
        run_copy_seed_skims = False
        run_skims_and_paths_seed_trips = True
        run_import_networks = True
        run_truck_model = True
        run_supplemental_trips = True
        run_network_summary = True
        run_create_daily_bank = True

    if run_skims_and_paths:
            run_import_networks = True
            run_truck_model = True
            run_supplemental_trips = True
            run_network_summary = True
            run_create_daily_bank = True
    else:
            run_import_networks = False
            run_truck_model = False
            run_supplemental_trips = False
            run_network_summary = False
            run_create_daily_bank = False

    pop_sample = []
    max_iterations_list = []

    while feedback_iterations > 0:
        # feedback iterations remaining
        if feedback_iterations == 1:
            pop_sample.append(2)
            max_iterations_list. append(100)
        elif feedback_iterations == 2:
            pop_sample.append(5)
            max_iterations_list.append(100)
        else:
            pop_sample.append(20)
            max_iterations_list.append(10)

        feedback_iterations -=1 





###########################################################################################################################################################
# These files generally do not change and don't need to be toggled here usually
master_project = 'LoadTripTables'
parcel_decay_file = 'inputs/buffered_parcels.txt' #File with parcel data to be compared to
# run daysim and assignment in feedback until convergence

main_log_file = 'soundcast_log.txt'
network_summary_files = ['6to7_transit', '7to8_transit', '8to9_transit', '9to10_transit',
                         'counts_output', 'network_summary']
#This is what you get if the model runs cleanly, but it's random:
good_thing = ["cookie", "run", "puppy", "seal sighting",  "beer", "snack", "nap","venti cinnamon dolce latte"]

# These files are often missing from a run.  We want to check they are present and warn if not.
# Please add to this list as you find files that are missing.
commonly_missing_files = ['buffered_parcels.txt', 'tazdata.in']

# Calibration Summary Configuration
h5_results_file = 'outputs/daysim/daysim_outputs.h5'
h5_results_name = 'DaysimOutputs'
h5_comparison_file = 'scripts/summarize/inputs/calibration/survey.h5'
h5_comparison_name = 'Survey'
guidefile = 'scripts/summarize/inputs/calibration/CatVarDict.xlsx'
districtfile = 'scripts/summarize/inputs/calibration/TAZ_TAD_County.csv'
report_output_location = 'outputs/daysim'