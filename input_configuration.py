import os

##############################
# Input paths and model years
##############################
model_year = '2018'
base_year = '2018'
landuse_inputs = 'lodes'
network_inputs = 'OSM'
soundcast_inputs_dir = 'R:/e2projects_two/SoundCast/Inputs/dev'

##############################
# Initial Setup
##############################
run_accessibility_calcs = True
run_setup_emme_project_folders = True
run_setup_emme_bank_folders = True
run_copy_scenario_inputs = True
run_import_networks = True

##############################
# Model Procedures
##############################
run_skims_and_paths_free_flow = True
run_skims_and_paths = True
run_truck_model = True
run_supplemental_trips = True
run_daysim = True
run_summaries = True

##############################
# Modes
##############################
include_av = False
include_tnc = False
tnc_av = False

##############################
# Pricing
##############################
add_distance_pricing = False
distance_rate_dict = {'md': 8.5, 'ev': 8.5, 'am': 13.5, 'ni': 8.5, 'pm': 13.5}
add_hot_lane_tolls = False
hot_rate_dict = {'md': 10.0, 'ev': 10.0, 'am': 35.0, 'ni': 10.0, 'pm': 35.0}

##############################
# Other Controls
##############################
create_daysim_zone_inputs = False
run_integrated = False
should_build_shadow_price = False
delete_banks = False