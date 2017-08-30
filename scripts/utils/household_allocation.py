import pandas as pd
import h5py
import numpy as np
import random 

# move or add? If false, houeholds will be added to specified parcels, but not removed from existing locations. 
move_households = True

# new files go here
output_dir = 'R:/Stefan/test/'

# input hh and persons file:
hdf_file = h5py.File(r'R:\SoundCast\Inputs\2014\landuse\hh_and_persons.h5', "r")

# output hh and persons file- don't overwrite existing one!
out_h5_file = h5py.File(output_dir + 'hh_and_persons.h5', 'w')

# parcels:
parcel_df = pd.read_csv(r'R:\SoundCast\Inputs\2014\landuse\parcels_urbansim.txt', sep = ' ')

# data about where housholds are going and how many. Each dictionary in the list is seperate move or addition. 
allocation_list= [{'taz_id' : 8, 'parcel_ids':[1077182], 'number_of_households' : 200}, 
                  {'taz_id' : 4, 'parcel_ids' : [719138], 'number_of_households' : 200},
                  {'taz_id' : 29, 'parcel_ids' : [909899], 'number_of_households' : 200},
                  {'taz_id' : 34, 'parcel_ids' : [717498], 'number_of_households' : 200},
                  {'taz_id' : 15, 'parcel_ids' : [789545], 'number_of_households' : 200}]
                  

# a list of TAZs that households will NOT be drawn from 
taz_list = [i['taz_id'] for i in allocation_list]

def h5_to_df(h5_file, group_name):
    """
    Converts the arrays in a H5 store to a Pandas DataFrame. 

    """
    col_dict = {}
    h5_set = hdf_file[group_name]
    for col in h5_set.keys():
        my_array = np.asarray(h5_set[col])
        col_dict[col] = my_array
    df = pd.DataFrame(col_dict)
    return df


def df_to_h5(df, h5_store, group_name):
    """
    Stores DataFrame series as indivdual to arrays in an h5 container. 

    """
    # delete store store if exists   
    if group_name in h5_store:
        del h5_store[group_name]
        my_group = h5_store.create_group(group_name)
        print "Group Skims Exists. Group deleSted then created"
        #If not there, create the group
    else:
        my_group = h5_store.create_group(group_name)
        print "Group Skims Created"
    
    for col in df.columns:
        h5_store[group_name].create_dataset(col, data=df[col].values.astype('int32'))
      

def bootstrap(data, freq):
    """
    Generates a weighted reandom sample from data (DataFrame) using freq (DataFrame), which is 
    created by the get_sample_frequencies function. 
    
    Parameters
    ----------
    data : DataFrame, must have a column named 'class'
    freq: DataFrame, column 'class' contains the unique values/codes of the 'class' column in data. Column
        'nostoextract' contains the number of samples for coresponding class. 
    """
    freq = freq.set_index('class')

    # This function will be applied on each group of instances of the same
    # class in `data`.
    def sampleClass(classgroup):
        cls = classgroup['class'].iloc[0]
        nDesired = freq.nostoextract[cls]
        nRows = len(classgroup)

        nSamples = min(nRows, nDesired)
        return classgroup.sample(nSamples)

    samples = data.groupby('class').apply(sampleClass)

    # If you want a new index with ascending values
    # samples.index = range(len(samples))

    # If you want an index which is equal to the row in `data` where the sample
    # came from
    samples.index = samples.index.get_level_values(1)

    # If you don't change it then you'll have a multiindex with level 0
    # being the class and level 1 being the row in `data` where
    # the sample came from.

    return samples

def get_sample_frequencies(number_of_samples, data, field, taz_id_list = None):
    """
    Using 'number_of_samples', determines how many samples should be taken
    from each unique class in the 'field' column in the 'data' DataFrame. 
    
    Parameters
    ----------
    number_of_samples : The total number of samples to be drawn.
    data: The DataFrame containing the data to create the frequency table.
    field: the field that frequencies are calculated.
    taz_id_list: A list of TAZ's that for which frequencies will be based on. 
    """
    if taz_id_list:
        print 'here'
        data = data[data['hhtaz'].isin(taz_id_list)]
    df = pd.DataFrame(data[field].value_counts())
    df['nostoextract'] = df[field]/df[field].sum() * number_of_samples
    df['nostoextract'] = df['nostoextract'].round()
    df['nostoextract'] = df['nostoextract'].astype(int)
    df.index.name = 'class'
    df.reset_index(level = 0, inplace = True)
    return df

person_df = h5_to_df(hdf_file, 'Person')
hh_df = h5_to_df(hdf_file, 'Household')

# Creating a cross classification of income and household size, which is used as a sampling weight. 
income_bins = [-1, 15000, 30000, 60000, 100000, 9999999999] 
income_bins_labels =  range(1, len(income_bins)) 
income_bins_labels = [i * 100 for i in income_bins_labels]
hh_df['income_cat'] = pd.cut(hh_df['hhincome'], income_bins, labels=income_bins_labels)
hh_df['cross_class'] = hh_df['hhsize'] + hh_df['income_cat']
hh_df['class'] = hh_df['cross_class']


for hh_dict in allocation_list:
    # get thr frequency of the cross classifiation column used to weight the sample
    freq = get_sample_frequencies(hh_dict['number_of_households'], hh_df, 'cross_class', [hh_dict['taz_id']])
    # possible that the TAZ does not have all possible cross class combinations:
    hh_df2 = hh_df[hh_df['class'].isin(freq['class'])]
    # remove HHs that are in the TAZs we are moving to
    hh_df2 = hh_df2[~hh_df2['hhtaz'].isin(taz_list)]
    sample2 = bootstrap(hh_df2, freq)
    # randomly assign new parcel ids from the given list of ids
    sample2['hhparcel'] = np.random.choice(hh_dict['parcel_ids'], sample2.shape[0])
    # assign correct taz id
    sample2['hhtaz'] = hh_dict['taz_id']
    # update original hh_df
    if move_households:
        hh_df.loc[hh_df.index.isin(sample2.index), ['hhparcel', 'hhtaz']] = sample2[['hhparcel', 'hhtaz']]
        # nummber of households should be the same
        assert len(hh_df) == parcel_df.hh_p.sum()
        parcel = hh_dict['parcel_ids'][0]
        # hh_df should have more households at the parcel because they were moved there
        assert len(hh_df[hh_df.hhparcel==parcel]) > int(parcel_df[parcel_df.parcelid == parcel].hh_p) 
        print len(hh_df)
    else:
        print len(hh_df)
        hh_df = hh_df.append(sample2)
        # nummber of households should be the same
        assert len(hh_df) > parcel_df.hh_p.sum()
        parcel = hh_dict['parcel_ids'][0]
        # hh_df should have more households at the parcel because they were moved there
        assert len(hh_df[hh_df.hhparcel==parcel]) > int(parcel_df[parcel_df.parcelid == parcel].hh_p) 
        print len(hh_df)

hh_df.drop(['income_cat', 'class', 'cross_class'], axis=1, inplace=True)
hh_count = pd.DataFrame(hh_df['hhparcel'].value_counts())
hh_count = hh_count.rename(columns={'hhparcel' : 'count'})
hh_count['count'] = hh_count[['count']].astype('float64')
hh_count.index.name = 'hhparcel'
hh_count.reset_index(level = 0, inplace = True)

parcel_df['hh_p'] = 0
parcel_df = parcel_df.merge(hh_count, how = 'left', left_on='parcelid', right_on = 'hhparcel')
#parcel_df.loc[parcel_df.parcelid.isin(hh_count['hhparcel']), ['hh_p']] = hh_count[['count']]
parcel_df['hh_p'] = parcel_df['count']
parcel_df['hh_p'] = parcel_df['hh_p'].fillna(0)

# write out files:
parcel_df.drop(['count', 'hhparcel'], axis=1, inplace=True)
parcel_df.to_csv(output_dir + 'parcels_urbansim.txt', sep = ' ', index = False)
df_to_h5(hh_df, out_h5_file, 'Household')
df_to_h5(person_df, out_h5_file, 'Person')
out_h5_file.close()
print 'Done!'