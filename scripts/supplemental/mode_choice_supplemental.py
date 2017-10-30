
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
from emme_configuration import *
from EmmeProject import *



def init_dir(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.mkdir(directory)


def json_to_dictionary(dict_name):
    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/supplemental/',dict_name).replace("\\","/")
    my_dictionary = json.load(open(input_filename))
    return(my_dictionary)
         

def load_skims(skim_file_loc, mode_name, divide_by_100=False):
    ''' Loads H5 skim matrix for specified mode. '''
    with h5py.File(skim_file_loc, "r") as f:
        skim_file = f['Skims'][mode_name][:]
    # Divide by 100 since decimals were removed in H5 source file through multiplication
    if divide_by_100:
        return skim_file.astype(float)/100.0
    else:
        return skim_file


def load_skim_data(trip_purpose, np_matrix_name_input, TrueOrFalse):
    # get am and pm skim
    am_skim = load_skims(r'inputs\7to8.h5', 
                         mode_name=np_matrix_name_input, 
                         divide_by_100=TrueOrFalse)
    pm_skim = load_skims(r'inputs\17to18.h5', 
                         mode_name=np_matrix_name_input, 
                         divide_by_100=TrueOrFalse)

    # calculate the bi_dictional skim
    return (am_skim + pm_skim) * .5


def get_cost_time_distance_skim_data(trip_purpose):
    skim_dict = {}
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
            skim_dict[output_skim[skim_name][sov_hov]] = load_skim_data(trip_purpose, input_skim[trip_purpose][skim_name][sov_hov], True)
    
    return skim_dict


def get_walk_bike_skim_data():
    skim_dict = {}
    for skim_name in ['walkt', 'biket']:
        skim_dict[skim_name]= load_skims(r'inputs\5to6.h5', mode_name=skim_name, divide_by_100=True)
    return skim_dict


def get_transit_skim_data():
    transit_skim_dict = {'ivtwa' : 'ivtwa', 
                         'iwtwa' : 'iwtwa',  
                         'ndbwa' : 'ndbwa', 
                         'xfrwa' : 'xfrwa',
                         'auxwa' : 'auxwa',
                         'ivtwr' : 'ivtwr', 
                         'iwtwr' : 'iwtwr',  
                         'ndbwr' : 'ndbwr', 
                         'xfrwr' : 'xfrwr',
                         'auxwr' : 'auxwr', 
                         'farwa' : 'mfafarps', 
                         'farbx' : 'mfafarbx'}
    skim_dict = {}

    for input, output in transit_skim_dict.iteritems():
        if input in ['farbx', 'farwa']:
            skim_dict[input] = load_skims(r'inputs\6to7.h5', mode_name = output, divide_by_100=True)
        else:
            am_skim = load_skims(r'inputs\7to8.h5', mode_name = output, 
                             divide_by_100=True) 
            pm_skim = load_skims(r'inputs\17to18.h5', mode_name = output, 
                             divide_by_100=True)
            skim_dict[input] = (am_skim + pm_skim) *.5
  
    return skim_dict

def get_total_transit_time(tod):
    transit_component_list = ['ivtwr', 'auxwr', 'iwtwr', 'xfrwr']
    skims = {}
    for component in transit_component_list:
        skims[component] = load_skims('inputs/' + tod + '.h5', mode_name= component, 
                             divide_by_100=True) 

    return sum(skims.values())


def calculate_auto_cost(trip_purpose, auto_skim_dict, parking_cost_array):
    input_paramas_vot_name = {'hbw1': {'svt': 'avot1v', 'h2v': 'avots2', 'h3v': 'avots3'},
                          'hbw2': {'svt': 'avot3v', 'h2v': 'avots2', 'h3v': 'avots3'},
                          'hbw3': {'svt': 'avot4v', 'h2v': 'avots2', 'h3v': 'avots3'},
                          'nhb': {'svt': 'mvotda', 'h2v': 'mvots2', 'h3v':'mvots3'},
                          'hbo': {'svt': 'mvotda', 'h2v': 'mvots2', 'h3v':'mvots3'}}
    output_auto_cost_name = {'svt': 'dabct', 'h2v': 's2bct', 'h3v': 's3bct'}

    auto_cost_matrices = {}

    # SOV
    #'(mf"dabds"*16.75) + (mf"dabcs")/0.0496+ (md"daily"/2)'
    # Need to add parking cost
    auto_cost_matrices['dabct'] = (auto_skim_dict['dabds'] * parameters_dict[trip_purpose]['global']['autoop']) + auto_skim_dict['dabcs'] / parameters_dict[trip_purpose]['vot'][input_paramas_vot_name[trip_purpose]['svt']] + (parking_cost_array/2)
    #test = auto_cost_matrices['dabct'] + (parking_cost_array/2)
    # HOV 2 passenger   
    auto_cost_matrices['s2bct'] = ((auto_skim_dict['s2bds'] * parameters_dict[trip_purpose]['global']['autoop']) + auto_skim_dict['s2bcs'] / parameters_dict[trip_purpose]['vot'][input_paramas_vot_name[trip_purpose]['h2v']] + (parking_cost_array/2))/2 
                                    #'+ (md"daily"/2))/2')
    auto_cost_matrices['s3bct'] = ((auto_skim_dict['s3bds'] * parameters_dict[trip_purpose]['global']['autoop']) + auto_skim_dict['s3bcs'] / parameters_dict[trip_purpose]['vot'][input_paramas_vot_name[trip_purpose]['h3v']] + (parking_cost_array/2))/3.5
                                    #+ (md"daily"/2))/3.5')                                
   

    return auto_cost_matrices


def calculate_mode_shares(trip_purpose, mode_utilities_dict):

    output_mode_share = {}

    output_mode_share_name = {'hbw1': ['eusm', 'w1shda', 'w1shs2', 'w1shs3', 'w1shtw', 'w1shrw', 'w1shtd', 'w1shbk', 'w1shwk'],
                          'hbw2': ['eusm', 'w2shda', 'w2shs2', 'w2shs3', 'w2shtw', 'w2shrw', 'w2shtd', 'w2shbk', 'w2shwk'],
                          'hbw3': ['eusm', 'w3shda', 'w3shs2', 'w3shs3', 'w3shtw', 'w3shrw', 'w3shtd', 'w3shbk', 'w3shwk'],
                          'nhb': ['eusm', 'nhshda', 'nhshs2', 'nhshs3', 'nhshtw', 'nhshrw', 'nhshtd', 'nhshbk', 'nhshwk'],
                          'hbo': ['eusm', 'nwshda', 'nwshs2', 'nwshs3', 'nwshtw', 'nwshrw', 'nwshtd', 'nwshbk', 'nwshwk']}

    # Calculate the sum of utility: eusm
    output_mode_share[output_mode_share_name[trip_purpose][0]] = mode_utilities_dict['euda'] + mode_utilities_dict['eus2'] + mode_utilities_dict['eus3'] + mode_utilities_dict['eutw'] + mode_utilities_dict['eurw'] + mode_utilities_dict['eubk'] + mode_utilities_dict['euwk']
    
    # Auto, shda
    output_mode_share[output_mode_share_name[trip_purpose][1]] = mode_utilities_dict['euda']/output_mode_share['eusm']
    output_mode_share[output_mode_share_name[trip_purpose][1]][np.isnan(output_mode_share[output_mode_share_name[trip_purpose][1]])] = 0
    # 2 passengers auto, shs2
    output_mode_share[output_mode_share_name[trip_purpose][2]] = mode_utilities_dict['eus2']/output_mode_share['eusm']
    output_mode_share[output_mode_share_name[trip_purpose][2]][np.isnan(output_mode_share[output_mode_share_name[trip_purpose][2]])] = 0
    # 3 passenger auto, shs3
    output_mode_share[output_mode_share_name[trip_purpose][3]] = mode_utilities_dict['eus3']/output_mode_share['eusm']
    output_mode_share[output_mode_share_name[trip_purpose][3]][np.isnan(output_mode_share[output_mode_share_name[trip_purpose][3]])] = 0
    
    # Transit to walk, shtw
    output_mode_share[output_mode_share_name[trip_purpose][4]] = mode_utilities_dict['eutw']/output_mode_share['eusm']
    output_mode_share[output_mode_share_name[trip_purpose][4]][np.isnan(output_mode_share[output_mode_share_name[trip_purpose][4]])] = 0

    # Light Rail to walk, shtw
    output_mode_share[output_mode_share_name[trip_purpose][5]] = mode_utilities_dict['eurw']/output_mode_share['eusm']
    output_mode_share[output_mode_share_name[trip_purpose][5]][np.isnan(output_mode_share[output_mode_share_name[trip_purpose][5]])] = 0
    
    # Bike, shbk
    output_mode_share[output_mode_share_name[trip_purpose][7]] = mode_utilities_dict['eubk']/output_mode_share['eusm']
    output_mode_share[output_mode_share_name[trip_purpose][7]][np.isnan(output_mode_share[output_mode_share_name[trip_purpose][7]])] = 0
    # Walk, shwk
    output_mode_share[output_mode_share_name[trip_purpose][8]] = mode_utilities_dict['euwk']/output_mode_share['eusm']
    output_mode_share[output_mode_share_name[trip_purpose][8]][np.isnan(output_mode_share[output_mode_share_name[trip_purpose][8]])] = 0
    
    return output_mode_share

def test(taz):
    return zone_lookup_dict[taz]


def get_destination_parking_costs(parcel_file):
    parking_cost_array = np.zeros(len(zones))
    df = pd.read_csv(parcel_file, sep = ' ')
    df = df[df.PPRICDYP > 0]
    df1 = pd.DataFrame(df.groupby('TAZ_P').mean()['PPRICDYP'])
    df1.reset_index(inplace=True)
    df1['zone_index'] = df1.TAZ_P.apply(test)
    df1 = df1.set_index('zone_index')
    parking = df1['PPRICDYP']
    parking = parking.reindex([zone_lookup_dict[x] for x in zones])
    parking.fillna(0, inplace = True)
    return np.array(parking)





def calculate_mode_utilties(trip_purpose, auto_skim_dict, walk_bike_skim_dict, transit_skim_dict, auto_cost_dict):
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
    
    utility_matrices = {}
    
    # Calculate Drive Alone Utility
    utility_matrices['euda'] = np.exp(parameters_dict[trip_purpose]['modechoice']['autivt'] * auto_skim_dict['dabtm'] + parameters_dict[trip_purpose]['modechoice']['autcos'] * auto_cost_dict['dabct'])
    # rows, cols includes internal, externals, exclude p&rs
    zone_start_constraint = zone_lookup_dict[3751]
    utility_matrices['euda'][zone_start_constraint:] = 0
    utility_matrices['euda'][:, zone_start_constraint:] = 0
    print 'euda done'
    
    # Calculate Shared Ride 2 utility
    utility_matrices['eus2'] = np.exp(parameters_dict[trip_purpose]['modechoice']['asccs2'] + parameters_dict[trip_purpose]['modechoice']['autivt'] * auto_skim_dict['s2btm'] + parameters_dict[trip_purpose]['modechoice']['autcos'] * auto_cost_dict['s2bct'])
    # rows, cols includes internal, externals, exclude p&rs
    zone_start_constraint = zone_lookup_dict[3751]
    utility_matrices['eus2'][zone_start_constraint:] = 0
    utility_matrices['eus2'][:, zone_start_constraint:] = 0
    print 'eus2 done'

    # Calculate Shared Ride 3+ Utility
    utility_matrices['eus3'] = np.exp(parameters_dict[trip_purpose]['modechoice']['asccs3'] + parameters_dict[trip_purpose]['modechoice']['autivt'] * auto_skim_dict['s3btm'] + parameters_dict[trip_purpose]['modechoice']['autcos'] * auto_cost_dict['s3bct'])
    # rows, cols includes internal, externals, exclude p&rs
    zone_start_constraint = zone_lookup_dict[3751]
    utility_matrices['eus3'][zone_start_constraint:] = 0
    utility_matrices['eus3'][:, zone_start_constraint:] = 0
    print 'eus3 done'

    # Calculate Walk to Transit Utility
    utility_matrices['eutw'] = np.exp(parameters_dict[trip_purpose]['modechoice']['ascctw'] + parameters_dict[trip_purpose]['modechoice']['trwivt'] * transit_skim_dict['ivtwa'] + parameters_dict[trip_purpose]['modechoice']['trwovt'] * (transit_skim_dict['auxwa'] + transit_skim_dict["iwtwa"] + transit_skim_dict['xfrwa']) + parameters_dict[trip_purpose]['modechoice']['trwcos'] * transit_skim_dict['farwa'])
    # rows, cols includes internal, excludes extermal, p&rs (no walk, transit to external stations)
    zone_start_constraint = zone_lookup_dict[3733]
    utility_matrices['eutw'][zone_start_constraint:] = 0
    utility_matrices['eutw'][:, zone_start_constraint:] = 0
    print 'eutw done'

    # Calculate Walk to Light Rail Utility
    utility_matrices['eurw'] = np.exp(parameters_dict[trip_purpose]['modechoice']['ascctw'] + parameters_dict[trip_purpose]['modechoice']['trwivt'] * transit_skim_dict['ivtwr'] + parameters_dict[trip_purpose]['modechoice']['trwovt'] * (transit_skim_dict['auxwr'] + transit_skim_dict["iwtwr"] + transit_skim_dict['xfrwr']) + parameters_dict[trip_purpose]['modechoice']['trwcos'] * transit_skim_dict['farwa'])
    # rows, cols includes internal, excludes extermal, p&rs (no walk, transit to external stations)
    zone_start_constraint = zone_lookup_dict[3733]
    utility_matrices['eurw'][zone_start_constraint:] = 0
    utility_matrices['eurw'][:, zone_start_constraint:] = 0
    print 'eurw done'

    # keep best utility between regular transit and light rail. Give to light rail if there is a tie. 
    utility_matrices['eutw'][utility_matrices['eurw'] >= utility_matrices['eutw']] = 0
    utility_matrices['eurw'][utility_matrices['eutw'] > utility_matrices['eurw']] = 0

    # Calculate Walk Utility
    utility_matrices['euwk'] = np.exp(parameters_dict[trip_purpose]['modechoice']['asccwk'] + parameters_dict[trip_purpose]['modechoice']['walktm'] * walk_bike_skim_dict['walkt'])
    # rows, cols includes internal, excludes extermal, p&rs (no walk, transit to external stations)
    zone_start_constraint = zone_lookup_dict[3733]
    utility_matrices['euwk'][zone_start_constraint:] = 0
    utility_matrices['euwk'][:, zone_start_constraint:] = 0
    print 'euwk done'
    
    # Calculate Bike Utility
    utility_matrices['eubk'] = np.exp(parameters_dict[trip_purpose]['modechoice']['asccbk'] + parameters_dict[trip_purpose]['modechoice']['biketm'] * walk_bike_skim_dict['biket'])
    # rows, cols includes internal, excludes extermal, p&rs (no walk, transit to most external stations)
    zone_start_constraint = zone_lookup_dict[3733]
    utility_matrices['eubk'][zone_start_constraint:] = 0
    utility_matrices['eubk'][:, zone_start_constraint:] = 0
    print 'eubk done'

    return utility_matrices
    

def calculate_log_sum(trip_purpose):

    output_mode_share_name = {'hbw1': ['lsum1'],
                          'hbw2': ['lsum2'],
                          'hbw3': ['lsum3']}

    # Calculate the sum of utility: eusm
    my_project.matrix_calculator(result = output_mode_share_name[trip_purpose][0], 
                                     expression = 'ln(mf"euda"+mf"eus2"+mf"eus3"+mf"eutw"+mf"eubk"+mf"euwk")')
    

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


def mode_choice_to_h5(trip_purpose, mode_shares_dict):
    output_mode_share_name = {'hbw1': ['eusm', 'w1shda', 'w1shs2', 'w1shs3', 'w1shtw', 'w1shrw', 'w1shtd', 'w1shbk', 'w1shwk'],
                          'hbw2': ['eusm', 'w2shda', 'w2shs2', 'w2shs3', 'w2shtw', 'w2shrw', 'w2shtd', 'w2shbk', 'w2shwk'],
                          'hbw3': ['eusm', 'w3shda', 'w3shs2', 'w3shs3', 'w3shtw', 'w3shrw', 'w3shtd', 'w3shbk', 'w3shwk'],
                          'nhb': ['eusm', 'nhshda', 'nhshs2', 'nhshs3', 'nhshtw', 'nhshrw', 'nhshbk', 'nhshwk'],
                          'hbo': ['eusm', 'nwshda', 'nwshs2', 'nwshs3', 'nwshtw', 'nwshrw', 'nwshbk', 'nwshwk']}


    #my_store = h5py.File('/outputs/supplemental/' + trip_purpose + '_ratio.h5', 'w')
    my_store = h5py.File(output_dir + '/' + trip_purpose + '_ratio.h5', "w")
    grp = my_store.create_group(trip_purpose)
    for mode in output_mode_share_name[trip_purpose]:
            grp.create_dataset(mode, data = mode_shares_dict[mode])
            print mode
    my_store.close()

def urbansim_skims_to_h5(h5_name):
    atrtwa = get_total_transit_time('7to8')
    output_skims = ['lsum1', 'lsum2', 'lsum3']
    my_store = h5py.File(output_dir + '/' + h5_name + '.h5', "w")
    grp = my_store.create_group('skims')
    for skim in output_skims:
            skim_np = my_project.bank.matrix(skim).get_numpy_data()
            grp.create_dataset(skim, data = skim_np)
            print skim
    grp.create_dataset('atrtwa', data = atrtwa)
    my_store.close()


def main():
    #trip_purpose_list = ['hbw1', 'hbw2', 'hbw3']
    trip_purpose_list = ['hbo']

    for trip_purpose in trip_purpose_list:
        
        print trip_purpose
        
        auto_skim_dict = get_cost_time_distance_skim_data(trip_purpose)
        print 'get auto skim done'
        
        walk_bike_skim_dict = get_walk_bike_skim_data()
        print 'get walk bike skim done'
        
        transit_skim_dict = get_transit_skim_data()
        print 'transit skim done'

        parking_costs = get_destination_parking_costs(parcels_file_name)
        
        auto_cost_dict = calculate_auto_cost(trip_purpose, auto_skim_dict, parking_costs)
        print 'calculate auto cost done'
        
        mode_utilities_dict = calculate_mode_utilties(trip_purpose, auto_skim_dict, walk_bike_skim_dict, transit_skim_dict, auto_cost_dict)
        print 'calculate mode done'
        
        mode_shares_dict = calculate_mode_shares(trip_purpose, mode_utilities_dict)
        print 'calculate mode shares done'
       
        mode_choice_to_h5(trip_purpose, mode_shares_dict)
        print trip_purpose, 'is done'


       
my_project = EmmeProject(r'projects\Supplementals\Supplementals.emp')
zones = my_project.current_scenario.zone_numbers
#Create a dictionary lookup where key is the taz id and value is it's numpy index. 
zone_lookup_dict = dict((value,index) for index,value in enumerate(zones))
#origin_destination_dict = json_to_dictionary(r'supplemental_matrices_dict.txt')
parameters_dict = json_to_dictionary('parameters.json')
ensembles_path = r'inputs\supplemental\generation\ensembles\ensembles_list.csv'
parcels_file_name = 'inputs/accessibility/parcels_urbansim.txt'

if __name__ == "__main__":
    main()


print 'end'



