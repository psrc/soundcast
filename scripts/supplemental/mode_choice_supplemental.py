import pandas as pd
import numpy as np
import os,sys
import h5py
from sqlalchemy import create_engine
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
from emme_configuration import *
from EmmeProject import *

def load_skims(skim_file_loc, mode_name, divide_by_100=False):
    ''' Loads H5 skim matrix for specified mode. '''
    with h5py.File(skim_file_loc, "r") as f:
        skim_file = f['Skims'][mode_name][:]
    # Divide by 100 since decimals were removed in H5 source file through multiplication
    if divide_by_100:
        return skim_file.astype(float)/100.0
    else:
        return skim_file

def load_skim_data(trip_purpose, np_matrix_name_input, _divide_by_100=False):
    # get am and pm skim
    am_skim = load_skims(r'inputs\model\roster\7to8.h5', 
                         mode_name=np_matrix_name_input, 
                         divide_by_100=_divide_by_100)
    pm_skim = load_skims(r'inputs\model\roster\17to18.h5', 
                         mode_name=np_matrix_name_input, 
                         divide_by_100=_divide_by_100)

    # calculate the bi_dictional skim
    return (am_skim + pm_skim) * .5

def get_cost_time_distance_skim_data(trip_purpose):
    
    ### 
    ### FIXME: use a standard set of modes here; why do we change the names/
    ###
    
    skim_dict = {}
    input_skim = {'hbw1' : {'cost' : {'svt' : 'sov_inc1c', 'h2v' : 'hov2_inc1c', 'h3v' : 'hov3_inc1c'}, 
                            'time' : {'svt' : 'sov_inc1t', 'h2v' : 'hov2_inc1t', 'h3v' : 'hov3_inc1t'}, 
                            'distance' : {'svt' : 'sov_inc1d', 'h2v' : 'hov2_inc1d', 'h3v' : 'hov3_inc1d'}},
                  'hbw2' : {'cost' : {'svt' : 'sov_inc2c', 'h2v' : 'hov2_inc2c', 'h3v' : 'hov3_inc2c'}, 
                            'time' : {'svt' : 'sov_inc2t', 'h2v' : 'hov2_inc2t', 'h3v' : 'hov3_inc2t'}, 
                            'distance' : {'svt' : 'sov_inc2d', 'h2v' : 'hov2_inc2d', 'h3v' : 'hov3_inc2d'}},
                  'hbw3' : {'cost' : {'svt' : 'sov_inc3c', 'h2v' : 'hov2_inc3c', 'h3v' : 'hov3_inc3c'}, 
                           'time' : {'svt' : 'sov_inc3t', 'h2v' : 'hov2_inc3t', 'h3v' : 'hov3_inc3t'}, 
                           'distance' : {'svt' : 'sov_inc3d', 'h2v' : 'hov2_inc3d', 'h3v' : 'hov3_inc3d'}},
                  'nhb' : {'cost' : {'svt' : 'sov_inc1c', 'h2v' : 'hov2_inc1c', 'h3v' : 'hov3_inc1c'}, 
                           'time' : {'svt' : 'sov_inc1t', 'h2v' : 'hov2_inc1t', 'h3v' : 'hov3_inc1t'}, 
                           'distance' : {'svt' : 'sov_inc1d', 'h2v' : 'hov2_inc1d', 'h3v' : 'hov3_inc1d'}},
                  'hbo' : {'cost' : {'svt' : 'sov_inc1c', 'h2v' : 'hov2_inc1c', 'h3v' : 'hov3_inc1c'}, 
                           'time' : {'svt' : 'sov_inc1t', 'h2v' : 'hov2_inc1t', 'h3v' : 'hov3_inc1t'}, 
                           'distance' : {'svt' : 'sov_inc1d', 'h2v' : 'hov2_inc1d', 'h3v' : 'hov3_inc1d'}}} 
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
        skim_dict[skim_name]= load_skims(r'inputs\model\roster\5to6.h5', mode_name=skim_name, divide_by_100=True)
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
            skim_dict[input] = load_skims(r'inputs\model\roster\6to7.h5', mode_name = output, divide_by_100=True)
        else:
            am_skim = load_skims(r'inputs\model\roster\7to8.h5', mode_name = output, 
                             divide_by_100=True) 
            pm_skim = load_skims(r'inputs\model\roster\17to18.h5', mode_name = output, 
                             divide_by_100=True)
            skim_dict[input] = (am_skim + pm_skim) *.5
  
    return skim_dict

def calculate_auto_cost(trip_purpose, auto_skim_dict, parking_cost_array, parameters_df):
    input_paramas_vot_name = {'hbw1': {'svt': 'avot1v', 'h2v': 'avots2', 'h3v': 'avots3'},
                          'hbw2': {'svt': 'avot3v', 'h2v': 'avots2', 'h3v': 'avots3'},
                          'hbw3': {'svt': 'avot4v', 'h2v': 'avots2', 'h3v': 'avots3'},
                          'nhb': {'svt': 'mvotda', 'h2v': 'mvots2', 'h3v':'mvots3'},
                          'hbo': {'svt': 'mvotda', 'h2v': 'mvots2', 'h3v':'mvots3'}}
    output_auto_cost_name = {'svt': 'dabct', 'h2v': 's2bct', 'h3v': 's3bct'}

    auto_cost_matrices = {}

    # Auto operating cost is assumed same across auto modes (SOV, HOV2, HOV3+)
    auto_op_cost = parameters_df[(parameters_df['purpose'] == trip_purpose) & (parameters_df['variable'] == 'autoop')]['value'].values[0]

    # SOV
    auto_cost_matrices['dabct'] = auto_skim_dict['dabds'] * auto_op_cost + auto_skim_dict['dabcs'] 
    
    # HOV2; divide 2 to account for occupancy
    auto_cost_matrices['s2bct'] = (auto_skim_dict['s2bds'] * auto_op_cost + auto_skim_dict['s2bcs'])/2 
    
    # HOV3+; assuming average occupancy of 3.5                     
    auto_cost_matrices['s3bct'] = (auto_skim_dict['s3bds'] * auto_op_cost + auto_skim_dict['s3bcs'])/3.5
                                                                  
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

def taz_lookup(taz):
    return zone_lookup_dict[taz]

def get_destination_parking_costs(parcel_file, zones, zone_lookup_dict):
    parking_cost_array = np.zeros(len(zones))
    df = pd.read_csv(parcel_file, sep = ' ')
    df = df[df.PPRICDYP > 0]
    df1 = pd.DataFrame(df.groupby('TAZ_P').mean()['PPRICDYP'])
    df1.reset_index(inplace=True)
    df1['zone_index'] = df1.TAZ_P.apply(taz_lookup)
    df1 = df1.set_index('zone_index')
    parking = df1['PPRICDYP']
    parking = parking.reindex([zone_lookup_dict[x] for x in zones])
    parking.fillna(0, inplace = True)
    return np.array(parking)

def get_param(df, variable):
    """Return model parameter from df. """

    return df.loc[df['variable'] == variable, 'value'].values[0]

def clip_matrix(matrix, min_index, max_index):
    """ Fill matrix with zero values outside of prescribed bounds """

    trimmed_matrix = np.zeros_like(matrix)
    trimmed_matrix[min_index:max_index] = matrix[min_index:max_index]
                               
    return trimmed_matrix

def calculate_mode_utilties(trip_purpose, auto_skim_dict, walk_bike_skim_dict, transit_skim_dict, auto_cost_dict, params_df):

    utility_matrices = {}
    
    # Filter parameters for given trip purpose
    params_df = params_df[params_df['purpose'] == trip_purpose]

    # Calculate Drive Alone Utility
    utility_matrices['euda'] = np.exp(get_param(params_df, 'autivt') * auto_skim_dict['dabtm'] + \
        get_param(params_df, 'autcos') * auto_cost_dict['dabct'])
    utility_matrices['euda'] = clip_matrix(utility_matrices['euda'], 0, zone_lookup_dict[LOW_PNR])
    
    # Calculate Shared Ride 2 utility
    utility_matrices['eus2'] = np.exp(get_param(params_df, 'asccs2') + \
        get_param(params_df, 'autivt') * auto_skim_dict['s2btm'] + \
        get_param(params_df, 'autcos') * auto_cost_dict['s2bct'])
    utility_matrices['eus2'] = clip_matrix(utility_matrices['eus2'], 0, zone_lookup_dict[LOW_PNR])

    # Calculate Shared Ride 3+ Utility
    utility_matrices['eus3'] = np.exp(get_param(params_df, 'asccs3') + \
       get_param(params_df, 'autivt') * auto_skim_dict['s3btm'] + \
       get_param(params_df, 'autcos') * auto_cost_dict['s3bct'])
    utility_matrices['eus3'] = clip_matrix(utility_matrices['eus3'], 0, zone_lookup_dict[LOW_PNR])

    # Calculate Walk to Transit Utility
    ###
    ### FIXME: what's up with the iwtwa and xfrawa values without coefficients? Are those asserted to be one?
    ###
    utility_matrices['eutw'] = np.exp(get_param(params_df, 'ascctw') + \
        get_param(params_df, 'trwivt') * transit_skim_dict['ivtwa'] + \
        get_param(params_df, 'trwovt') * (transit_skim_dict['auxwa'] + \
        transit_skim_dict["iwtwa"] + \
        transit_skim_dict['xfrwa']) + \
        get_param(params_df, 'trwcos') * transit_skim_dict['farwa'])
    utility_matrices['eutw'] = clip_matrix(utility_matrices['eutw'], 0, zone_lookup_dict[MIN_EXTERNAL])

    # Calculate Walk to Light Rail Utility
        ###
    ### FIXME: what's up with the iwtwa and xfrawa values without coefficients? Are those asserted to be one?
    ###
    utility_matrices['eurw'] = np.exp(get_param(params_df, 'ascctw') + \
        get_param(params_df, 'trwivt') * transit_skim_dict['ivtwr'] + \
        get_param(params_df, 'trwovt') * (transit_skim_dict['auxwr'] + \
        transit_skim_dict["iwtwr"] + \
        transit_skim_dict['xfrwr']) + \
        get_param(params_df, 'trwcos') * transit_skim_dict['farwa'])
    utility_matrices['eurw'] = clip_matrix(utility_matrices['eurw'], 0, zone_lookup_dict[MIN_EXTERNAL])

    # keep best utility between regular transit and light rail. Give to light rail if there is a tie. 
    utility_matrices['eutw'][utility_matrices['eurw'] >= utility_matrices['eutw']] = 0
    utility_matrices['eurw'][utility_matrices['eutw'] > utility_matrices['eurw']] = 0

    # Calculate Walk Utility
    utility_matrices['euwk'] = np.exp(get_param(params_df, 'asccwk') + \
       get_param(params_df, 'walktm') * walk_bike_skim_dict['walkt'])
    utility_matrices['euwk'] = clip_matrix(utility_matrices['euwk'], 0, zone_lookup_dict[MIN_EXTERNAL])
    
    # Calculate Bike Utility
    utility_matrices['eubk'] = np.exp(get_param(params_df, 'asccbk') + \
       get_param(params_df, 'biketm') * walk_bike_skim_dict['biket'])
    utility_matrices['eubk'] = clip_matrix(utility_matrices['eubk'], 0, zone_lookup_dict[MIN_EXTERNAL])

    return utility_matrices
        
def mode_choice_to_h5(trip_purpose, mode_shares_dict, output_dir):
    output_mode_share_name = {'hbw1': ['eusm', 'w1shda', 'w1shs2', 'w1shs3', 'w1shtw', 'w1shrw', 'w1shtd', 'w1shbk', 'w1shwk'],
                          'hbw2': ['eusm', 'w2shda', 'w2shs2', 'w2shs3', 'w2shtw', 'w2shrw', 'w2shtd', 'w2shbk', 'w2shwk'],
                          'hbw3': ['eusm', 'w3shda', 'w3shs2', 'w3shs3', 'w3shtw', 'w3shrw', 'w3shtd', 'w3shbk', 'w3shwk'],
                          'nhb': ['eusm', 'nhshda', 'nhshs2', 'nhshs3', 'nhshtw', 'nhshrw', 'nhshbk', 'nhshwk'],
                          'hbo': ['eusm', 'nwshda', 'nwshs2', 'nwshs3', 'nwshtw', 'nwshrw', 'nwshbk', 'nwshwk']}

    my_store = h5py.File(output_dir + '/' + trip_purpose + '_ratio.h5', "w")
    grp = my_store.create_group(trip_purpose)
    for mode in output_mode_share_name[trip_purpose]:
            grp.create_dataset(mode, data = mode_shares_dict[mode])
            print(mode)
    my_store.close()

def main():

    output_dir = r'outputs/supplemental/'

    my_project = EmmeProject(r'projects\Supplementals\Supplementals.emp')
    zones = my_project.current_scenario.zone_numbers
    #Create a dictionary lookup where key is the taz id and value is it's numpy index. 
    global zone_lookup_dict
    zone_lookup_dict = dict((value,index) for index,value in enumerate(zones))

    conn = create_engine('sqlite:///inputs/db/soundcast_inputs.db')
    parameters_df = pd.read_sql('SELECT * FROM mode_choice_parameters', con=conn)
    parcels_file_name = r'inputs/scenario/landuse/parcels_urbansim.txt'

    trip_purpose_list = ['hbo']

    for trip_purpose in trip_purpose_list:
        
        auto_skim_dict = get_cost_time_distance_skim_data(trip_purpose)
        walk_bike_skim_dict = get_walk_bike_skim_data()
        transit_skim_dict = get_transit_skim_data()
        parking_costs = get_destination_parking_costs(parcels_file_name, zones, zone_lookup_dict)
        auto_cost_dict = calculate_auto_cost(trip_purpose, auto_skim_dict, parking_costs, parameters_df)
        mode_utilities_dict = calculate_mode_utilties(trip_purpose, auto_skim_dict, walk_bike_skim_dict, 
                                                      transit_skim_dict, auto_cost_dict, parameters_df)
        mode_shares_dict = calculate_mode_shares(trip_purpose, mode_utilities_dict)
        mode_choice_to_h5(trip_purpose, mode_shares_dict, output_dir)

if __name__ == "__main__":
    main()