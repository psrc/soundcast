import os, sys, math, h5py
import pandas as pd
from standard_summary_configuration import *

labels = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/variable_labels.csv'))
districts = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/district_lookup.csv'))
rgc_taz = pd.read_csv(r'scripts\summarize\inputs\rgc_taz.csv')

table_list = ['Household','Trip','Tour','Person','HouseholdDay','PersonDay']

overwrite = True

output_csv_list = ['hh_rgc','trip_rgc_homeloc','trip_rgc_dest']

def h5_to_df(h5file, table_list, name=False):
    """
    Load h5-formatted data based on a table list. Assumes heirarchy of a set of tables.
    """
    output_dict = {}
    
    for table in table_list:
        df = pd.DataFrame()
        for field in h5file[table].keys():
            df[field] = h5file[table][field][:]
            
        output_dict[table] = df
    
    if name:
        output_dict['name'] = name
    
    return output_dict

def add_row(df, row_name, description, value):
    df.ix[row_name,'description'] = description
    df.ix[row_name,'value'] = value
    
    return df

def apply_lables(h5data):
    '''
    Replace daysim formatted values with human readable lablels.
    '''
    for table in labels['table'].unique():
        df = labels[labels['table'] == table]
        for field in df['field'].unique():
            newdf = df[df['field'] == field]
            local_series = pd.Series(newdf['text'].values, index=newdf['value'])
            h5data[table][field] = h5data[table][field].map(local_series)
    
    return h5data

def hh(dataset):

	hh = dataset['Household']

	# Join RGC geography based on household TAZ location
	hh = pd.merge(hh,rgc_taz,left_on='hhtaz', right_on='taz')

	hh['income_bins'] = pd.cut(hh['hhincome'],bins=income_bins,labels=income_bin_labels)

	agg_fields = ['center','hhsize','income_bins','hhvehs','hownrent','hrestype']

	# Sums
	df = pd.DataFrame(hh.groupby(agg_fields).sum()['hhexpfac'])
	# df.reset_index(inplace=True)

	# average hhsize and hhvehs (weighted)
	hh['hhsize_wt'] = hh['hhsize'].astype('float')*hh['hhexpfac']
	hhsize_df = pd.DataFrame(hh.groupby(agg_fields).sum()['hhsize_wt']/hh.groupby(agg_fields).sum()['hhexpfac'])
	hhsize_df.rename(columns={0:'avg_hhsize'},inplace=True)
	df = df.join(hhsize_df)

	hh['hhvehs_wt'] = hh['hhvehs'].astype('float')*hh['hhexpfac']
	hhvehs_df = pd.DataFrame(hh.groupby(agg_fields).sum()['hhvehs_wt']/hh.groupby(agg_fields).sum()['hhexpfac'])
	hhvehs_df.rename(columns={0:'avg_hhvehs'},inplace=True)
	df = df.join(hhvehs_df)

	df = df.fillna(0)
	df = df.reset_index()

	# Join with rgc_taz to get lat and lon
	df = pd.merge(df, rgc_taz[['center','lat_1','lon_1']], on='center', how='left')

	df['source'] = dataset['name']

	return df

def trip(dataset, geog):

	trip = dataset['Trip']
	trip = trip[trip['travdist'] >= 0]
	person = dataset['Person']
	hh = dataset['Household']
	    
	# total trips
	# join with person file and rgc based on destination
	trip_person = pd.merge(trip,person,on=['hhno','pno'], how='left')
	trip_person = pd.merge(trip_person,hh,on='hhno',how='left')

	trip_person = pd.merge(trip_person,rgc_taz,left_on=geog, right_on='taz')

	trip_person['income_group'] = pd.cut(trip_person['hhincome'],
	    bins=income_bins,
	    labels=income_bin_labels)

	if 'sov_ff_time' in trip.columns:
		trip_person['delay'] = trip['travtime']-(trip['sov_ff_time']/100.0)

	# Tours by person type, purpose, mode, and destination district
	agg_fields = ['pptyp','dpurp','mode', 'center']
	trips_df = pd.DataFrame(trip_person.groupby(agg_fields)['trexpfac'].sum())

	# average trip distance and time (weighted)
	trip_person['travdist_wt'] = trip_person['travdist']*trip_person['trexpfac']
	trip_person['travtime_wt'] = trip_person['travtime']*trip_person['trexpfac']
	trip_person['travcost_wt'] = trip_person['travcost']*trip_person['trexpfac']
	if 'sov_ff_time' in trip.columns:
		trip_person['delay_wt'] = trip_person['delay']*trip_person['trexpfac']

	travdist_df = pd.DataFrame(trip_person.groupby(agg_fields).sum()['travdist_wt']/trip_person.groupby(agg_fields).sum()['trexpfac'])
	travdist_df.rename(columns={0:'travdist'},inplace=True)
	trips_df = trips_df.join(travdist_df)

	travtime_df = pd.DataFrame(trip_person.groupby(agg_fields).sum()['travtime_wt']/trip_person.groupby(agg_fields).sum()['trexpfac'])
	travtime_df.rename(columns={0:'travtime'},inplace=True)
	trips_df = trips_df.join(travtime_df)

	travcost_df = pd.DataFrame(trip_person.groupby(agg_fields).sum()['travcost_wt']/trip_person.groupby(agg_fields).sum()['trexpfac'])
	travcost_df.rename(columns={0:'travcost'},inplace=True)
	trips_df = trips_df.join(travcost_df)	    

	if 'sov_ff_time' in trip.columns:
	    travtime_df = pd.DataFrame(trip_person.groupby(agg_fields).sum()['delay_wt']/trip_person.groupby(agg_fields).sum()['trexpfac'])
	    travtime_df.rename(columns={0:'delay'},inplace=True)
	    trips_df = trips_df.join(travtime_df)
	else:
	    trips_df['delay'] = 0   

	trips_df = trips_df.reset_index()

	# add datasource field
	trips_df['source'] = dataset['name']

	trips_df = pd.merge(trips_df, rgc_taz[['center','lat_1','lon_1']], on='center', how='left')
    
	return trips_df

def process_dataset(h5file, scenario_name):
	# Load h5 data as dataframes
    dataset = h5_to_df(h5file, table_list=['Household','Trip','Tour','Person','HouseholdDay','PersonDay'], name=scenario_name)

    dataset = apply_lables(dataset)
    
    hh_df = hh(dataset)
    write_csv(hh_df,fname='hh_rgc.csv')

    # Trips based on location in regional center
    trip_df = trip(dataset, geog='hhtaz')
    write_csv(trip_df,fname='trip_rgc_homeloc.csv')

    # Trips based on destination location in regional center
    trip_df = trip(dataset, geog='dtaz')
    write_csv(trip_df,fname='trip_rgc_dest.csv')

def write_csv(df,fname):
    '''
    Write dataframe to file; append existing file
    '''
#     df.to_csv(os.path.join(output_dir,fname),mode='a')
    if not os.path.isfile(os.path.join(output_dir,fname)):

        df.to_csv(os.path.join(output_dir,fname),index=False)
    else: # append without writing the header
        df.to_csv(os.path.join(output_dir,fname), mode ='a', header=False, index=False)

if __name__ == '__main__':

    # Use root directory name as run name
    run_name = os.getcwd().split('\\')[-1]

    output_dir = r'outputs/rgc'

    comparison_run_dir = r'P:\Stefan\soundcast_20peak_2offpeak\outputs'

    h5_file_dict = {
        '2014': r'outputs/daysim_outputs.h5', 
        '2040_tolling': os.path.join(comparison_run_dir,'daysim_outputs.h5'),
        'survey': r'scripts/summarize/inputs/calibration/survey.h5'
                    }

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if overwrite:
	    for fname in output_csv_list:
	        if os.path.isfile(os.path.join(output_dir,fname+'.csv')):
	            os.remove(os.path.join(output_dir,fname+'.csv'))

	# Process all h5 files
    for name, file_dir in h5_file_dict.iteritems():

		daysim_h5 = h5py.File(file_dir)

		print 'processing h5: ' + name

		process_dataset(h5file=daysim_h5, scenario_name=name)
		del daysim_h5 # drop from memory to save space for next comparison