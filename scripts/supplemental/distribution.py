import numpy as np
import pandas as pd
import h5py
import time
import gc
import os
import json
import shutil
from input_configuration import *

# Load external and special generator trips into dataframe
trip_table = pd.read_csv(trip_table_loc, index_col="index")
trip_table = pd.DataFrame(trip_table,dtype="float32")

# Load group quarters trips into dataframe
gq_trip_table = pd.read_csv(gq_trips_loc, index_col="index")
gq_trip_table = pd.DataFrame(gq_trip_table,dtype="float32")

def json_to_dictionary(dict_name):
    ''' Loads input files as dictionary '''
    input_filename = os.path.join('inputs/supplemental/',dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)

# Import JSON inputs
coeff = json_to_dictionary('gravity_model')
mode_dict = json_to_dictionary('mode_dict')
time_dict = json_to_dictionary('time_dict')
purp_tod_dict = json_to_dictionary('purp_tod_dict')
mode_list = ['svtl2', 'h2tl2', 'h3tl2', 'trnst', 'walk', 'bike']
time_periods = time_dict['svtl'].keys()

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

#def trips_by_tod(pro_dict_results, att_dict_results, trip_table_input):
#    ''' Multiply trip-type-TOD shares by original productions and attractions.
#        Returns dictionary of attractions by TOD and trip purpose. '''
#    for key, value in purp_tod_dict.items():
#        # Calculate productions by time of day
#        for tod in time_periods:
#            pro_dict_results[key][tod] = trip_table[key + 'pro'] * purp_tod_dict[key][tod]
#        gc.collect()
#    # Returns dictionary of productions by TOD and trip purpose
#    for key, value in purp_tod_dict.items():
#        # Calculate productions by time of day
#        for tod in time_periods:
#            att_dict_results[key][tod] = trip_table[key + 'att'] * purp_tod_dict[key][tod]
#        #gc.collect()

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
        for purpose in ['hbo', 'sch', 'wko', 'oto', 'col', 'hbw', 'hsp']:
            print purpose
            # Use the same shares for HBW trips (for all income groups)
            if purpose is 'hbw':
                for incomeclass in ['hw1', 'hw2', 'hw3', 'hw4']:
                    init_results[incomeclass] = mode_dict[key]['hbw'] * results[incomeclass]['trips']
            # all other trip types
            else:
                init_results[purpose] = mode_dict[key][purpose] * results[purpose]['trips']
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
        ext_spg.close()
        group_quarters.close()
        
def load_skims(trip_table, skim_file_loc, mode_name):
    #define_fric_factors
    skim_file = h5py.File(skim_file_loc, "r")
    skim = pd.DataFrame(skim_file['Skims'][mode_name][:len(trip_table)])/100
    skim = skim[[x for x in xrange(0,len(trip_table))]]
    return skim
    del skim_file

def crunch_the_numbers(trip_table, results_dir):
    # load skims
    cost_skim = load_skims(trip_table, skim_file_loc, mode_name='svtl1c')
    dist_skim = load_skims(trip_table, base_skim_file_loc, mode_name='svtl1d')
    pro_dict = create_empty_tod_dict()    # Hold all the TOD productions here for general trips
    att_dict = create_empty_tod_dict()    # all TOD attractions here
    trip_purps = purp_tod_dict.keys()
    tods = purp_tod_dict['col'].keys()
    friction_fac_dic = calc_fric_fac(trip_table, cost_skim, dist_skim)
    trip_table_dic = {}
    dist_tod_purp(trip_table_dic, trip_table, friction_fac_dic)
    del trip_table ; del friction_fac_dic
    dist_trips = fratar(trip_table_dic)
    # fill NA values with zero. This happens for some trip purposes that don't exist in group quarters
    for purp in dist_trips.keys():
        dist_trips[purp] = dist_trips[purp].fillna(0)        
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
    for dir in [ext_spg_dir, gq_directory]:
        if os.path.exists(dir):
            shutil.rmtree(dir)

if __name__ == "__main__":
    main()