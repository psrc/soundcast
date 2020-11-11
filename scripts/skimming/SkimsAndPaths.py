
import array as _array
import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import json
import numpy as np
import time
import os,sys
import h5py
import Tkinter, tkFileDialog
import shutil
import multiprocessing as mp
import subprocess
from multiprocessing import Pool
import logging
import datetime
import argparse
import traceback
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.getcwd())
from emme_configuration import *
from EmmeProject import *
from data_wrangling import text_to_dictionary, json_to_dictionary

#Create a logging file to report model progress
logging.basicConfig(filename=log_file_name, level=logging.DEBUG)

#Report model starting
current_time = str(time.strftime("%H:%M:%S"))
logging.debug('----Began SkimsAndPaths script at ' + current_time)

if '-build_free_flow_skims' in sys.argv:
    build_free_flow_skims = True
else:
    build_free_flow_skims = False

hdf5_file_path = 'outputs/daysim/daysim_outputs.h5'

# Link list output
#global link_df
#link_list = []
#link_list = Manager.list()
#global daily_link_df

def parse_args():
    """Parse command line arguments for max number of assignment iterations"""
    return sys.argv[1]

def get_model_year():
    return sys.argv[2]

def create_hdf5_skim_container(hdf5_name):
    #create containers for TOD skims
    start_time = time.time()

    hdf5_filename = os.path.join('inputs/model/roster', hdf5_name +'.h5').replace("\\","/")

    my_user_classes = json_to_dictionary('user_classes')

    # IOError will occur if file already exists with "w-", so in this case
    # just prints it exists. If file does not exist, opens new hdf5 file and
    # create groups based on the subgroup list above.

    # Create a sub groups with the same name as the container, e.g. 5to6, 7to8
    # These facilitate multi-processing and will be imported to a master HDF5 file
    # at the end of the run

    if not os.path.exists(hdf5_filename):
        my_store=h5py.File(hdf5_filename, "w-")
        my_store.create_group(hdf5_name)
        my_store.close()

    end_time = time.time()
    text = 'It took ' + str(round((end_time-start_time),2)) + ' seconds to create the HDF5 file.'
    logging.debug(text)
    return hdf5_filename

def vdf_initial(my_project):

    start_vdf_initial = time.time()
    
    #Point to input file for the VDF's and Read them in
    function_file = 'inputs/model/vdfs/vdfs' + my_project.tod + '.txt'

    my_project.process_function_file(function_file)
    end_vdf_initial = time.time()

def delete_matrices(my_project, matrix_type):
    for matrix in my_project.bank.matrices():
        if matrix.type == matrix_type:
            my_project.delete_matrix(matrix)

def define_matrices(my_project):
    """Create and load matrix data."""

    start_define_matrices = time.time()
    # Load in the necessary Dictionaries
    matrix_dict = json_to_dictionary("user_classes")
    bike_walk_matrix_dict = json_to_dictionary("bike_walk_matrix_dict", "nonmotor")

    for x in range (0, len(emme_matrix_subgroups)):
        for y in range (0, len(matrix_dict[emme_matrix_subgroups[x]])):
                my_project.create_matrix(matrix_dict[emme_matrix_subgroups[x]][y]["Name"],
                          matrix_dict[emme_matrix_subgroups[x]][y]["Description"], "FULL")

    # Create the Highway Skims in Emme
        #Check to see if we want to make Distance skims for this period:
    if my_project.tod in distance_skim_tod:
            #overide the global skim matrix designation (time & cost most likely) to make sure distance skims are created for this tod
        my_skim_matrix_designation=skim_matrix_designation_limited + skim_matrix_designation_all_tods
    else:
        my_skim_matrix_designation = skim_matrix_designation_all_tods

    for x in range (0, len(my_skim_matrix_designation)):
            for y in range (0, len(matrix_dict["Highway"])):
                my_project.create_matrix(matrix_dict["Highway"][y]["Name"]+my_skim_matrix_designation[x], 
                                          matrix_dict["Highway"][y]["Description"], "FULL")
                   
    #Create Generalized Cost Skims matrices for only for tod in generalized_cost_tod
    if my_project.tod in generalized_cost_tod:
        for key, value in gc_skims.items():
            my_project.create_matrix(value + 'g', "Generalized Cost Skim: " + key, "FULL")

    #Create empty Transit Skim matrices in Emme only for tod in transit_skim_tod list
    # Actual In Vehicle Times by Mode
    if my_project.tod in transit_skim_tod:
        for item in transit_submodes:
            my_project.create_matrix('ivtwa' + item, "Actual IVTs by Mode: " + item, "FULL")
            my_project.create_matrix('ivtwr' + item, "Actual IVTs by Mode, Light Rail Assignment: " + item, "FULL")
            my_project.create_matrix('ivtwf' + item, "Actual IVTs by Mode, Ferry Assignment: " + item, "FULL")
            my_project.create_matrix('ivtwc' + item, "Actual IVTs by Mode, Commuter Rail: " + item, "FULL")
            my_project.create_matrix('ivtwp' + item, "Actual IVTs by Mode, Passenger Ferry Assignment: " + item, "FULL")
            
        #Transit, All Modes:
        dct_aggregate_transit_skim_names = json_to_dictionary('transit_skim_aggregate_matrix_names', "transit")

        for key, value in dct_aggregate_transit_skim_names.items():
            my_project.create_matrix(key, value, "FULL")  
               
    #bike & walk, do not need for all time periods. most likely just 1:
    if my_project.tod in bike_walk_skim_tod:
        for key in bike_walk_matrix_dict.keys():
            my_project.create_matrix(bike_walk_matrix_dict[key]['time'], bike_walk_matrix_dict[key]['description'], "FULL")
          
    #transit fares, farebox & monthly matrices :
    fare_dict = json_to_dictionary('transit_fare_dictionary', 'transit')
    if my_project.tod in fare_matrices_tod:
        for value in fare_dict[my_project.tod]['Names'].itervalues():
             my_project.create_matrix(value, 'transit fare', "FULL")
            
    #intrazonals:
    for key, value in intrazonal_dict.items():
         my_project.create_matrix(value, key, "FULL")
      
    # Create matrices
    my_project.create_matrix('tazacr', 'taz area', "ORIGIN")
    my_project.create_matrix('prodtt', 'origin terminal times', "ORIGIN")
    my_project.create_matrix('attrtt', 'destination terminal times', "DESTINATION")
    my_project.create_matrix('termti', 'combined terminal times', "FULL")
  
    end_define_matrices = time.time()

    text = 'It took ' + str(round((end_define_matrices-start_define_matrices)/60,2)) + ' minutes to define all matrices in Emme.'
    logging.debug(text)

def create_fare_zones(my_project, zone_file, fare_file):
   
    my_project.initialize_zone_partition("gt")
    my_project.process_zone_partition(zone_file)
    my_project.matrix_transaction(os.path.join('inputs/scenario/networks/fares',fare_file)) 
    
def populate_intrazonals(my_project):
    """populate origin matrix with zone data"""

    # Load matrix transaction files
    my_project.matrix_transaction(taz_area_file)
    my_project.matrix_transaction(origin_tt_file)
    my_project.matrix_transaction(destination_tt_file)
    
    taz_area_matrix = my_project.bank.matrix('tazacr').id
    distance_matrix = my_project.bank.matrix(intrazonal_dict['distance']).id

    for key, value in intrazonal_dict.iteritems():
        if key == 'distance':
            my_project.matrix_calculator(result=value, expression="sqrt(" +taz_area_matrix+"/640) * 45/60*(p.eq.q)")
        if key == 'time auto':
            my_project.matrix_calculator(result=value, expression=distance_matrix+" *(60/15)")    # 15 mph avg
        if key == 'time bike':
            my_project.matrix_calculator(result=value, expression=distance_matrix+" *(60/10)")    # 10 mph avg
        if key == 'time walk':
            my_project.matrix_calculator(result=value, expression=distance_matrix+" *(60/3)")     # 3 mph avg
            
    #calculate full matrix terminal times
    my_project.matrix_calculator(result = 'termti', expression = 'prodtt + attrtt' )
    
    logging.debug('finished populating intrazonals')

def intitial_extra_attributes(my_project):

    start_extra_attr = time.time()

    #Load in the necessary Dictionaries
    matrix_dict = json_to_dictionary("user_classes")

    # Create the link extra attributes to store volume results
    for x in range (0, len(matrix_dict["Highway"])):
        my_project.create_extra_attribute("LINK", "@"+matrix_dict["Highway"][x]["Name"], matrix_dict["Highway"][x]["Description"], True)
                     
    # Create the link extra attributes to store the auto equivalent of bus vehicles
    my_project.create_extra_attribute("LINK", "@trnv3", "Transit Vehicles",True)
 
    # Create the link extra attribute to store the arterial delay in
    #my_project.create_extra_attribute("LINK", "@rdly","Intersection Delay", True)
    end_extra_attr = time.time()

def calc_bus_pce(my_project):
     total_hours = transit_tod[my_project.tod]['num_of_hours']
     my_expression = str(total_hours) + ' * vauteq * (60/hdw)'
     my_project.transit_segment_calculator(result = "@trnv3", expression = my_expression, aggregation = "+")

def traffic_assignment(my_project):

    start_traffic_assignment = time.time()
    print('starting traffic assignment for' +  my_project.tod)
    #Define the Emme Tools used in this function
    assign_extras = my_project.m.tool("inro.emme.traffic_assignment.set_extra_function_parameters")
    assign_traffic = my_project.m.tool("inro.emme.traffic_assignment.path_based_traffic_assignment")

    #Load in the necessary Dictionaries
    assignment_specification = json_to_dictionary("path_based_assignment", "auto")
    my_user_classes = json_to_dictionary("user_classes")

    # Modify the Assignment Specifications for the Closure Criteria and Perception Factors
    mod_assign = assignment_specification
    max_num_iterations = parse_args()
    mod_assign["stopping_criteria"]["max_iterations"]= int(max_num_iterations)
    mod_assign["stopping_criteria"]["best_relative_gap"]= best_relative_gap 
    mod_assign["stopping_criteria"]["relative_gap"]= relative_gap
    mod_assign["stopping_criteria"]["normalized_gap"]= normalized_gap

    for x in range (0, len(mod_assign["classes"])):
        vot = ((1/float(my_user_classes["Highway"][x]["Value of Time"]))*60)
        mod_assign["classes"][x]["generalized_cost"]["perception_factor"] = vot
        mod_assign["classes"][x]["generalized_cost"]["link_costs"] = my_user_classes["Highway"][x]["Toll"]
        mod_assign["classes"][x]["demand"] = "mf"+ my_user_classes["Highway"][x]["Name"]
        mod_assign["classes"][x]["mode"] = my_user_classes["Highway"][x]["Mode"]

    assign_extras(el1 = "@rdly", el2 = "@trnv3")

    if my_project.current_scenario.has_traffic_results:
        assign_traffic(mod_assign, warm_start = True)
    else:
        assign_traffic(mod_assign, warm_start = False)    
    # assign_traffic(mod_assign, warm_start = False)    
    end_traffic_assignment = time.time()

    print('It took', round((end_traffic_assignment-start_traffic_assignment)/60,2), 'minutes to run traffic assignment for '+str(my_project.tod))
    text = 'It took ' + str(round((end_traffic_assignment-start_traffic_assignment)/60,2)) + 'minutes to run traffic assignment for '+str(my_project.tod)
    logging.debug(text)

def transit_assignment(my_project, spec, keep_exisiting_volumes, class_name):

    start_transit_assignment = time.time()

    #Define the Emme Tools used in this function
    assign_transit = my_project.m.tool("inro.emme.transit_assignment.extended_transit_assignment")

    #Load in the necessary Dictionaries
    assignment_specification = json_to_dictionary(spec)

    #modify constants for certain nodes:
    assignment_specification["waiting_time"]["headway_fraction"] = transit_node_attributes['headway_fraction']['name'] 
    assignment_specification["waiting_time"]["perception_factor"] = transit_node_attributes['wait_time_perception']['name'] 
    assignment_specification["in_vehicle_time"]["perception_factor"] = transit_node_attributes['in_vehicle_time']['name']

    assign_transit(assignment_specification, add_volumes=keep_exisiting_volumes, class_name=class_name)

    end_transit_assignment = time.time()
    print('It took', round((end_transit_assignment-start_transit_assignment)/60,2), 'mins to run '+class_name+' assignment for '+str(my_project.tod))

def transit_skims(my_project, spec, class_name):

    skim_transit = my_project.m.tool("inro.emme.transit_assignment.extended.matrix_results")
    #specs are stored in a dictionary where "spec1" is the key and a list of specs for each skim is the value
    skim_specs = json_to_dictionary(spec)
    my_spec_list = skim_specs["spec1"]
    for item in my_spec_list:
        skim_transit(item, class_name=class_name)

def attribute_based_skims(my_project,my_skim_attribute):
    """ Generate time or distance skims """
    start_time_skim = time.time()

    skim_traffic = my_project.m.tool("inro.emme.traffic_assignment.path_based_traffic_analysis")
   
    #Load in the necessary Dictionaries
    skim_specification = json_to_dictionary("attribute_based_skim", "auto")
    my_user_classes = json_to_dictionary("user_classes")
    tod = my_project.tod 

    # Figure out what skim matrices to use based on attribute (either time or length)
    if my_skim_attribute == "Time":
        my_attribute = "timau"
        my_extra = "@timau"
        skim_type = "Time Skims"
        skim_desig = "t"

        #Create the Extra Attribute
        t1 = my_project.create_extra_attribute("LINK", my_extra, "copy of "+ my_attribute, True)

        # Store timau (auto time on links) into an extra attribute so we can skim for it
        my_project.network_calculator("link_calculation", result=my_extra, expression=my_attribute, selections_by_link="all") 

    if my_skim_attribute =="Distance":
        my_attribute = "length"
        my_extra = "@dist"
        skim_type = "Distance Skims"
        skim_desig = "d"
        
        t1 = my_project.create_extra_attribute("LINK", my_extra, "copy of "+ my_attribute, True)
        # Store Length (auto distance on links) into an extra attribute so we can skim for it
        my_project.network_calculator("link_calculation", result=my_extra, expression=my_attribute, selections_by_link="all") 
        
    mod_skim = skim_specification

    for x in range (0, len(mod_skim["classes"])):
        my_extra = my_user_classes["Highway"][x][my_skim_attribute]
        matrix_name = my_user_classes["Highway"][x]["Name"] + skim_desig
        matrix_id = my_project.bank.matrix(matrix_name).id
        mod_skim["classes"][x]["analysis"]["results"]["od_values"] = matrix_id
        mod_skim["path_analysis"]["link_component"] = my_extra
        #only need generalized cost skims for trucks and only doing it when skimming for time.
        if tod in generalized_cost_tod and skim_desig == 't':
            if my_user_classes["Highway"][x]["Name"] in gc_skims.values():
                mod_skim["classes"][x]["results"]["od_travel_times"]["shortest_paths"] = my_user_classes["Highway"][x]["Name"] + 'g'
        #otherwise, make sure we do not skim for GC!
       
    skim_traffic(mod_skim)

    #add in intrazonal values & terminal times:
    inzone_auto_time = my_project.bank.matrix(intrazonal_dict['time auto']).id
    inzone_terminal_time = my_project.bank.matrix('termti').id
    inzone_distance = my_project.bank.matrix(intrazonal_dict['distance']).id
    if my_skim_attribute =="Time":
        for x in range (0, len(mod_skim["classes"])):
            matrix_name= my_user_classes["Highway"][x]["Name"]+skim_desig
            matrix_id = my_project.bank.matrix(matrix_name).id
            my_project.matrix_calculator(result = matrix_id, expression = inzone_auto_time + "+" + inzone_terminal_time +  "+" + matrix_id)
           
    #only want to do this once!
    if my_project.tod in generalized_cost_tod and skim_desig == 't': 
        for value in gc_skims.values():
           matrix_name = value + 'g'
           matrix_id = my_project.bank.matrix(matrix_name).id
           my_project.matrix_calculator(result = matrix_id, expression = inzone_auto_time + "+" + inzone_terminal_time +  "+" + matrix_id)      

    if my_skim_attribute =="Distance":
        for x in range (0, len(mod_skim["classes"])):
            matrix_name= my_user_classes["Highway"][x]["Name"]+skim_desig
            matrix_id = my_project.bank.matrix(matrix_name).id
            my_project.matrix_calculator(result = matrix_id, expression = inzone_distance + "+" + matrix_id)
            
    #delete the temporary extra attributes
    my_project.delete_extra_attribute(my_extra)

    end_time_skim = time.time()

    print('It took', round((end_time_skim-start_time_skim)/60,2), 'minutes to calculate the ' +skim_type+'.')
    text = 'It took ' + str(round((end_time_skim-start_time_skim)/60,2)) + ' minutes to calculate the ' + skim_type + '.'
    logging.debug(text)

def attribute_based_toll_cost_skims(my_project, toll_attribute):
    #Function to calculate true/toll cost skims. Should fold this into attribute_based_skims function.

     start_time_skim = time.time()

     skim_traffic = my_project.m.tool("inro.emme.traffic_assignment.path_based_traffic_analysis")
     skim_specification = json_to_dictionary("attribute_based_skim", "auto")
     my_user_classes = json_to_dictionary("user_classes")

     #current_scenario = my_project.desktop.data_explorer().primary_scenario.core_scenario.ref
     my_bank = my_project.bank

     my_skim_attribute = "Toll"
     skim_desig = "c"

     #at this point, mod_skim is an empty spec ready to be populated with 21 classes. Here we are only populating the classes that
     #that have the appropriate occupancy(sv, hov2, hov3) to skim for the passed in toll_attribute (@toll1, @toll2, @toll3)
     #no need to create the extra attribute, already done in initial_extra_attributes
     mod_skim = skim_specification
     for x in range (0, len(mod_skim["classes"])):
        if my_user_classes["Highway"][x][my_skim_attribute] == toll_attribute:
            my_extra = my_user_classes["Highway"][x][my_skim_attribute]
            matrix_name= my_user_classes["Highway"][x]["Name"]+skim_desig
            matrix_id = my_bank.matrix(matrix_name).id
            mod_skim["classes"][x]["analysis"]["results"]["od_values"] = matrix_id
            mod_skim["path_analysis"]["link_component"] = my_extra
     skim_traffic(mod_skim)

def class_specific_volumes(my_project):

    start_vol_skim = time.time()

    #Define the Emme Tools used in this function
    skim_traffic = my_project.m.tool("inro.emme.traffic_assignment.path_based_traffic_analysis")

    #Load in the necessary Dictionaries
    skim_specification = json_to_dictionary("path_based_volume", "auto")
    my_user_classes = json_to_dictionary("user_classes")

    mod_skim = skim_specification
    for x in range (0, len(mod_skim["classes"])):
        mod_skim["classes"][x]["results"]["link_volumes"] = "@"+my_user_classes["Highway"][x]["Name"]
    skim_traffic(mod_skim)

    end_vol_skim = time.time()

    print('It took', round((end_vol_skim-start_vol_skim),2), 'seconds to generate class specific volumes.')
    text = 'It took ' + str(round((end_vol_skim-start_vol_skim),2)) + ' seconds to generate class specific volumes.'
    logging.debug(text)

def emmeMatrix_to_numpyMatrix(matrix_name, emmebank, np_data_type, multiplier, max_value = None):
     matrix_id = emmebank.matrix(matrix_name).id
     emme_matrix = emmebank.matrix(matrix_id)
     matrix_data = emme_matrix.get_data()
     np_matrix = np.matrix(matrix_data.raw_data) 
     np_matrix = np_matrix * multiplier
    
     if np_data_type == 'uint16':
        max_value = np.iinfo(np_data_type).max
        np_matrix = np.where(np_matrix > max_value, max_value, np_matrix)
    
     if np_data_type != 'float32':
        np_matrix = np.where(np_matrix > np.iinfo(np_data_type).max, np.iinfo(np_data_type).max, np_matrix)
     return np_matrix    

def average_matrices(old_matrix, new_matrix):
    avg_matrix = old_matrix + new_matrix
    avg_matrix = avg_matrix * .5
    return avg_matrix

def average_skims_to_hdf5_concurrent(my_project, average_skims):

    start_export_hdf5 = time.time()
    bike_walk_matrix_dict = json_to_dictionary("bike_walk_matrix_dict", "nonmotor")
    my_user_classes = json_to_dictionary("user_classes")

    #Create the HDF5 Container if needed and open it in read/write mode using "r+"
    hdf5_filename = create_hdf5_skim_container(my_project.tod)
    my_store = h5py.File(hdf5_filename, "r+")
    #if averaging, load old skims in dictionary of numpy matrices
    if average_skims:
        np_old_matrices = {}
        for key in my_store['Skims'].keys():
            np_matrix = my_store['Skims'][key]
            np_matrix = np.matrix(np_matrix)
            np_old_matrices[str(key)] = np_matrix

    e = "Skims" in my_store
    #Now delete "Skims" store if exists   
    if e:
        del my_store["Skims"]
        skims_group = my_store.create_group("Skims")
        #If not there, create the group
    else:
        skims_group = my_store.create_group("Skims")

    #Load in the necessary Dictionaries
    matrix_dict = json_to_dictionary("user_classes")

   # First Store a Dataset containing the Indicices for the Array to Matrix using mf01
    try:
        mat_id = my_project.bank.matrix("mf01")
        emme_matrix = my_project.bank.matrix(mat_id)
        em_val = emme_matrix.get_data()
        my_store["Skims"].create_dataset("indices", data=em_val.indices, compression='gzip')

    except RuntimeError:
        del my_store["Skims"]["indices"]
        my_store["Skims"].create_dataset("indices", data=em_val.indices, compression='gzip')

        # Loop through the Subgroups in the HDF5 Container
        #highway, walk, bike, transit
        #need to make sure we include Distance skims for TOD specified in distance_skim_tod

    if my_project.tod in distance_skim_tod:
        my_skim_matrix_designation = skim_matrix_designation_limited + skim_matrix_designation_all_tods
    else:
        my_skim_matrix_designation = skim_matrix_designation_all_tods

    for x in range (0, len(my_skim_matrix_designation)):

        for y in range (0, len(matrix_dict["Highway"])):
            matrix_name= matrix_dict["Highway"][y]["Name"]+my_skim_matrix_designation[x]
            if my_skim_matrix_designation[x] == 'c':
                matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 1, 99999)
            elif my_skim_matrix_designation[x] == 'd':
                matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100, 2000)
            else:
                matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100, 2000)  
            #open old skim and average
            if average_skims:
                matrix_value = average_matrices(np_old_matrices[matrix_name], matrix_value)
            #delete old skim so new one can be written out to h5 container
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('uint16'),compression='gzip')
            print(matrix_name+' was transferred to the HDF5 container.')

    # Transit Skims
    if my_project.tod in transit_skim_tod:
        # assignment path types - a: all, r: light rail, f: ferry, c: commuter rail, p: passenger ferry
        for path_mode in ['a','r','f','c','p']:    
            for item in transit_submodes:
                matrix_name= 'ivtw' + path_mode + item
                matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100)
                my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('uint16'),compression='gzip')
                print(matrix_name+' was transferred to the HDF5 container.')

        dct_aggregate_transit_skim_names = json_to_dictionary('transit_skim_aggregate_matrix_names', 'transit')

        for matrix_name, description in dct_aggregate_transit_skim_names.items():
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100)
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('uint16'),compression='gzip')
            print(matrix_name+' was transferred to the HDF5 container.')

         # Perceived and actual bike skims
        for matrix_name in ["mfbkpt", "mfbkat"]:
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100)
            #open old skim and average
            if average_skims:
                matrix_value = average_matrices(np_old_matrices[matrix_name], matrix_value)
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('uint16'),compression='gzip')
            print(matrix_name+' was transferred to the HDF5 container.')

    # Bike and walk time for single TOD
    if my_project.tod in bike_walk_skim_tod:
        for key in bike_walk_matrix_dict.keys():
            matrix_name= bike_walk_matrix_dict[key]['time']
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100)
            #open old skim and average
            if average_skims:
                matrix_value = average_matrices(np_old_matrices[matrix_name], matrix_value)
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('uint16'),compression='gzip')
            print(matrix_name+' was transferred to the HDF5 container.')

    # Transit Fare
    fare_dict = json_to_dictionary('transit_fare_dictionary', 'transit')
    if my_project.tod in fare_matrices_tod:
        for value in fare_dict[my_project.tod]['Names'].values():
            matrix_name= 'mf' + value
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100, 2000)
            #open old skim and average
            if average_skims:
                matrix_value = average_matrices(np_old_matrices[matrix_name], matrix_value)
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('uint16'),compression='gzip')
            print(matrix_name+' was transferred to the HDF5 container.')

    if my_project.tod in generalized_cost_tod:
        for value in gc_skims.values():
            matrix_name = value + 'g'
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 1, 2000)
            #open old skim and average
            if average_skims:
                matrix_value = average_matrices(np_old_matrices[matrix_name], matrix_value)
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('float32'),compression='gzip')
            print(matrix_name+' was transferred to the HDF5 container.')

    my_store.close()
    end_export_hdf5 = time.time()
    print('It took', round((end_export_hdf5-start_export_hdf5)/60,2), ' minutes to export all skims to the HDF5 File.')
    text = 'It took ' + str(round((end_export_hdf5-start_export_hdf5)/60,2)) + ' minutes to import matrices to Emme.'
    logging.debug(text)

def hdf5_trips_to_Emme(my_project, hdf_filename):

    start_time = time.time()

    #Determine the Path and Scenario File and Zone indicies that go with it
    zonesDim = len(my_project.current_scenario.zone_numbers)
    zones = my_project.current_scenario.zone_numbers
 
    #load zones into a NumpyArray to index trips otaz and dtaz
 
    #Create a dictionary lookup where key is the taz id and value is it's numpy index. 
    dictZoneLookup = dict((value,index) for index,value in enumerate(zones))
    #create an index of trips for this TOD. This prevents iterating over the entire array (all trips).
    tod_index = create_trip_tod_indices(my_project.tod)

    #Create the HDF5 Container if needed and open it in read/write mode using "r+"
    my_store=h5py.File(hdf_filename, "r+")

    #Read the Matrix File from the Dictionary File and Set Unique Matrix Names
    matrix_dict = text_to_dictionary('demand_matrix_dictionary')
    uniqueMatrices = set(matrix_dict.values())

    #Stores in the HDF5 Container to read or write to
    daysim_set = my_store['Trip']

    #Store arrays from Daysim/Trips Group into numpy arrays, indexed by TOD.
    #This means that only trip info for the current Time Period will be included in each array.
    otaz = np.asarray(daysim_set["otaz"])
    otaz = otaz.astype('int')
    otaz = otaz[tod_index]
    
    dtaz = np.asarray(daysim_set["dtaz"])
    dtaz = dtaz.astype('int')
    dtaz = dtaz[tod_index]

    mode = np.asarray(daysim_set["mode"])
    mode = mode.astype("int")
    mode = mode[tod_index]
    
    trexpfac = np.asarray(daysim_set["trexpfac"])
    trexpfac = trexpfac[tod_index]

    vot = np.asarray(daysim_set["vot"])
    vot = vot[tod_index]

    deptm = np.asarray(daysim_set["deptm"])
    deptm =deptm[tod_index]

    dorp = np.asarray(daysim_set["dorp"])
    dorp = dorp.astype('int')
    dorp = dorp[tod_index]

    pathtype = np.asarray(daysim_set["pathtype"])
    pathtype = pathtype.astype('int')
    pathtype = pathtype[tod_index]

    my_store.close

    # create & store in-memory numpy matrices in a dictionary. Key is matrix name, value is the matrix
    demand_matrices={}
   
    for matrix_name in ['medium_truck','heavy_truck', 'delivery_truck']:
        demand_matrix = load_trucks(my_project, matrix_name, zonesDim)
        demand_matrices.update({matrix_name : demand_matrix})
        
    # Load in supplemental trips
    # We're assuming all trips are only for income 2, toll classes
    for matrix_name in ['sov_inc2', 'hov2_inc2', 'hov3_inc2','bike','walk', 'trnst','litrat','passenger_ferry','ferry','commuter_rail']:
        demand_matrix = load_supplemental_trips(my_project, matrix_name, zonesDim)
        demand_matrices.update({matrix_name : demand_matrix})

    # Create empty demand matrices for other modes without supplemental trips
    for matrix in list(uniqueMatrices):
        if matrix not in demand_matrices.keys():
            demand_matrix = np.zeros((zonesDim,zonesDim), np.float16)
            demand_matrices.update({matrix : demand_matrix})

    # Start going through each trip & assign it to the correct Matrix. Using Otaz, but array length should be same for all
    # The correct matrix is determined using a tuple that consists of (mode, VOT class, AV/standard). This tuple is the key in matrix_dict.

    for x in range (0, len(otaz)):
        # Start building the tuple key, 3 VOT of categories...
        
        if vot[x] < vot_1_max: 
            vot[x] = 1 
        elif vot[x] < vot_2_max : 
            vot[x] = 2
        else: 
            vot[x]=3

        # Get matrix name from matrix_dict. Do not assign school bus trips (8) to the network.
        if mode[x] != 8 and mode[x] > 0:
            
            # Only want driver trips assigned to network, and non auto modes
            auto_mode_ids = [3, 4, 5]    # SOV, HOV2, HOV3
            non_auto_mode_ids = [1, 2, 6]    # walk, bike, transit

            # Determine if trip is AV or conventional vehicle
            av_flag = 0    # conventional vehicle by default
            if mode[x] in auto_mode_ids:
                if dorp[x] == 3 and include_av:
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
            if mode[x] == 6 and pathtype[x] in [7,12]:
                av_flag = 7


            # Retrieve trip information from Daysim records
            mat_name = matrix_dict[(int(mode[x]),int(vot[x]),av_flag)]
            myOtaz = dictZoneLookup[otaz[x]]
            myDtaz = dictZoneLookup[dtaz[x]]
            trips = np.asscalar(np.float32(trexpfac[x]))
            trips = round(trips, 2)

            # Assign TNC trips using fractional occupancy (factor of 1 for 1 passenger, 0.5 for 2 passengers, etc.)
            if (mode[x] == 9) and (dorp[x] in tnc_occupancy.keys()):
                trips = trips*tnc_occupancy[dorp[x]]
                demand_matrices[mat_name][myOtaz, myDtaz] = demand_matrices[mat_name][myOtaz, myDtaz] + trips

            # Use "dorp" field to select driver trips only; for non-auto trips, add all trips for assignment                             
            # dorp==3 for primary trips in AVs, include these along with driver trips (dorp==1)
            elif (dorp[x] <= 1 or dorp[x] == 3) or (mode[x] in non_auto_mode_ids):
                demand_matrices[mat_name][myOtaz, myDtaz] = demand_matrices[mat_name][myOtaz, myDtaz] + trips
  
  #all in-memory numpy matrices populated, now write out to emme
    for mat_name in uniqueMatrices:
        print(mat_name)
        matrix_id = my_project.bank.matrix(str(mat_name)).id
        np_array = demand_matrices[mat_name]
        print(np_array)
        emme_matrix = ematrix.MatrixData(indices=[zones,zones],type='f')
        emme_matrix.from_numpy(np_array)
        my_project.bank.matrix(matrix_id).set_data(emme_matrix, my_project.current_scenario)
    
    end_time = time.time()

    print('It took', round((end_time-start_time)/60,2), ' minutes to import trip tables to emme.')
    text = 'It took ' + str(round((end_time-start_time)/60,2)) + ' minutes to import trip tables to emme.'
    logging.debug(text)

def load_trucks(my_project, matrix_name, zonesDim):
    """ Load truck trip tables, apply time of day (TOD) factor from aggregate time periods to Soundcast TOD periods"""

    demand_matrix = np.zeros((zonesDim,zonesDim), np.float16)
    hdf_file = h5py.File(truck_trips_h5_filename, "r")
    tod = my_project.tod

    truck_matrix_name_dict = {'medium_truck': 'medtrk_trips',
                              'heavy_truck': 'hvytrk_trips',
                              'delivery_truck': 'deltrk_trips'}

    time_dictionary = json_to_dictionary('time_of_day_crosswalk_ab_4k_dictionary', 'lookup')

    # Prepend an aggregate time period (e.g., AM, PM, NI) to the truck demand matrix to import from h5
    aggregate_time_period = time_dictionary[tod]['TripBasedTime']
    truck_demand_matrix_name = 'mf' + aggregate_time_period + '_' + truck_matrix_name_dict[matrix_name]

    np_matrix = np.matrix(hdf_file[aggregate_time_period][truck_demand_matrix_name]).astype(float)

    # Apply time of day factor to convert from aggregate time periods to 12 soundcast periods
    sub_demand_matrix = np_matrix[0:zonesDim, 0:zonesDim]
    demand_matrix = sub_demand_matrix * time_dictionary[tod]['TimeFactor']
    demand_matrix = np.squeeze(np.asarray(demand_matrix))
       
    return demand_matrix

def load_supplemental_trips(my_project, matrix_name, zonesDim):
    ''' Load externals, special generator, and group quarters trips
        from the supplemental trip model. Supplemental trips are assumed
        only on Income Class 2, so only these income class modes are modified here. '''

    tod = my_project.tod
    # Create empty array to fill with trips
    demand_matrix = np.zeros((zonesDim,zonesDim), np.float16)
    hdf_file = h5py.File(os.path.join(supplemental_output_dir,tod + '.h5'), "r")

    # Open mode-specific array for this TOD and mode
    hdf_array = hdf_file[matrix_name]
    
    # Extract specified array size and store as NumPy array 
    sub_demand_matrix = hdf_array[0:zonesDim, 0:zonesDim]
    sub_demand_array = (np.asarray(sub_demand_matrix))
    demand_matrix[0:len(sub_demand_array), 0:len(sub_demand_array)] = sub_demand_array

    return demand_matrix

def create_trip_tod_indices(tod):
    # Create an index for trips that belong to TOD (time of day)
    tod_dict = text_to_dictionary('time_of_day', 'lookup')
    uniqueTOD = set(tod_dict.values())
    todIDListdict = {}
     
     # Create a dictionary where the TOD string, e.g. 18to20, is the key, and the value is a list of the hours for that period, e.g [18, 19, 20]
    for k, v in tod_dict.items():
        todIDListdict.setdefault(v, []).append(k)

    # For the given TOD, get the index of all the trips for that Time Period
    my_store = h5py.File(hdf5_file_path, "r+")
    daysim_set = my_store["Trip"]
    #open departure time array
    deptm = np.asarray(daysim_set["deptm"])
    #convert to hours
    deptm = deptm.astype('float')
    deptm = deptm/60
    deptm = deptm.astype('int')

    #Get the list of hours for this tod
    todValues = todIDListdict[tod]
    # ix is an array of true/false
    ix = np.in1d(deptm.ravel(), todValues)
    #An index for trips from this tod, e.g. [3, 5, 7) means that there are trips from this time period from the index 3, 5, 7 (0 based) in deptm
    indexArray = np.where(ix)
    my_store.close

    return indexArray

def matrix_controlled_rounding(my_project):
    
    matrix_dict = text_to_dictionary('demand_matrix_dictionary')
    uniqueMatrices = set(matrix_dict.values())
    
    NAMESPACE = "inro.emme.matrix_calculation.matrix_controlled_rounding"
    for matrix_name in uniqueMatrices:
        matrix_id = my_project.bank.matrix(matrix_name).id
        result = my_project.matrix_calculator(result = None, aggregation_destinations = '+', aggregation_origins = '+', expression = matrix_name)
        if result['maximum'] > 0:
            controlled_rounding = my_project.m.tool("inro.emme.matrix_calculation.matrix_controlled_rounding")
            report = controlled_rounding(demand_to_round=matrix_id,
                             rounded_demand=matrix_id,
                             min_demand=0.1,
                             values_to_round="SMALLER_THAN_MIN")
    text = 'finished matrix controlled rounding'
    logging.debug(text)

def start_pool(project_list):
    #An Emme databank can only be used by one process at a time. Emme Modeler API only allows one instance of Modeler and
    #it cannot be destroyed/recreated in same script. In order to run things con-currently in the same script, must have
    #seperate projects/banks for each time period and have a pool for each project/bank.
    #Fewer pools than projects/banks will cause script to crash.
    pool = Pool(processes=parallel_instances)
    pool_list = pool.map(run_assignments_parallel_wrapped,project_list[0:parallel_instances])
    pool.close()

    return pool_list

def init_pool(daily_link_df):
    global global_daily_link_df
    global_daily_link_df = daily_link_df

def start_transit_pool(project_list, daily_link_df):
    
    #Transit assignments/skimming seem to do much better running sequentially (not con-currently). Still have to use pool to get by the one
    #instance of modeler issue. Will change code to be more generalized later.
    pool = Pool(11, init_pool, [daily_link_df])
    pool.map(run_transit_wrapped, project_list[0:11])
    pool.close()

def run_transit_wrapped(project_name):
    try:
        run_transit(project_name)
    except:
        print('%s: %s' % (project_name, traceback.format_exc()))

def run_transit(project_name):
    start_of_run = time.time()

    my_project = EmmeProject(project_name)

    # Remove strategy output directory if it exists
    strat_dir = os.path.join('Banks', my_project.tod, 'STRATS_s1002')
    if os.path.exists(strat_dir):
        shutil.rmtree(strat_dir)

    # Transit demand:
    for submode, class_name in {'bus':'trnst','light_rail':'litrat','ferry':'ferry',
            'passenger_ferry':'passenger_ferry','commuter_rail':'commuter_rail'}.items():
        transit_assignment(my_project, "transit/extended_transit_assignment_"+submode, False, class_name=class_name)
        transit_skims(my_project, "transit/transit_skim_setup_"+submode, class_name)    

    # Calculate wait times
    app.App.refresh_data
    matrix_calculator = json_to_dictionary("matrix_calculation", "templates")
    matrix_calc = my_project.m.tool("inro.emme.matrix_calculation.matrix_calculator")

    # Wait times for general transit
    total_wait_matrix = my_project.bank.matrix('twtwa').id
    initial_wait_matrix = my_project.bank.matrix('iwtwa').id
    transfer_wait_matrix = my_project.bank.matrix('xfrwa').id
    mod_calc = matrix_calculator
    mod_calc["result"] = transfer_wait_matrix
    mod_calc["expression"] = total_wait_matrix + "-" + initial_wait_matrix
    matrix_calc(mod_calc)
    
    # Wait times for transit submodes
    for submode in ['r','f','p','c']:

        total_wait_matrix = my_project.bank.matrix('twtw'+submode).id
        initial_wait_matrix = my_project.bank.matrix('iwtw'+submode).id
        transfer_wait_matrix = my_project.bank.matrix('xfrw'+submode).id

        mod_calc = matrix_calculator
        mod_calc["result"] = transfer_wait_matrix
        mod_calc["expression"] = total_wait_matrix + "-" + initial_wait_matrix
        matrix_calc(mod_calc)

    # Bicycle Assignment
    calc_bike_weight(my_project, global_daily_link_df)
    tod = project_name.split('/')[1]
    bike_assignment(my_project, tod)

    my_project.bank.dispose()
 
def export_to_hdf5_pool(project_list):

    pool = Pool(processes=parallel_instances)
    pool.map(start_export_to_hdf5, project_list[0:parallel_instances])
    pool.close()

def start_export_to_hdf5(test):

    my_project = EmmeProject(test)
    #do not average skims if using seed_trips because we are starting the first iteration
    if build_free_flow_skims:
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
    #Define the Emme Tools used in this function
    assign_transit = my_project.m.tool("inro.emme.transit_assignment.standard_transit_assignment")

    #Load in the necessary Dictionaries
    assignment_specification = json_to_dictionary("bike_walk_assignment", "nonmotor")
    # get demand matrix name from user_classes:
    user_classes = json_to_dictionary("user_classes")
    bike_walk_matrix_dict = json_to_dictionary("bike_walk_matrix_dict", "nonmotor")
    mod_assign = assignment_specification
    # Only skim for time for certain TODs
    # Also fill in intrazonals
    
    #intrazonal_dict
    if my_project.tod in bike_walk_skim_tod:
        for key in bike_walk_matrix_dict.keys():
            #modify spec
            mod_assign['demand'] = 'mf' + bike_walk_matrix_dict[key]['demand']
            mod_assign['od_results']['transit_times'] = bike_walk_matrix_dict[key]['time']
            mod_assign['modes'] = bike_walk_matrix_dict[key]['modes']
            assign_transit(mod_assign)

            #intrazonal
            matrix_name= bike_walk_matrix_dict[key]['intrazonal_time']
            matrix_id = my_bank.matrix(matrix_name).id
            my_project.matrix_calculator(result = 'mf' + bike_walk_matrix_dict[key]['time'], expression = 'mf' + bike_walk_matrix_dict[key]['time'] + "+" + matrix_id)
            
    elif assign_for_all_tods == 'true':
        #Dont Skim
        for key in bike_walk_matrix_dict.keys():
            mod_assign['demand'] = bike_walk_matrix_dict[key]['demand']
            mod_assign['modes'] = bike_walk_matrix_dict[key]['modes']
            assign_transit(mod_assign)

    end_transit_assignment = time.time()
    print('It took', round((end_transit_assignment-start_transit_assignment)/60,2), ' minutes to run the bike/walk assignment.')
    text = 'It took ' + str(round((end_transit_assignment-start_transit_assignment)/60,2)) + ' minutes to run the bike/walk assignment.'
    logging.debug(text)

def feedback_check(emmebank_path_list):
     
     matrix_dict = json_to_dictionary("user_classes")
     passed = True
     for emmebank_path in emmebank_path_list:
        my_bank =  _eb.Emmebank(emmebank_path)
        tod = my_bank.title
        my_store=h5py.File('inputs/model/roster/' + tod + '.h5', "r+")
        #put current time skims in numpy:
        skims_dict = {}

        for y in range (0, len(matrix_dict["Highway"])):
           #trips
            matrix_name= matrix_dict["Highway"][y]["Name"]
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_bank, 'float32', 1)
            
            trips = np.where(matrix_value > np.iinfo('uint16').max, np.iinfo('uint16').max, matrix_value)
            
            #new skims
            matrix_name = matrix_name + 't'
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_bank, 'float32', 100)
            new_skim = np.where(matrix_value > np.iinfo('uint16').max, np.iinfo('uint16').max, matrix_value)
            
            #now old skims
            old_skim = np.asmatrix(my_store['Skims'][matrix_name])

            change_test=np.sum(np.multiply(np.absolute(new_skim-old_skim),trips))/np.sum(np.multiply(old_skim,trips))

            text = tod + " " + str(change_test) + " " + matrix_name
            logging.debug(text)
            if change_test > STOP_THRESHOLD:
                passed = False
                break

        my_bank.dispose()
     return passed

def get_link_attribute(attr, network):
    ''' Return dataframe of link attribute and link ID'''
    link_dict = {}
    for i in network.links():
        link_dict[i.id] = i[attr]
    df = pd.DataFrame({'link_id': link_dict.keys(), attr: link_dict.values()})

    return df

def bike_facility_weight(my_project, link_df):
    '''Compute perceived travel distance impacts from bike facilities
       In the geodatabase, bike facility of 2=bicycle track and 8=separated path
       These are redefined as "premium" facilities
       Striped bike lanes receive a 2nd tier designatinon of "standard"
       All other links remain unchanged'''

    network = my_project.current_scenario.get_network()

    # Load the extra attribute data for bike facility type 
    # and replace geodb typology with the 2-tier definition
    df = get_link_attribute('@bkfac', network)
    df = df.merge(link_df)
    df = df.replace(bike_facility_crosswalk)

    # Replace the facility ID with the estimated  marginal rate of substituion
    # value from Broach et al., 2012 (e.g., replace 'standard' with -0.108)
    df['facility_wt'] = df['@bkfac']
    df = df.replace(facility_dict)

    return df

def volume_weight(my_project, df):
    ''' For all links without bike lanes, apply a factor for the adjacent traffic (AADT).'''

    # Separate auto volume into bins
    df['volume_wt'] = pd.cut(df['@tveh'], bins=aadt_bins, labels=aadt_labels, right=False)
    df['volume_wt'] = df['volume_wt'].astype('int')

    # Replace bin label with weight value, only for links with no bike facilities
    over_df = df[df['facility_wt'] < 0].replace(to_replace=aadt_dict)
    over_df['volume_wt'] = 0
    under_df = df[df['facility_wt'] >= 0]
    df = over_df.append(under_df)

    return df

def process_attributes(my_project):
    '''Import bike facilities and slope attributes for an Emme network'''
    network = my_project.current_scenario.get_network()

    for attr in ['@bkfac', '@upslp']:
        if attr not in my_project.current_scenario.attributes('LINK'):
            my_project.current_scenario.create_extra_attribute('LINK',attr)
        else:
            try:
                my_project.current_scenario.delete_extra_attribute(attr)
                my_project.current_scenario.create_extra_attribute('LINK',attr)
            except:
                print('unable to recreate bike link attributes')

    import_attributes = my_project.m.tool("inro.emme.data.network.import_attribute_values")
    filename = 'inputs/scenario/bike/bike_attributes.csv'
    import_attributes(filename, 
                      scenario = my_project.current_scenario,
                      revert_on_error=False)

def process_slope_weight(df, my_project):
    ''' Calcualte slope weights on an Emme network dataframe
        and merge with a bike attribute dataframe to get total perceived 
        biking distance from upslope, facilities, and traffic volume'''

    network = my_project.current_scenario.get_network()

    # load in the slope term from the Emme network
    upslope_df = get_link_attribute('@upslp', network)

    # Join slope df with the length df
    upslope_df = upslope_df.merge(df)

    # Separate the slope into bins with the penalties as indicator values
    upslope_df['slope_wt'] = pd.cut(upslope_df['@upslp'], bins=slope_bins, labels=slope_labels, right=False)
    upslope_df['slope_wt'] = upslope_df['slope_wt'].astype('float')
    upslope_df = upslope_df.replace(to_replace=slope_dict)

    return upslope_df

def write_generalized_time(df):
    ''' Export normalized link biking weights as Emme attribute file. '''

    # Rename total weight column for import as Emme attribute
    df['@bkwt'] = df['total_wt']

    # Reformat and save as a text file in Emme format
    df['inode'] = df['link_id'].str.split('-').str[0]
    df['jnode'] = df['link_id'].str.split('-').str[1]

    filename = 'working/bike_link_weights.csv'
    df[['inode','jnode', '@bkwt']].to_csv(filename, sep=' ', index=False)

    print('results written to working/bike_link_weights.csv')

def calc_bike_weight(my_project, link_df):
    ''' Calculate perceived travel time weight for bikes
        based on facility attributes, slope, and vehicle traffic.'''

    # Calculate weight of bike facilities
    bike_fac_df = bike_facility_weight(my_project, link_df)

    # Calculate weight from daily traffic volumes
    vol_df = volume_weight(my_project, bike_fac_df)

    # Calculate weight from elevation gain (for all links)
    df = process_slope_weight(df=vol_df, my_project=my_project)

    # Calculate total weights
    # add inverse of premium bike coeffient to set baseline as a premium bike facility with no slope (removes all negative weights)
    # add 1 so this weight can be multiplied by original link travel time to produced "perceived travel time"
    df['total_wt'] = 1 - np.float(facility_dict['facility_wt']['premium']) + df['facility_wt'] + df['slope_wt'] + df['volume_wt']    

    # Calibrate ferry links
    _index = df['modes'].str.contains("f")
    df.loc[_index,'total_wt'] = df['total_wt']*ferry_bike_factor

    # Write link data for analysis
    df.to_csv(r'outputs/bike/bike_attr.csv')

    # export total link weight as an Emme attribute file ('@bkwt.in')
    write_generalized_time(df=df)

def bike_assignment(my_project, tod):
    ''' Assign bike trips using links weights based on slope, traffic, and facility type, for a given TOD.'''

    my_project.change_active_database(tod)

    # Create attributes for bike weights (inputs) and final bike link volumes (outputs)
    for attr in ['@bkwt', '@bvol']:
        if attr not in my_project.current_scenario.attributes('LINK'):
            my_project.current_scenario.create_extra_attribute('LINK',attr)   

    # Create matrices for bike assignment and skim results
    for matrix in ['bkpt', 'bkat', ]:
        if matrix not in [i.name for i in my_project.bank.matrices()]:
            my_project.create_matrix(matrix, '', 'FULL')

    # Load in bike weight link attributes
    import_attributes = my_project.m.tool("inro.emme.data.network.import_attribute_values")
    filename = 'working/bike_link_weights.csv'
    import_attributes(filename, 
                    scenario = my_project.current_scenario,
                    revert_on_error=False)

    # Invoke the Emme assignment tool
    extended_assign_transit = my_project.m.tool("inro.emme.transit_assignment.extended_transit_assignment")
    bike_spec = json.load(open('inputs/model/skim_parameters/nonmotor/bike_assignment.json'))
    extended_assign_transit(bike_spec, add_volumes=True, class_name='bike')

    skim_bike = my_project.m.tool("inro.emme.transit_assignment.extended.matrix_results")
    bike_skim_spec = json.load(open('inputs/model/skim_parameters/nonmotor/bike_skim_setup.json'))
    skim_bike(bike_skim_spec, class_name='bike')

    # Add bike volumes to bvol network attribute
    bike_network_vol = my_project.m.tool("inro.emme.transit_assignment.extended.network_results")

    # Skim for final bike assignment results
    bike_network_spec = json.load(open('inputs/model/skim_parameters/nonmotor/bike_network_setup.json'))
    bike_network_vol(bike_network_spec, class_name='bike')

    # Export skims to h5
    for matrix in ["mfbkpt", "mfbkat"]:
        print('exporting skim: ' + str(matrix))
        export_skims(my_project, matrix_name=matrix, tod=tod)

def export_skims(my_project, matrix_name, tod):
    '''Write skim matrix to h5 container'''

    my_store = h5py.File(r'inputs/model/roster/' + tod + '.h5', "r+")

    matrix_value = my_project.bank.matrix(matrix_name).get_numpy_data()

    # scale to store as integer
    matrix_value = matrix_value * bike_skim_mult
    matrix_value = matrix_value.astype('uint16')

    # Remove unreasonably high values, replace with max allowed by numpy
    max_value = np.iinfo('uint16').max
    matrix_value = np.where(matrix_value > max_value, max_value, matrix_value)

    if matrix_name in my_store['Skims'].keys():
        my_store["Skims"][matrix_name][:] = matrix_value
    else:
        try:
            my_store["Skims"].create_dataset(name=matrix_name, data=matrix_value, compression='gzip', dtype='uint16')
        except:
            'unable to export skim: ' + str(matrix_name)

    my_store.close()


def calc_total_vehicles(my_project):
    '''For a given time period, calculate link level volume, store as extra attribute on the link'''

    #medium trucks
    my_project.network_calculator("link_calculation", result = '@mveh', expression = '@medium_truck/1.5')

    #heavy trucks:
    my_project.network_calculator("link_calculation", result = '@hveh', expression = '@heavy_truck/2.0')

    #busses:
    my_project.network_calculator("link_calculation", result = '@bveh', expression = '@trnv3/2.0')

    #calc total vehicles, store in @tveh 
    user_classes = json_to_dictionary("user_classes")
    modelist = ['@mveh','@hveh','@bveh']
    for i in xrange(len(user_classes['Highway'])):
        mode = user_classes['Highway'][i]['Name']
        if mode not in ['medium_truck','heavy_truck']:
            modelist.append('@'+mode)

    str_expression = ''
    for idx, mode in enumerate(modelist):
        if idx == len(modelist)-1:
            str_expression += mode
        else:
            str_expression += mode + ' + '

    my_project.network_calculator("link_calculation", result='@tveh', expression=str_expression)


def get_aadt(my_project):
    '''Calculate link level daily total vehicles/volume, store in a DataFrame'''
    
    link_list = []

    for key, value in sound_cast_net_dict.iteritems():
        my_project.change_active_database(key)
        
        # Create extra attributes to store link volume data
        for name, desc in extra_attributes_dict.iteritems():
            my_project.create_extra_attribute('LINK', name, desc, 'True')
        
        # Calculate total vehicles for each link
        calc_total_vehicles(my_project)
        
        # Loop through each link, store length and volume
        network = my_project.current_scenario.get_network()
        for link in network.links():
            link_list.append({'link_id' : link.id, '@tveh' : link['@tveh'], 'length' : link.length, 'modes': link.modes})
            
    df = pd.DataFrame(link_list, columns = link_list[0].keys())   
    df['modes'] = df['modes'].apply(lambda x: ''.join(list([j.id for j in x])))    
    df['modes'] = df['modes'].astype('str').fillna('')
    grouped = df.groupby(['link_id'])
    
    df = grouped.agg({'@tveh':sum, 'length':min, 'modes':min})
    df.reset_index(level=0, inplace=True)
    
    return df

def run_assignments_parallel_wrapped(project_name):
    try:
        pool_list = run_assignments_parallel(project_name)
    except:
        print('%s: %s' % (project_name, traceback.format_exc()))


    return pool_list


def run_assignments_parallel(project_name):

    start_of_run = time.time()

    my_project = EmmeProject(project_name)
   
    # Delete and create new demand and skim matrices:
    for matrix_type in ['FULL','ORIGIN','DESTINATION']:
       delete_matrices(my_project, matrix_type)

    define_matrices(my_project)

    if not build_free_flow_skims:
       hdf5_trips_to_Emme(my_project, hdf5_file_path)
       matrix_controlled_rounding(my_project)

    populate_intrazonals(my_project)

    # Create transit fare matrices:
    if my_project.tod in fare_matrices_tod:
       fare_dict = json_to_dictionary('transit_fare_dictionary', 'transit')
       fare_file = fare_dict[my_project.tod]['Files']['fare_box_file']

       # fare box:
       create_fare_zones(my_project, zone_file, fare_file)

       # monthly fares:
       fare_file = fare_dict[my_project.tod]['Files']['monthly_pass_file']
       create_fare_zones(my_project, zone_file, fare_file)

    # Set up extra attributes to hold assignment results
    intitial_extra_attributes(my_project)
    if my_project.tod in transit_tod:
       calc_bus_pce(my_project)

    # Load volume-delay functions (VDFs)
    vdf_initial(my_project)

    # Run auto assignment and skimming
    traffic_assignment(my_project)
    attribute_based_skims(my_project, "Time")

    # Assign bike and walk trips
    bike_walk_assignment(my_project, 'false')

    # Skim for distance for a single time-of-day
    if my_project.tod in distance_skim_tod:
      attribute_based_skims(my_project,"Distance")

    # Generate toll skims for different user classes, and trucks
    for toll_class in ['@toll1', '@toll2', '@toll3', '@trkc2', '@trkc3']:
        attribute_based_toll_cost_skims(my_project, toll_class)
    class_specific_volumes(my_project)

    # Export link volumes to calculate daily network flows (AADT for bike assignment)
        # Create extra attributes to store link volume data
    for name, desc in extra_attributes_dict.iteritems():
        my_project.create_extra_attribute('LINK', name, desc, 'True')
        
    # Calculate total vehicles for each link
    calc_total_vehicles(my_project)
        
    # Loop through each link, store length and volume
    link_list = []
    network = my_project.current_scenario.get_network()
    for link in network.links():
        link_list.append({'link_id' : link.id, '@tveh' : link['@tveh'], 'length' : link.length, 'modes': link.modes})

    df = pd.DataFrame(link_list, columns = link_list[0].keys())   
    df['modes'] = df['modes'].apply(lambda x: ''.join(list([j.id for j in x])))    
    df['modes'] = df['modes'].astype('str').fillna('')
    grouped = df.groupby(['link_id'])
    
    link_df = grouped.agg({'@tveh':sum, 'length':min, 'modes':min})
    link_df.reset_index(level=0, inplace=True)
    link_df['tod'] = my_project.tod

    # Clear emmebank in memory
    my_project.bank.dispose()
    print('Clearing emmebank from local memory...')
    print(my_project.tod + " emmebank cleared.")
    
    end_of_run = time.time()
    print('It took', round((end_of_run-start_of_run)/60,2), ' minutes to execute all processes for ' + my_project.tod)
    text = 'It took ' + str(round((end_of_run-start_of_run)/60,2)) + ' minutes to execute all processes for ' + my_project.tod
    logging.debug(text)

    return link_df

def main():

    # Start Daysim-Emme Equilibration
    # This code is organized around the time periods for which we run assignments, 
    # often represented by the variable "tod". This variable will always
    # represent a Time of Day string, such as 6to7, 7to8, 9to10, etc.
        start_of_run = time.time()
        pool_list = []
        for i in range (0, 12, parallel_instances):
            l = project_list[i:i+parallel_instances]
            pool_list.append(start_pool(l))

         #run_assignments_parallel('projects/8to9/8to9.emp')
        
        # calculate link daily volumes for use in bike model
        daily_link_df = pd.DataFrame()
        for _df in pool_list[0]:
            daily_link_df = daily_link_df.append(_df)
            grouped = daily_link_df.groupby(['link_id'])
        daily_link_df = grouped.agg({'@tveh':sum, 'length':min, 'modes':min})
        daily_link_df.reset_index(level=0, inplace=True)
        
        start_transit_pool(project_list, daily_link_df)
        
        #run_transit(r'projects/9to10/9to10.emp', daily_link_df)
       
        f = open('outputs/logs/converge.txt', 'w')
       
        #if using seed_trips, we are starting the first iteration and do not want to compare skims from another run. 
        if build_free_flow_skims == False:
              #run feedback check 
             if feedback_check(feedback_list) == False:
                 go = 'continue'
                 json.dump(go, f)
             else:
                 go = 'stop'
                 json.dump(go, f)
        else:
           go = 'continue'
           json.dump(go, f)

        # export skims even if skims converged
        for i in range (0, 12, parallel_instances):
           l = project_list[i:i+parallel_instances]
           export_to_hdf5_pool(l)
        #average_skims_to_hdf5_concurrent(EmmeProject('projects/20to5/20to5.emp'), False)
           
        f.close()

        end_of_run = time.time()

        text = "Emme Skim Creation and Export to HDF5 completed normally"
        print(text)
        logging.debug(text)
        text = 'The Total Time for all processes took', round((end_of_run-start_of_run)/60,2), 'minutes to execute.'
        print(text)
        logging.debug(text)

if __name__ == "__main__":
    main()
