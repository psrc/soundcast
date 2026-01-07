import inro.emme.desktop.app as app
import inro.emme.matrix as ematrix
import inro.emme.database.emmebank as _eb
import json
import numpy as np
import time
import os, sys
import h5py
import shutil
from multiprocessing import Pool
import traceback
import openmatrix as omx

sys.path.append(os.path.join(os.getcwd(), "scripts"))
sys.path.append(os.path.join(os.getcwd(), "inputs"))
sys.path.append(os.getcwd())

from scripts import emme_project
from scripts.emme_project import *
from skimming.tod_parameters import *
from skimming.user_classes import *
from settings.data_wrangling import text_to_dictionary, json_to_dictionary
from skimming import asim_park_and_ride
import logcontroller
from settings import run_args
from scripts.settings import state
from pathlib import Path

skims_logger = logcontroller.create_skims_and_paths_logger()
state = state.generate_state(run_args.args.configs_dir)

def create_hdf5_skim_container(hdf5_name):
    """Create HDF5/OMX container file for storing time-of-day specific skims.
    
    Args:
        hdf5_name (str): Name of the time period (e.g., '5to9', '18to20') to create container for
        
    Returns:
        str: Path to the created HDF5 filename
        
    Note:
        Creates different file structures based on ABM model type:
        - Daysim: .h5 files in roster directory
        - ActivitySim: .omx files in data directory
    """
    # create containers for TOD skims
    start_time = time.time()

    if state.input_settings.abm_model == "daysim":
        hdf5_filename = Path(f"{state.model_input_dir}/roster/{hdf5_name}.h5")
    elif state.input_settings.abm_model == "activitysim":
        hdf5_filename = os.path.join(run_args.args.data_dir, f"Skims_{hdf5_name}.omx")

    # Create a sub groups with the same name as the container, e.g. 5to6, 7to8
    # These facilitate multi-processing and will be imported to a master HDF5 file
    # at the end of the run

    if not os.path.exists(hdf5_filename):
        my_store = h5py.File(hdf5_filename, "w-")
        my_store.create_group(hdf5_name)
        my_store.close()

    end_time = time.time()
    text = f"Seconds required to create HDF5 file: {round((end_time - start_time), 2)}."
    skims_logger.info(text)

    return hdf5_filename


def vdf_initial(my_project):
    """Initialize Volume Delay Functions (VDFs) for the given project.
    
    Args:
        my_project: Emme project instance
        
    Note:
        Reads and processes VDF file specific to the project's time-of-day period.
        VDF files are located in the vdfs directory with naming convention vdfs{tod}.txt
    """

    # Point to input file for the VDF's and Read them in
    function_file = state.model_input_dir / f"vdfs/vdfs{my_project.tod}.txt"
    my_project.process_function_file(function_file)

def delete_matrices(my_project, matrix_type):
    """Delete all matrices of a specific type from the Emme project.
    
    Args:
        my_project: Emme project instance
        matrix_type (str): Type of matrices to delete (e.g., 'FULL', 'ORIGIN', 'DESTINATION')
    """
    for matrix in my_project.bank.matrices():
        if matrix.type == matrix_type:
            my_project.delete_matrix(matrix)


def define_matrices(my_project, user_classes, tod_parameters):
    """Create and load matrix data for the Emme project.
    
    Args:
        my_project: Emme project instance
        user_classes (dict): Dictionary containing user class definitions for different modes
        tod_parameters: Time-of-day specific parameters object
        
    Note:
        Creates matrices for:
        - Trip table matrices for each user class
        - Highway skims (time, distance, cost)
        - Generalized cost skims (if enabled for this time period)
        - Transit skims by mode (if transit is enabled)
        - Bike & walk skims (if enabled for this time period)
        - Transit fare matrices
        - Intrazonal matrices (distance, time for auto/bike/walk)
        - Zone area and terminal time matrices
    """
    start_define_matrices = time.time()
    # tod_parameters = tod_parameters_dict[my_project.tod]
    # Load in the necessary Dictionaries
    # matrix_dict = json_to_dictionary("user_classes")
    bike_walk_matrix_dict = json_to_dictionary(
        "bike_walk_matrix_dict", state.model_input_dir, "nonmotor"
    )

    # create trip table matrices
    for user_type in user_classes.keys():
        for user in user_classes[user_type].users:
            my_project.create_matrix(user.name, user.description, "FULL")
    if state.input_settings.abm_model == "activitysim":
        # Create park and ride demand matrices
        my_project.create_matrix("pnr_demand_access", "PNR Demand Access", "FULL")
        my_project.create_matrix("pnr_demand_egress", "PNR Demand Egress", "FULL")
    # create highway skims
    for skim_type in tod_parameters.skim_types:
        for user in user_classes["Highway"].users:
            my_project.create_matrix(user.name + skim_type, user.description, "FULL")

    # Create Generalized Cost Skims matrices for only for tod in generalized_cost_tod
    if tod_parameters.skim_generalized_cost:
        for key, value in state.network_settings.gc_skims.items():
            my_project.create_matrix(
                value + "g", "Generalized Cost Skim: " + key, "FULL"
            )

    # Create empty Transit Skim matrices in Emme only for tod in transit_skim_tod list
    # Actual In Vehicle Times by Mode
    if tod_parameters.run_transit:
        for item in state.network_settings.transit_submodes:
            my_project.create_matrix(
                "ivtwa" + item, "Actual IVTs by Mode: " + item, "FULL"
            )
            my_project.create_matrix(
                "ivtwr" + item,
                "Actual IVTs by Mode, Light Rail Assignment: " + item,
                "FULL",
            )
            my_project.create_matrix(
                "ivtwf" + item, "Actual IVTs by Mode, Ferry Assignment: " + item, "FULL"
            )
            my_project.create_matrix(
                "ivtwc" + item, "Actual IVTs by Mode, Commuter Rail: " + item, "FULL"
            )
            my_project.create_matrix(
                "ivtwp" + item,
                "Actual IVTs by Mode, Passenger Ferry Assignment: " + item,
                "FULL",
            )

        # Transit, All Modes:
        dct_aggregate_transit_skim_names = json_to_dictionary(
            "transit_skim_aggregate_matrix_names", state.model_input_dir, "transit"
        )

        for key, value in dct_aggregate_transit_skim_names.items():
            my_project.create_matrix(key, value, "FULL")

    # bike & walk, do not need for all time periods. most likely just 1:
    if tod_parameters.skim_bike_walk:
        for key in bike_walk_matrix_dict.keys():
            my_project.create_matrix(
                bike_walk_matrix_dict[key]["time"],
                bike_walk_matrix_dict[key]["description"],
                "FULL",
            )

    # transit fares, farebox & monthly matrices :
    fare_dict = json_to_dictionary(
        "transit_fare_dictionary", state.model_input_dir, "transit"
    )
    if my_project.tod in state.network_settings.fare_matrices_tod:
        for value in fare_dict[my_project.tod]["Names"].values():
            my_project.create_matrix(value, "transit fare", "FULL")

    # intrazonals:
    for key, value in state.network_settings.intrazonal_dict.items():
        my_project.create_matrix(value, key, "FULL")

    # Create matrices
    my_project.create_matrix("tazacr", "taz area", "ORIGIN")
    my_project.create_matrix("prodtt", "origin terminal times", "ORIGIN")
    my_project.create_matrix("attrtt", "destination terminal times", "DESTINATION")
    my_project.create_matrix("termti", "combined terminal times", "FULL")

    end_define_matrices = time.time()

    text = f"{round((end_define_matrices - start_define_matrices) / 60, 2)} minutes required to define all matrices in Emme."
    skims_logger.info(text)


def create_fare_zones(my_project, zone_file, fare_file):
    """Create fare zones and process fare zone partition and matrix transaction.
    
    Args:
        my_project: Emme project instance
        zone_file (str): Path to zone partition file
        fare_file (str): Path to fare matrix transaction file
    """
    my_project.initialize_zone_partition("gt")
    my_project.process_zone_partition(zone_file)
    my_project.matrix_transaction(
        os.path.join("inputs/scenario/networks/fares", fare_file)
    )


def populate_intrazonals(my_project):
    """Populate intrazonal distance and time matrices for auto, bike, and walk modes.
    
    Args:
        my_project: Emme project instance
        
    Note:
        Calculates intrazonal values based on zone area and assumed speeds:
        - Distance: sqrt(zone_area/640) * 45/60 (miles)
        - Auto time: distance * (60/15) - assumes 15 mph average speed
        - Bike time: distance * (60/10) - assumes 10 mph average speed  
        - Walk time: distance * (60/3) - assumes 3 mph average speed
        Also calculates combined terminal times matrix.
    """

    # Load matrix transaction files
    my_project.matrix_transaction(state.network_settings.taz_area_file)
    my_project.matrix_transaction(state.network_settings.origin_tt_file)
    my_project.matrix_transaction(state.network_settings.destination_tt_file)

    taz_area_matrix = my_project.bank.matrix("tazacr").id
    distance_matrix = my_project.bank.matrix(
        state.network_settings.intrazonal_dict["distance"]
    ).id

    for key, value in state.network_settings.intrazonal_dict.items():
        if key == "distance":
            my_project.matrix_calculator(
                result=value,
                expression="sqrt(" + taz_area_matrix + "/640) * 45/60*(p.eq.q)",
            )
        if key == "time auto":
            my_project.matrix_calculator(
                result=value, expression=distance_matrix + " *(60/15)"
            )  # 15 mph avg
        if key == "time bike":
            my_project.matrix_calculator(
                result=value, expression=distance_matrix + " *(60/10)"
            )  # 10 mph avg
        if key == "time walk":
            my_project.matrix_calculator(
                result=value, expression=distance_matrix + " *(60/3)"
            )  # 3 mph avg

    # calculate full matrix terminal times
    my_project.matrix_calculator(result="termti", expression="prodtt + attrtt")

    skims_logger.info("finished populating intrazonals")


def intitial_extra_attributes(my_project):
    """Create initial extra attributes for storing assignment results.
    
    Args:
        my_project: Emme project instance
        
    Note:
        Creates link extra attributes for:
        - Volume results for each user class (highway modes)
        - Transit vehicle volumes converted to auto equivalents (@trnv3)
    """

    # Load in the necessary Dictionaries
    matrix_dict = json_to_dictionary("user_classes", state.model_input_dir)

    # Create the link extra attributes to store volume results
    for x in range(0, len(matrix_dict["Highway"])):
        my_project.create_extra_attribute(
            "LINK",
            "@" + matrix_dict["Highway"][x]["Name"],
            matrix_dict["Highway"][x]["Description"],
            True,
        )

    # Create the link extra attributes to store the auto equivalent of bus vehicles
    my_project.create_extra_attribute("LINK", "@trnv3", "Transit Vehicles", True)


def calc_bus_pce(my_project):
    """Calculate passenger car equivalents (PCE) for transit vehicles.
    
    Args:
        my_project: Emme project instance
        
    Note:
        Calculates auto equivalent volumes for bus vehicles based on:
        - Number of hours in the time period 
        - Vehicle auto equivalency factor (vauteq)
        - Headway (hdw) to determine frequency
        Stores results in @trnv3 link attribute for use in traffic assignment.
    """
    total_hours = state.network_settings.transit_tod[my_project.tod]["num_of_hours"]
    my_expression = str(total_hours) + " * vauteq * (60/hdw)"
    my_project.transit_segment_calculator(
        result="@trnv3", expression=my_expression, aggregation="+"
    )


def traffic_assignment(my_project, max_num_iterations):
    """Perform path-based traffic assignment for highway network.
    
    Args:
        my_project: Emme project instance
        max_num_iterations (int): Maximum number of assignment iterations to run
        
    Note:
        - Uses path-based traffic assignment with Frank-Wolfe algorithm
        - Configures stopping criteria (relative gap, normalized gap)
        - Sets value of time perception factors for each user class
        - Handles warm start if previous assignment results exist
        - Assigns link volumes and calculates equilibrium flows
    """
    start_traffic_assignment = time.time()
    print("starting traffic assignment for" + my_project.tod)
    # Define the Emme Tools used in this function
    assign_extras = my_project.m.tool(
        "inro.emme.traffic_assignment.set_extra_function_parameters"
    )
    assign_traffic = my_project.m.tool(
        "inro.emme.traffic_assignment.path_based_traffic_assignment"
    )

    # Load in the necessary Dictionaries
    assignment_specification = json_to_dictionary(
        "path_based_assignment", state.model_input_dir, "auto"
    )
    my_user_classes = json_to_dictionary("user_classes", state.model_input_dir)

    # Modify the Assignment Specifications for the Closure Criteria and Perception Factors
    mod_assign = assignment_specification
    mod_assign["stopping_criteria"]["max_iterations"] = int(max_num_iterations)
    mod_assign["stopping_criteria"][
        "best_relative_gap"
    ] = state.emme_settings.best_relative_gap
    mod_assign["stopping_criteria"]["relative_gap"] = state.emme_settings.relative_gap
    mod_assign["stopping_criteria"][
        "normalized_gap"
    ] = state.emme_settings.normalized_gap

    for x in range(0, len(mod_assign["classes"])):
        vot = (1 / float(my_user_classes["Highway"][x]["Value of Time"])) * 60
        mod_assign["classes"][x]["generalized_cost"]["perception_factor"] = vot
        mod_assign["classes"][x]["generalized_cost"]["link_costs"] = my_user_classes[
            "Highway"
        ][x]["Toll"]
        mod_assign["classes"][x]["demand"] = (
            "mf" + my_user_classes["Highway"][x]["Name"]
        )
        mod_assign["classes"][x]["mode"] = my_user_classes["Highway"][x]["Mode"]

    assign_extras(el1="@rdly", el2="@trnv3")

    if my_project.current_scenario.has_traffic_results:
        assign_traffic(mod_assign, warm_start=True)
    else:
        assign_traffic(mod_assign, warm_start=False)

    end_traffic_assignment = time.time()

    text = f"{round((end_traffic_assignment - start_traffic_assignment) / 60, 2)} minutes required to run traffic assignment for {my_project.tod}"
    skims_logger.info(text)


def transit_assignment(my_project, spec, keep_exisiting_volumes, class_name=None):
    """Perform extended transit assignment for a specific mode or class.
    
    Args:
        my_project: Emme project instance
        spec (str): Path to assignment specification JSON file
        keep_exisiting_volumes (bool): Whether to add volumes to existing results
        class_name (str, optional): Transit class name for the assignment
        
    Note:
        - Configures waiting time and in-vehicle time perception factors
        - Uses headway fraction and node-specific attributes
        - Supports multiple transit submodes (bus, rail, ferry, etc.)
    """

    # Define the Emme Tools used in this function
    assign_transit = my_project.m.tool(
        "inro.emme.transit_assignment.extended_transit_assignment"
    )

    # Load in the necessary Dictionaries
    assignment_specification = json_to_dictionary(spec, state.model_input_dir)

    # modify constants for certain nodes:
    assignment_specification["waiting_time"][
        "headway_fraction"
    ] = state.network_settings.transit_node_attributes["headway_fraction"]["name"]
    assignment_specification["waiting_time"][
        "perception_factor"
    ] = state.network_settings.transit_node_attributes["wait_time_perception"]["name"]
    assignment_specification["in_vehicle_time"][
        "perception_factor"
    ] = state.network_settings.transit_node_attributes["in_vehicle_time"]["name"]

    assign_transit(
        assignment_specification,
        add_volumes=keep_exisiting_volumes,
        class_name=class_name,
    )
    if not class_name:
        class_name = ""


def transit_skims(my_project, spec, class_name=None):
    """Generate transit skims using extended transit assignment results.
    
    Args:
        my_project: Emme project instance
        spec (str): Path to skim specification JSON file
        class_name (str, optional): Transit class name for skims
        
    Note:
        Creates matrices for various transit impedance measures including:
        - In-vehicle time, wait time, walk time
        - Transfer penalties, fare costs
        - Access/egress times and distances
    """
    skim_transit = my_project.m.tool(
        "inro.emme.transit_assignment.extended.matrix_results"
    )
    # specs are stored in a dictionary where "spec1" is the key and a list of specs for each skim is the value
    skim_specs = json_to_dictionary(spec, state.model_input_dir)
    my_spec_list = skim_specs["spec1"]
    for item in my_spec_list:
        skim_transit(item, class_name=class_name)


def attribute_based_skims(my_project, my_skim_attribute):
    """Generate time or distance skims"""
    start_time_skim = time.time()

    skim_traffic = my_project.m.tool(
        "inro.emme.traffic_assignment.path_based_traffic_analysis"
    )

    # Load in the necessary Dictionaries
    skim_specification = json_to_dictionary(
        "attribute_based_skim", state.model_input_dir, "auto"
    )
    my_user_classes = json_to_dictionary("user_classes", state.model_input_dir)
    tod = my_project.tod

    # Figure out what skim matrices to use based on attribute (either time or length)
    if my_skim_attribute == "Time":
        my_attribute = "timau"
        my_extra = "@timau"
        skim_type = "Time Skims"
        skim_desig = "t"

        # Create the Extra Attribute
        my_project.create_extra_attribute(
            "LINK", my_extra, "copy of " + my_attribute, True
        )

        # Store timau (auto time on links) into an extra attribute so we can skim for it
        my_project.network_calculator(
            "link_calculation",
            result=my_extra,
            expression=my_attribute,
            selections_by_link="all",
        )

    if my_skim_attribute == "Distance":
        my_attribute = "length"
        my_extra = "@dist"
        skim_type = "Distance Skims"
        skim_desig = "d"

        my_project.create_extra_attribute(
            "LINK", my_extra, "copy of " + my_attribute, True
        )

        # Store Length (auto distance on links) into an extra attribute so we can skim for it
        my_project.network_calculator(
            "link_calculation",
            result=my_extra,
            expression=my_attribute,
            selections_by_link="all",
        )

    mod_skim = skim_specification

    for x in range(0, len(mod_skim["classes"])):
        matrix_name = my_user_classes["Highway"][x]["Name"]

        if matrix_name not in [
            "tnc_inc1",
            "tnc_inc2",
            "tnc_inc3",
        ]:  # TNC used HOV skims, no need to export
            my_extra = my_user_classes["Highway"][x][my_skim_attribute]
            matrix_name = matrix_name + skim_desig
            matrix_id = my_project.bank.matrix(matrix_name).id
            mod_skim["classes"][x]["analysis"]["results"]["od_values"] = matrix_id
            mod_skim["path_analysis"]["link_component"] = my_extra
            # only need generalized cost skims for trucks and only doing it when skimming for time.
            if tod in state.network_settings.generalized_cost_tod and skim_desig == "t":
                if (
                    my_user_classes["Highway"][x]["Name"]
                    in state.network_settings.gc_skims.values()
                ):
                    mod_skim["classes"][x]["results"]["od_travel_times"][
                        "shortest_paths"
                    ] = (my_user_classes["Highway"][x]["Name"] + "g")
            # otherwise, make sure we do not skim for GC!

    skim_traffic(mod_skim)

    # add in intrazonal values & terminal times:
    inzone_auto_time = my_project.bank.matrix(
        state.network_settings.intrazonal_dict["time auto"]
    ).id
    inzone_terminal_time = my_project.bank.matrix("termti").id
    inzone_distance = my_project.bank.matrix(
        state.network_settings.intrazonal_dict["distance"]
    ).id
    if my_skim_attribute == "Time":
        for x in range(0, len(mod_skim["classes"])):
            matrix_name = my_user_classes["Highway"][x]["Name"] + skim_desig
            matrix_id = my_project.bank.matrix(matrix_name).id
            my_project.matrix_calculator(
                result=matrix_id,
                expression=inzone_auto_time
                + "+"
                + inzone_terminal_time
                + "+"
                + matrix_id,
            )

    # only want to do this once!
    if (
        my_project.tod in state.network_settings.generalized_cost_tod
        and skim_desig == "t"
    ):
        for value in state.network_settings.gc_skims.values():
            matrix_name = value + "g"
            matrix_id = my_project.bank.matrix(matrix_name).id
            my_project.matrix_calculator(
                result=matrix_id,
                expression=inzone_auto_time
                + "+"
                + inzone_terminal_time
                + "+"
                + matrix_id,
            )

    if my_skim_attribute == "Distance":
        for x in range(0, len(mod_skim["classes"])):
            matrix_name = my_user_classes["Highway"][x]["Name"] + skim_desig
            matrix_id = my_project.bank.matrix(matrix_name).id
            my_project.matrix_calculator(
                result=matrix_id, expression=inzone_distance + "+" + matrix_id
            )

    # delete the temporary extra attributes
    my_project.delete_extra_attribute(my_extra)

    end_time_skim = time.time()

    text = f"Minutes required to calculate {skim_type}: {round((end_time_skim - start_time_skim) / 60, 2)}."
    skims_logger.info(text)


def attribute_based_toll_cost_skims(my_project, toll_attribute):
    """Calculate toll cost skims for specific occupancy classes.
    
    Args:
        my_project: Emme project instance
        toll_attribute (str): Toll attribute name (@toll1, @toll2, @toll3)
        
    Note:
        Generates cost skims only for user classes that match the specified
        toll attribute (SOV, HOV2, HOV3). Uses path-based traffic analysis
        to calculate shortest path costs through tolled facilities.
    """
    # Function to calculate true/toll cost skims. Should fold this into attribute_based_skims function.

    skim_traffic = my_project.m.tool(
        "inro.emme.traffic_assignment.path_based_traffic_analysis"
    )
    skim_specification = json_to_dictionary(
        "attribute_based_skim", state.model_input_dir, "auto"
    )
    my_user_classes = json_to_dictionary("user_classes", state.model_input_dir)

    # current_scenario = my_project.desktop.data_explorer().primary_scenario.core_scenario.ref
    my_bank = my_project.bank

    my_skim_attribute = "Toll"
    skim_desig = "c"

    # at this point, mod_skim is an empty spec ready to be populated with 21 classes. Here we are only populating the classes that
    # that have the appropriate occupancy(sv, hov2, hov3) to skim for the passed in toll_attribute (@toll1, @toll2, @toll3)
    # no need to create the extra attribute, already done in initial_extra_attributes
    mod_skim = skim_specification
    for x in range(0, len(mod_skim["classes"])):
        if my_user_classes["Highway"][x][my_skim_attribute] == toll_attribute:
            my_extra = my_user_classes["Highway"][x][my_skim_attribute]
            matrix_name = my_user_classes["Highway"][x]["Name"] + skim_desig
            matrix_id = my_bank.matrix(matrix_name).id
            mod_skim["classes"][x]["analysis"]["results"]["od_values"] = matrix_id
            mod_skim["path_analysis"]["link_component"] = my_extra
    skim_traffic(mod_skim)

def integerize_id_columns(df, table_name):
    """Convert ID columns to integer data type.
    
    Args:
        df (pandas.DataFrame): DataFrame containing ID columns
        table_name (str): Name of the table (used for error reporting)
        
    Note:
        Converts common ID columns (MAZ, OMAZ, DMAZ, TAZ, zone_id, household_id, HHID)
        to integer type. Prints null values if found before conversion.
    """
    columns = ['MAZ', 'OMAZ', 'DMAZ', 'TAZ', 'zone_id', 'household_id', 'HHID']
    for c in df.columns:
        if c in columns:
            # print(f"converting {table_name}.{c} to int")
            if df[c].isnull().any():
                print(df[c][df[c].isnull()])
            df[c] = df[c].astype(int)

def class_specific_volumes(my_project):
    """Calculate class-specific traffic volumes for each user class.
    
    Args:
        my_project: Emme project instance
        
    Note:
        Uses path-based traffic analysis to calculate link volumes
        for each highway user class (SOV, HOV2, HOV3, trucks, etc.).
        Results are stored in link extra attributes for analysis.
    """
    start_vol_skim = time.time()

    # Define the Emme Tools used in this function
    skim_traffic = my_project.m.tool(
        "inro.emme.traffic_assignment.path_based_traffic_analysis"
    )

    # Load in the necessary Dictionaries
    skim_specification = json_to_dictionary(
        "path_based_volume", state.model_input_dir, "auto"
    )
    my_user_classes = json_to_dictionary("user_classes", state.model_input_dir)

    mod_skim = skim_specification
    for x in range(0, len(mod_skim["classes"])):
        mod_skim["classes"][x]["results"]["link_volumes"] = (
            "@" + my_user_classes["Highway"][x]["Name"]
        )
    skim_traffic(mod_skim)

    end_vol_skim = time.time()

    text = f"Seconds required to calculate class specific volumes: {round((end_vol_skim - start_vol_skim), 2)}."
    skims_logger.info(text)


def emmeMatrix_to_numpyMatrix(
    matrix_name, emmebank, np_data_type, multiplier, max_value=None
):
    """Convert Emme matrix to NumPy matrix with data type conversion and scaling.
    
    Args:
        matrix_name (str): Name of the matrix in Emme
        emmebank: Emme bank object containing the matrix
        np_data_type (str): Target NumPy data type ('uint16', 'float32', etc.)
        multiplier (float): Scaling factor to apply to matrix values
        max_value (float, optional): Maximum value to cap the matrix at
        
    Returns:
        numpy.matrix: Converted and scaled matrix
        
    Note:
        - Applies multiplier for unit conversion or storage efficiency
        - Clips values to data type maximum to prevent overflow
        - Commonly used for converting time/distance skims to integer storage
    """
    matrix_id = emmebank.matrix(matrix_name).id
    emme_matrix = emmebank.matrix(matrix_id)
    matrix_data = emme_matrix.get_data()
    np_matrix = np.matrix(matrix_data.raw_data)
    np_matrix = np_matrix * multiplier

    if np_data_type == "uint16":
        max_value = np.iinfo(np_data_type).max
        np_matrix = np.where(np_matrix > max_value, max_value, np_matrix)

    if np_data_type != "float32":
        np_matrix = np.where(
            np_matrix > np.iinfo(np_data_type).max,
            np.iinfo(np_data_type).max,
            np_matrix,
        )

    return np_matrix


def average_matrices(old_matrix, new_matrix):
    """Average two matrices by taking their mean.
    
    Args:
        old_matrix (numpy.matrix): First matrix to average
        new_matrix (numpy.matrix): Second matrix to average
        
    Returns:
        numpy.matrix: Averaged matrix (mean of the two inputs)
        
    Note:
        Used in iterative assignment processes to average skims from
        multiple iterations for better convergence.
    """
    avg_matrix = old_matrix + new_matrix
    avg_matrix = avg_matrix * 0.5
    return avg_matrix

def fill_inf_with_max(matrix_data, dtype, fill_zero=True):
        
    # FIXME: Replace inf and nan values with max value for now, should only apply to park and ride
    max_value = np.nanmax(matrix_data[matrix_data != np.inf])
    matrix_data = np.nan_to_num(matrix_data, copy=True, posinf=max_value)

    # FIXME: Replace 0 values with max_value for now, should only apply to park and ride
    if fill_zero:
        matrix_data[matrix_data == 0] = max_value
    assert not np.isnan(np.min(matrix_data))
    assert True not in np.isinf(matrix_data)

    return matrix_data

def write_skims(state, matrix_data, h5_file, matrix_out_name, dtype, taz_indexes):
    """Write skim matrices to HDF5 format for activity-based models.
    
    Args:
        state: Configuration object containing model settings
        matrix_data: Numpy array containing skim matrix data
        h5_file: HDF5 file handle for skim storage
        matrix_out_name: Name for the matrix dataset in HDF5
        dtype: Data type for matrix storage (e.g., float32)
        taz_indexes: Zone indexing array for proper zone mapping
        
    Note:
        Handles format differences between DaySim and ActivitySim models.
        DaySim uses compressed HDF5 datasets, while ActivitySim uses
        DataFrames with proper zone indexing.
    """

    if state.input_settings.abm_model == "daysim":
        # Write skims to h5 format for Daysim with proper zone indexing
        h5_file["Skims"].create_dataset(
                        matrix_out_name, 
                        data=matrix_data.astype(dtype), 
                        compression="gzip"
                    )

    if state.input_settings.abm_model == "activitysim":
        # # Write full skims to h5 format (?) for supplemental trip modeling
        # h5_file["full"].create_dataset(
        #                 matrix_out_name, 
        #                 data=matrix_data.astype(dtype), 
        #                 compression="gzip"
        #             )

        # Write skims to OMX format for Activitysim with proper zone indexing
        # matrix_data = matrix_data[taz_indexes, :][:, taz_indexes]
        h5_file["data"].create_dataset(
                        matrix_out_name, 
                        data=matrix_data.astype(dtype), 
                        compression="gzip"
                    )

def average_skims_to_hdf5_concurrent(my_project, average_skims):
    start_export_hdf5 = time.time()
    bike_walk_matrix_dict = json_to_dictionary(
        "bike_walk_matrix_dict", state.model_input_dir, "nonmotor"
    )

    # Activitysim skims need time of day period appended to matrix name
    if state.input_settings.abm_model == "activitysim":
        tod_tag = f"__{state.network_settings.sound_cast_net_dict[my_project.tod]}"
        skim_dir_name = "data"
        dtype = "float32"    # always export as float
        scale_value = 1    # no scaling for factors used for activitysim
        cost_scale_value = 0.01   # cost inputs are in cents, convert to dollars for activitysim
    else:
        tod_tag = ""
        skim_dir_name = "Skims"
        dtype = "uint16"    # export as integer by default
        scale_value = 100   #  multiply values to store efficiently
        cost_scale_value = 1    # no scaling for cost values
    # Get TAZ indeces for Activitysim
    if state.input_settings.abm_model == "activitysim":
        taz = pd.read_csv(os.path.join(run_args.args.data_dir, "taz.csv")).sort_values('TAZ')
        integerize_id_columns(taz, 'taz')
        taz.index = taz.TAZ - 1
        taz_indexes = taz.index.tolist()  # index of TAZ in skim (zero-based, no mapping)
        taz_labels = taz.TAZ.tolist()  # TAZ zone_ids in omx index order
    else:
        taz_indexes = None

    # Create the HDF5 Container if needed and open it in read/write mode using "r+"
    hdf5_filename = create_hdf5_skim_container(my_project.tod)
    my_store = h5py.File(hdf5_filename, "r+")

    # if averaging, load old skims in dictionary of numpy matrices
    # Use full set of skims for averaging; results will trimmed and exported as needed
    if average_skims:
        np_old_matrices = {}
        for key in my_store[skim_dir_name].keys():
            np_matrix = my_store[skim_dir_name][key]
            np_matrix = np.matrix(np_matrix)
            np_old_matrices[str(key)] = np_matrix

    if skim_dir_name in my_store:
        del my_store[skim_dir_name]
        my_store.create_group(skim_dir_name)
    else:
        my_store.create_group(skim_dir_name)

    # Load in the necessary Dictionaries
    matrix_dict = json_to_dictionary("user_classes", state.model_input_dir)

    # First Store a Dataset containing the Indicices for the Array to Matrix using mf01
    if state.input_settings.abm_model != "activitysim":
        try:
            mat_id = my_project.bank.matrix("mf01")
            emme_matrix = my_project.bank.matrix(mat_id)
            em_val = emme_matrix.get_data()
            my_store[skim_dir_name].create_dataset(
                "indices", data=em_val.indices, compression="gzip"
            )

        except RuntimeError:
            del my_store[skim_dir_name]["indices"]
            my_store[skim_dir_name].create_dataset(
                "indices", data=em_val.indices, compression="gzip"
            )

    # Export park and ride skims
    if state.input_settings.abm_model == "activitysim":
        for matrix_name in asim_park_and_ride.matrix_dict.keys():
            matrix_out_name = matrix_name + tod_tag
            matrix_value = emmeMatrix_to_numpyMatrix(
                matrix_name, my_project.bank, dtype, 1, 99999
            )
            if state.input_settings.abm_model == "activitysim":
                matrix_value = fill_inf_with_max(matrix_value, dtype)

            # # Write numpy results back to Emme
            # matrix_id = my_project.bank.matrix(str(matrix_name)).id
            # # emme_matrix = emmebank.matrix(matrix_id)
            # # matrix_data = emme_matrix.get_data()
            # # np_matrix = np.matrix(matrix_data.raw_data)
            # full_zones = my_project.current_scenario.zone_numbers
            # emme_matrix = ematrix.MatrixData(indices=[full_zones, full_zones], type="f")
            # emme_matrix.from_numpy(matrix_value)
            # my_project.bank.matrix(matrix_id).set_data(
            #     emme_matrix, my_project.current_scenario
            # )

            # open old skim and average
            if average_skims:
                matrix_value = average_matrices(
                    np_old_matrices[matrix_out_name], matrix_value
                )
            
            write_skims(state, matrix_value, my_store, matrix_out_name, dtype, taz_indexes)

        # Export transfer wait time matrices as difference between total wait time and initial wait time
        for pnr_direction in ['DRV_TRN_WLK', 'WLK_TRN_DRV']:
            total_wait_value = emmeMatrix_to_numpyMatrix(
                f"{pnr_direction}_WAIT", my_project.bank, dtype, 1, 99999
            )
            initial_wait_value = emmeMatrix_to_numpyMatrix(
                f"{pnr_direction}_IWAIT", my_project.bank, dtype, 1, 99999
            )
            matrix_value = total_wait_value - initial_wait_value
            matrix_out_name = f"{pnr_direction}_XWAIT" + tod_tag

            # open old skim and average
            if average_skims:
                matrix_value = average_matrices(
                    np_old_matrices[matrix_out_name], matrix_value
                )

            if state.input_settings.abm_model == "activitysim":
                matrix_value = fill_inf_with_max(matrix_value, dtype)

            write_skims(state, matrix_value, my_store, matrix_out_name, dtype, taz_indexes)

        # Export fare matrix for park and ride trips (use the same one as for all transit trips)
        fare_dict = json_to_dictionary(
            "transit_fare_dictionary", state.model_input_dir, "transit"
        )
        
        matrix_name = "mf" + fare_dict[my_project.tod]["Names"]['fare_box_matrix']
        matrix_out_name = "WLK_TRN_DRV_FAR" + tod_tag
        matrix_value = emmeMatrix_to_numpyMatrix(
            matrix_name, my_project.bank, dtype, 1, 99999
        )

        # open old skim and average
        if average_skims:
            matrix_value = average_matrices(
                np_old_matrices[matrix_out_name], matrix_value
            )

        if state.input_settings.abm_model == "activitysim":
                matrix_value = fill_inf_with_max(matrix_value, dtype)

        write_skims(state, matrix_value, my_store, matrix_out_name, dtype, taz_indexes)

    # Loop through the Subgroups in the HDF5 Container
    # highway, walk, bike, transit
    # need to make sure we include Distance skims for TOD specified in distance_skim_tod
    if my_project.tod in state.network_settings.distance_skim_tod:
        my_skim_matrix_designation = (
            state.network_settings.skim_matrix_designation_limited
            + state.network_settings.skim_matrix_designation_all_tods
        )
    else:
        my_skim_matrix_designation = (
            state.network_settings.skim_matrix_designation_all_tods
        )

    for x in range(0, len(my_skim_matrix_designation)):
        for y in range(0, len(matrix_dict["Highway"])):
            matrix_name = matrix_dict["Highway"][y]["Name"]
            if matrix_name not in [
                "tnc_inc1",
                "tnc_inc2",
                "tnc_inc3",
            ]:  # TNC uses HOV skims, no need to export
                matrix_name = matrix_name + my_skim_matrix_designation[x]
                matrix_out_name = matrix_name + tod_tag
                
                if my_skim_matrix_designation[x] == "c":
                    matrix_value = emmeMatrix_to_numpyMatrix(
                        matrix_name, my_project.bank, dtype, cost_scale_value, 99999
                    )
                elif my_skim_matrix_designation[x] == "d":
                    matrix_value = emmeMatrix_to_numpyMatrix(
                        matrix_name, my_project.bank, dtype, scale_value, 2000
                    )
                else:
                    matrix_value = emmeMatrix_to_numpyMatrix(
                        matrix_name, my_project.bank, dtype, scale_value, 2000
                    )
                # open old skim and average
                if average_skims:
                    matrix_value = average_matrices(
                        np_old_matrices[matrix_out_name], matrix_value
                    )
                write_skims(state, matrix_value, my_store, matrix_out_name, dtype, taz_indexes)

    # Transit Skims
    if my_project.tod in state.network_settings.transit_skim_tod:
        # assignment path types - a: all, r: light rail, f: ferry, c: commuter rail, p: passenger ferry
        for path_mode in ["a", "r", "f", "c", "p"]:
            for item in state.network_settings.transit_submodes:
                matrix_name = "ivtw" + path_mode + item
                matrix_out_name = matrix_name + tod_tag
                matrix_value = emmeMatrix_to_numpyMatrix(
                    matrix_name, my_project.bank, dtype, scale_value
                )
                write_skims(state, matrix_value, my_store, matrix_out_name, dtype, taz_indexes)

        dct_aggregate_transit_skim_names = json_to_dictionary(
            "transit_skim_aggregate_matrix_names", state.model_input_dir, "transit"
        )

        for matrix_name, description in dct_aggregate_transit_skim_names.items():
            matrix_value = emmeMatrix_to_numpyMatrix(
                matrix_name, my_project.bank, dtype, scale_value
            )
            matrix_out_name = matrix_name + tod_tag
            write_skims(state, matrix_value, my_store, matrix_out_name, dtype, taz_indexes)

        # Perceived and actual bike skims
        for matrix_name in ["mfbkpt", "mfbkat"]:
            matrix_value = emmeMatrix_to_numpyMatrix(
                matrix_name, my_project.bank, dtype, scale_value
            )
            matrix_out_name = matrix_name + tod_tag
            # open old skim and average
            if average_skims:
                matrix_value = average_matrices(
                    np_old_matrices[matrix_out_name], matrix_value
                )
            write_skims(state, matrix_value, my_store, matrix_out_name, dtype, taz_indexes)

    # Basic Bike and walk time for single TOD
    if my_project.tod in state.network_settings.bike_walk_skim_tod:
        for key in bike_walk_matrix_dict.keys():
            matrix_name = bike_walk_matrix_dict[key]["time"]
            matrix_out_name = matrix_name + tod_tag
            matrix_value = emmeMatrix_to_numpyMatrix(
                matrix_name, my_project.bank, dtype, scale_value
            )
            # open old skim and average
            if average_skims:
                matrix_value = average_matrices(
                    np_old_matrices[matrix_out_name], matrix_value
                )
            write_skims(state, matrix_value, my_store, matrix_out_name, dtype, taz_indexes)

    # Distance, bike and walk skims for Activitysim for single time period
    if state.input_settings.abm_model == "activitysim":
        asim_export_tod = state.network_settings.bike_walk_skim_tod[0]
        if my_project.tod == asim_export_tod:
            # Need single distance skim for Activitysim
            matrix_value = emmeMatrix_to_numpyMatrix(
                "sov_inc2d", my_project.bank, "float32", scale_value, 2000
            )
            write_skims(state, matrix_value, my_store, "DIST", dtype, taz_indexes)

            walkt_matrix = emmeMatrix_to_numpyMatrix(
                "walkt", my_project.bank, dtype, scale_value
            ) 
            bikedist_matrix = walkt_matrix * (10.0 / 60.0)
            # open old skim and average
            if average_skims:
                bikedist_matrix = average_matrices(
                    np_old_matrices["DISTBIKE"], bikedist_matrix
                )
            write_skims(state, bikedist_matrix, my_store, "DISTBIKE", dtype, taz_indexes)

            walkdist_matrix = walkt_matrix * (3.0 / 60.0)
            # open old skim and average
            if average_skims:
                walkdist_matrix = average_matrices(
                    np_old_matrices["DISTWALK"], walkdist_matrix
                )
            write_skims(state, walkdist_matrix, my_store, "DISTWALK", dtype, taz_indexes)

    # Transit Fare
    fare_dict = json_to_dictionary(
        "transit_fare_dictionary", state.model_input_dir, "transit"
    )
    if my_project.tod in state.network_settings.fare_matrices_tod:
        for value in fare_dict[my_project.tod]["Names"].values():
            matrix_name = "mf" + value
            matrix_out_name = matrix_name + tod_tag
            if state.input_settings.abm_model == "activitysim" and value in ['mfarbx','afarbx']:
                matrix_out_name = "mfafarbx" + tod_tag
            matrix_value = emmeMatrix_to_numpyMatrix(
                matrix_name, my_project.bank, dtype, scale_value, 2000
            )
            # open old skim and average
            if average_skims:
                matrix_value = average_matrices(
                    np_old_matrices[matrix_out_name], matrix_value
                )

            write_skims(state, matrix_value, my_store, matrix_out_name, dtype, taz_indexes)

    if my_project.tod in state.network_settings.generalized_cost_tod:
        for value in state.network_settings.gc_skims.values():
            matrix_name = value + "g"
            matrix_out_name = matrix_name + tod_tag
            matrix_value = emmeMatrix_to_numpyMatrix(
                matrix_name, my_project.bank, dtype, 1, 2000
            )
            # open old skim and average
            if average_skims:
                matrix_value = average_matrices(
                    np_old_matrices[matrix_out_name], matrix_value
                )

            write_skims(state, matrix_value, my_store, matrix_out_name, dtype, taz_indexes)

    # Add zones indeces
    if "lookup" in my_store:
        del my_store["lookup"]
        my_store.create_group("lookup")
        # If not there, create the group
    else:
        my_store.create_group("lookup")

    if state.input_settings.abm_model == "activitysim":
        my_store["lookup"].create_dataset(
                    "ZONE", data=np.array(taz_labels).astype("uint32"), compression="gzip"
                )

    my_store.close()
    end_export_hdf5 = time.time()
    text = f"Minutes required to export skims to HDF5: {round((end_export_hdf5 - start_export_hdf5) / 60, 2)}."
    skims_logger.info(text)


def hdf5_trips_to_Emme(my_project, hdf_filename):
    """Load trip tables from HDF5 format into Emme databank.
    
    Args:
        my_project: Emme project instance
        hdf_filename: Path to HDF5 file containing trip data
        
    Note:
        Reads trip matrices from HDF5 format and loads them into
        Emme project for traffic assignment. Handles zone indexing
        and matrix format conversion between ActivitySim and Emme.
    """
    start_time = time.time()

    # Determine the Path and Scenario File and Zone indicies that go with it
    zonesDim = len(my_project.current_scenario.zone_numbers)
    zones = my_project.current_scenario.zone_numbers

    # load zones into a NumpyArray to index trips otaz and dtaz

    # Create a dictionary lookup where key is the taz id and value is it's numpy index.
    dictZoneLookup = dict((value, index) for index, value in enumerate(zones))
    # create an index of trips for this TOD. This prevents iterating over the entire array (all trips).
    tod_index = create_trip_tod_indices(my_project.tod)

    # Create the HDF5 Container if needed and open it in read/write mode using "r+"
    my_store = h5py.File(hdf_filename, "r")

    # Read the Matrix File from the Dictionary File and Set Unique Matrix Names
    matrix_dict = text_to_dictionary(
        "demand_matrix_dictionary",
        state.model_input_dir,
    )
    uniqueMatrices = set(matrix_dict.values())

    # Stores in the HDF5 Container to read or write to
    daysim_set = my_store["Trip"]

    # Store arrays from Daysim/Trips Group into numpy arrays, indexed by TOD.
    # This means that only trip info for the current Time Period will be included in each array.
    otaz = np.asarray(daysim_set["otaz"])
    otaz = otaz.astype("int")
    otaz = otaz[tod_index]

    dtaz = np.asarray(daysim_set["dtaz"])
    dtaz = dtaz.astype("int")
    dtaz = dtaz[tod_index]

    mode = np.asarray(daysim_set["mode"])
    mode = mode.astype("int")
    mode = mode[tod_index]

    trexpfac = np.asarray(daysim_set["trexpfac"])
    trexpfac = trexpfac[tod_index]

    vot = np.asarray(daysim_set["vot"])
    vot = vot[tod_index]

    deptm = np.asarray(daysim_set["deptm"])
    deptm = deptm[tod_index]

    dorp = np.asarray(daysim_set["dorp"])
    dorp = dorp.astype("int")
    dorp = dorp[tod_index]

    pathtype = np.asarray(daysim_set["pathtype"])
    pathtype = pathtype.astype("int")
    pathtype = pathtype[tod_index]

    my_store.close

    # create & store in-memory numpy matrices in a dictionary. Key is matrix name, value is the matrix
    demand_matrices = {}

    for matrix_name in ["medium_truck", "heavy_truck", "delivery_truck"]:
        demand_matrix = load_trucks(my_project, matrix_name, zonesDim)
        demand_matrices.update({matrix_name: demand_matrix})

    # Load in supplemental trips
    # We're assuming all trips are only for income 2, toll classes
    for matrix_name in [
        "sov_inc2",
        "hov2_inc2",
        "hov3_inc2",
        "bike",
        "walk",
        "trnst",
        "litrat",
        "passenger_ferry",
        "ferry",
        "commuter_rail",
    ]:
        demand_matrix = load_supplemental_trips(my_project, matrix_name, zonesDim)
        demand_matrices.update({matrix_name: demand_matrix})

    # Create empty demand matrices for other modes without supplemental trips
    for matrix in list(uniqueMatrices):
        if matrix not in demand_matrices.keys():
            demand_matrix = np.zeros((zonesDim, zonesDim), np.float16)
            demand_matrices.update({matrix: demand_matrix})

    # Start going through each trip & assign it to the correct Matrix. Using Otaz, but array length should be same for all
    # The correct matrix is determined using a tuple that consists of (mode, VOT class, AV/standard). This tuple is the key in matrix_dict.

    for x in range(0, len(otaz)):
        # Start building the tuple key, 3 VOT of categories...

        if vot[x] < state.network_settings.vot_1_max:
            vot[x] = 1
        elif vot[x] < state.network_settings.vot_2_max:
            vot[x] = 2
        else:
            vot[x] = 3

        # Get matrix name from matrix_dict. Do not assign school bus trips (8) to the network.
        if mode[x] != 8 and mode[x] > 0:
            # Only want driver trips assigned to network, and non auto modes
            auto_mode_ids = [3, 4, 5]  # SOV, HOV2, HOV3
            non_auto_mode_ids = [1, 2, 6]  # walk, bike, transit

            # Determine if trip is AV or conventional vehicle
            av_flag = 0  # conventional vehicle by default
            if mode[x] in auto_mode_ids:
                if dorp[x] == 3 and state.input_settings.include_av:
                    av_flag = 1

            # Light Rail Trips:
            if mode[x] == 6 and pathtype[x] == 4:
                av_flag = 4

            # Passenger-Only Ferrry Trips:
            if mode[x] == 6 and pathtype[x] == 5:
                av_flag = 5

            # Commuter Rail:
            if mode[x] == 6 and pathtype[x] == 6:
                av_flag = 6

            # Ferry Trips
            if mode[x] == 6 and pathtype[x] in [7, 12]:
                av_flag = 7

            # Retrieve trip information from Daysim records
            mat_name = matrix_dict[(int(mode[x]), int(vot[x]), av_flag)]
            myOtaz = dictZoneLookup[otaz[x]]
            myDtaz = dictZoneLookup[dtaz[x]]
            trips = np.float32(trexpfac[x]).item()
            trips = round(trips, 2)

            # Assign TNC trips using fractional occupancy (factor of 1 for 1 passenger, 0.5 for 2 passengers, etc.)
            if (mode[x] == 9) and (
                dorp[x] in {int(k) for k in state.network_settings.tnc_occupancy.keys()}
            ):
                trips = trips * state.network_settings.tnc_occupancy[str(dorp[x])]
                demand_matrices[mat_name][myOtaz, myDtaz] = (
                    demand_matrices[mat_name][myOtaz, myDtaz] + trips
                )

            # Use "dorp" field to select driver trips only; for non-auto trips, add all trips for assignment
            # dorp==3 for primary trips in AVs, include these along with driver trips (dorp==1)
            elif (dorp[x] <= 1 or dorp[x] == 3) or (mode[x] in non_auto_mode_ids):
                demand_matrices[mat_name][myOtaz, myDtaz] = (
                    demand_matrices[mat_name][myOtaz, myDtaz] + trips
                )

    # all in-memory numpy matrices populated, now write out to emme
    for mat_name in uniqueMatrices:
        matrix_id = my_project.bank.matrix(str(mat_name)).id
        np_array = demand_matrices[mat_name]
        emme_matrix = ematrix.MatrixData(indices=[zones, zones], type="f")
        emme_matrix.from_numpy(np_array)
        my_project.bank.matrix(matrix_id).set_data(
            emme_matrix, my_project.current_scenario
        )

    end_time = time.time()

    text = f"It took {round((end_time - start_time) / 60, 2)} minutes to import trip tables to emme."
    skims_logger.info(text)


def load_trucks(my_project, matrix_name, zonesDim):
    """Load truck trip tables and apply time-of-day factors.
    
    Args:
        my_project: Emme project instance
        matrix_name: Name of truck matrix type (medium_truck, heavy_truck, delivery_truck)
        zonesDim: Number of transportation analysis zones
        
    Returns:
        np.array: Truck trip matrix for the specified time period
        
    Note:
        Applies time-of-day factors to convert aggregate daily truck trips
        to specific time periods used in Soundcast. Reads from HDF5 truck
        trip files and scales by appropriate temporal factors.
    """

    demand_matrix = np.zeros((zonesDim, zonesDim), np.float16)
    hdf_file = h5py.File(state.network_settings.truck_trips_h5_filename, "r")
    tod = my_project.tod

    truck_matrix_name_dict = {
        "medium_truck": "medtrk_trips",
        "heavy_truck": "hvytrk_trips",
        "delivery_truck": "deltrk_trips",
    }

    truck_demand_matrix_name = (
        f"mf{tod}_{truck_matrix_name_dict[matrix_name]}"
    )

    np_matrix = np.matrix(
        hdf_file[tod][truck_demand_matrix_name]
    ).astype(float)

    # Apply time of day factor to convert from aggregate time periods to 12 soundcast periods
    demand_matrix = np_matrix[0:zonesDim, 0:zonesDim]
    demand_matrix = np.squeeze(np.asarray(demand_matrix))

    return demand_matrix


def load_supplemental_trips(my_project, matrix_name, zonesDim, datatype=np.float16):
    """Load externals, special generator, and group quarters trips from supplemental trip model.
    
    Args:
        my_project: Emme project instance
        matrix_name: Name of trip matrix type to load
        zonesDim: Number of transportation analysis zones
        datatype: Numpy data type for matrix storage (default: np.float16)
        
    Returns:
        np.array: Supplemental trip matrix for the specified time period
        
    Note:
        Supplemental trips include externals, special generators, and group quarters.
        These trips are assumed only on Income Class 2, so only these modes are modified.
        Reads from time-of-day specific HDF5 files in supplemental output directory.
    """

    tod = my_project.tod
    # Create empty array to fill with trips
    demand_matrix = np.zeros((zonesDim, zonesDim), np.float16)
    hdf_file = h5py.File(
        os.path.join(state.emme_settings.supplemental_output_dir, tod + ".h5"), "r"
    )

    # Open mode-specific array for this TOD and mode
    hdf_array = hdf_file[matrix_name]

    # Extract specified array size and store as NumPy array
    sub_demand_matrix = hdf_array[0:zonesDim, 0:zonesDim]
    sub_demand_array = np.asarray(sub_demand_matrix)
    demand_matrix[
        0 : len(sub_demand_array), 0 : len(sub_demand_array)
    ] = sub_demand_array

    return demand_matrix


def create_trip_tod_indices(tod):
    # Create an index for trips that belong to TOD (time of day)
    tod_dict = text_to_dictionary("time_of_day", state.model_input_dir, "lookup")
    uniqueTOD = set(tod_dict.values())
    todIDListdict = {}

    # Create a dictionary where the TOD string, e.g. 18to20, is the key, and the value is a list of the hours for that period, e.g [18, 19, 20]
    for k, v in tod_dict.items():
        todIDListdict.setdefault(v, []).append(k)

    # For the given TOD, get the index of all the trips for that Time Period
    my_store = h5py.File("outputs/daysim/daysim_outputs.h5", "r")
    daysim_set = my_store["Trip"]
    # open departure time array
    deptm = np.asarray(daysim_set["deptm"])
    # convert to hours
    deptm = deptm.astype("float")
    deptm = deptm / 60
    deptm = deptm.astype("int")

    # Get the list of hours for this tod
    todValues = todIDListdict[tod]
    # ix is an array of true/false
    ix = np.in1d(deptm.ravel(), todValues)
    # An index for trips from this tod, e.g. [3, 5, 7) means that there are trips from this time period from the index 3, 5, 7 (0 based) in deptm
    indexArray = np.where(ix)
    my_store.close

    return indexArray


def matrix_controlled_rounding(my_project):
    matrix_dict = text_to_dictionary("demand_matrix_dictionary", state.model_input_dir)
    uniqueMatrices = set(matrix_dict.values())

    for matrix_name in uniqueMatrices:
        matrix_id = my_project.bank.matrix(matrix_name).id
        result = my_project.matrix_calculator(
            result=None,
            aggregation_destinations="+",
            aggregation_origins="+",
            expression=matrix_name,
        )
        if result["maximum"] > 0:
            controlled_rounding = my_project.m.tool(
                "inro.emme.matrix_calculation.matrix_controlled_rounding"
            )
            controlled_rounding(
                demand_to_round=matrix_id,
                rounded_demand=matrix_id,
                min_demand=0.1,
                values_to_round="SMALLER_THAN_MIN",
            )
    text = "finished matrix controlled rounding"
    skims_logger.info(text)


def start_pool(project_list, free_flow_skims, max_iterations):
    # An Emme databank can only be used by one process at a time. Emme Modeler API only allows one instance of Modeler and
    # it cannot be destroyed/recreated in same script. In order to run things con-currently in the same script, must have
    # seperate projects/banks for each time period and have a pool for each project/bank.
    # Fewer pools than projects/banks will cause script to crash.
    pool = Pool(processes=state.emme_settings.parallel_instances)
    params = []
    for item in project_list:
        params.append((item, free_flow_skims, max_iterations))
    pool_list = pool.starmap(run_assignments_parallel_wrapped, params)
    pool.close()

    return pool_list


def init_bike_pool(daily_link_df):
    global global_daily_link_df
    global_daily_link_df = daily_link_df


def start_transit_pool(project_list):
    pool = Pool(len(project_list))
    params = []
    for item in project_list:
        params.append([item])
    pool.starmap(run_transit_wrapped, params)
    pool.close()


def start_bike_pool(project_list, daily_link_df):
    pool = Pool(12, init_bike_pool, [daily_link_df])
    params = []
    for item in project_list:
        params.append([item])
    pool.starmap(run_bike_wrapped, params)
    pool.close()


def run_transit_wrapped(project_name):
    try:
        run_transit(project_name)
    except:
        print("{}: {}".format(project_name, traceback.format_exc()))


def run_bike_wrapped(project_name):
    try:
        run_bike(project_name)
    except:
        print("{}: {}".format(project_name, traceback.format_exc()))


def run_bike(project_name):
    start_of_run = time.time()
    my_project = EmmeProject(project_name, state.model_input_dir)

    # Bicycle Assignment
    calc_bike_weight(my_project, global_daily_link_df)
    tod = project_name.split("/")[1]
    bike_assignment(my_project, tod)

    my_project.bank.dispose()


def run_bike_test(project_name, daily_link_df):
    start_of_run = time.time()
    my_project = EmmeProject(project_name, state.model_input_dir)

    # Bicycle Assignment
    calc_bike_weight(my_project, daily_link_df)
    tod = project_name.split("/")[1]
    bike_assignment(my_project, tod)

    my_project.bank.dispose()


def run_transit(project_name):
    start_of_run = time.time()

    my_project = EmmeProject(project_name, state.model_input_dir)

    # Assign transit submodes, adding volumes to existing after first submode:
    counter = 0
    for submode, class_name in {
        "bus": "trnst",
        "light_rail": "litrat",
        "ferry": "ferry",
        "passenger_ferry": "passenger_ferry",
        "commuter_rail": "commuter_rail",
    }.items():
        if counter > 0:
            add_volumes = True
        else:
            add_volumes = False
        transit_assignment(
            my_project,
            "transit/extended_transit_assignment_" + submode,
            keep_exisiting_volumes=add_volumes,
            class_name=class_name,
        )
        transit_skims(my_project, "transit/transit_skim_setup_" + submode, class_name)
        counter += 1

    # Calculate wait times
    app.App.refresh_data
    matrix_calculator = json_to_dictionary(
        "matrix_calculation", state.model_input_dir, "templates"
    )
    matrix_calc = my_project.m.tool("inro.emme.matrix_calculation.matrix_calculator")

    # Wait times for general transit
    total_wait_matrix = my_project.bank.matrix("twtwa").id
    initial_wait_matrix = my_project.bank.matrix("iwtwa").id
    transfer_wait_matrix = my_project.bank.matrix("xfrwa").id
    mod_calc = matrix_calculator
    mod_calc["result"] = transfer_wait_matrix
    mod_calc["expression"] = total_wait_matrix + "-" + initial_wait_matrix
    matrix_calc(mod_calc)

    # Wait times for transit submodes
    for submode in ["r", "f", "p", "c"]:
        total_wait_matrix = my_project.bank.matrix("twtw" + submode).id
        initial_wait_matrix = my_project.bank.matrix("iwtw" + submode).id
        transfer_wait_matrix = my_project.bank.matrix("xfrw" + submode).id

        mod_calc = matrix_calculator
        mod_calc["result"] = transfer_wait_matrix
        mod_calc["expression"] = total_wait_matrix + "-" + initial_wait_matrix
        matrix_calc(mod_calc)

    my_project.bank.dispose()


def export_to_hdf5_pool(project_list, free_flow_skims):
    params = []
    for item in project_list:
        params.append((item, free_flow_skims))
    # pool_list = pool.starmap(run_assignments_parallel_wrapped, params)

    pool = Pool(processes=state.emme_settings.parallel_instances)
    pool.starmap(start_export_to_hdf5, params)
    pool.close()


def start_export_to_hdf5(test, free_flow_skims):
    my_project = EmmeProject(test, state.model_input_dir)
    # do not average skims if using seed_trips because we are starting the first iteration
    if free_flow_skims:
        average_skims_to_hdf5_concurrent(my_project, False)
    else:
        average_skims_to_hdf5_concurrent(my_project, True)


def bike_walk_assignment(my_project, assign_for_all_tods):
    # One bank
    # this runs the assignment and produces a time skim as well, is all we need- converted
    # to distance in Daysim.
    # Assignment is run for all time periods (at least it should be for the final iteration). Only need to
    # skim for one TOD. Skim is an optional output of the assignment.

    start_transit_assignment = time.time()
    my_bank = my_project.bank
    # Define the Emme Tools used in this function
    assign_transit = my_project.m.tool(
        "inro.emme.transit_assignment.standard_transit_assignment"
    )

    # Load in the necessary Dictionaries
    assignment_specification = json_to_dictionary(
        "bike_walk_assignment", state.model_input_dir, "nonmotor"
    )
    # get demand matrix name from user_classes:
    user_classes = json_to_dictionary("user_classes", state.model_input_dir)
    bike_walk_matrix_dict = json_to_dictionary(
        "bike_walk_matrix_dict", state.model_input_dir, "nonmotor"
    )
    mod_assign = assignment_specification
    # Only skim for time for certain TODs
    # Also fill in intrazonals

    # intrazonal_dict
    if my_project.tod in state.network_settings.bike_walk_skim_tod:
        for key in bike_walk_matrix_dict.keys():
            # modify spec
            mod_assign["demand"] = "mf" + bike_walk_matrix_dict[key]["demand"]
            mod_assign["od_results"]["transit_times"] = bike_walk_matrix_dict[key][
                "time"
            ]
            mod_assign["modes"] = bike_walk_matrix_dict[key]["modes"]
            assign_transit(mod_assign)

            # intrazonal
            matrix_name = bike_walk_matrix_dict[key]["intrazonal_time"]
            matrix_id = my_bank.matrix(matrix_name).id
            my_project.matrix_calculator(
                result="mf" + bike_walk_matrix_dict[key]["time"],
                expression="mf" + bike_walk_matrix_dict[key]["time"] + "+" + matrix_id,
            )

    elif assign_for_all_tods == "true":
        # Dont Skim
        for key in bike_walk_matrix_dict.keys():
            mod_assign["demand"] = bike_walk_matrix_dict[key]["demand"]
            mod_assign["modes"] = bike_walk_matrix_dict[key]["modes"]
            assign_transit(mod_assign)

    end_transit_assignment = time.time()
    text = f"It took {round((end_transit_assignment - start_transit_assignment) / 60, 2)} minutes to run the bike/walk assignment."
    skims_logger.info(text)


def feedback_check(emmebank_path_list, emme_settings):
    matrix_dict = json_to_dictionary("user_classes", state.model_input_dir)
    passed = True
    for emmebank_path in emmebank_path_list:
        my_bank = _eb.Emmebank(emmebank_path)
        tod = my_bank.title
        # my_store = h5py.File(f"{state.model_input_dir}/roster/{tod}.h5", "r+")
        if state.input_settings.abm_model == "daysim":
            my_store = h5py.File(Path(f"{state.model_input_dir}/roster/{tod}.h5"), "r+")
            skim_group = "Skims"
            multiplier = 100
        elif state.input_settings.abm_model == "activitysim":
            my_store = h5py.File(os.path.join(run_args.args.data_dir, f"Skims_{tod}.omx"), "r+")
            skim_group = "data"
            multiplier = 1
        # put current time skims in numpy:

        for y in range(0, len(matrix_dict["Highway"])):
            # trips
            matrix_name = matrix_dict["Highway"][y]["Name"]
            if matrix_name not in ["tnc_inc1", "tnc_inc2", "tnc_inc3"]:
                matrix_value = emmeMatrix_to_numpyMatrix(
                    matrix_name, my_bank, "float32", 1
                )

                trips = np.where(
                    matrix_value > np.iinfo("uint16").max,
                    np.iinfo("uint16").max,
                    matrix_value,
                )

                # new skims
                matrix_name = matrix_name + "t"
                # if state.input_settings.abm_model == "activitysim":
                #     matrix_name = matrix_name + f"__{state.network_settings.sound_cast_net_dict[tod]}"
                matrix_value = emmeMatrix_to_numpyMatrix(
                    matrix_name, my_bank, "float32", multiplier
                )
                new_skim = np.where(
                    matrix_value > np.iinfo("uint16").max,
                    np.iinfo("uint16").max,
                    matrix_value,
                )

                # now old skims
                h5_skim_name = matrix_name
                if state.input_settings.abm_model == "activitysim":
                    h5_skim_name = matrix_name + f"__{state.network_settings.sound_cast_net_dict[tod]}"
                old_skim = np.asmatrix(my_store[skim_group][h5_skim_name])

                change_test = np.sum(
                    np.multiply(np.absolute(new_skim - old_skim), trips)
                ) / np.sum(np.multiply(old_skim, trips))

                text = f"{tod} {change_test} {matrix_name}"
                skims_logger.info(text)
                if change_test > emme_settings.STOP_THRESHOLD:
                    passed = False
                    break

        my_bank.dispose()
    return passed


def get_link_attribute(attr, network):
    """Return dataframe of link attribute and link ID"""
    link_dict = {}
    for i in network.links():
        link_dict[i.id] = i[attr]
    df = pd.DataFrame({"link_id": link_dict.keys(), attr: link_dict.values()})

    return df


def bike_facility_weight(my_project, link_df, network_settings):
    """Compute perceived travel distance impacts from bike facilities
    In the geodatabase, bike facility of 2=bicycle track and 8=separated path
    These are redefined as "premium" facilities
    Striped bike lanes receive a 2nd tier designatinon of "standard"
    All other links remain unchanged"""

    network = my_project.current_scenario.get_network()

    # Load the extra attribute data for bike facility type
    # and replace geodb typology with the 2-tier definition
    df = get_link_attribute("@bkfac", network)
    df = df.merge(link_df)
    df["@bkfac"] = df["@bkfac"].astype(int)
    df["@bkfac"] = df["@bkfac"].astype(str)
    df = df.replace(network_settings.bike_facility_crosswalk)

    # Replace the facility ID with the estimated  marginal rate of substituion
    # value from Broach et al., 2012 (e.g., replace 'standard' with -0.108)
    df["facility_wt"] = df["@bkfac"].copy()
    with pd.option_context("future.no_silent_downcasting", True):
        df = df.replace(network_settings.facility_dict)
    df["facility_wt"] = df["facility_wt"].astype(float)

    return df


def volume_weight(my_project, df, network_settings):
    """For all links without bike lanes, apply a factor for the adjacent traffic (AADT)."""

    # Separate auto volume into bins
    df["volume_wt"] = pd.cut(
        df["@tveh"],
        bins=network_settings.aadt_bins,
        labels=network_settings.aadt_labels,
        right=False,
    )
    df["volume_wt"] = df["volume_wt"].astype("int")

    # Replace bin label with weight value, only for links with no bike facilities
    over_df = df[df["facility_wt"] < 0].replace(to_replace=network_settings.aadt_dict)
    over_df["volume_wt"] = 0
    under_df = df[df["facility_wt"] >= 0]
    df = pd.concat([over_df, under_df])

    return df

def process_slope_weight(network_settings, df, my_project):
    """Calcualte slope weights on an Emme network dataframe
    and merge with a bike attribute dataframe to get total perceived
    biking distance from upslope, facilities, and traffic volume"""

    network = my_project.current_scenario.get_network()

    # load in the slope term from the Emme network
    upslope_df = get_link_attribute("@upslp", network)

    # Join slope df with the length df
    upslope_df = upslope_df.merge(df)

    # Separate the slope into bins with the penalties as indicator values
    upslope_df["slope_wt"] = pd.cut(
        upslope_df["@upslp"],
        bins=network_settings.slope_bins,
        labels=network_settings.slope_labels,
        right=False,
    )
    # upslope_df['slope_wt'] = upslope_df['slope_wt'].astype('float')
    upslope_df["slope_wt"] = upslope_df["slope_wt"].astype("str")
    upslope_df = upslope_df.replace(to_replace=network_settings.slope_dict)

    return upslope_df


def write_generalized_time(df, tod):
    """Export normalized link biking weights as Emme attribute file."""

    # Rename total weight column for import as Emme attribute
    df["@bkwt"] = df["total_wt"]

    # Reformat and save as a text file in Emme format
    df["inode"] = df["link_id"].str.split("-").str[0]
    df["jnode"] = df["link_id"].str.split("-").str[1]

    filename = "working/bike_link_weights_%s.csv" % (tod,)
    df[["inode", "jnode", "@bkwt"]].to_csv(filename, sep=" ", index=False)


def calc_bike_weight(my_project, link_df):
    """Calculate perceived travel time weight for bikes
    based on facility attributes, slope, and vehicle traffic."""

    try:
        # Calculate weight of bike facilities
        bike_fac_df = bike_facility_weight(my_project, link_df, state.network_settings)

        # Calculate weight from daily traffic volumes
        vol_df = volume_weight(my_project, bike_fac_df, state.network_settings)

        # Calculate weight from elevation gain (for all links)
        df = process_slope_weight(
            state.network_settings, df=vol_df, my_project=my_project
        )

        # Calculate total weights
        # add inverse of premium bike coeffient to set baseline as a premium bike facility with no slope (removes all negative weights)
        # add 1 so this weight can be multiplied by original link travel time to produced "perceived travel time"
        df["total_wt"] = (
            1
            - np.float64(state.network_settings.facility_dict["facility_wt"]["premium"])
            + df["facility_wt"].astype(float)
            + df["slope_wt"].astype(float)
            + df["volume_wt"].astype(float)
        )

        # Calibrate ferry links
        _index = df["modes"].str.contains("f")
        df.loc[_index, "total_wt"] = (
            df["total_wt"] * state.network_settings.ferry_bike_factor
        )

        # Write link data for analysis

        df.to_csv(r"outputs/bike/bike_attr_%s.csv" % (my_project.tod,))

        # export total link weight as an Emme attribute file ('@bkwt.in')
        write_generalized_time(df, my_project.tod)
    except ValueError:
        sys.exit("calc bike weight failed")


def bike_assignment(my_project, tod):
    """Assign bike trips using links weights based on slope, traffic, and facility type, for a given TOD."""

    my_project.change_active_database(tod)

    # Create attributes for bike weights (inputs) and final bike link volumes (outputs)
    for attr in ["@bkwt", "@bvol"]:
        if attr not in my_project.current_scenario.attributes("LINK"):
            my_project.current_scenario.create_extra_attribute("LINK", attr)

    # Create matrices for bike assignment and skim results
    for matrix in ["bkpt", "bkat"]:
        if matrix not in [i.name for i in my_project.bank.matrices()]:
            my_project.create_matrix(matrix, "", "FULL")

    # Load in bike weight link attributes
    import_attributes = my_project.m.tool(
        "inro.emme.data.network.import_attribute_values"
    )
    filename = "working/bike_link_weights_%s.csv" % (my_project.tod,)
    import_attributes(
        filename, scenario=my_project.current_scenario, revert_on_error=True
    )

    # Invoke the Emme assignment tool
    extended_assign_transit = my_project.m.tool(
        "inro.emme.transit_assignment.extended_transit_assignment"
    )
    bike_spec = json.load(
        open(f"{state.model_input_dir}/skim_parameters/nonmotor/bike_assignment.json")
    )
    extended_assign_transit(bike_spec, add_volumes=True, class_name="bike")

    skim_bike = my_project.m.tool(
        "inro.emme.transit_assignment.extended.matrix_results"
    )
    bike_skim_spec = json.load(
        open(f"{state.model_input_dir}/skim_parameters/nonmotor/bike_skim_setup.json")
    )
    skim_bike(bike_skim_spec, class_name="bike")

    # add intrazonal times to skim
    bike_walk_matrix_dict = json_to_dictionary(
        "bike_walk_matrix_dict", state.model_input_dir, "nonmotor"
    )
    matrix_name = bike_walk_matrix_dict["bike"]["intrazonal_time"]
    iz_matrix_id = my_project.bank.matrix(matrix_name).id
    for matrix_name in ["bkpt", "bkat"]:
        my_project.matrix_calculator(
            result="mf" + matrix_name,
            expression="mf" + matrix_name + "+" + iz_matrix_id,
        )

    # Add bike volumes to bvol network attribute
    bike_network_vol = my_project.m.tool(
        "inro.emme.transit_assignment.extended.network_results"
    )

    # Skim for final bike assignment results
    bike_network_spec = json.load(
        open(
            f"{state.model_input_dir}/skim_parameters/nonmotor/bike_network_setup.json"
        )
    )
    bike_network_vol(bike_network_spec, class_name="bike")


def calc_total_vehicles(my_project):
    """For a given time period, calculate link level volume, store as extra attribute on the link"""

    # medium trucks
    my_project.network_calculator(
        "link_calculation", result="@mveh", expression="@medium_truck/1.5"
    )

    # heavy trucks:
    my_project.network_calculator(
        "link_calculation", result="@hveh", expression="@heavy_truck/2.0"
    )

    # busses:
    my_project.network_calculator(
        "link_calculation", result="@bveh", expression="@trnv3/2.0"
    )

    # calc total vehicles, store in @tveh
    user_classes = json_to_dictionary("user_classes", state.model_input_dir)
    modelist = ["@mveh", "@hveh", "@bveh"]
    for i in range(len(user_classes["Highway"])):
        mode = user_classes["Highway"][i]["Name"]
        if mode not in ["medium_truck", "heavy_truck"]:
            modelist.append("@" + mode)

    str_expression = ""
    for idx, mode in enumerate(modelist):
        if idx == len(modelist) - 1:
            str_expression += mode
        else:
            str_expression += mode + " + "

    my_project.network_calculator(
        "link_calculation", result="@tveh", expression=str_expression
    )


def get_aadt(my_project):
    """Calculate link level daily total vehicles/volume, store in a DataFrame"""

    link_list = []

    for key, value in state.network_settings.sound_cast_net_dict.items():
        my_project.change_active_database(key)

        # Create extra attributes to store link volume data
        for name, desc in state.network_settings.extra_attributes_dict.items():
            my_project.create_extra_attribute("LINK", name, desc, "True")

        # Calculate total vehicles for each link
        calc_total_vehicles(my_project)

        # Loop through each link, store length and volume
        network = my_project.current_scenario.get_network()
        for link in network.links():
            link_list.append(
                {
                    "link_id": link.id,
                    "@tveh": link["@tveh"],
                    "length": link.length,
                    "modes": link.modes,
                }
            )

    df = pd.DataFrame(link_list, columns=link_list[0].keys())
    df["modes"] = df["modes"].apply(lambda x: "".join(list([j.id for j in x])))
    df["modes"] = df["modes"].astype("str").fillna("")
    grouped = df.groupby(["link_id"])

    df = grouped.agg({"@tveh": sum, "length": min, "modes": min})
    df.reset_index(level=0, inplace=True)

    return df


def run_assignments_parallel_wrapped(project_name, free_flow_skims, max_iterations):
    try:
        pool_list = run_assignments_parallel(
            project_name, free_flow_skims, max_iterations
        )
    except:
        print("%s: %s" % (project_name, traceback.format_exc()))

    return pool_list

def load_asim_trip_matrices(state, my_project):
    """Load trip tables from ActivitySim outputs"""

    zones = my_project.current_scenario.zone_numbers
    zonesDim = len(zones)

    demand_matrices = {}

    for matrix_name in ["medium_truck", "heavy_truck", "delivery_truck"]:
        demand_matrix = load_trucks(my_project, matrix_name, zonesDim)
        demand_matrices.update({matrix_name: demand_matrix})

    # Load in supplemental trips
    # We're assuming all trips are only for Income Class 2
    for matrix_name in [
        "sov_inc2",
        "hov2_inc2",
        "hov3_inc2",
        "bike",
        "walk",
        "trnst",
        "litrat",
        "passenger_ferry",
        "ferry",
        "commuter_rail",
    ]:
        demand_matrix = load_supplemental_trips(my_project, matrix_name, zonesDim)
        demand_matrices.update({matrix_name: demand_matrix})

    # Trips from Activitysim are only for internal zones
    # Reformat to full zone system for Emme and store as an OMX file
    # Use Emme's import_from_omx tool to read in the full matrix with correct zone ordering
    trips_omx = omx.open_file(os.path.join(run_args.args.output_dir, f"{my_project.tod}.omx"), "r")
    new_omx_filename = os.path.join(run_args.args.output_dir, f"full_{my_project.tod}.omx")
    new_omx = omx.open_file(new_omx_filename,'w') 
    
    # Create an empty matrix for all zones (internal + external and park and ride)
    for table_name in trips_omx.list_matrices():
        # Create an empty matrix with full size
        table = trips_omx[table_name][:].copy()
        new_array = np.zeros([zonesDim, zonesDim], dtype=table.dtype)

        # Fill empty matrix with internal zone trips
        new_array[:table.shape[0], :table.shape[1]] = table[:] 
        new_omx[table_name] = new_array

    # Append (unsorted) TAZ mapping with any missing zones
    activitysim_mapping = list(trips_omx.mapping("TAZ").keys())
    new_mapping = activitysim_mapping + [zone for zone in zones if zone not in activitysim_mapping]
    new_omx.create_mapping('TAZ', new_mapping)

    new_omx.close()

    # Use Emme's import_from_omx tool to read in the full matrix with correct zone ordering
    matrix_dict = {}
    for matrix_name in trips_omx.list_matrices():
        try:
            matrix_id = my_project.bank.matrix(str(matrix_name)).id
            matrix_dict[matrix_name] = matrix_id
        except:
            print("Matrix {} not found in Emme bank".format(matrix_name))

    import_omx = my_project.m.tool("inro.emme.data.matrix.import_from_omx")
    import_omx(
        file_path=new_omx_filename,
        matrices=matrix_dict,
        scenario=my_project.current_scenario,
        zone_mapping="TAZ"
    )

def run_assignments_parallel(project_name, free_flow_skims, max_iterations):
    user_classes = create_user_class_dict(
        json_to_dictionary("user_classes", state.model_input_dir)
    )

    start_of_run = time.time()

    my_project = EmmeProject(project_name, state.model_input_dir)
    tod_parameters = TOD_Parameters(state.network_settings, my_project.tod)

    # Delete and create new demand and skim matrices:
    for matrix_type in ["FULL", "ORIGIN", "DESTINATION"]:
        delete_matrices(my_project, matrix_type)

    define_matrices(my_project, user_classes, tod_parameters)

    # Load demand if ABM has already been run, otherwise assign zero demand for free flow conditions
    if not free_flow_skims:
        if state.input_settings.abm_model == "daysim":
            hdf5_trips_to_Emme(my_project, "outputs/daysim/daysim_outputs.h5")
        elif state.input_settings.abm_model == "activitysim":
            load_asim_trip_matrices(state, my_project)
        matrix_controlled_rounding(my_project)

    populate_intrazonals(my_project)

    # Create transit fare matrices:
    if tod_parameters.skim_transit_fares:
        fare_dict = json_to_dictionary(
            "transit_fare_dictionary", state.model_input_dir, "transit"
        )
        fare_file = fare_dict[tod_parameters.tod]["Files"]["fare_box_file"]

        # fare box:
        create_fare_zones(my_project, state.network_settings.zone_file, fare_file)

        # monthly fares:
        fare_file = fare_dict[my_project.tod]["Files"]["monthly_pass_file"]
        create_fare_zones(my_project, state.network_settings.zone_file, fare_file)

    # Set up extra attributes to hold assignment results
    intitial_extra_attributes(my_project)
    if tod_parameters.run_transit:
        calc_bus_pce(my_project)

    # Load volume-delay functions (VDFs)
    my_project.process_function_file(state.model_input_dir / f"vdfs/vdfs{my_project.tod}.txt")

    # Run auto assignment and skimming
    traffic_assignment(my_project, max_iterations)
    attribute_based_skims(my_project, "Time")

    # Assign bike and walk trips
    bike_walk_assignment(my_project, "false")

    # Skim for distance for a single time-of-day
    if tod_parameters.skim_distance:
        attribute_based_skims(my_project, "Distance")

    # Run park and ride assignment with skim results
    if state.input_settings.abm_model == "activitysim" :
        asim_park_and_ride.run_park_and_ride(
            state,
            # EmmeProject("projects/LoadTripTables/LoadTripTables.emp", state.model_input_dir),
            my_project,
            Path("R:/e2projects_two/activitysim/assignment_skims_inputs"),
            state.network_settings.sound_cast_net_dict
            )
        
    # Fill inf with max values for park and ride matrices
    for emme_matrix_name in [
        "DRV_TRN_WLK_A_DEMAND",
        "WLK_TRN_DRV_T_DEMAND",
        "DRV_TRN_WLK_T_DEMAND",
        "WLK_TRN_DRV_A_DEMAND",
    ]:

        matrix_value = emmeMatrix_to_numpyMatrix(
            emme_matrix_name, my_project.bank, "float32", 1, 99999
        )
        if state.input_settings.abm_model == "activitysim":
            matrix_value = fill_inf_with_max(matrix_value, "float32", fill_zero=False)

        # Write numpy results back to Emme
        matrix_id = my_project.bank.matrix(str(emme_matrix_name)).id
        full_zones = my_project.current_scenario.zone_numbers
        emme_matrix = ematrix.MatrixData(indices=[full_zones, full_zones], type="f")
        emme_matrix.from_numpy(matrix_value)
        my_project.bank.matrix(matrix_id).set_data(
            emme_matrix, my_project.current_scenario
        )
        
    # Add park and ride demand to the model
    # DRV_TRN_WALK_A_DEMAND and WLK_TRN_DRV_T_DEMAND are auto trips
    # Add to sov_inc2 matrix
    pnr_access_matrix = my_project.bank.matrix("DRV_TRN_WLK_A_DEMAND").id
    pnr_egress_matrix = my_project.bank.matrix("WLK_TRN_DRV_T_DEMAND").id
    sov_inc2_matrix = my_project.bank.matrix("sov_inc2").id
    my_project.matrix_calculator(
        result=sov_inc2_matrix,
        expression=f"{sov_inc2_matrix} + {pnr_access_matrix} + {pnr_egress_matrix}",
    )

    controlled_rounding = my_project.m.tool(
                "inro.emme.matrix_calculation.matrix_controlled_rounding"
            )
    controlled_rounding(
        demand_to_round=sov_inc2_matrix,
        rounded_demand=sov_inc2_matrix,
        min_demand=0.1,
        values_to_round="SMALLER_THAN_MIN",
    )

    # DRV_TRN_WALK_T_DEMAND and WLK_TRN_DRV_A_DEMAND are transit trips, add to trnst
    pnr_access_matrix = my_project.bank.matrix("DRV_TRN_WLK_T_DEMAND").id
    pnr_egress_matrix = my_project.bank.matrix("WLK_TRN_DRV_A_DEMAND").id
    trnst_matrix = my_project.bank.matrix("trnst").id
    my_project.matrix_calculator(
        result=trnst_matrix,
        expression=f"{trnst_matrix} + {pnr_access_matrix} + {pnr_egress_matrix}",
    )

    controlled_rounding(
        demand_to_round=trnst_matrix,
        rounded_demand=trnst_matrix,
        min_demand=0.1,
        values_to_round="SMALLER_THAN_MIN",
    )

    # Park and ride demand needs to be re-run
    # FIXME: maybe only run this once after convergence

    # Generate toll skims for different user classes, and trucks
    for toll_class in ["@toll1", "@toll2", "@toll3", "@trkc2", "@trkc3"]:
        attribute_based_toll_cost_skims(my_project, toll_class)
    class_specific_volumes(my_project)

    # Export link volumes to calculate daily network flows (AADT for bike assignment)
    # Create extra attributes to store link volume data
    for name, desc in state.network_settings.extra_attributes_dict.items():
        my_project.create_extra_attribute("LINK", name, desc, "True")

    # Calculate total vehicles for each link
    calc_total_vehicles(my_project)

    # Loop through each link, store length and volume
    link_list = []
    network = my_project.current_scenario.get_network()
    for link in network.links():
        link_list.append(
            {
                "link_id": link.id,
                "@tveh": link["@tveh"],
                "length": link.length,
                "modes": link.modes,
            }
        )

    df = pd.DataFrame(link_list, columns=link_list[0].keys())
    df["modes"] = df["modes"].apply(lambda x: "".join(list([j.id for j in x])))
    df["modes"] = df["modes"].astype("str").fillna("")
    grouped = df.groupby(["link_id"])

    link_df = grouped.agg({"@tveh": "sum", "length": "min", "modes": "min"})
    link_df.reset_index(level=0, inplace=True)
    link_df["tod"] = my_project.tod

    # Clear emmebank in memory
    my_project.bank.dispose()
    print("Clearing emmebank from local memory...")
    print(my_project.tod + " emmebank cleared.")

    end_of_run = time.time()
    print(
        "It took",
        round((end_of_run - start_of_run) / 60, 2),
        " minutes to execute all processes for " + my_project.tod,
    )
    text = f"It took {round((end_of_run - start_of_run) / 60, 2)} minutes to execute all processes for {my_project.tod}"
    skims_logger.info(text)

    return link_df


def run(free_flow_skims=False, num_iterations=100):
    
    current_time = str(time.strftime("%H:%M:%S"))
    skims_logger.info("----Began SkimsAndPaths script at " + current_time)

    for tod in state.network_settings.tods:
        strat_dir = os.path.join("Banks", tod, "STRATS_s1002")
        if os.path.exists(strat_dir):
            shutil.rmtree(strat_dir)

    # # Start Daysim-Emme Equilibration
    # # This code is organized around the time periods for which we run assignments,
    # # often represented by the variable "tod". This variable will always
    # # represent a Time of Day string, such as 6to7, 7to8, 9to10, etc.
    start_of_run = time.time()
    pool_list = []
    project_list = [
        "Projects/" + tod + "/" + tod + ".emp" for tod in state.network_settings.tods
    ]

    if not state.input_settings.debug_skims_and_paths:
        for i in range(0, 12, state.emme_settings.parallel_instances):
            l = project_list[i : i + state.emme_settings.parallel_instances]
            pool_list.append(start_pool(l, free_flow_skims, num_iterations))
    else:
        run_assignments_parallel("projects/5to9/5to9.emp", free_flow_skims, num_iterations)

    ## calculate link daily volumes for use in bike model

    daily_link_df = pd.DataFrame()
    for _df in pool_list[0]:
        daily_link_df = pd.concat([daily_link_df, _df], axis=0)
        grouped = daily_link_df.groupby(["link_id"])
    daily_link_df = grouped.agg({"@tveh": "sum", "length": "min", "modes": "min"})
    daily_link_df.reset_index(level=0, inplace=True)
    daily_link_df.to_csv("outputs/bike/daily_link_volume.csv")
    start_transit_pool(project_list)
    # # run_transit(r'projects/20to5/20to5.emp')

    daily_link_df = pd.read_csv("outputs/bike/daily_link_volume.csv")
    start_bike_pool(project_list, daily_link_df)
    # # run_bike_test("projects/18to20/18to20.emp", daily_link_df)

    f = open("outputs/logs/converge.txt", "w")
    #if using seed_trips, we are starting the first iteration and do not want to compare skims from another run.
    if free_flow_skims is False:
        if (
            feedback_check(state.network_settings.feedback_list, state.emme_settings)
            is False
        ):
            go = "continue"
            json.dump(go, f)
        else:
            go = "stop"
            json.dump(go, f)
    else:
        go = "continue"
        json.dump(go, f)
    # export skims even if skims converged

    for i in range(0, 12, state.emme_settings.parallel_instances):
        l = project_list[i : i + state.emme_settings.parallel_instances]
        export_to_hdf5_pool(l, free_flow_skims)
    # average_skims_to_hdf5_concurrent(EmmeProject("projects/5to9/5to9.emp", state.model_input_dir), False)

    f.close()
    end_of_run = time.time()
    text = "Emme skim creation and export to HDF5 completed normally."
    print(text)
    skims_logger.info(text)
    text = f"Total time for all processes to execute: {round((end_of_run - start_of_run) / 60, 2)}."
    print(text)
    skims_logger.info(text)