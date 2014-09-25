import numpy as np
import pandas as pd
import h5py
import time
import gc
import os
import json
import shutil

# Load external and special generator trips into dataframe
trip_table = pd.read_csv(trip_table_loc, index_col="index")
trip_table = pd.DataFrame(trip_table,dtype="float32")

# Load group quarters trips into dataframe
gq_trip_table = pd.read_csv(gq_trips_loc, index_col="index")
gq_trip_table = pd.DataFrame(gq_trip_table,dtype="float32")

# Iterations for fratar process in trip distribution
bal_iters = 5

# Load in JSON inputs

# Define gravity model coefficients
autoop = 16.75    # Auto operation costs (in hundreds of cents per mile?)
avotda = 0.0303    # VOT

coeff = {'col': -0.1382, 'hbo': -0.1423, 'sch': -0.2290,
         'hsp': -0.2223, 'hw1': -0.0858, 'hw2': -0.0775,
         'hw3': -0.0740, 'hw4': -0.0629, 'oto': -0.1493, 'wko': -0.0910}

mode_dict = {'svtl': {'hbw': 0.2733, 'col': 0.0104, 'sch': 0.0084, 'hsp': 0.1071, 
                     'hbo': 0.2999, 'wko': 0.1463, 'oto': 0.1546},
             'h2tl': {'hbw': 0.0506,'col': 0.0028, 'sch': 0.0683, 'hsp': 0.0973,
                     'hbo': 0.4721, 'wko': 0.0465, 'oto': 0.2625},
             'h3tl': {'hbw': 0.0150, 'col': 0.0016, 'sch': 0.1197, 'hsp': 0.0405,
                     'hbo': 0.5147, 'wko': 0.0241, 'oto': 0.2711},
             'trnst': {'hbw': 0.5410,'col': 0.0488, 'sch': 0.0433, 'hsp': 0.0405,
                     'hbo': 0.1543, 'wko': 0.1040, 'oto': 0.0681},
             'walk': {'hbw': 0.0601,'col': 0.0039, 'sch': 0.1006, 'hsp': 0.0752,
                     'hbo': 0.4157, 'wko': 0.1686, 'oto': 0.1759},
             'bike': {'hbw': 0.3756,'col': 0.0199, 'sch': 0.1169, 'hsp': 0.0510,
                     'hbo': 0.2799, 'wko': 0.0808, 'oto': 0.0759}}

time_dict = {'svtl': {'5to6': 0.720, '6to7': 0.596, '7to8': 0.506, '8to9': 0.445,
                     '9to10': 0.510, '10to14': 0.513, '14to15': 0.487, '15to16': 0.426,
                     '16to17': 0.476, '17to18': 0.453, '18to20': 0.397, '20to5': 0.444},
             'h2tl': {'5to6': 0.101, '6to7': 0.141, '7to8': 0.191, '8to9': 0.183,
                     '9to10': 0.195, '10to14': 0.216, '14to15': 0.224, '15to16': 0.201,
                     '16to17': 0.202, '17to18': 0.200, '18to20': 0.238, '20to5': 0.252},
             'h3tl': {'5to6': 0.062, '6to7': 0.075, '7to8': 0.142, '8to9': 0.208,
                     '9to10': 0.150, '10to14': 0.140, '14to15': 0.146, '15to16': 0.224,
                     '16to17': 0.179, '17to18': 0.206, '18to20': 0.243, '20to5': 0.202},
             'trnst': {'5to6': 0.070, '6to7': 0.129, '7to8': 0.083, '8to9': 0.053,
                     '9to10': 0.038, '10to14': 0.026, '14to15': 0.027, '15to16': 0.034,
                     '16to17': 0.059, '17to18': 0.067, '18to20': 0.029, '20to5': 0.022},
             'walk': {'5to6': 0.035, '6to7': 0.047, '7to8': 0.064, '8to9': 0.094,
                     '9to10': 0.093, '10to14': 0.099, '14to15': 0.106, '15to16': 0.103,
                     '16to17': 0.073, '17to18': 0.061, '18to20': 0.077, '20to5': 0.072},
             'bike': {'5to6': 0.011, '6to7': 0.012, '7to8': 0.014, '8to9': 0.018,
                     '9to10': 0.012, '10to14': 0.006, '14to15': 0.010, '15to16': 0.012,
                     '16to17': 0.010, '17to18': 0.014, '18to20': 0.014, '20to5': 0.008},
             }

mode_list = ['svtl2', 'h2tl2', 'h3tl2', 'trnst', 'walk', 'bike']


             
# Trip purpose shares by time of day, from 2006 PSRC HH Survey
purp_tod_dict = {'col' : {'5to6': 0.0, '6to7': 0.044, '7to8': 0.092, '8to9': 0.119,
                          '9to10': 0.106, '10to14': 0.224, '14to15': 0.060, '15to16': 0.049,
                          '16to17': 0.065, '17to18':0.073, '18to20': 0.073, '20to5': 0.094},
                 'sch' : {'5to6': 0.003, '6to7': 0.040, '7to8': 0.196, '8to9': 0.231,
                          '9to10': 0.039, '10to14': 0.070, '14to15': 0.126, '15to16': 0.201,
                          '16to17': 0.033, '17to18':0.039, '18to20': 0.017, '20to5': 0.006},
                 'hsp' : {'5to6': 0.002, '6to7': 0.009, '7to8': 0.017, '8to9': 0.021,
                          '9to10': 0.043, '10to14': 0.298, '14to15': 0.086, '15to16': 0.086,
                          '16to17': 0.095, '17to18':0.095, '18to20': 0.154, '20to5': 0.095},
                 'hbo' : {'5to6': 0.009, '6to7': 0.024, '7to8': 0.050, '8to9': 0.071,
                          '9to10': 0.060, '10to14': 0.199, '14to15': 0.058, '15to16': 0.079,
                          '16to17': 0.076, '17to18':0.091, '18to20': 0.158, '20to5': 0.125},
                 'wko' : {'5to6': 0.008, '6to7': 0.029, '7to8': 0.066, '8to9': 0.067,
                          '9to10': 0.062, '10to14': 0.330, '14to15': 0.078, '15to16': 0.090,
                          '16to17': 0.105, '17to18':0.091, '18to20': 0.055, '20to5': 0.019},
                 'oto' : {'5to6': 0.001, '6to7': 0.006, '7to8': 0.027, '8to9': 0.038,
                          '9to10': 0.054, '10to14': 0.355, '14to15': 0.094, '15to16': 0.102,
                          '16to17': 0.082, '17to18':0.074, '18to20': 0.106, '20to5': 0.060}}

def create_empty_tod_dict():
    ''' Create an empty dataset matching structure of purp_tod_dict '''
    key_dict = dict.fromkeys(purp_tod_dict.iterkeys(), 0 )
    value_dict = purp_tod_dict.fromkeys(purp_tod_dict['hbo'], 0)
    for key, value in key_dict.iteritems():
        key_dict[key] = value_dict
    return key_dict

def calc_beta(df):
    ''' Calculate beta balancing term. '''
    df = pd.DataFrame(df[['origin', 'destination', 'friction', 'alpha', 'beta', 'trips', 'prod', 'attr']])
    df['beta'] = df['alpha'] * df['prod'] * df['friction']
    sum_beta = df.groupby('destination')
    result = sum_beta.sum()['beta']
    result.name = 'betasum'
    df = df.join(result,'destination')
    df['beta'] = 1/df['betasum']
    # Calculate total trips
    df['trips'] = df['alpha']*df['prod']*df['beta']*df['attr']*df['friction']
    return df

def calc_alpha(df):
    ''' Calculate alpha balancing term. '''
    df = pd.DataFrame(df[['origin', 'destination', 'friction', 'alpha', 'beta', 'trips', 'prod', 'attr']])
    df['alpha'] = df['beta'] * df['attr'] * df['friction']
    sum_alpha = df.groupby('origin')
    result = sum_alpha.sum()['alpha']
    result.name = 'alphasum'
    df = df.join(result,'origin')
    df['alpha'] = 1/df['alphasum']
    # Calculate total trips
    df['trips'] = df['alpha']*df['prod']*df['beta']*df['attr']*df['friction']
    return df

def error_check(df):
    ''' General test for differences between total and distributed productions and attractions. '''
    balpro = df[['origin', 'trips']].groupby('origin')
    balpro = balpro.sum()['trips']
    balatt = df[['destination', 'trips']].groupby('destination')
    balatt = balatt.sum()['trips']
    # Calculate error
    prodiff = np.abs(balpro - prod)
    attdiff = np.abs(balatt[0:len(trip_table)] - attr)
    error = prodiff.sum() + attdiff.sum()
    return error

def emme_error(df1,df2):
    ''' Reports relative change in alpha and beta between iterations.'''
    alpha1 = df1['alpha']
    alpha2 = df2['alpha']
    beta1 = df1['beta']
    beta2 = df2['beta']

    # Calculate error
    alpha_error = np.abs(alpha2-alpha1)/alpha2
    beta_error = np.abs(beta2-beta1)/beta2
    error1 = pd.DataFrame(alpha_error) ; error2 = pd.DataFrame(beta_error)
    error = error1.join(error2)
    return error

def json_to_dictionary(dict_name):
    ''' Loads input files as dictionary '''
    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)

def trips_by_tod(pro_dict_results, att_dict_results, trip_table_input):
    ''' Multiply trip-type-TOD shares by original productions and attractions.
        Returns dictionary of attractions by TOD and trip purpose. '''
    for key, value in purp_tod_dict.items():
        # Calculate productions by time of day
        for tod in time_periods:
            pro_dict_results[key][tod] = trip_table[key + 'pro'] * purp_tod_dict[key][tod]
        gc.collect()
    # Returns dictionary of productions by TOD and trip purpose
    for key, value in purp_tod_dict.items():
        # Calculate productions by time of day
        for tod in time_periods:
            att_dict_results[key][tod] = trip_table[key + 'att'] * purp_tod_dict[key][tod]
        #gc.collect()

def calc_fric_fac(trip_table, cost_skim, dist_skim):
    ''' Calculate friction factors for all trip purposes '''
    friction_fac_dic = {}
    for key, value in coeff.iteritems():
        friction_fac_dic[key] = np.exp((coeff[key])*(cost_skim[0:len(trip_table)][0:len(trip_table)] \
                                             + (dist_skim[0:len(trip_table)][0:len(trip_table)]*autoop*avotda)))
        gc.collect()
    return friction_fac_dic

def dist_tod_purp(trip_table_dic, trip_table, friction_fac_dic):
    ''' Distribute trips across each trip purpose and each time of day '''
    trip_dict = {}
    for key, value in friction_fac_dic.iteritems():
        trip_table_dic[key] = pd.DataFrame(value.unstack())    # Convert to long form
        trip_table_dic[key] = trip_table_dic[key].reset_index()
        trip_table_dic[key].columns = ['origin', 'destination','friction']
        trip_table_dic[key]['origin'] += 1 
        trip_table_dic[key]['destination'] += 1
        gc.collect()

    # Store index for converting back to matrix form 
    global origin_dest_index
    origin_dest_index = pd.DataFrame(trip_table_dic['hbo'][['origin','destination']])

    # Create empty columns for processing and add to each trip table
    df = pd.DataFrame(np.ones([len(trip_table_dic['hbo']),3]))
    df = df.reset_index()    # Reindex
    df.columns = ["index", "alpha", "beta", 'trips']
    df = df[["alpha", "beta", 'trips']]

    # Define productions and attractions
    pro_dict = {} ; att_dict = {}
    for key, value in friction_fac_dic.iteritems():
        pro_dict[key] = pd.DataFrame(trip_table[key + 'pro'])
        pro_dict[key].index = [i for i in xrange(1, len(trip_table) + 1)]
        att_dict[key] = pd.DataFrame(trip_table[key + 'att'])
        att_dict[key].index = pro_dict[key].index
        gc.collect()
    # Join productions, attractions, and friction factors by trip purpose
    for key, value in trip_table_dic.iteritems():
        print 'Processing trip purpose: ' + str(key)
        trip_table_dic[key] = pd.DataFrame(trip_table_dic[key].join(df))
        print 'Joining productions for ' + str(key)
        trip_table_dic[key] = pd.DataFrame(trip_table_dic[key].join(pro_dict[key],'origin'))
        print 'Joining attractions for ' + str(key)
        trip_table_dic[key] = pd.DataFrame(trip_table_dic[key].join(att_dict[key],'destination'))
        # Rename columns 
        trip_table_dic[key].columns = ['origin', 'destination', 'friction', 'alpha', 'beta', 'trips', 'prod', 'attr']
        gc.collect()

    # Clean up some dataframes...
    del pro_dict ; del att_dict ; del df 


# Fratar
def fratar(trip_dict):
    iter = 0
    df_0 = {} ; df1 = {}; df2 = {}
    results = {}
    for key, value in trip_dict.iteritems():
        print 'Balancing trip purpose: ' + str(key)
        df_0[key] = pd.DataFrame(trip_dict[key], dtype="float32")
        df1[key] = pd.DataFrame(calc_alpha(df_0[key]), dtype="float32")
        df2[key] = pd.DataFrame(calc_beta(df1[key]), dtype="float32")
        for x in xrange(0,bal_iters):
            print "iteration " + str(x)
            df1[key] = pd.DataFrame(calc_beta(df2[key]), dtype="float32")
            #error = emme_error(df1[key],df2[key])
            #print error
            df2[key] = pd.DataFrame(calc_alpha(df1[key]), dtype="float32")
            #error = emme_error(df1[key],df2[key])
            #print error
            gc.collect()
        # Export the data and delete old DFs?
        results[key] = pd.DataFrame(df2[key],dtype="float32")

        del df2[key] ; del df1[key];
    return results
    # Clean up unused variables from memory
    del df_0; del df1; del df2; del trip_dict
    gc.collect()

def dist_by_mode(results):
    ''' Distribute trips across modes '''
    init_results = {} ; trips_by_mode = {}
    #final = {}
    for key, value in mode_dict.iteritems():
        print key
        for purpose in ['hbo', 'sch', 'wko', 'oto', 'col']:
            print purpose
            # Use the same shares for HBW trips (for all income groups)
            if purpose == 'hbw':
                for incomeclass in ['hw1', 'hw2', 'hw3', 'hw4']:
                    init_results[purpose] = mode_dict[key]['hbw'] * results[incomeclass]['trips']
                    #print str(incomeclass) + ' final results = ' + str(final_results[key][0]) 
            # all other trip types
            else:
                init_results[purpose] = mode_dict[key][purpose] * results[purpose]['trips']
            print init_results[purpose][0]
        # sum purposes across modes
        trips_by_mode[key] = pd.DataFrame(sum([init_results[x] for x in init_results]))
        gc.collect()
    return trips_by_mode 
    del init_results ; del results
 
def dist_by_tod(trips_by_mode):
    ''' Distribute trips across times of day '''
    tod_df = {} ; trips_by_tod = {}
    for key, value in time_dict.iteritems():
        for tod in time_periods:
            tod_df[tod] = trips_by_mode[key] * time_dict[key][tod]
            print tod
        trips_by_tod[key] = tod_df
        tod_df = {}
        print key
    return trips_by_tod
    del trips_by_mode


# Reformat as matrix
def reformat_to_matrix(trips_by_tod):
    matrix_trips = {}; matrix_trips_inner = {}
    for key, value in trips_by_tod.iteritems():
        print key
        for tod in time_periods:
            print tod
            join_od_index = trips_by_tod[key][tod].join(origin_dest_index)
            matrix_trips_inner[tod] = join_od_index.pivot(index='origin', columns='destination', values='trips')
        matrix_trips[key] = matrix_trips_inner
        matrix_trips_inner = {}
    return matrix_trips
    del _matrix_trips_inner ; del trips_by_tod

def init_dir(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.mkdir(directory)

# Sort files with modes in TOD H5 containers
def export_to_hdf(matrix_trips, output_dir):
    tod_matrices = {} ; tod_matrices_inner = {}
    for tod in time_periods:
        print tod
        for key, value in matrix_trips.iteritems():
            print key
            tod_matrices_inner[key] = matrix_trips[key][tod]
        tod_matrices[tod] = tod_matrices_inner
        tod_matrices_inner = {}
        # Save result to H5 format
        my_store = h5py.File(output_dir + '/' + str(tod) + '.h5', "w-")
        for key, value in matrix_trips.iteritems():
            my_store.create_dataset(str(key), data=tod_matrices[tod][key])
        my_store.close()
    gc.collect()
    del tod_matrices ; del tod_matrices_inner; del matrix_trips

# Combine group quarters and special generators into single trip table
def combine_trips(output_dir):
    combined = {}
    # import H5 files
    for tod in purp_tod_dict['col'].keys():
        mode_result = {}
        # 
        my_store = h5py.File(output_dir + '/' + str(tod) + '.h5', "w-")
        # Loop through each TOD
        ext_spg = h5py.File('outputs/supplemental/ext_spg/' + str(tod) + '.h5', 'r')
        group_quarters = h5py.File('outputs/supplemental/group_quarters/' + str(tod) + '.h5', 'r')
        # Loop through each mode
        filtered = []
        for mode in mode_dict.keys():
            # Add placeholders to group quarters to make sure array sizes match
            empty_rows = len(ext_spg[mode]) - len(group_quarters[mode])
            # Append rows
            gq = np.array(np.append(group_quarters[mode][:],
                                    np.zeros([empty_rows,len(group_quarters[mode])]),
                                    axis=0))
            # Append columns
            gq = np.array(np.append(gq,
                                    np.zeros([len(ext_spg[mode]), empty_rows]),
                                    axis=1))
            filtered = np.empty_like(ext_spg[mode])
            # Add only special generator rows
            for key, value in SPECIAL_GENERATORS.iteritems():
                # Add rows
                filtered[value,:] = ext_spg[mode][value,:]
                # Add columns
                filtered[:,value] = ext_spg[mode][:,value]
                # Combine with group quarters array
                filtered += gq
            # Add only external rows and columns
            filtered[3700:][:] = ext_spg[mode][3700:][:]
            filtered[:][3700:] = ext_spg[mode][:][3700:]
            # Save mode result
            mode_result[mode] = filtered
            my_store.create_dataset(str(mode), data=mode_result[mode])
        #combined[tod] = mode_result
        my_store.close()
        
def load_skims(trip_table, skim_file_loc, mode_name):
    #define_fric_factors
    skim_file = h5py.File(skim_file_loc, "r")
    skim = pd.DataFrame(skim_file['Skims'][mode_name][:len(trip_table)])/100
    skim = skim[[x for x in xrange(0,len(trip_table))]]
    return skim
    del skim_file

def crunch_the_numbers(trip_table, results_dir):
    time_periods = time_dict['svtl'].keys()
    # load skims
    cost_skim = load_skims(trip_table, skim_file_loc, mode_name='svtl1c')
    dist_skim = load_skims(trip_table, base_skim_file_loc, mode_name='svtl1d')
    ## Allocate productions and attractions to times of day
    pro_dict = create_empty_tod_dict()    # Hold all the TOD productions here for general trips
    att_dict = create_empty_tod_dict()    # all TOD attractions here
    trip_purps = purp_tod_dict.keys()
    tods = purp_tod_dict['col'].keys()
    trips_by_tod(pro_dict, att_dict, trip_table)
    friction_fac_dic = calc_fric_fac(trip_table, cost_skim, dist_skim)
    trip_table_dic = {}
    dist_tod_purp(trip_table_dic, trip_table, friction_fac_dic)
    del trip_table ; del friction_fac_dic
    dist_trips = fratar(trip_table_dic)
    del trip_table_dic
    by_mode_results = dist_by_mode(dist_trips)
    del dist_trips
    by_tod_results = dist_by_tod(by_mode_results)
    del by_mode_results
    reformatted = reformat_to_matrix(by_tod_results)
    del by_tod_results
    export_to_hdf(reformatted, results_dir)
    del reformatted

def main():
    # Initialize directory for storing HDF5 output
    for dir in [output_dir, ext_spg_dir, gq_directory]:
        init_dir(dir)

    # Create trip table for externals and special generators
    crunch_the_numbers(trip_table, results_dir = ext_spg_dir)

    # Create trip table for group quarters
    crunch_the_numbers(gq_trip_table, results_dir = gq_directory)

    # Combine external, special gen., and group quarters trips
    combine_trips(output_dir = 'outputs/supplemental/')

    # Clean up separate H5 files
    # Delete all but combined H5 files?

if __name__ == "__main__":
    main()

