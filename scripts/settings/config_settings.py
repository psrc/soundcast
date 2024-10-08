from pydantic import BaseModel, validator
from typing import List, Optional
import typing
from pathlib import Path
import toml
import typing
import settings.run_args
class InputSettings(BaseModel):
    # toml input notes:
    # dictionary keys are always interpreted as strings
    # there’s no way to mark the end of a TOML table: all dictionaries/tables come after all other values

    ##############################
    # Input paths and model years
    ##############################
    model_year: str
    base_year: str
    landuse_inputs: str
    network_inputs: str
    db_name: str
    soundcast_inputs_dir: str
    use_activitysim: bool

    ##############################
    # Initial Setup
    ##############################
    run_accessibility_calcs: bool
    run_setup_emme_project_folders: bool
    run_setup_emme_bank_folders: bool
    run_copy_scenario_inputs: bool
    run_import_networks: bool

    ##############################
    # Model Procedures
    ##############################
    run_skims_and_paths_free_flow: bool
    run_skims_and_paths: bool
    run_truck_model: bool
    run_supplemental_trips: bool
    run_daysim: bool
    run_summaries: bool

    ##############################
    # Modes and Path Types
    ##############################
    include_av: bool
    include_tnc: bool
    tnc_av: bool    # T: boolNCs (if available) are AVs
    include_tnc_to_transit: bool # AV to transit path type allowed
    include_knr_to_transit: bool # Kiss and Ride to Transit
    include_delivery: bool
    include_telecommute: bool

    ##############################
    # Other Controls
    ##############################
    run_integrated: bool
    should_build_shadow_price: bool
    delete_banks: bool
    include_tnc_emissions: bool

    ##############################
    # Pricing
    ##############################
    add_distance_pricing: bool
    distance_rate_dict: dict

class EmmeSettings(BaseModel):
    log_file_name: str 
    STOP_THRESHOLD: float    # Global convergence criteria
    parallel_instances: int
    relative_gap: float      # Assignment Convergence Criteria
    best_relative_gap: float  # Set to zero, only using relative gap as criteria
    normalized_gap: float     # See above


    pop_sample: list
# Assignment Iterations must be same length as pop_sample:
    max_iterations_list: list
    min_pop_sample_convergence_test: int
    shadow_work: list
    shadow_con: int # %RMSE for shadow pricing to consider being converged

    ###################################
    # Zone Defintions
    ###################################
    MIN_EXTERNAL: int      #zone of externals (subtract 1 because numpy is zero-based)
    MAX_EXTERNAL: int      #zone of externals (subtract 1 because numpy is zero-based)
    HIGH_TAZ: int
    LOW_PNR: int
    #HIGH_PNR = 4000
    SEATAC: int
    EXTERNALS_DONT_GROW: list


    #################################
    # Supplementals Settings
    #################################

    trip_table_loc: str
    supplemental_project: str 
    supplemental_output_dir: str

    # Define gravity model coefficients
    autoop: float    # Auto operation costs (in hundreds of cents per mile?)
    avotda: float    # VOT

    # Home delivery trips, must be > 0
    total_delivery_trips: float

    #This is what you get if the model runs cleanly, but it's random:
    good_thing: list

    #################################
    # Integrated Run Settings
    #################################
    # Only required for integrated Urbans runs; leave as default for standard runs

    # Root dir for all Soundcast runs
    urbansim_skims_dir: str

    # Urbansim outputs dir
    urbansim_outputs_dir: str

class NetworkSettings(BaseModel):
    #####################################
    # Network Import Settings
    ####################################
    master_project: str
    network_summary_project: str
    transit_tod_list: list

    unit_of_length: str    # units of miles in Emme
    rdly_factor: float
    coord_unit_length: float    # network links measured in feet, converted to miles (1/5280)
    main_log_file: str

    link_extra_attributes: list
    node_extra_attributes: list
    transit_line_extra_attributes: list


    # VOT ranges for assignment classes
    vot_1_max: float    # VOT for User Class 1 < vot_1_max
    vot_2_max: float    # vot_1_max < VOT for User Class 2 < vot_2_max

    feedback_list: list


    # Time of day periods
    tods: list
    tod_networks: list
    #project_list = ['Projects/' + tod + '/' + tod + '.emp' for tod in tods]

    emme_matrix_subgroups: list
    # Skim for time, cost
    skim_matrix_designation_all_tods: list # Time (t) and direct cost (c) skims
    skim_matrix_designation_limited: list    # Distance skim

    # Skim for distance for only these time periods
    distance_skim_tod: list
    generalized_cost_tod: list

    truck_trips_h5_filename: str

    # Bike/Walk Skims
    bike_walk_skim_tod: list

    # Transit Inputs:
    transit_skim_tod: list
    transit_submodes: list

    # Transit Fare:
    zone_file: str
    fare_matrices_tod: list


    taz_area_file: str
    origin_tt_file: str
    destination_tt_file: str

    #################################
    # Bike Model Settings
    #################################
    # AADT segmentation breaks to apply volume penalties
    aadt_bins: list
    aadt_labels: list # Corresponding "bucket" labels for AADT segmentation for aadt_dict

    # Bin definition of total elevation gain (per link)
    slope_bins: list
    slope_labels: list

    #avg_bike_speed = 10 # miles per hour

    # Multiplier for storing skim results
    #bike_skim_mult = 100    # divide by 100 to store as int

    # Calibration factor for bike weights on ferry links
    ferry_bike_factor: float

    #################################
    # Truck Model Settings
    #################################

    truck_model_project: str
    districts_file: str
    truck_base_net_name: str

    # 4k time of day
    tod_list: list
    # External Magic Numbers
    LOW_STATION: int
    HIGH_STATION: int
    EXTERNAL_DISTRICT: str


    #####################################
    # Network Import Settings
    ####################################
    sound_cast_net_dict: dict

    extra_attributes_dict: dict
    

    # TNC fraction to assign
    # Based on survey data from SANDAG for now
    tnc_occupancy: dict
    


    gc_skims: dict
    transit_node_attributes: dict
    transit_tod: dict

    

    # Intrazonals
    intrazonal_dict: dict
    
    #################################
    # Bike Model Settings
    #################################

    # Distance perception penalties for link AADT from Broach et al., 2012
    # 1 is AADT 10k-20k, 2 is 20k-30k, 3 is 30k+
    # No penalty applied for AADT < 10k
    aadt_dict : dict

    # Crosswalk of bicycle facilities from geodatabase to a 2-tier typology - premium, standard (and none)
    # Associated with IJBikeFacility from modeAttributes table
    # "Premium" represents trails and fully separated bike facilities
    # "Standard" represents painted bike lanes only
    bike_facility_crosswalk: dict
    
    # Perception factor values corresponding to these tiers, from Broch et al., 2012
    facility_dict: dict
   

    # Perception factor values for 3-tiered measure of elevation gain per link
    slope_dict: dict
    
    #################################
    # Truck Model Settings
    #################################
    #TOD to create Bi-Dir skims (AM/EV Peak)
    truck_generalized_cost_tod: dict
    
    #GC & Distance skims that get read in from Soundcast

    truck_adjustment_factor: dict

class Settings(BaseModel):
    input_settings: InputSettings
    emme_settings: EmmeSettings
    network_settings: NetworkSettings
    configs_dir: typing.Any

def generate_settings(configs_dir):
    # set up configs/settings:
    if configs_dir is None:
        config = toml.load(Path.cwd()/'configuration/input_configuration.toml')
        emme_config = toml.load(Path.cwd()/'configuration/emme_configuration.toml')
        network_config = toml.load(Path.cwd()/'configuration/network_configuration.toml')
    else :
        configs_dir = Path(configs_dir)
        config = toml.load(configs_dir/'input_configuration.toml')
        emme_config = toml.load(configs_dir/'emme_configuration.toml')
        network_config = toml.load(configs_dir/'network_configuration.toml')

    input_settings = InputSettings(**config)
    emme_settings = EmmeSettings(**emme_config)
    network_settings = NetworkSettings(**network_config)
    
    return Settings(input_settings=input_settings,
                    emme_settings=emme_settings,
                    network_settings= network_settings,
                    configs_dir= configs_dir)

# def generate_settings():
#     # set up configs/settings:
#     configs_dir = run_args.args.configs_dir
#     if configs_dir is None:
#         config = toml.load(Path.cwd()/'configuration/input_configuration.toml')
#         emme_config = toml.load(Path.cwd()/'configuration/emme_configuration.toml')
#         network_config = toml.load(Path.cwd()/'configuration/network_configuration.toml')
#     else :
#         configs_dir = Path(configs_dir)
#         config = toml.load(configs_dir/'input_configuration.toml')
#         emme_config = toml.load(configs_dir/'emme_configuration.toml')
#         network_config = toml.load(configs_dir/'network_configuration.toml')

#     input_settings = InputSettings(**config)
#     emme_settings = EmmeSettings(**emme_config)
#     network_settings = NetworkSettings(**network_config)
    
#     return Settings(input_settings=input_settings,
#                     emme_settings=emme_settings,
#                     network_settings= network_settings,
#                     configs_dir= configs_dir)
    
# if __name__ == "__main__":
#     generate_settings()



    

