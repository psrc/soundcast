import numpy as np
import pandas as pd
import h5py
import time
import gc
import os
import json

skim_file_loc = 'R:/SoundCast/Inputs/2010/seed_skims/10to14.h5'
base_skim_file_loc = 'R:/SoundCast/Inputs/2010/seed_skims/7to8.h5'
trip_table_loc = 'outputs/prod_att.csv'
crosswalk_dict = 'D:/soundcast/soundcat/inputs/skim_params/demand_crosswalk_ab_4k_dictionary'
#hdf5_filename_dist = 'D:/soundcast/soundcat/test_h5_results.h5'

bal_iters = 1

# Define gravity model coefficients
autoop = 16.75    # Auto operation costs (in hundreds of cents per mile?)
avotda = 0.0303    # Load some VOT parameters for this...

coeff = {'col': -0.1382, 'hbo': -0.1423, 'sch': -0.2290,
         'hsp': -0.2223, 'wk1': -0.0858, 'wk2': -0.0775,
         'wk3': -0.0740, 'wk4': -0.0629, 'oto': -0.1493, 'wko': -0.0910}

mode_dict = {'svtl': {'hbw': 0.151087966, 'col': 0.005726962, 'sch': 0.00465709, 'hsp': 0.0591891, 
                     'hbo': 0.16576724, 'wko': 0.08090121, 'oto': 0.085479633},
             'h2tl': {'hbw': 0.012272062,'col': 0.000676537, 'sch': 0.016551551, 'hsp': 0.023584386,
                     'hbo': 0.11446058, 'wko': 0.011265124, 'oto': 0.063657389},
             'h3tl': {'hbw': 0.003068016, 'col': 0.000330402, 'sch': 0.024496924, 'hsp': 0.011029123,
                     'hbo': 0.105366667, 'wko': 0.004940292, 'oto': 0.055491748}}

# Need to update these values...
###
####
###

time_dict = {'svtl': {'5to6': 0.720, '6to7': 0.596, '7to8': 0.506, '8to9': 0.445,
                     '9to10': 0.510, '10to14': 0.513, '14to15': 0.487, '15to16': 0.426,
                     '16to17': 0.476, '17to18': 0.453, '18to20': 0.397, '20to5': 0.444},
             'h2tl': {'5to6': 0.101, '6to7': 0.141, '7to8': 0.191, '8to9': 0.183,
                     '9to10': 0.195, '10to14': 0.216, '14to15': 0.224, '15to16': 0.201,
                     '16to17': 0.202, '17to18': 0.200, '18to20': 0.238, '20to5': 0.252},
             'h3tl': {'5to6': 0.062, '6to7': 0.075, '7to8': 0.142, '8to9': 0.208,
                     '9to10': 0.150, '10to14': 0.140, '14to15': 0.146, '15to16': 0.224,
                     '16to17': 0.179, '17to18': 0.206, '18to20': 0.243, '20to5': 0.202}
             }

mode_list = ['svtl1', 'svtl2', 'svtl3', 'h2tl1', 'h2tl2', 'h2tl3', 'h3tl1', 'h3tl2', 'h3tl3']


             
# Trip purpose shares by time of day, from 2006 PSRC HH Survey
#####
####
### Fill this in...
##
#
#purp_tod_dict = {'hbw' : {'5to6': 0.04659, '6to7': 0.105994, '7to8': 0.1528, '8to9': 0.0963,
#                          '9to10': 0.039881, '10to14': 0.087311, '14to15': 0.059555, '16to17': 0.095013, 
#                          '17to18':0.122922, '18to20': 0.091353, '20to5': 0.0664118},
purp_tod_dict = {                 'col' : {'5to6': 0.0, '6to7': 0.0444, '7to8': 0.092063, '8to9': 0.119,
                          '9to10': 0.1063492, '10to14': 0.22381, '14to15': 0.060317, '15to16': 0.049,
                          '16to17': 0.065079, '17to18':0.073016, '18to20': 0.073016, '20to5': 0.093651}}
####
### Fill this in...
##
#

# Load trip table
trip_table = pd.read_csv(trip_table_loc)[:3700]
trip_table = pd.DataFrame(trip_table,dtype="float32")

# Allocate productions and attractions to times of day
pro_dict = purp_tod_dict    # Hold all the TOD productions here
att_dict = purp_tod_dict    # all TOD attractions here
trip_purps = purp_tod_dict.keys()
tods = purp_tod_dict['col'].keys()

time_periods = time_dict['svtl'].keys()

# Multiply trip-type-TOD shares by original productions and attractions
for key, value in pro_dict.iteritems():
    # Calculate productions by time of day
    for tod in time_periods:
        value[tod] *= trip_table[key + 'pro']
    gc.collect()
    # Returns dictionary of productions by TOD and trip purpose

for key, value in att_dict.iteritems():
    # Calculate productions by time of day
    for tod in time_periods:
        value[tod] *= trip_table[key + 'att']
    gc.collect()
    # Returns dictionary of productions by TOD and trip purpose

#### Develop friction factors
 #Using coefficients estimated for trip-based model
 #   Assuming impedance skims are from AM peak for home-based work and home-based college trips. 
 #   Off-peak costs are assumed for all other trips.
 #   Choosing 8to9 for AM peak and 10to14 for off-peak.
 #   Also assuming the skims are for SOVs. 


# Load skim container
skim_file = h5py.File(skim_file_loc, "r")
base_skim_file = h5py.File(base_skim_file_loc, "r")

# Access the cost and time skims
# import am non-hbw sov generalized cost skim matrix
# divide skims by 100 since they had previously been converted to remove decimals
cost_skim = pd.DataFrame(skim_file['Skims']['svtl1c'][:3700])/100
cost_skim = cost_skim[[x for x in xrange(0,3700)]]
time_skim = pd.DataFrame(skim_file['Skims']['svtl1t'][:3700])/100
time_skim = time_skim[[x for x in xrange(0,3700)]]
dist_skim = pd.DataFrame(base_skim_file['Skims']['svtl1d'][:3700])/100
dist_skim = dist_skim[[x for x in xrange(0,3700)]]

# Calculate friction factors for all trip purposes
friction_fac_dic = {}
for key, value in coeff.iteritems():
    friction_fac_dic[key] = np.exp((coeff[key])*(cost_skim[0:3700][0:3700] \
                                         + (dist_skim[0:3700][0:3700]*autoop*avotda)))
    gc.collect()
#### Distribute trips across each trip purpose and each time of day
# Convert to long form

trip_dict = {}
for key, value in friction_fac_dic.iteritems():
    trip_dict[key] = pd.DataFrame(value.unstack())
    trip_dict[key] = trip_dict[key].reset_index()
    trip_dict[key].columns = ['origin', 'destination','friction']
    trip_dict[key]['origin'] += 1 
    trip_dict[key]['destination'] += 1
    gc.collect()
# Create empty columns for processing and add to each trip table
df = pd.DataFrame(np.ones([len(trip_dict['hbo']),3]))
df = df.reset_index()    # Reindex
df.columns = ["index", "alpha", "beta", 'trips']
df = df[["alpha", "beta", 'trips']]

# Define productions and attractions
pro_dict = {} ; att_dict = {}
for key, value in friction_fac_dic.iteritems():
    pro_dict[key] = pd.DataFrame(trip_table[key + 'pro'][:3700])
    pro_dict[key].index = [i for i in xrange(1, 3700 + 1)]
    att_dict[key] = pd.DataFrame(trip_table[key + 'att'][:3700])
    att_dict[key].index = pro_dict[key].index
    gc.collect()
# Join productions, attractions, and friction factors by trip purpose
for key, value in trip_dict.iteritems():
    print 'Processing trip purpose: ' + str(key)
    trip_dict[key] = pd.DataFrame(trip_dict[key].join(df))
    print 'Joining productions for ' + str(key)
    trip_dict[key] = pd.DataFrame(trip_dict[key].join(pro_dict[key],'origin'))
    print 'Joining attractions for ' + str(key)
    trip_dict[key] = pd.DataFrame(trip_dict[key].join(att_dict[key],'destination'))
    # Rename columns 
    trip_dict[key].columns = ['origin', 'destination', 'friction', 'alpha', 'beta', 'trips', 'prod', 'attr']
    gc.collect()
# Clean up some dataframes...
del pro_dict ; del att_dict ; del df ; del skim_file ; del base_skim_file

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
    attdiff = np.abs(balatt[0:3700] - attr)
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

    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)

# Initialization

# Fratar
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

del df_0; del df1; del df2; del trip_dict
gc.collect()



#### Distribute across modes

final_results = {} ; trips_by_mode = {}
#final = {}
for key, value in mode_dict.iteritems():
    print key
    for purpose in ['hbo', 'sch', 'wko', 'oto', 'hbw', 'col']:
        print purpose
        # Use the same shares for HBW trips (for all income groups)
        if purpose == 'hbw':
            for incomeclass in ['wk1', 'wk2', 'wk3', 'wk4']:
                final_results[purpose] = mode_dict[key]['hbw'] * results[incomeclass]['trips']
                #print str(incomeclass) + ' final results = ' + str(final_results[key][0]) 
        # all other trip types
        else:
            final_results[purpose] = mode_dict[key][purpose] * results[purpose]['trips']
        print final_results[purpose][0]
    # sum purposes across modes
    trips_by_mode[key] = pd.DataFrame(sum([final_results[x] for x in final_results]))
    gc.collect()

del final_results ; del results
 
# Distribute trips across times of day
tod_df = {} ; trips_by_tod = {}
for key, value in time_dict.iteritems():
    for tod in time_periods:
        tod_df[tod] = trips_by_mode[key] * time_dict[key][tod]
    trips_by_tod[key] = tod_df

# Distribute across income classes
# see demand_crosswalk_ab_4k_dictionary.json

crosswalk = json_to_dictionary(crosswalk_dict)
#### Save as an H5 container
# Assume that all trips are toll class? or no toll?

df_final = {} ; df_inner = {}
for key, value in crosswalk.iteritems():
    if key not in mode_list:
        pass
    else:
        for tod in time_periods:
            df_inner[tod] = trips_by_tod[key[0:4]][tod]*value['FirstTripBasedFactor']
        df_final[key] = df_inner

# Convert back to matrix format???

# Write results out to H5 format
my_store = h5py.File(hdf5_filename_dist, "w-")
my_store.create_dataset('test',data=df_final['svtl1']['5to6'])
my_store.close()