import os

##############################
# Input paths and model years
##############################
model_year = '2018'
base_year = '2018'
landuse_inputs = 'vers2_july2020'
network_inputs = 'OSM_bike_test'
soundcast_inputs_dir = 'R:/e2projects_two/SoundCast/Inputs/dev'

##############################
# Initial Setup
##############################
run_accessibility_calcs = False
run_setup_emme_project_folders = False
run_setup_emme_bank_folders = False
run_copy_scenario_inputs = False
run_import_networks = False

##############################
# Model Procedures
##############################
run_skims_and_paths_free_flow = False
run_skims_and_paths = True
run_truck_model = False
run_supplemental_trips = False
run_daysim = False
run_summaries = False

##############################
# Modes and Path Types
##############################
include_av = False
include_tnc = True
tnc_av = False    # TNCs (if available) are AVs
include_tnc_to_transit = False # AV to transit path type allowed
include_knr_to_transit = False # Kiss and Ride to Transit
include_delivery = False

##############################
# Pricing
##############################
add_distance_pricing = False
distance_rate_dict = {'md': 8.5, 'ev': 8.5, 'am': 13.5, 'ni': 8.5, 'pm': 13.5}

##############################
# Other Controls
##############################
run_integrated = False
should_build_shadow_price = False
delete_banks = False