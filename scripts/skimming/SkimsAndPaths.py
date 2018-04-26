
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
import multiprocessing as mp
import subprocess
from multiprocessing import Pool
import logging
import datetime
import argparse
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.getcwd())
from emme_configuration import *
from EmmeProject import *

#Create a logging file to report model progress
logging.basicConfig(filename=log_file_name, level=logging.DEBUG)

#Report model starting
current_time = str(time.strftime("%H:%M:%S"))
logging.debug('----Began SkimsAndPaths script at ' + current_time)

# When we start a model run, we want to start with seed trips to assign.  Usually this will be
# an old daysim outputs, but sometimes you may want to use the expanded survey. On the second or
# higher iteration, you will want to use daysim_outputs.h5 from the h5 directory because these outputs
# result from using the latest assignment and skimming.
if '-use_survey_seed_trips' in sys.argv:
    survey_seed_trips = True
    daysim_seed_trips= False

elif '-use_daysim_output_seed_trips' in sys.argv:
    survey_seed_trips = False
    daysim_seed_trips= True
    build_free_flow_skims = False
elif '-build_free_flow_skims' in sys.argv:
    survey_seed_trips = False
    daysim_seed_trips= False
    build_free_flow_skims = True
else:
    survey_seed_trips = False
    daysim_seed_trips= False
    build_free_flow_skims = False
if survey_seed_trips:
	print 'Using SURVEY SEED TRIPS.'
	hdf5_file_path = base_inputs + '/' + scenario_name + '/etc/survey_seed_trips.h5'
elif daysim_seed_trips:
	print 'Using DAYSIM OUTPUT SEED TRIPS'
	hdf5_file_path = 'inputs/daysim_outputs_seed_trips.h5'
else:
	print 'Using DAYSIM OUTPUTS'
	hdf5_file_path = 'outputs/daysim/daysim_outputs.h5'

def parse_args():
    """Parse command line arguments for max number of assignment iterations"""
    return sys.argv[1]

def get_model_year():
    return sys.argv[2]

def create_hdf5_skim_container2(hdf5_name):
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

    if os.path.exists(hdf5_filename):
        print 'HDF5 File already exists - no file was created'

    else:
        my_store=h5py.File(hdf5_filename, "w-")
        my_store.create_group(hdf5_name)
        print 'HDF5 File was successfully created'
        my_store.close()

    end_time = time.time()
    text = 'It took ' + str(round((end_time-start_time),2)) + ' seconds to create the HDF5 file.'
    logging.debug(text)
    return hdf5_filename

def text_to_dictionary(dict_name):

    input_filename = os.path.join('inputs/model/skim_parameters/',dict_name+'.json').replace("\\","/")
    my_file=open(input_filename)
    my_dictionary = {}

    for line in my_file:
        k, v = line.split(':')
        my_dictionary[eval(k)] = v.strip()

    return(my_dictionary)

def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/model/skim_parameters/',dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)

def vdf_initial(my_project):

    start_vdf_initial = time.time()
    
    #Point to input file for the VDF's and Read them in
    function_file = 'inputs/model/vdfs/vdfs' + my_project.tod + '.txt'

    #manage_vdfs(transaction_file = function_file,throw_on_error = True)
    my_project.process_function_file(function_file)
    end_vdf_initial = time.time()

def delete_matrices(my_project, matrix_type):
    for matrix in my_project.bank.matrices():
        if matrix.type == matrix_type:
            my_project.delete_matrix(matrix)

def define_matrices(my_project):
    print 'starting define matrices'

    start_define_matrices = time.time()
    ##Load in the necessary Dictionaries
    matrix_dict = json_to_dictionary("user_classes")
    bike_walk_matrix_dict = json_to_dictionary("bike_walk_matrix_dict")

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
        for key, value in gc_skims.iteritems():
            my_project.create_matrix(value + 'g', "Generalized Cost Skim: " + key, "FULL")

    #Create empty Transit Skim matrices in Emme only for tod in transit_skim_tod list
    # Actual In Vehicle Times by Mode
    if my_project.tod in transit_skim_tod:
        for item in transit_submodes:
            my_project.create_matrix('ivtwa' + item, "Actual IVTs by Mode: " + item, "FULL")
        for item in transit_submodes:
            my_project.create_matrix('ivtwr' + item, "Actual IVTs by Mode, Light Rail Assignment: " + item, "FULL")
             
        #Transit, All Modes:
        dct_aggregate_transit_skim_names = json_to_dictionary('transit_skim_aggregate_matrix_names')

        for key, value in dct_aggregate_transit_skim_names.iteritems():
            my_project.create_matrix(key, value, "FULL")  
               
    #bike & walk, do not need for all time periods. most likely just 1:
    if my_project.tod in bike_walk_skim_tod:
        for key in bike_walk_matrix_dict.keys():
            my_project.create_matrix(bike_walk_matrix_dict[key]['time'], bike_walk_matrix_dict[key]['description'], "FULL")
          
    #transit fares, farebox & monthly matrices :
    fare_dict = json_to_dictionary('transit_fare_dictionary')
    if my_project.tod in fare_matrices_tod:
        for value in fare_dict[my_project.tod]['Names'].itervalues():
             my_project.create_matrix(value, 'transit fare', "FULL")
            
    #intrazonals:
    for key, value in intrazonal_dict.iteritems():
         my_project.create_matrix(value, key, "FULL")
     
    
    #origin matrix to hold TAZ Area:
    my_project.create_matrix('tazacr', 'taz area', "ORIGIN")
    
    #origin terminal time:
    my_project.create_matrix('prodtt', 'origin terminal times', "ORIGIN")
   
    #Destination terminal time:
    my_project.create_matrix('attrtt', 'destination terminal times', "DESTINATION")
   
    #Combined O/D terminal times:
    my_project.create_matrix('termti', 'combined terminal times', "FULL")
  
    end_define_matrices = time.time()

    text = 'It took ' + str(round((end_define_matrices-start_define_matrices)/60,2)) + ' minutes to define all matrices in Emme.'
    logging.debug(text)

def create_fare_zones(my_project, zone_file, fare_file):
   
    my_project.initialize_zone_partition("gt")
    my_project.process_zone_partition(zone_file)
    print fare_file
    my_project.matrix_transaction(os.path.join('inputs/scenario/networks/fares',fare_file)) 
    
def populate_intrazonals(my_project):
    #populate origin matrix with zone areas:

    #taz area
    my_project.matrix_transaction(taz_area_file)
    
    #origin terminal times
    my_project.matrix_transaction(origin_tt_file)
    
    #destination terminal times
    my_project.matrix_transaction(destination_tt_file)
    
    taz_area_matrix = my_project.bank.matrix('tazacr').id
    distance_matrix = my_project.bank.matrix(intrazonal_dict['distance']).id

    #Hard coded for now, generalize later
    for key, value in intrazonal_dict.iteritems():
        
        if key == 'distance':
            my_project.matrix_calculator(result = value, expression = "sqrt(" +taz_area_matrix + "/640) * 45/60*(p.eq.q)")
         
        if key == 'time auto':
            my_project.matrix_calculator(result = value, expression = distance_matrix + " *(60/15)")
           
        if key == 'time bike':
            my_project.matrix_calculator(result = value, expression = distance_matrix + " *(60/10)")
            
        if key == 'time walk':
            my_project.matrix_calculator(result = value, expression = distance_matrix + " *(60/3)")
            
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

def arterial_delay_calc(my_project):

    start_arterial_calc = time.time()

    # Create the temporary attributes needed for the signal delay calculations
    #t1 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@tmpl1",extra_attribute_description="temp link calc 1",overwrite=True)
    #t1 = my_project.create_extra_attribute("LINK", "@tmpl1", "temp link calc 1", True)
    #t2 = my_project.create_extra_attribute("LINK", "@tmpl2", "temp link calc 2", True)
    #t3 = my_project.create_extra_attribute("NODE", "@tmpn1", "temp node calc 1", True)
    #t4 = my_project.create_extra_attribute("NODE", "@tmpn2", "temp node calc 2", True)
    #t5 = my_project.create_extra_attribute("NODE", "@cycle", "Cycle Length", True)
    #t6 = my_project.create_extra_attribute("LINK", "@red", "Red Time", True)

    ## Set Temporary Link Attribute #1 to 1 for arterial links (ul3 .ne. 1,2)
    ## Exclude links that intersect with centroid connectors and weave links
    #my_project.network_calculator("link_calculation", result = "@tmpl1", expression = "1", selections_by_link = "mod=a and i=4001,9999999 and j=4001,9999999 and ul3=3,99 and not length=0,.015")
    
    ## Set Temporary Link Attribute #2 to the minimum of lanes+2 or 5
    ## for arterial links (ul3 .ne. 1,2)  - tmpl2 will equal either 3,4,5
    ## Exclude links that intersect with centroid connectors and weave links
    #my_project.network_calculator("link_calculation", result = "@tmpl2", expression = "(lanes+2).min.5", selections_by_link = "mod=a and i=4001,9999999 and j=4001,9999999 and ul3=3,99 and not length=0,.015")
   
    ## Set Temporary Node Attribute #1 to sum of intersecting arterial links (@tmpl1)
    #my_project.network_calculator("link_calculation", result = "@tmpn1", expression = "@tmpl1", aggregation = "+")
    
    ## Set Temporary Node Attribute #2 to sum of intersecting arterial links (@tmpl2)
    #my_project.network_calculator("link_calculation", result = "@tmpn2", expression = "@tmpl2", aggregation = "+")
    
    ## Cycle Time at Every I-Node
    #my_project.network_calculator("node_calculation", result = "@cycle", expression = "(1+(@tmpn2/8)*(@tmpn1/4))*(@tmpn1.gt.2)")
 
    #my_project.network_calculator("link_calculation", result = "@red", expression = "1.2*@cyclej*(1-(@tmpn1j*@tmpl2)/(2*@tmpn2j))", selections_by_link = "mod=a and i=4001,9999999 and j=4001,9999999 and ul3=3,99 and @cyclej=0.01,999999")
    ## Red Time at Every J-Node
    
    ## Calculate intersection delay factor for every link with a cycle time exceeding zero
    #my_project.network_calculator("link_calculation", result = "@rdly", expression = "((@red*@red)/(2*@cyclej).max.0.2).min.1.0", selections_by_link = "@cyclej=0.01,999999")
 
    ## Set intersection delay factor to 0 for links of 0.01 mile lenght or less
    #my_project.network_calculator("link_calculation", result = "@rdly", expression = "0", selections_by_link = "length=0,0.01")
    
    ##delete the temporary extra attributes
    #my_project.delete_extra_attribute("@tmpl1")
    #my_project.delete_extra_attribute("@tmpl2")
    #my_project.delete_extra_attribute("@tmpn1")
    #my_project.delete_extra_attribute("@tmpn2")
    #my_project.delete_extra_attribute("@cycle")
    #my_project.delete_extra_attribute("@red")
    #my_project.network_calculator("link_calculation", result = "@rdly", expression = "@rdly * .75")
    end_arterial_calc = time.time()


def traffic_assignment(my_project):

    start_traffic_assignment = time.time()
    print 'starting traffic assignment for' +  my_project.tod
    #Define the Emme Tools used in this function
    assign_extras = my_project.m.tool("inro.emme.traffic_assignment.set_extra_function_parameters")
    assign_traffic = my_project.m.tool("inro.emme.traffic_assignment.path_based_traffic_assignment")

    #Load in the necessary Dictionaries
    assignment_specification = json_to_dictionary("general_path_based_assignment")
    my_user_classes= json_to_dictionary("user_classes")

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
        print 'using warm starts'
        assign_traffic(mod_assign, warm_start = True)
    else:
        print 'not using warm starts'
        assign_traffic(mod_assign, warm_start = False)    
    end_traffic_assignment = time.time()

    print 'It took', round((end_traffic_assignment-start_traffic_assignment)/60,2), 'minutes to run the assignment.'
    text = 'It took ' + str(round((end_traffic_assignment-start_traffic_assignment)/60,2)) + ' minutes to run the traffic assignment.'
    logging.debug(text)

def transit_assignment(my_project, spec, keep_exisiting_volumes):

    start_transit_assignment = time.time()

    #Define the Emme Tools used in this function
    assign_transit = my_project.tool("inro.emme.transit_assignment.extended_transit_assignment")

    #Load in the necessary Dictionaries
    assignment_specification = json_to_dictionary(spec)
    
    #modify constants for certain nodes:
    assignment_specification["waiting_time"]["headway_fraction"] = transit_node_attributes['headway_fraction']['name'] 
    assignment_specification["waiting_time"]["perception_factor"] = transit_node_attributes['wait_time_perception']['name'] 
    assignment_specification["in_vehicle_time"]["perception_factor"] = transit_node_attributes['in_vehicle_time']['name']
    assign_transit(assignment_specification, add_volumes=keep_exisiting_volumes)

    end_transit_assignment = time.time()
    print 'It took', round((end_transit_assignment-start_transit_assignment)/60,2), 'minutes to run the assignment.'


def transit_skims(my_project, spec):

    skim_transit = my_project.tool("inro.emme.transit_assignment.extended.matrix_results")
    #specs are stored in a dictionary where "spec1" is the key and a list of specs for each skim is the value
    skim_specs = json_to_dictionary(spec)
    my_spec_list = skim_specs["spec1"]
    for item in my_spec_list:
        skim_transit(item)


def attribute_based_skims(my_project,my_skim_attribute):
    #Use only for Time or Distance!

    start_time_skim = time.time()

    skim_traffic = my_project.m.tool("inro.emme.traffic_assignment.path_based_traffic_analysis")
   
    #Load in the necessary Dictionaries
    skim_specification = json_to_dictionary("general_attribute_based_skim")
    my_user_classes = json_to_dictionary("user_classes")
    tod = my_project.tod 

    #Figure out what skim matrices to use based on attribute (either time or length)
    if my_skim_attribute =="Time":
        my_attribute = "timau"
        my_extra = "@timau"
        skim_type = "Time Skims"
        skim_desig = "t"

        #Create the Extra Attribute
        t1 = my_project.create_extra_attribute("LINK", my_extra, "copy of "+ my_attribute, True)

        # Store timau (auto time on links) into an extra attribute so we can skim for it
        my_project.network_calculator("link_calculation", result = my_extra, expression = my_attribute, selections_by_link = "all") 

    if my_skim_attribute =="Distance":
        my_attribute = "length"
        my_extra = "@dist"
        skim_type = "Distance Skims"
        skim_desig = "d"
        
        t1 = my_project.create_extra_attribute("LINK", my_extra, "copy of "+ my_attribute, True)
        # Store Length (auto distance on links) into an extra attribute so we can skim for it
        my_project.network_calculator("link_calculation", result = my_extra, expression = my_attribute, selections_by_link = "all") 
        
    mod_skim = skim_specification

    for x in range (0, len(mod_skim["classes"])):
        my_extra = my_user_classes["Highway"][x][my_skim_attribute]
        matrix_name= my_user_classes["Highway"][x]["Name"]+skim_desig
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

    print 'It took', round((end_time_skim-start_time_skim)/60,2), 'minutes to calculate the ' +skim_type+'.'
    text = 'It took ' + str(round((end_time_skim-start_time_skim)/60,2)) + ' minutes to calculate the ' + skim_type + '.'
    logging.debug(text)

def attribute_based_toll_cost_skims(my_project, toll_attribute):
    #Function to calculate true/toll cost skims. Should fold this into attribute_based_skims function.

     start_time_skim = time.time()

     skim_traffic = my_project.m.tool("inro.emme.traffic_assignment.path_based_traffic_analysis")
     skim_specification = json_to_dictionary("general_attribute_based_skim")
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



def cost_skims(my_project):

    start_gc_skim = time.time()

    #Define the Emme Tools used in this function
    skim_traffic = my_project.tool("inro.emme.traffic_assignment.path_based_traffic_analysis")

    #Load in the necessary Dictionaries
    skim_specification = json_to_dictionary("general_generalized_cost_skim")
    my_user_classes = json_to_dictionary("user_classes")

    current_scenario = my_project.desktop.data_explorer().primary_scenario.core_scenario.ref
    my_bank = current_scenario.emmebank

    mod_skim = skim_specification
    for x in range (0, len(mod_skim["classes"])):
        matrix_name= 'mf'+my_user_classes["Highway"][x]["Name"]+'c'
        mod_skim["classes"][x]["results"]["od_travel_times"]["shortest_paths"] = matrix_name

    skim_traffic(mod_skim)

    end_gc_skim = time.time()

    print 'It took', round((end_gc_skim-start_gc_skim)/60,2), 'minutes to calculate the generalized cost skims.'
    text = 'It took ' + str(round((end_gc_skim-start_gc_skim)/60,2)) + ' minutes to calculate the generalized cost skims.'
    logging.debug(text)

def class_specific_volumes(my_project):

    start_vol_skim = time.time()

    #Define the Emme Tools used in this function
    skim_traffic = my_project.m.tool("inro.emme.traffic_assignment.path_based_traffic_analysis")

    #Load in the necessary Dictionaries
    skim_specification = json_to_dictionary("general_path_based_volume")
    my_user_classes = json_to_dictionary("user_classes")

    mod_skim = skim_specification
    for x in range (0, len(mod_skim["classes"])):
        mod_skim["classes"][x]["results"]["link_volumes"] = "@"+my_user_classes["Highway"][x]["Name"]
    skim_traffic(mod_skim)

    end_vol_skim = time.time()

    print 'It took', round((end_vol_skim-start_vol_skim),2), 'seconds to generate class specific volumes.'
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
    
     if np_data_type <> 'float32':
        np_matrix = np.where(np_matrix > np.iinfo(np_data_type).max, np.iinfo(np_data_type).max, np_matrix)
     return np_matrix    

def average_matrices(old_matrix, new_matrix):
    avg_matrix = old_matrix + new_matrix
    avg_matrix = avg_matrix * .5
    return avg_matrix

def average_skims_to_hdf5_concurrent(my_project, average_skims):

    start_export_hdf5 = time.time()
    bike_walk_matrix_dict = json_to_dictionary("bike_walk_matrix_dict")
    my_user_classes = json_to_dictionary("user_classes")

    #Create the HDF5 Container if needed and open it in read/write mode using "r+"
    hdf5_filename = create_hdf5_skim_container2(my_project.tod)
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
        print "Group Skims Exists. Group deleted then created"
        #If not there, create the group
    else:
        skims_group = my_store.create_group("Skims")
        print "Group Skims Created"

    #Load in the necessary Dictionaries
    matrix_dict = json_to_dictionary("user_classes")

   # First Store a Dataset containing the Indicices for the Array to Matrix using mf01
    try:
        mat_id=my_project.bank.matrix("mf01")
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
            print matrix_name+' was transferred to the HDF5 container.'

        #transit
    if my_project.tod in transit_skim_tod:
        for item in transit_submodes:
            matrix_name= 'ivtwa' + item
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100)
            #open old skim and average
            #if average_skims:
            #    matrix_value = average_matrices(np_old_matrices[matrix_name], matrix_value)
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('uint16'),compression='gzip')
            print matrix_name+' was transferred to the HDF5 container.'

            # Must use light rail assignment
            matrix_name= 'ivtwr' + item
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100)
            #open old skim and average
            print matrix_name
            #if average_skims:
            #    matrix_value = average_matrices(np_old_matrices[matrix_name], matrix_value)
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('uint16'),compression='gzip')
            print matrix_name+' was transferred to the HDF5 container.'
        #Transit, All Modes:
        dct_aggregate_transit_skim_names = json_to_dictionary('transit_skim_aggregate_matrix_names')

        for key, value in dct_aggregate_transit_skim_names.iteritems():
            matrix_name= key
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100)
            #open old skim and average
            #if average_skims:
            #    matrix_value = average_matrices(np_old_matrices[matrix_name], matrix_value)
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('uint16'),compression='gzip')
            print matrix_name+' was transferred to the HDF5 container.'

    #bike/walk
    if my_project.tod in bike_walk_skim_tod:
        for key in bike_walk_matrix_dict.keys():
            matrix_name= bike_walk_matrix_dict[key]['time']
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100)
            #open old skim and average
            if average_skims:
                matrix_value = average_matrices(np_old_matrices[matrix_name], matrix_value)
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('uint16'),compression='gzip')
            print matrix_name+' was transferred to the HDF5 container.'

    #transit/fare
    fare_dict = json_to_dictionary('transit_fare_dictionary')
    if my_project.tod in fare_matrices_tod:
        for value in fare_dict[my_project.tod]['Names'].values():
            matrix_name= 'mf' + value
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 100, 2000)
            #open old skim and average
            if average_skims:
                matrix_value = average_matrices(np_old_matrices[matrix_name], matrix_value)
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('uint16'),compression='gzip')
            print matrix_name+' was transferred to the HDF5 container.'

    if my_project.tod in generalized_cost_tod:
        for value in gc_skims.values():
            matrix_name = value + 'g'
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_project.bank, 'uint16', 1, 2000)
            #open old skim and average
            if average_skims:
                matrix_value = average_matrices(np_old_matrices[matrix_name], matrix_value)
            my_store["Skims"].create_dataset(matrix_name, data=matrix_value.astype('float32'),compression='gzip')
            print matrix_name+' was transferred to the HDF5 container.'

    my_store.close()
    end_export_hdf5 = time.time()
    print 'It took', round((end_export_hdf5-start_export_hdf5)/60,2), ' minutes to export all skims to the HDF5 File.'
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

    if not survey_seed_trips:
        vot = np.asarray(daysim_set["vot"])
        vot = vot[tod_index]

    deptm = np.asarray(daysim_set["deptm"])
    deptm =deptm[tod_index]

    dorp = np.asarray(daysim_set["dorp"])
    dorp = dorp.astype('int')
    dorp = dorp[tod_index]

    toll_path = np.asarray(daysim_set["pathtype"])
    toll_path = toll_path.astype('int')
    toll_path = toll_path[tod_index]

    my_store.close

    #create & store in-memory numpy matrices in a dictionary. Key is matrix name, value is the matrix
    #also load up the external and truck trips
    demand_matrices={}
   
    for matrix_name in ['lttrk','metrk','hvtrk']:
        demand_matrix = load_trucks_external(my_project, matrix_name, zonesDim)
        demand_matrices.update({matrix_name : demand_matrix})
        
    # Load in supplemental trips
    # We're assuming all trips are only for income 2, toll classes
    for matrix_name in ['svtl2', 'h2tl2', 'h3tl2', 'litrat', 'trnst', 'bike', 'walk']:
        demand_matrix = load_supplemental_trips(my_project, matrix_name, zonesDim)
        demand_matrices.update({matrix_name : demand_matrix})

    # Create empty demand matrices for other modes without supplemental trips
    for matrix in list(uniqueMatrices):
        if matrix not in demand_matrices.keys():
            demand_matrix = np.zeros((zonesDim,zonesDim), np.float16)
            demand_matrices.update({matrix : demand_matrix})

    #Start going through each trip & assign it to the correct Matrix. Using Otaz, but array length should be same for all
    #The correct matrix is determined using a tuple that consists of (mode, vot, toll path). This tuple is the key in matrix_dict.

    for x in range (0, len(otaz)):
        #Start building the tuple key, 3 VOT of categories...
        if survey_seed_trips:
            vot = 2
            # if mode[x]<7:
            #     mat_name = matrix_dict[mode[x], vot, toll_path[x]]

            #     if dorp[x] <= 1:
            #         #get the index of the Otaz
            #         #some missing Os&Ds in seed trips!
            #         if dictZoneLookup.has_key[otaz[x]] and dictZoneLookup.has_key[dtaz[x]]:
            #             myOtaz = dictZoneLookup[otaz[x]]
            #             myDtaz = dictZoneLookupd[dtaz[x]] 
            #             trips = np.asscalar(np.float32(trexpfac[x]))
            #             trips = round(trips, 2)
            #             #if mode in supplemental_modes:
            #             demand_matrices[mat_name][myOtaz, myDtaz] = demand_matrices[mat_name][myOtaz, myDtaz] + trips
        
        #Regular Daysim Output:            
        else:
            if vot[x] < 13.07: vot[x]=1
            elif vot[x] < 26.14: vot[x]=2
            else: vot[x]=3

        #get the matrix name from matrix_dict. Throw out school bus (8) for now.
            if mode[x]<8 and mode[x]>0:
                #Only want drivers, transit trips.
                # to do: this should probably be in the emme_configuration file, in case the ids change
                auto_mode_ids = [3, 4, 5]
                # using dorp to select out driver trips only for car trips; for non-auto trips, put all trips in the matrix                              
                # dorp==3 for primary trips in AVs, include these along with driver trips (dorp==1)
                if (dorp[x] <= 1 or dorp[x] == 3) or mode[x] not in auto_mode_ids:
                    mat_name = matrix_dict[(int(mode[x]),int(vot[x]),int(toll_path[x]))]
                    myOtaz = dictZoneLookup[otaz[x]]
                    myDtaz = dictZoneLookup[dtaz[x]]
                    #add the trip, if it's not in a special generator location
                    #if OtazInt not in SPECIAL_GENERATORS.values() and DtazInt not in SPECIAL_GENERATORS.values():
                    trips = np.asscalar(np.float32(trexpfac[x]))
                    trips = round(trips, 2)
                    demand_matrices[mat_name][myOtaz, myDtaz] = demand_matrices[mat_name][myOtaz, myDtaz] + trips
  
  #all in-memory numpy matrices populated, now write out to emme
    if survey_seed_trips:
        for matrix in demand_matrices.itervalues():
            matrix = matrix.astype(np.uint16)
    for mat_name in uniqueMatrices:
        matrix_id = my_project.bank.matrix(str(mat_name)).id
        np_array = demand_matrices[mat_name]
        emme_matrix = ematrix.MatrixData(indices=[zones,zones],type='f')
        emme_matrix.from_numpy(np_array)
        my_project.bank.matrix(matrix_id).set_data(emme_matrix, my_project.current_scenario)
    
    end_time = time.time()

    print 'It took', round((end_time-start_time)/60,2), ' minutes to import trip tables to emme.'
    text = 'It took ' + str(round((end_time-start_time)/60,2)) + ' minutes to import trip tables to emme.'
    logging.debug(text)

def load_trucks_external(my_project, matrix_name, zonesDim):

    demand_matrix = np.zeros((zonesDim,zonesDim), np.float16)
    hdf_file = h5py.File(hdf_auto_filename, "r")
    tod = my_project.tod

    time_dictionary = json_to_dictionary('time_of_day_crosswalk_ab_4k_dictionary')
    class_dictionary = json_to_dictionary('demand_crosswalk_ab_4k_dictionary')

    # don't do anything for the classes not in the dictionary
    if matrix_name not in class_dictionary:
        return demand_matrix

    this_time_dictionary = time_dictionary[tod]
    this_class_dictionary = class_dictionary[matrix_name]
    trip_time= this_time_dictionary['TripBasedTime']

    #now we are constructing the name of the trip-based matrices needed for this matrix_name

    #replace the third letter for the time period in the trip based model
    time_class_name_1 = list(this_class_dictionary['FirstTripBasedClass'])

    #pm transit gets an am name
    if this_class_dictionary['TripBasedMode']=='transit' and this_time_dictionary['TripBasedTime'] == 'pm':
         time_class_name_1[0]=this_time_dictionary['TransitTripLetter']
         trip_time= this_time_dictionary['TransitTripTime']
    else:
        time_class_name_1[0]=this_time_dictionary['TripTimeLetter']

   
    trip_name_1=''.join(time_class_name_1)

    matrix_4k_1 = hdf_file[trip_time][trip_name_1]
    np_matrix_1 = np.matrix(matrix_4k_1)
    np_matrix_1 = np_matrix_1.astype(float)

    # Copy truck trip tables with a time of day factor
    if matrix_name == "lttrk" or matrix_name == "metrk" or matrix_name == "hvtrk":
       sub_demand_matrix= np_matrix_1[0:zonesDim, 0:zonesDim]
       #hdf5 matrix is brought into numpy as a matrix, need to put back into emme as an arry
       np_matrix =  sub_demand_matrix*this_time_dictionary['TimeFactor']
       demand_matrix = np.squeeze(np.asarray(np_matrix))
       
    return demand_matrix

def load_supplemental_trips(my_project, matrix_name, zonesDim):
    ''' Load externals, special generator, and group quarters trips
        from the supplemental trip model. Supplemental trips are assumed
        only on Income Class 2, so only these income class modes are modified here. '''

    tod = my_project.tod
    # Create empty array to fill with trips
    demand_matrix = np.zeros((zonesDim,zonesDim), np.float16)
    hdf_file = h5py.File(supplemental_loc + tod + '.h5', "r")
    # Call correct mode name by removing income class value when needed
    if matrix_name not in ['bike', 'litrat', 'trnst', 'walk']:
        mode_name = matrix_name[:-1]
    else:
        mode_name = matrix_name

    # Open mode-specific array for this TOD and mode
    hdf_array = hdf_file[mode_name]
    
    # Extract specified array size and store as NumPy array 
    sub_demand_matrix = hdf_array[0:zonesDim, 0:zonesDim]
    sub_demand_array = (np.asarray(sub_demand_matrix))
    demand_matrix[0:len(sub_demand_array), 0:len(sub_demand_array)] = sub_demand_array
    print matrix_name
    return demand_matrix

def create_trip_tod_indices(tod):
     #creates an index for those trips that belong to tod (time of day)
     tod_dict = text_to_dictionary('time_of_day')
     uniqueTOD = set(tod_dict.values())
     todIDListdict = {}
     
     #this creates a dictionary where the TOD string, e.g. 18to20, is the key, and the value is a list of the hours for that period, e.g [18, 19, 20]
     for k, v in tod_dict.iteritems():
        todIDListdict.setdefault(v, []).append(k)

     #Now for the given tod, get the index of all the trips for that Time Period
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

     return indexArray
     my_store.close

def matrix_controlled_rounding(my_project):
    #
    print 'start matrix conrolled rounding'
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

    #Doing some testing on best approaches to con-currency
    pool = Pool(processes=parallel_instances)
    pool.map(run_assignments_parallel,project_list[0:parallel_instances])
    pool.close()

def start_delete_matrices_pool(project_list):
    pool = Pool(processes=parallel_instances)
    pool.map(delete_matrices_parallel, project_list[0:parallel_instances])
    pool.close()

def start_transit_pool(project_list):
    
    #Transit assignments/skimming seem to do much better running sequentially (not con-currently). Still have to use pool to get by the one
    #instance of modeler issue. Will change code to be more generalized later.
    pool = Pool(processes=11)
    pool.map(run_transit,project_list[0:11])
    pool.close()

def run_transit(project_name):
    start_of_run = time.time()

    my_desktop = app.start_dedicated(True, "sc", project_name) 
    
    m = _m.Modeller(my_desktop)
    for t in m.toolboxes:
        t.connection.execute("PRAGMA busy_timeout=1000")

    #delete locki if one exists
    m.emmebank.dispose()
    
    my_bank = m.emmebank

    create_node_attributes(transit_node_attributes, m)
    # Non light rail demand
    transit_assignment(m, "extended_transit_assignment", False)
    transit_skims(m, "transit_skim_setup")

    #Light Rail demand:
    transit_assignment(m, "extended_transit_assignment_lr", True)
    transit_skims(m, "transit_skim_setup_lr")

    #Calc Wait Times
    app.App.refresh_data
    matrix_calculator = json_to_dictionary("matrix_calculation")
    matrix_calc = m.tool("inro.emme.matrix_calculation.matrix_calculator")

    #Hard coded for now, generalize later
    total_wait_matrix = my_bank.matrix('twtwa').id
    initial_wait_matrix = my_bank.matrix('iwtwa').id
    transfer_wait_matrix = my_bank.matrix('xfrwa').id

    mod_calc = matrix_calculator
    mod_calc["result"] = transfer_wait_matrix
    mod_calc["expression"] = total_wait_matrix + "-" + initial_wait_matrix
    matrix_calc(mod_calc)

    
    #Light rail Wait Times
    total_wait_matrix = my_bank.matrix('twtwr').id
    initial_wait_matrix = my_bank.matrix('iwtwr').id
    transfer_wait_matrix = my_bank.matrix('xfrwr').id

    mod_calc = matrix_calculator
    mod_calc["result"] = transfer_wait_matrix
    mod_calc["expression"] = total_wait_matrix + "-" + initial_wait_matrix
    matrix_calc(mod_calc)

    my_bank.dispose()
 
def export_to_hdf5_pool(project_list):

    pool = Pool(processes=parallel_instances)
    pool.map(start_export_to_hdf5, project_list[0:parallel_instances])
    pool.close()

def start_export_to_hdf5(test):

    my_project = EmmeProject(test)
    #do not average skims if using seed_trips because we are starting the first iteration
    if survey_seed_trips or daysim_seed_trips or build_free_flow_skims:
        average_skims_to_hdf5_concurrent(my_project, False)
    else:
        average_skims_to_hdf5_concurrent(my_project, True)

def bike_walk_assignment(my_project, assign_for_all_tods):
    #One bank
    #this runs the assignment and produces a time skim as well, which we need is all we need- converted
    #to distance in Daysim.
    #Assignment is run for all time periods (at least it should be for the final iteration). Only need to
    #skim for one TOD. Skim is an optional output of the assignment.

    start_transit_assignment = time.time()
    my_bank = my_project.bank
    #Define the Emme Tools used in this function
    assign_transit = my_project.m.tool("inro.emme.transit_assignment.standard_transit_assignment")

    #Load in the necessary Dictionaries


    assignment_specification = json_to_dictionary("bike_walk_assignment")
    #get demand matrix name from here:
    user_classes = json_to_dictionary("user_classes")
    bike_walk_matrix_dict = json_to_dictionary("bike_walk_matrix_dict")
    mod_assign = assignment_specification
    #only skim for time for certain tod
    #Also fill in intrazonals
    
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
    print 'It took', round((end_transit_assignment-start_transit_assignment)/60,2), ' minutes to run the bike/walk assignment.'
    text = 'It took ' + str(round((end_transit_assignment-start_transit_assignment)/60,2)) + ' minutes to run the bike/walk assignment.'
    logging.debug(text)

def bike_walk_assignment_NonConcurrent(project_name):
    #One bank
    #this runs the assignment and produces a time skim as well, which we need is all we need- converted
    #to distance in Daysim.
    #Assignment is run for all time periods (at least it should be for the final iteration). Only need to
    #skim for one TOD. Skim is an optional output of the assignment.
    tod_dict = text_to_dictionary('time_of_day')
    uniqueTOD = set(tod_dict.values())
    uniqueTOD = list(uniqueTOD)
    bike_walk_matrix_dict = json_to_dictionary("bike_walk_matrix_dict")
    #populate a dictionary of with key=bank name, value = emmebank object
    data_explorer = project_name.desktop.data_explorer()
    all_emmebanks = {}
    for database in data_explorer.databases():
        emmebank = database.core_emmebank
        all_emmebanks.update({emmebank.title: emmebank})
    start_transit_assignment = time.time()

    #Define the Emme Tools used in this function

    for tod in uniqueTOD:       
        my_bank = all_emmebanks[tod]
        #need a scenario, get the first one
        current_scenario = list(my_bank.scenarios())[0]
        #Determine the Path and Scenario File

        zones=current_scenario.zone_numbers
        bank_name = my_bank.title
        assign_transit = project_name.tool("inro.emme.transit_assignment.standard_transit_assignment")

    	# Load in the necessary Dictionaries
        assignment_specification = json_to_dictionary("bike_walk_assignment")
        # get demand matrix name from here:
        user_classes = json_to_dictionary("user_classes")
        mod_assign = assignment_specification
        # only skim for time for certain tod
        if tod in bike_walk_skim_tod:
            for key in bike_walk_matrix_dict.keys():
                mod_assign['demand'] = bike_walk_matrix_dict[key]['demand']
                mod_assign['od_results']['transit_times'] = bike_walk_matrix_dict[key]['time']
                mod_assign['modes'] = bike_walk_matrix_dict[key]['modes']
                assign_transit(mod_assign)
        else:
            # Dont Skim
            for key in bike_walk_matrix_dict.keys():
                mod_assign['demand'] = bike_walk_matrix_dict[key]['demand']
                mod_assign['modes'] = bike_walk_matrix_dict[key]['modes']
                assign_transit(mod_assign)


    end_transit_assignment = time.time()
    print 'It took', round((end_transit_assignment-start_transit_assignment)/60,2), ' minutes to run the bike/walk assignment.'
    text = 'It took ' + str(round((end_transit_assignment-start_transit_assignment)/60,2)) + ' minutes to run the bike/walk assignment.'
    logging.debug(text)

def feedback_check(emmebank_path_list):
     
     #current_scenario = m.desktop.data_explorer().primary_scenario.core_scenario.refe_list
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
            print 'trips'
            print trips[563,547]
            
            #new skims
            matrix_name = matrix_name + 't'
            matrix_value = emmeMatrix_to_numpyMatrix(matrix_name, my_bank, 'float32', 100)
            new_skim = np.where(matrix_value > np.iinfo('uint16').max, np.iinfo('uint16').max, matrix_value)
            
            print matrix_name
            print 'new_skim'
            print new_skim[563,547]
            
            #now old skims
            old_skim = np.asmatrix(my_store['Skims'][matrix_name])
            print 'old_skim'
            print old_skim[563,547]
          

            change_test=np.sum(np.multiply(np.absolute(new_skim-old_skim),trips))/np.sum(np.multiply(old_skim,trips))
            print 'test value'
            print change_test
            text = tod + " " + str(change_test) + " " + matrix_name
            logging.debug(text)
            if change_test > STOP_THRESHOLD:
                passed = False
                break

        my_bank.dispose()
     return passed

def create_node_attributes(node_attribute_dict, my_project):
        current_scenario = my_project.desktop.data_explorer().primary_scenario.core_scenario.ref
        my_bank = current_scenario.emmebank
        tod = my_bank.title
        NAMESPACE = "inro.emme.data.extra_attribute.create_extra_attribute"
        create_extra = my_project.tool(NAMESPACE)
        for key, value in node_attribute_dict.iteritems():
            new_att = create_extra(extra_attribute_type="NODE",
                       extra_attribute_name=value['name'],
                       extra_attribute_description=key,
                       extra_attribute_default_value = value['init_value'],
                       overwrite=True)
        
        network_calc = my_project.tool("inro.emme.network_calculation.network_calculator")  
        node_calculator_spec = json_to_dictionary("node_calculation")
        model_year = get_model_year()
      
        for line_id, attribute_dict in transit_node_constants[model_year].iteritems():

            for attribute_name, value in attribute_dict.iteritems():
            #Load in the necessary Dictionarie
                mod_calc = node_calculator_spec
                mod_calc["result"] = attribute_name
                mod_calc["expression"] = value
                mod_calc["selections"]["node"] = "Line = " + line_id
                network_calc(mod_calc)

def delete_matrices_parallel(project_name):
    my_project = EmmeProject(project_name)
   
    ##delete and create new demand and skim matrices:
    delete_matrices(my_project, "FULL")
    delete_matrices(my_project, "ORIGIN")
    delete_matrices(my_project, "DESTINATION")

def run_assignments_parallel(project_name):

    start_of_run = time.time()

    my_project = EmmeProject(project_name)
   
    ##delete and create new demand and skim matrices:
    delete_matrices(my_project, "FULL")
    delete_matrices(my_project, "ORIGIN")
    delete_matrices(my_project, "DESTINATION")

    define_matrices(my_project)

    if not build_free_flow_skims:
        hdf5_trips_to_Emme(my_project, hdf5_file_path)
        matrix_controlled_rounding(my_project)

    ##tod = m.emmebank.title
    populate_intrazonals(my_project)

    ##create transit fare matrices:
    if my_project.tod in fare_matrices_tod:
        fare_dict = json_to_dictionary('transit_fare_dictionary')
        fare_file = fare_dict[my_project.tod]['Files']['fare_box_file']
        #fare box:
        create_fare_zones(my_project, zone_file, fare_file)
        #monthly:
        fare_file = fare_dict[my_project.tod]['Files']['monthly_pass_file']
        create_fare_zones(my_project, zone_file, fare_file)

    ##set up for assignments
    intitial_extra_attributes(my_project)
    if my_project.tod in transit_tod:
        calc_bus_pce(my_project)

    # ************arterial delay is being handled in network_importer for now. Leave commented!!!!!!!!!!!!!
    #arterial_delay_calc(my_project)

    vdf_initial(my_project)
    ##run auto assignment/skims
    traffic_assignment(my_project)
    
    attribute_based_skims(my_project, "Time")

    ###bike/walk:
    bike_walk_assignment(my_project, 'false')
    ###Only skim for distance if in global distance_skim_tod list
    if my_project.tod in distance_skim_tod:
       attribute_based_skims(my_project,"Distance")

    ####Toll skims
    attribute_based_toll_cost_skims(my_project, "@toll1")
    attribute_based_toll_cost_skims(my_project, "@toll2")
    attribute_based_toll_cost_skims(my_project, "@toll3")
    attribute_based_toll_cost_skims(my_project, "@trkc2")
    attribute_based_toll_cost_skims(my_project, "@trkc3")
    class_specific_volumes(my_project)

    ##dispose emmebank
    my_project.bank.dispose()
    
    print my_project.tod + " finished"
    
    end_of_run = time.time()
    print 'It took', round((end_of_run-start_of_run)/60,2), ' minutes to execute all processes for ' + my_project.tod
    text = 'It took ' + str(round((end_of_run-start_of_run)/60,2)) + ' minutes to execute all processes for ' + my_project.tod
    logging.debug(text)

def main():

    #Start Daysim-Emme Equilibration
    #This code is organized around the time periods for which we run assignments, often represented by the variable tod. This variable will always
    #represent a Time of Day string, such as 6to7, 7to8, 9to10, etc.
        start_of_run = time.time()

        for i in range (0, 12, parallel_instances):
            l = project_list[i:i+parallel_instances]
            start_pool(l)

        #want pooled processes finished before executing more code in main:
        # run_assignments_parallel('projects/6to7/6to7.emp')
        
        start_transit_pool(project_list)
        #run_transit('projects/20to5/20to5.emp')
       
        f = open('outputs/logs/converge.txt', 'w')
       
        #If using seed_trips, we are starting the first iteration and do not want to compare skims from another run. 
        if (survey_seed_trips == False and daysim_seed_trips == False and build_free_flow_skims == False):
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

        #export skims even if skims converged
        for i in range (0, 12, parallel_instances):
                l = project_list[i:i+parallel_instances]
                export_to_hdf5_pool(l)
        
        #delete emme matrices to save space:
        #start_delete_matrices_pool(project_list)
           
        f.close()

        end_of_run = time.time()

        text =  "Emme Skim Creation and Export to HDF5 completed normally"
        print text
        logging.debug(text)
        text = 'The Total Time for all processes took', round((end_of_run-start_of_run)/60,2), 'minutes to execute.'
        print text
        logging.debug(text)


if __name__ == "__main__":

    main()