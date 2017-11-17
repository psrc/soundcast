
import pandas as pd
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
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.path.join(os.getcwd(),"scripts/trucks"))
sys.path.append(os.getcwd())
#os.chdir('D:\\soundcast_mode_choice\\soundcast')
from emme_configuration import *
from EmmeProject import *
#from truck_configuration import *


def init_dir(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.mkdir(directory)

def json_to_dictionary(dict_name):
    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/model/supplementals/',dict_name).replace("\\","/")
    my_dictionary = json.load(open(input_filename))
    return(my_dictionary)


# Help check current matrix ids and names in the bank
def matrix_name_list(my_project):
    for id in my_project.bank.matrices():
        print id, my_project.bank.matrix(id).name


# Create scalar matrices/initialize scalar matrices:
def create_scalar_matrices():
    for y in range(0, len(origin_destination_dict["Scalar_Matrices"])):
        my_project.create_matrix(origin_destination_dict['Scalar_Matrices'][y]['Name'], 
                                 origin_destination_dict['Scalar_Matrices'][y]['Description'], 
                                 'SCALAR')


# Creat origin and destination matrices
def create_origin_destination_matrices():
    for y in range (0, len(origin_destination_dict["Origin_Matrices"])):
        my_project.create_matrix(origin_destination_dict['Origin_Matrices'][y]['Name'],
                                 origin_destination_dict['Origin_Matrices'][y]['Description'], 
                                 'ORIGIN')
    for y in range (0, len(origin_destination_dict["Destination_Matrices"])):
        my_project.create_matrix(origin_destination_dict['Destination_Matrices'][y]['Name'],
                                 origin_destination_dict['Destination_Matrices'][y]['Description'], 
                                 'DESTINATION')


# Create full matrices:
def create_full_matrices():
    for y in range(0, len(origin_destination_dict["Full_Matrices"])):
        my_project.create_matrix(origin_destination_dict['Full_Matrices'][y]['Name'],
                                 origin_destination_dict['Full_Matrices'][y]['Description'], 
                                 'FULL')


# Create skim matrices: cost, time, distance, transit, bike, walk, park&ride
def create_skim_matrices():
    for y in range(0, len(origin_destination_dict["Skim_Matrices"])):
        my_project.create_matrix(origin_destination_dict['Skim_Matrices'][y]['Name'],
                                 origin_destination_dict['Skim_Matrices'][y]['Description'], 
                                 'FULL')

# Create terminal matrices:
def create_terminal_matrices():
    for y in range(0, len(origin_destination_dict["Terminal_Matrices"])):
        my_project.create_matrix(origin_destination_dict['Terminal_Matrices'][y]['Name'],
                                 origin_destination_dict['Terminal_Matrices'][y]['Description'], 
                                 'FULL')

         
# Initialize partitions
def create_ensembles_dict():
    ensembles = pd.read_csv(ensembles_path)
    ensembles_dict = {}
    i = 0
    for i in range(len(ensembles)):
        short_name = ensembles.iat[i, 0]
        file_name = 'inputs/scenario/supplemental/generation/ensembles/' + ensembles.iat[i, 1]
        ensembles_dict[short_name] = file_name
    return ensembles_dict

def initialize_process_zone_partition():
    ensembles_dict = create_ensembles_dict()
    for short_name, file_name in ensembles_dict.items():
        #print short_name
        #print file_name
        my_project.initialize_zone_partition(short_name)
        my_project.process_zone_partition(file_name)


# Reset utility to zero 
def reset_utility():
    utilities = ['euda', 'eus2', 'eus3', 'eutw', 'eutd', 'eubk', 'euwk', 'eusm', 'dabct', 's2bct', 's3bct']
    for u in utilities:
        my_project.matrix_calculator(result = u, expression = "0")


# Import data (skim data) from external database (1.31: IMPORT DATA FROM EXTERNAL DATABASE)
def load_skims(skim_file_loc, mode_name, divide_by_100=False):
    ''' Loads H5 skim matrix for specified mode. '''
    with h5py.File(skim_file_loc, "r") as f:
        skim_file = f['Skims'][mode_name][:]
    # Divide by 100 since decimals were removed in H5 source file through multiplication
    if divide_by_100:
        return skim_file.astype(float)/100.0
    else:
        return skim_file

# SKIM: bi-directional cost, distance, time;
def load_skim_data(np_matrix_name_input, np_matrix_name_output, TrueOrFalse):
    # get am and pm skim
    am_skim = load_skims('outputs/skims/7to8.h5', 
                         mode_name=np_matrix_name_input, 
                         divide_by_100=TrueOrFalse)
    pm_skim = load_skims('outputs/skims/17to18.h5', 
                         mode_name=np_matrix_name_input, 
                         divide_by_100=TrueOrFalse)

    # calculate the bi_dictional skim
    np_matrix_dic = {}
    np_matrix_dic[np_matrix_name_output] = (am_skim + pm_skim) * .5
    #print np_matrix_dic

    # import the final skim into emme bank
    for np_matrix_name_output, np_matrix in np_matrix_dic.iteritems():
        targeted_matrix = my_project.bank.matrix(np_matrix_name_output)
        targeted_matrix.set_numpy_data(np_matrix)
        #print my_project.bank.matrix(np_matrix_name_output).id


def get_cost_time_distance_skim_data():
    input_skim = {'hbw1' : {'cost' : {'svt' : 'svtl1c', 'h2v' : 'h2tl1c', 'h3v' : 'h3tl1c'}, 
                            'time' : {'svt' : 'svtl1t', 'h2v' : 'h2tl1t', 'h3v' : 'h3tl1t'}, 
                            'distance' : {'svt' : 'svtl1d', 'h2v' : 'h2tl1d', 'h3v' : 'h3tl1d'}},
                  'hbw2' : {'cost' : {'svt' : 'svtl2c', 'h2v' : 'h2tl2c', 'h3v' : 'h3tl2c'}, 
                            'time' : {'svt' : 'svtl2t', 'h2v' : 'h2tl2t', 'h3v' : 'h3tl2t'}, 
                            'distance' : {'svt' : 'svtl2d', 'h2v' : 'h2tl2d', 'h3v' : 'h3tl2d'}},
                  'hbw3' : {'cost' : {'svt' : 'svtl3c', 'h2v' : 'h2tl3c', 'h3v' : 'h3tl3c'}, 
                           'time' : {'svt' : 'svtl3t', 'h2v' : 'h2tl3t', 'h3v' : 'h3tl3t'}, 
                           'distance' : {'svt' : 'svtl3d', 'h2v' : 'h2tl3d', 'h3v' : 'h3tl3d'}},
                  'nhb' : {'cost' : {'svt' : 'svtl1c', 'h2v' : 'h2tl1c', 'h3v' : 'h3tl1c'}, 
                           'time' : {'svt' : 'svtl1t', 'h2v' : 'h2tl1t', 'h3v' : 'h3tl1t'}, 
                           'distance' : {'svt' : 'svtl1d', 'h2v' : 'h2tl1d', 'h3v' : 'h3tl1d'}},
                  'hbo' : {'cost' : {'svt' : 'svtl1c', 'h2v' : 'h2tl1c', 'h3v' : 'h3tl1c'}, 
                           'time' : {'svt' : 'svtl1t', 'h2v' : 'h2tl1t', 'h3v' : 'h3tl1t'}, 
                           'distance' : {'svt' : 'svtl1d', 'h2v' : 'h2tl1d', 'h3v' : 'h3tl1d'}}} 
    output_skim = {'cost' : {'svt' : 'dabcs', 'h2v' : 's2bcs', 'h3v' : 's3bcs'}, 
                   'time' : {'svt' : 'dabtm', 'h2v' : 's2btm', 'h3v' : 's3btm'}, 
                   'distance' : {'svt' : 'dabds', 'h2v' : 's2bds', 'h3v' : 's3bds'}}
    
    for skim_name in ['cost', 'time', 'distance']:
        for sov_hov in ['svt', 'h2v', 'h3v']:
            #print sov_hov
            if skim_name == 'cost':
                load_skim_data(input_skim[trip_purpose][skim_name][sov_hov],
                               output_skim[skim_name][sov_hov], True)
            else:
                load_skim_data(input_skim[trip_purpose][skim_name][sov_hov], 
                               output_skim[skim_name][sov_hov], True)



# calculate full matrix terminal times
def get_terminal_skim_data():
        my_project.matrix_calculator(result = 'termti', expression = 'prodtt + attrtt' )



# Walk and Bike Skims emmebank
def load_walk_bike_skim_data(np_matrix_name_input, np_matrix_name_output, TrueOrFalse):
    np_matrix_dic = {}
    np_matrix_dic[np_matrix_name_output] = load_skims('outputs/skims/5to6.h5', 
                                                      mode_name=np_matrix_name_input, 
                                                      divide_by_100=TrueOrFalse)

    for np_matrix_name, np_matrix in np_matrix_dic.iteritems():
        targeted_matrix = my_project.bank.matrix(np_matrix_name_output)
        targeted_matrix.set_numpy_data(np_matrix)
        #print my_project.bank.matrix(np_matrix_name_output).id

def get_walk_bike_skim_data():
    walk_bike_skim_dict = {'walkt' : 'walkt', 'biket' : 'biket'}
    for input, output in walk_bike_skim_dict.iteritems():
        load_walk_bike_skim_data(input, output, True)



# Transit Skims emmebank
def load_transit_skim_data(np_matrix_name_input, np_matrix_name_output, TrueOrFalse):
    '''
    #auxwa_skim :?
    #iwtwa : First waiting time
    #brdwa : ?
    #nbdwa : ABs all mode
    #xfrwa : Transfer time
    #farbx : Ferry?
    #farwa : Ferry?
    np_matrix_dic = {}
    '''
    np_matrix_dic = {}

    if np_matrix_name_input in ['ivtwa', 'iwtwa', 'brdwa', 'nbdwa', 'xfrwa']:
        np_matrix_dic[np_matrix_name_input] = load_skims('outputs/skims/10to14.h5', 
                                                         mode_name= np_matrix_name_output, 
                                                         divide_by_100=TrueOrFalse) # Actual in vehicle time
   
    if np_matrix_name_input in ['farbx', 'farwa']:
        np_matrix_dic[np_matrix_name_input] = load_skims('outputs/skims/6to7.h5', 
                                                         mode_name= np_matrix_name_output, 
                                                         divide_by_100=TrueOrFalse)

    for np_matrix_name, np_matrix in np_matrix_dic.iteritems():
        targeted_matrix = my_project.bank.matrix(np_matrix_name)
        targeted_matrix.set_numpy_data(np_matrix)
        #print np_matrix_name, my_project.bank.matrix(np_matrix_name).id

def get_transit_skim_data():
    transit_skim_dict = {'ivtwa' : 'ivtwa', 
                         'iwtwa' : 'iwtwa', 
                         'brdwa' : 'iwtwa', 
                         'nbdwa' : 'ndbwa', 
                         'xfrwa' : 'xfrwa', 
                         'farwa' : 'mfafarps', 
                         'farbx' : 'mfafarbx'}
    for input, output in transit_skim_dict.iteritems():
        #print input, output
        load_transit_skim_data(input, output, True)



# Calculate Auto Cost
def calculate_auto_cost():
    input_paramas_vot_name = {'hbw1': {'svt': 'avot1v', 'h2v': 'avots2', 'h3v': 'avots3'},
                          'hbw2': {'svt': 'avot3v', 'h2v': 'avots2', 'h3v': 'avots3'},
                          'hbw3': {'svt': 'avot4v', 'h2v': 'avots2', 'h3v': 'avots3'},
                          'nhb': {'svt': 'mvotda', 'h2v': 'mvots2', 'h3v':'mvots3'},
                          'hbo': {'svt': 'mvotda', 'h2v': 'mvots2', 'h3v':'mvots3'}}
    output_auto_cost_name = {'svt': 'dabct', 'h2v': 's2bct', 'h3v': 's3bct'}

    # SOV
    my_project.matrix_calculator(result = output_auto_cost_name['svt'], 
                                          expression = '(mf"dabds"*' \
                                              + str(parameters_dict[trip_purpose]['global']['autoop']) + \
                                              ') + (mf"dabcs")/' \
                                              + str(parameters_dict[trip_purpose]['vot'][input_paramas_vot_name[trip_purpose]['svt']]) + \
                                              '+ (md"daily"/2)')
    #print output_auto_cost_name['svt'], input_paramas_vot_name[trip_purpose]['svt']

    # HOV 2 passenger               
    my_project.matrix_calculator(result = output_auto_cost_name['h2v'], 
                                          expression = '((mf"s2bds"*' \
                                              + str(parameters_dict[trip_purpose]['global']['autoop']) + \
                                              ') + (mf"s2bcs")/' \
                                              + str(parameters_dict[trip_purpose]['vot'][input_paramas_vot_name[trip_purpose]['h2v']]) + \
                                              '+ (md"daily"/2))/2')
    #print output_auto_cost_name['h2v'], input_paramas_vot_name[trip_purpose]['h2v']

    # HOV 3+ passengers
    my_project.matrix_calculator(result = output_auto_cost_name['h3v'], 
                                          expression = '((mf"s3bds"*' \
                                              + str(parameters_dict[trip_purpose]['global']['autoop']) + \
                                              ') + (mf"s3bcs")/' \
                                              + str(parameters_dict[trip_purpose]['vot'][input_paramas_vot_name[trip_purpose]['h3v']])+ \
                                              '+ (md"daily"/2))/3.5')
    #print output_auto_cost_name['h3v'], input_paramas_vot_name[trip_purpose]['h3v']




def calculate_mode():
    '''
    some submatrices restrictions:
    mode_choice.bat : %hightaz% %lowstation% %highstation% %lowpnr% %highpnr%
    %1%: 3700 - regional TAZ
    %2%: 3733 - external TAZ
    %3%: 3750 - external TAZ
    %4%: 3751 - PNR TAZ
    %5%: 4000 - PNR TAZ

    there are -e+21 values in the TAZ zone after 3751, it is because the ln(0)
    will come back fix it later
    '''
    
    #os.chdir(r'D:\\Angela\\soundcast_mode_choice')
    # Calculate Drive Alone Utility
    my_project.matrix_calculator(result = 'euda', 
                                     expression = 'exp(' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['autivt']) + \
                                         '*mf"dabtm" +'\
                                         + str(parameters_dict[trip_purpose]['modechoice']['autcos']) + \
                                         '* mf"dabct")',
                                     constraint_by_zone_origins = '1-3750', # 1, %3%
                                     constraint_by_zone_destinations = '1-3750') # 1, %3% 

    print 'euda done'
    # Calculate Shared Ride 2, 3+ Utility
    my_project.matrix_calculator(result = 'eus2', 
                                     expression = 'exp(' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['asccs2']) + '+' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['autivt']) + \
                                         '* mf"s2btm" + ' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['autcos']) + \
                                         '* mf"s2bct")',
                                     constraint_by_zone_origins = '1-3750', # 1, %3%
                                     constraint_by_zone_destinations = '1-3750') # 1, %3% 
    print 'eus2 done'
    my_project.matrix_calculator(result = 'eus3', 
                                     expression = 'exp('\
                                         + str(parameters_dict[trip_purpose]['modechoice']['asccs3']) + '+ ' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['autivt']) + \
                                         '* mf"s3btm" + ' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['autcos']) + \
                                         '* mf"s3bct")',
                                     constraint_by_zone_origins = '1-3750', # 1, %3%
                                     constraint_by_zone_destinations = '1-3750') # 1, %3% 
    print 'eus3 done'
    # Calculate Walk, drive to Transit Utility
    my_project.matrix_calculator(result = 'eutw', 
                                     expression = 'exp(' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['ascctw']) + '+' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['trwivt']) + \
                                         '* mf"ivtwa" +' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['trwovt']) + \
                                         '* (mf"auxwa"+mf"iwtwa"+mf"xfrwa") +' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['trwcos']) + \
                                         '* mf"farwa")',
                                     constraint_by_zone_origins = '1-3700', # 1, %1%
                                     constraint_by_zone_destinations = '1-3700') # 1, %1% 
    print 'eutw done'
    # Calculate  Walk, Bike Utility
    my_project.matrix_calculator(result = 'euwk', 
                                     expression = 'exp(' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['asccwk']) + '+'\
                                         + str(parameters_dict[trip_purpose]['modechoice']['walktm']) + \
                                         '* mf"walkt")',
                                     constraint_by_zone_origins = '1-3700', # 1, %1%
                                     constraint_by_zone_destinations = '1-3700') # 1, %1%
    print 'euwk done'
    my_project.matrix_calculator(result = 'eubk', 
                                     expression = 'exp(' + str(parameters_dict[trip_purpose]['modechoice']['asccbk']) + '+' \
                                         + str(parameters_dict[trip_purpose]['modechoice']['biketm']) + '*mf"biket")',
                                     constraint_by_zone_origins = '1-3700', # 1, %1%
                                     constraint_by_zone_destinations = '1-3700') # 1, %1%

    print 'eubk done'




# Calculate Mode Shares

def calculate_mode_shares():

    output_mode_share_name = {'hbw1': ['eusm', 'w1shda', 'w1shs2', 'w1shs3', 'w1shtw', 'w1shtd', 'w1shbk', 'w1shwk'],
                          'hbw2': ['eusm', 'w2shda', 'w2shs2', 'w2shs3', 'w2shtw', 'w2shtd', 'w2shbk', 'w2shwk'],
                          'hbw3': ['eusm', 'w3shda', 'w3shs2', 'w3shs3', 'w3shtw', 'w3shtd', 'w3shbk', 'w3shwk'],
                          'nhb': ['eusm', 'nhshda', 'nhshs2', 'nhshs3', 'nhshtw', 'nhshtd', 'nhshbk', 'nhshwk'],
                          'hbo': ['eusm', 'nwshda', 'nwshs2', 'nwshs3', 'nwshtw', 'nwshtd', 'nwshbk', 'nwshwk']}

    # Calculate the sum of utility: eusm
    my_project.matrix_calculator(result = output_mode_share_name[trip_purpose][0], 
                                     expression = 'mf"euda"+mf"eus2"+mf"eus3"+mf"eutw"+mf"eubk"+mf"euwk"')
    #print output_mode_share_name[trip_purpose][0]

    # Auto, shda
    my_project.matrix_calculator(result = output_mode_share_name[trip_purpose][1],
                                     expression = 'mf"euda"/mf"eusm"',
                                     constraint_by_value = {
                                         "interval_min": 0,
                                         "interval_max": 0.00000001,
                                         "condition": "EXCLUDE",
                                         "od_values": 'mf"eusm"'})
    #print output_mode_share_name[trip_purpose][1]

    # 2 passengers auto, shs2
    my_project.matrix_calculator(result = output_mode_share_name[trip_purpose][2], 
                                     expression = 'mf"eus2"/mf"eusm"',
                                     constraint_by_value = {
                                         "interval_min": 0,
                                         "interval_max": 0.00000001,
                                         "condition": "EXCLUDE",
                                         "od_values": 'mf"eusm"'})
    #print output_mode_share_name[trip_purpose][2]

    # 3 passenger auto, shs3
    my_project.matrix_calculator(result = output_mode_share_name[trip_purpose][3], 
                                     expression = 'mf"eus3"/mf"eusm"',
                                     constraint_by_value = {
                                         "interval_min": 0,
                                         "interval_max": 0.00000001,
                                         "condition": "EXCLUDE",
                                         "od_values": 'mf"eusm"'})
    #print output_mode_share_name[trip_purpose][3]

    # Transit to walk, shtw
    my_project.matrix_calculator(result = output_mode_share_name[trip_purpose][4], 
                                     expression = 'mf"eutw"/mf"eusm"',
                                     constraint_by_value = {
                                         "interval_min": 0,
                                         "interval_max": 0.00000001,
                                         "condition": "EXCLUDE",
                                         "od_values": 'mf"eusm"'})
    #print output_mode_share_name[trip_purpose][4]

    # Bike, shbk
    my_project.matrix_calculator(result = output_mode_share_name[trip_purpose][6], 
                                     expression = 'mf"eubk"/mf"eusm"',
                                     constraint_by_value = {
                                         "interval_min": 0,
                                         "interval_max": 0.00000001,
                                         "condition": "EXCLUDE",
                                         "od_values": 'mf"eusm"'})
    #print output_mode_share_name[trip_purpose][6]

    # Walk, shwk
    my_project.matrix_calculator(result = output_mode_share_name[trip_purpose][7], 
                                     expression = 'mf"euwk"/mf"eusm"',
                                     constraint_by_value = {
                                         "interval_min": 0,
                                         "interval_max": 0.00000001,
                                         "condition": "EXCLUDE",
                                         "od_values": 'mf"eusm"'})
    #print output_mode_share_name[trip_purpose][7]


# Validate, test the results 
def test_results():
    shda = my_project.bank.matrix('mf68').get_numpy_data()
    shs2 = my_project.bank.matrix('mf69').get_numpy_data()
    shs3 = my_project.bank.matrix('mf70').get_numpy_data()
    shtw = my_project.bank.matrix('mf71').get_numpy_data()
    shtd = my_project.bank.matrix('mf72').get_numpy_data()
    shbk = my_project.bank.matrix('mf73').get_numpy_data()
    shwk = my_project.bank.matrix('mf74').get_numpy_data()
    
    sum = shda + shs2 + shs3 + shtw + shtd +shbk + shwk
    error = 0
    for i in range(0,3868):
        for j in range(0, 3868):
            if sum[i][j] > 0.1 and sum[i][j] < 0.9:
               # every value should be very close to 1, so that means nothing would print out at this step.
               error += 1
    print 'there are', error, 'cells might have error.'


def mode_choice_to_h5(trip_purpose):
    output_mode_share_name = {'hbw1': ['eusm', 'w1shda', 'w1shs2', 'w1shs3', 'w1shtw', 'w1shtd', 'w1shbk', 'w1shwk'],
                          'hbw2': ['eusm', 'w2shda', 'w2shs2', 'w2shs3', 'w2shtw', 'w2shtd', 'w2shbk', 'w2shwk'],
                          'hbw3': ['eusm', 'w3shda', 'w3shs2', 'w3shs3', 'w3shtw', 'w3shtd', 'w3shbk', 'w3shwk'],
                          'nhb': ['eusm', 'nhshda', 'nhshs2', 'nhshs3', 'nhshtw',  'nhshbk', 'nhshwk'],
                          'hbo': ['eusm', 'nwshda', 'nwshs2', 'nwshs3', 'nwshtw',  'nwshbk', 'nwshwk']}

    #my_store = h5py.File('/outputs/supplemental/' + trip_purpose + '_ratio.h5', 'w')
    my_store = h5py.File(output_dir + '/' + trip_purpose + '_ratio.h5', "w")
    grp = my_store.create_group(trip_purpose)
    for mod in output_mode_share_name[trip_purpose]:
            mod_np = my_project.bank.matrix(mod).get_numpy_data()
            grp.create_dataset(mod, data = mod_np)
            print mod
    my_store.close()


def delete_matrices(my_project, matrix_type):
    for matrix in my_project.bank.matrices():
        if matrix.type == matrix_type:
            my_project.delete_matrix(matrix)

def main():
    #init_dir('outputs/supplemental/mode_choice')
    my_project.delete_matrices("ALL")
    create_scalar_matrices()
    print 'scalar done'
    create_origin_destination_matrices()
    print 'OD done'
    create_full_matrices()
    print 'full done'
    create_skim_matrices()
    print 'skim done'
    create_terminal_matrices()
    print 'terminal done'
    initialize_process_zone_partition()
    print 'initialize done'
    reset_utility()
    print 'reset utility done'

    get_cost_time_distance_skim_data()
    print 'get auto skim done'
    get_terminal_skim_data()
    print 'get terminal skim done'
    get_walk_bike_skim_data()
    print 'get walk bike skim done'
    get_transit_skim_data()
    print 'transit skim done'

    calculate_auto_cost()
    print 'calculate auto cost done'
    calculate_mode()
    print 'calculate mode done'
    calculate_mode_shares()
    print 'calculate mode shares done'

    test_results()
    mode_choice_to_h5(trip_purpose)
    print trip_purpose, 'is done'

my_project = EmmeProject(r'projects/Supplementals/Supplementals.emp')
origin_destination_dict = json_to_dictionary(r'supplemental_matrices_dict.txt')
parameters_dict = json_to_dictionary('parameters.json')
ensembles_path = r'inputs/scenario/supplemental/generation/ensembles/ensembles_list.csv'
#trip_purpose_list = ['hbw1', 'hbw2', 'hbw3', 'hbo', 'nhb']
#for trip_purp in trip_purpose_list:
#     trip_purpose = trip_purp
trip_purpose = 'hbo'

if __name__ == "__main__":
    main()


print 'end'



