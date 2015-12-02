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
import Tkinter, tkFileDialog
import multiprocessing as mp
import subprocess
from multiprocessing import Pool
import h5py
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from input_configuration import *
from EmmeProject import *

# Temp log file for de-bugging
logfile = open("truck_log.txt", 'wb')
          
def network_importer(EmmeProject):
    for scenario in list(EmmeProject.bank.scenarios()):
            my_project.bank.delete_scenario(scenario)
        #create scenario
    EmmeProject.bank.create_scenario(1002)
    EmmeProject.change_scenario()
        #print key
    EmmeProject.delete_links()
    EmmeProject.delete_nodes()
    EmmeProject.process_modes('inputs/networks/' + mode_file)
    EmmeProject.process_base_network('inputs/networks/' + truck_base_net_name)  

def json_to_dictionary(dict_name):
    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/trucks/',dict_name+'.txt').replace("\\","/")
    my_dictionary = json.load(open(input_filename))
    return(my_dictionary)

def skims_to_hdf5(EmmeProject):
    truck_od_matrices = ['lttrk', 'mdtrk', 'hvtrk']
  
    #open h5 container, delete existing truck trip matrices:
    my_store = h5py.File(truck_trips_h5_filename, "r+")
    for tod in tod_list:
        for name in truck_od_matrices:
            matrix_name = tod[0] + name       
            #delete if matrix exists
            e = matrix_name in my_store[tod]
            if e:
                del my_store[tod][matrix_name]
            #export to hdf5
            print 'exporting'
            matrix_name = tod[0] + name
            print matrix_name
            matrix_id = EmmeProject.bank.matrix(matrix_name).id
            print matrix_id
            matrix = EmmeProject.bank.matrix(matrix_id)
            matrix_value = np.matrix(matrix.raw_data)
            my_store[tod].create_dataset(matrix_name, data=matrix_value.astype('float32'),compression='gzip')
            print matrix_name+' was transferred to the HDF5 container.'
            matrix_value = None
                    
    my_store.close()


#create a place holder scalar matrix
def place_holder_scalar_matrix():
    my_project.create_matrix('place', 'place holder', 'SCALAR')

#create origin and destination matrices
def create_origin_destination_matrices():
    for y in range (0, len(origin_destination_dict["Origin_Matrices"])):
        my_project.create_matrix(origin_destination_dict['Origin_Matrices'][y]['Name'],
                                 origin_destination_dict['Origin_Matrices'][y]['Description'], 
                                 'ORIGIN')
    for y in range (0, len(origin_destination_dict["Destination_Matrices"])):
        my_project.create_matrix(origin_destination_dict['Destination_Matrices'][y]['Name'],
                                 origin_destination_dict['Destination_Matrices'][y]['Description'], 
                                 'DESTINATION')

#create scalar matrices:
def create_scalar_matrices():
    for y in range(0, len(origin_destination_dict["Scalar_Matrices"])):
        my_project.create_matrix(origin_destination_dict['Scalar_Matrices'][y]['Name'], 
                                 origin_destination_dict['Scalar_Matrices'][y]['Description'], 
                                 'SCALAR')

#create full matrices
def create_full_matrices():
    for y in range(0, len(origin_destination_dict["Full_Matrices"])):
        my_project.create_matrix(origin_destination_dict['Full_Matrices'][y]['Name'],
                                 origin_destination_dict['Full_Matrices'][y]['Description'], 
                                 'FULL')

#import matrices(employment shares):
def import_emp_matrices():
    truck_emp_dict = json_to_dictionary('truck_emp_dict')
    truck_matrix_import_list = ['tazdata', 'agshar', 'minshar', 'prodshar', 'equipshar', 
                                 'tcushar', 'whlsshar', 'const', 'special_gen_light_trucks',
                                 'special_gen_medium_trucks', 'special_gen_heavy_trucks', 
                                 'heavy_trucks_reeb_ee', 'heavy_trucks_reeb_ei', 'heavy_trucks_reeb_ie']
    for name in truck_matrix_import_list:
        my_project.import_matrices('inputs/trucks/' + name + '.in')

#calculate total households (9_calculate_total_households.mac) by origin:
#destinations 102-105 represent household information
def calc_total_households():
    my_project.matrix_calculator(result = 'mohhlds', 
                                 expression = 'mfhhemp', 
                                 aggregation_destinations = '+', 
                                 constraint_by_zone_origins = '*', 
                                 constraint_by_zone_destinations = '102-105')

#Populating origin matrices from household/employment matrix (10_copy_matrices.mac)
#Copying each colunn into the appropriate Origin Matrix
def truck_productions():
    origin_emp_dict = json_to_dictionary('origin_emp_dict')
    truck_emp_dict = json_to_dictionary('truck_emp_dict')
    for key, value in origin_emp_dict.iteritems():
        my_project.matrix_calculator(result = key, aggregation_destinations = '+',
                                     constraint_by_zone_origins = '*',
                                     constraint_by_zone_destinations = value, 
                                     expression = 'hhemp')
    #Populating origin matrices with Employment Sector totals by origin
    for key, value in truck_emp_dict.iteritems():
        my_project.matrix_calculator(result = key, expression = value)

    #Calculate Productions for 3 truck classes (Origin Matrices are populated)
    for key, value in truck_generation_dict['productions'].iteritems():
        my_project.matrix_calculator(result = value['results'], expression = value['expression'])
        print "We're printing the productions part."
        logfile.write("We're printing the productions part.")

def truck_attractions():
    #Calculate Attractions for 3 truck classes (Destination Matrices are populated)
    for key, value in truck_generation_dict['attractions'].iteritems():
        my_project.matrix_calculator(result = value['results'], expression = value['expression'])
        print "We're printing the attractions part."
        logfile.write("We're printing the attractions part.")

    truck_dest_matrices = ['ltatt', 'mtatt', 'htatt']
    print 'done with productions and attractions'
    logfile.write('done with productions and attractions')

    #Transpose Attractions (Destination Matrices are populated)
    for item in truck_dest_matrices:
        my_project.matrix_calculator(result = 'md' + item, expression = 'mo' + item + "'")

    spec_gen_dict = {'ltatt' : "spllgt", 'mtatt' : 'splmed', 'htatt' : 'splhvy'}
    #Special Generators (Destination Matrices are populated
    for key, value in spec_gen_dict.iteritems():
        my_project.matrix_calculator(result = 'md' + key, expression = 'md' + key + '+ md' + value)

    refactor_dict = {'moltprof' : 'moltpro * 0.554',
                     'momtprof' : 'momtpro * 0.309',
                     'mohtprof' : 'mohtpro * 0.413',
                     'mdltattf' : 'mdltatt * 0.749',
                     'mdmtattf' : 'mdmtatt * 0.500',
                     'mdhtattf' : 'mdhtatt * 1.375'}

    for key, value in refactor_dict.iteritems():
        my_project.matrix_calculator(result = key, expression = value)

def import_skims():
    # Import districts
    my_project.initialize_zone_partition('ga')
    my_project.process_zone_partition('inputs/trucks/' + districts_file)
    # Import truck operating costs
    my_project.import_matrices('inputs/trucks/truck_operating_costs.in')
    
    # Open GC skims from H5 container, average am/pm, import to emme:
    np_gc_skims = {}
    np_bidir_gc_skims = {}
    for tod in truck_generalized_cost_tod.keys():
        hdf_file = h5py.File('inputs/' + tod + '.h5', "r")
        for item in input_skims.values():
            #gc
            skim_name = item['gc_name']
            h5_skim = hdf_file['Skims'][skim_name]
            np_skim = np.matrix(h5_skim)
            np_gc_skims[skim_name + '_' + truck_generalized_cost_tod[tod]] = np_skim
        
            #distance
            skim_name = item['dist_name']
            h5_skim = hdf_file['Skims'][skim_name]
            np_skim = np.matrix(h5_skim)
            np_gc_skims[skim_name + '_' + truck_generalized_cost_tod[tod]] = np_skim

    zones = my_project.current_scenario.zone_numbers
    zonesDim = len(my_project.current_scenario.zone_numbers)

    for truck_type in input_skims.values():
        #gc:
        am_skim_name = truck_type['gc_name'] + '_am'
        pm_skim_name = truck_type['gc_name'] + '_pm'
        bidir_skim_name = truck_type['gc_bidir_name']
        bi_dir_skim = np_gc_skims[am_skim_name] + np_gc_skims[pm_skim_name]
        bi_dir_skim = np.asarray(bi_dir_skim)
        #have sum, now get average
        bi_dir_skim *= .5
        bi_dir_skim = bi_dir_skim[0:zonesDim, 0:zonesDim]
        np_bidir_gc_skims[bidir_skim_name] = bi_dir_skim
   
        #distance
        am_skim_name = truck_type['dist_name'] + '_am'
        pm_skim_name = truck_type['dist_name'] + '_pm'
        bidir_skim_name = truck_type['dist_bidir_name']
        #distance skims are multiplied by 100 when exported by SkimsAndPaths, so we devide by 100
        bi_dir_skim = (np_gc_skims[am_skim_name] + np_gc_skims[pm_skim_name])/100
        bi_dir_skim = np.asarray(bi_dir_skim)
        #have sum, now get average
        bi_dir_skim *= .5
        bi_dir_skim = bi_dir_skim[0:zonesDim, 0:zonesDim]
        np_bidir_gc_skims[bidir_skim_name] = bi_dir_skim

    #import bi-directional skims to emmebank
    for mat_name, matrix in np_bidir_gc_skims.iteritems():
        matrix_id = my_project.bank.matrix(str(mat_name)).id
        emme_matrix = ematrix.MatrixData(indices=[zones,zones],type='f')
        emme_matrix.raw_data=[_array.array('f',row) for row in matrix]
        my_project.bank.matrix(matrix_id).set_data(emme_matrix,my_project.current_scenario)

def balance_attractions():
    #Balance Refactored Light Truck Attractions to productions:
    my_project.matrix_calculator(result = 'msltprof', expression = 'moltprof', aggregation_origins = '+')
    my_project.matrix_calculator(result = 'msltattf', expression = 'mdltattf', aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'msltatfe', expression = 'mdltattf', 
                                 constraint_by_zone_destinations = str(LOW_STATION) + '-' + str(HIGH_STATION),
                                 aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'mdltattf', 
                                 expression = 'mdltattf * ((msltprof - msltatfe)/(msltattf-msltatfe))')

    #Balance Refactored Medium Truck Attractions to productions:
    my_project.matrix_calculator(result = 'msmtprof', expression = 'momtprof', aggregation_origins = '+')
    my_project.matrix_calculator(result = 'msmtattf', expression = 'mdmtattf', aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'msmtatfe', expression = 'mdmtattf', 
                                 constraint_by_zone_destinations = str(LOW_STATION) + '-' + str(HIGH_STATION),
                                 aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'mdmtattf', 
                                 expression = 'mdmtattf * ((msmtprof - msmtatfe)/(msmtattf-msmtatfe))')

    #Balance Refactored Heavy Truck Attractions to productions:
    my_project.matrix_calculator(result = 'mshtprof', expression = 'mohtprof', aggregation_origins = '+')
    my_project.matrix_calculator(result = 'mshtattf', expression = 'mdhtattf', aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'mshtatfe', expression = 'mdhtattf', 
                                 constraint_by_zone_destinations = str(LOW_STATION) + '-' + str(HIGH_STATION),
                                 aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'mdhtattf',
                                     expression = 'mdhtattf * ((mshtprof - mshtatfe)/(mshtattf-mshtatfe))')

# Calculate Impedances
def calculate_impedance():
    # set flag to 0 for external-external OD paris and all others equal to 1
    my_project.matrix_calculator(result = 'mfintflg', expression = '1')
    my_project.matrix_calculator(result = 'mfintflg', expression = '0', 
                                 constraint_by_zone_destinations = EXTERNAL_DISTRICT, 
                                 constraint_by_zone_origins = EXTERNAL_DISTRICT)

    # calculate light truck impedances:
    my_project.matrix_calculator(result = 'mflgtimp', expression = 'exp(-0.04585*(mfblgtcs+(mfblgtds*mslgtop*.0150)))*mfintflg', 
                                 constraint_by_zone_destinations = '1-' + str(HIGH_STATION), 
                                 constraint_by_zone_origins = '1-' + str(HIGH_STATION))

    # calculate medium truck impedances:
    my_project.matrix_calculator(result = 'mfmedimp', 
                                 expression = 'exp(-0.0053*(mfbmedcs+(mfbmedds*msmedop*.0133)))*mfintflg', 
                                 constraint_by_zone_destinations = '1-' + str(HIGH_STATION), 
                                 constraint_by_zone_origins = '1-' + str(HIGH_STATION))

    # calculate heavy truck impedances:
    my_project.matrix_calculator(result = 'mfhvyimp', 
                                 expression = 'exp(-0.00001*(mfbhvycs+(mfbhvyds*mshvyop*.0120)))*mfintflg', 
                                 constraint_by_zone_destinations = '1-' + str(HIGH_STATION), 
                                 constraint_by_zone_origins = '1-' + str(HIGH_STATION))

def balance_matrices():
    # Balance Light Trucks
    my_project.matrix_balancing(results_od_balanced_values = 'mflgtdis', 
                                od_values_to_balance = 'mflgtimp', 
                                origin_totals = 'moltprof', destination_totals = 'mdltattf', 
                                constraint_by_zone_destinations = '1-' + str(HIGH_STATION), 
                                constraint_by_zone_origins = '1-' + str(HIGH_STATION))
    # Balance Medium Trucks
    my_project.matrix_balancing(results_od_balanced_values = 'mfmeddis', 
                                od_values_to_balance = 'mfmedimp', 
                                origin_totals = 'momtprof', 
                                destination_totals = 'mdmtattf', 
                                constraint_by_zone_destinations = '1-' + str(HIGH_STATION), 
                                constraint_by_zone_origins = '1-' + str(HIGH_STATION))
    # Balance Heavy Trucks
    my_project.matrix_balancing(results_od_balanced_values = 'mfhvydis', 
                                od_values_to_balance = 'mfhvyimp', 
                                origin_totals = 'mohtprof', 
                                destination_totals = 'mdhtattf', 
                                constraint_by_zone_destinations = '1-' + str(HIGH_STATION), 
                                constraint_by_zone_origins = '1-' + str(HIGH_STATION))

def calculate_daily_trips():
    #Calculate Daily OD trips:
    #The distribution matrices (e.g. 'mflgtdis') are in PA format. Need to convert to OD format by transposing
    my_project.matrix_calculator(result = 'mflgtod', expression = '0.5*mflgtdis + 0.5*mflgtdis'+ "'")
    my_project.matrix_calculator(result = 'mfmedod', expression = '0.5*mfmeddis + 0.5*mfmeddis'+ "'")
    my_project.matrix_calculator(result = 'mfhvyod', expression = '0.5*mfhvydis + 0.5*mfhvydis'+ "'")
    
    #convert annual external heavy truck trips to daily and add to heavy od:
    my_project.matrix_calculator(result = 'mfhvyod', 
                                 expression = 'mfhvyod + (mfreebee + mfreebei + mfreebie)/264')
    #apply vehicle-equivalency factors to medium and heavy trucks:
    my_project.matrix_calculator(result = 'mfmedod', expression = 'mfmedod * 1.5')
    my_project.matrix_calculator(result = 'mfhvyod', expression = 'mfhvyod * 2')
    
    #apply time of day factors:
    
    truck_tod_factor_dict = json_to_dictionary('truck_tod_factor_dict')
    for tod in tod_list:
        for key, value in truck_tod_factor_dict.iteritems():
            my_project.matrix_calculator(result = 'mf' + tod[0] + key, 
                                         expression = value['daily_trips'] + '*' + value[tod])

def main():
    network_importer(my_project)
    my_project.delete_matrices("ALL")
    place_holder_scalar_matrix()
    create_origin_destination_matrices()
    create_scalar_matrices()
    create_full_matrices()
    import_emp_matrices()
    calc_total_households()
    truck_productions()
    truck_attractions()
    import_skims()
    balance_attractions()
    calculate_impedance()
    balance_matrices()
    calculate_daily_trips()
    skims_to_hdf5(my_project)

input_skims = json_to_dictionary('input_skims')
origin_destination_dict = json_to_dictionary('truck_matrices_dict')
truck_generation_dict = json_to_dictionary('truck_gen_calc_dict')
my_project = EmmeProject(truck_model_project)

if __name__ == "__main__":
    main()






