
# This is a simple configuration to do a run. If you need a more detailed configuration, set use_simple_configuration to False
# and manually change input_configuration_detail

use_simple_configuration = False

base_year = '2014'
scenario_name = '2014'
daysim_code = 'R:/SoundCast/daysim_2016' 
main_inputs_folder =  'R:/SoundCast/Inputs/'
master_project = 'LoadTripTables'
base_inputs = main_inputs_folder + base_year
scenario_inputs = main_inputs_folder + scenario_name

run_setup = False
run_daysim = False
# By not creating shadow prices, 3 hours of shadow price building are saved
should_build_shadow_price = False
run_skims_and_paths = False
# By starting with skims, if the network changes that are being made are small, 4 hours of assignment are saved.
start_with_seed_skims = False
feedback_iterations = 3
