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