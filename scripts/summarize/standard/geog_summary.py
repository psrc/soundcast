import os, sys, math, h5py
import pandas as pd
from standard_summary_configuration import *

labels = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/variable_labels.csv'))
districts = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/district_lookup.csv'))
county_taz = pd.read_csv(r'scripts/summarize/inputs/county_taz.csv')
rgc_taz = pd.read_csv(r'scripts/summarize/inputs/rgc_taz.csv')
lu = pd.read_csv(r'inputs/accessibility/parcels_urbansim.txt', sep=' ')
income_tiers = pd.read_csv(r'scripts/summarize/inputs/income_tiers.csv')

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

def hh(dataset, geog_file):
	"""
	geog_file: TAZ-based geography lookup, e.g., district, county, RGC
	"""

	hh = dataset['Household']

	# Join RGC geography based on household TAZ location
	hh = pd.merge(hh,geog_file,left_on='hhtaz', right_on='taz')

	hh['income_bins'] = pd.cut(hh['hhincome'],bins=income_bins,labels=income_bin_labels)

	agg_fields = ['geog_name','income_bins','hrestype']

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

	# Join with taz lookup to get lat and lon of desired geog_field
	geog_lat_lon = geog_file.groupby('geog_name').min()[['lat_1','lon_1']]
	geog_lat_lon.reset_index(inplace=True)
	df = pd.merge(df, geog_lat_lon, on='geog_name', how='left')

	df['source'] = dataset['name']

	return df

def trip(dataset, geog_file, geog_field):
	"""
	geog_file: TAZ-based geography lookup, e.g., district, county, RGC
	geog_field: join field, e.g., hhtaz to summarize trips for households in RGC or dtaz 
	            for trips ending in RGC
	"""

	trip = dataset['Trip']
	trip = trip[trip['travdist'] >= 0]
	person = dataset['Person']
	hh = dataset['Household']
	    
	# total trips
	# join with person file and rgc based on destination
	trip_person = pd.merge(trip,person,on=['hhno','pno'], how='left')
	trip_person = pd.merge(trip_person,hh,on='hhno',how='left')

	trip_person = pd.merge(trip_person,geog_file,left_on=geog_field, right_on='taz')

	# # Attach parking costs
	# if 'PARCEL_ID' in trip_person.columns:
	# 	trip_person = pd.merge(trip_person, lu[['PARCEL_ID','PPRICHRP']], left_on='dpcl', right_on='PARCEL_ID', how='left')
	# else:
	# 	trip_person = pd.merge(trip_person, lu[['parcel_id','pprichrp']], left_on='dpcl', right_on='parcel_id', how='left')

	# Calculate parking costs based on time at destination
	# trip_person['dur']	 = trip_person['endacttm']-trip_person['arrtm']
	# trip_person['park_cost'] = trip_person['PPRICHRP']*(trip_person['dur']/60)    # for drive modes only!

	trip_person['income_group'] = pd.cut(trip_person['hhincome'],
	    bins=income_bins,
	    labels=income_bin_labels)

	if 'sov_ff_time' in trip.columns:
		trip_person['delay'] = trip['travtime']-(trip['sov_ff_time']/100.0)

	# Tours by person type, purpose, mode, and destination district
	agg_fields = ['pptyp','dpurp','mode', 'geog_name','income_group']
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

	# Attach geog lookup
	geog_lat_lon = geog_file.groupby('geog_name').min()[['lat_1','lon_1']]
	geog_lat_lon.reset_index(inplace=True)
	df = pd.merge(trips_df, geog_lat_lon, on='geog_name', how='left')
    
	return trips_df

def person(dataset, geog_file, geog_field):

	trip = dataset['Trip']
	trip = trip[trip['travdist'] >= 0]
	person = dataset['Person']
	hh = dataset['Household']

	hh = pd.merge(hh, income_tiers, on='hhsize', how='left')
	hh['income_group'] = '0'
	hh.ix[hh['hhincome'] <= hh['income_threshold'], 'income_group'] = 'lower'
	hh.ix[hh['hhincome'] > hh['income_threshold'], 'income_group'] = 'higher'

	trip_person = pd.merge(trip,person,on=['hhno','pno'], how='left')
	trip_person = pd.merge(trip_person,hh,on='hhno',how='left')

	trip_person = pd.merge(trip_person,geog_file,left_on=geog_field, right_on='taz')

	if 'sov_ff_time' in trip.columns:
		trip_person['delay'] = trip['travtime']-(trip['sov_ff_time']/100.0)

	# Don't double count household travcost - only sum travcost for drive trips
	trip_person.ix[(trip_person.dorp != 1) & (trip_person['mode'].isin(['SOV','HOV2','HOV3+'])), 'travcost'] = 0

	# Total travel time, cost, and delay per person
	df = trip_person.groupby(['pno','hhno']).sum()[['travcost','delay','travtime']]
	df = df.reset_index()

	df = pd.merge(df, trip_person[['pno','hhno','geog_name','income_group','pptyp','hhincome']], on=['pno','hhno'], how='left')

	# Results by geography
	agg_fields = ['geog_name','income_group','pptyp']

	# Sums
	df = pd.DataFrame(df.groupby(agg_fields).mean()[['hhincome','travcost','travtime','delay']])

	df['source'] = dataset['name']

	return df

def costs(dataset, geog_file, geog_field):
	"""
	Calculate daily travel costs for each household
	"""

	trip = dataset['Trip']
	trip = trip[trip['travdist'] >= 0]
	person = dataset['Person']
	hh = dataset['Household']
	    
	# total trips
	# join with person file and rgc based on destination
	trip_person = pd.merge(trip,person,on=['hhno','pno'], how='left')
	trip_person = pd.merge(trip_person,hh,on='hhno',how='left')

	# trip_person = pd.merge(trip_person,geog_file,left_on=geog_field, right_on='taz')

	# hh['income_group'] = pd.cut(hh['hhincome'],
	#     bins=income_bins,
	#     labels=income_bin_labels)

	# Calculate low income as 200% of state povery level, which is based on hhsize
	hh = pd.merge(hh, income_tiers, on='hhsize', how='left')
	hh['income_group'] = '0'
	hh.ix[hh['hhincome'] <= hh['income_threshold'], 'income_group'] = 'lower'
	hh.ix[hh['hhincome'] > hh['income_threshold'], 'income_group'] = 'higher'

	if 'sov_ff_time' in trip.columns:
		trip_person['delay'] = trip['travtime']-(trip['sov_ff_time']/100.0)

	# Don't double count household travcost - only sum travcost for drive trips
	trip_person.ix[(trip_person.dorp != 1) & (trip_person['mode'].isin(['SOV','HOV2','HOV3+'])), 'travcost'] = 0

	# Total travcost for each household
	tot_by_hh = pd.DataFrame(trip_person.groupby('hhno').sum()[['travcost','travtime','delay']])
	tot_by_hh.reset_index(inplace=True)

	df = pd.merge(tot_by_hh, hh[['hhno','hhincome','income_group','hhtaz']], on='hhno')

	# calculate share of income spent on 
	# total weekday household travel

	# Replace income <= 1 with 1 to avoid negative and div/0
	df.ix[df['hhincome'] < 1, 'hhincome'] = 1

	df['travcost_inc_share'] = (df['travcost']*262)/df['hhincome']

	# Average of the daily total for each TAZ
	df = df.groupby(['hhtaz','income_group']).mean()[['travcost_inc_share','hhincome','travcost','travtime','delay']]
	df.reset_index(inplace=True)

	# Attach geog lookup
	# geog_lat_lon = geog_file.groupby('geog_name').min()
	# geog_lat_lon.reset_index(inplace=True)
	df = pd.merge(df, geog_file, left_on='hhtaz', right_on='taz', how='left')

	df['source'] = dataset['name']

	return df

def income(dataset, geog_file, geog_field):
	'''
	income distribution by geography
	'''
	trip = dataset['Trip']
	trip = trip[trip['travdist'] >= 0]
	person = dataset['Person']
	hh = dataset['Household']
	    
	# total trips
	# join with person file and rgc based on destination
	trip_person = pd.merge(trip,person,on=['hhno','pno'], how='left')
	trip_person = pd.merge(trip_person,hh,on='hhno',how='left')

	trip_person = pd.merge(trip_person,geog_file,left_on=geog_field, right_on='taz')

	# Attach parking costs
	# trip_person = pd.merge(trip_person, lu[['PARCEL_ID','PPRICHRP']], left_on='dpcl', right_on='PARCEL_ID', how='left')
	# trip_person = pd.merge(trip_person, lu[['parcel_id','pprichrp']], left_on='dpcl', right_on='parcel_id', how='left')

	# Calculate parking costs based on time at destination
	# trip_person['dur'] = trip_person['endacttm']-trip_person['arrtm']
	# trip_person['park_cost'] = trip_person['PPRICHRP']*(trip_person['dur']/60)    # for drive modes only!

	income_bins = [-99999999]+[i*10000 for i in xrange(21)]+[999999999]
	income_bin_labels = [str(i*10000) for i in xrange(21)]+['+']

	hh = pd.merge(hh, income_tiers, on='hhsize', how='left')
	hh['income_group'] = '0'
	hh.ix[hh['hhincome'] <= hh['income_threshold'], 'income_group'] = 'lower'
	hh.ix[hh['hhincome'] > hh['income_threshold'], 'income_group'] = 'higher'

	if 'sov_ff_time' in trip.columns:
		trip_person['delay'] = trip['travtime']-(trip['sov_ff_time']/100.0)

	# Sum of travel costs by household
	tot_by_hh = pd.DataFrame(trip_person.groupby('hhno').sum()[['travcost','travtime','delay']])
	tot_by_hh.reset_index(inplace=True)

	df = pd.merge(tot_by_hh, hh[['hhno','hhincome','income_group','hhtaz']], on='hhno')

	# Replace income <= 1 with 1 to avoid negative and div/0
	# df.ix[df['hhincome'] < 1, 'hhincome'] = 1

	# df['travcost_inc_share'] = (df['travcost']*262)/df['hhincome']

	# # Average 
	# df = df.groupby(['hhtaz','income_group']).mean()[['travcost_inc_share','hhincome','travcost']]
	# df.reset_index(inplace=True)

	# # Attach geog lookup
	# # geog_lat_lon = geog_file.groupby('geog_name').min()
	# # geog_lat_lon.reset_index(inplace=True)
	# df = pd.merge(df, geog_file, left_on='hhtaz', right_on='taz', how='left')

	df['source'] = dataset['name']

	return df

def landuse(landuse_file, fname):

	lu_df = pd.read_csv(landuse_file, sep=' ')

	if 'taz_p' in lu_df.columns:

		sums_df = lu_df.groupby('taz_p').sum()
		sums_df = sums_df.drop(['ppricdyp','pprichrp','xcoord_p','ycoord_p'], axis=1)
		sums_df.reset_index(inplace=True)

		means_df = lu_df.groupby('taz_p').mean()[['ppricdyp','pprichrp']]
		means_df.reset_index(inplace=True)

	else:

		sums_df = lu_df.groupby('TAZ_P').sum()
		sums_df = sums_df.drop(['PPRICDYP','PPRICHRP','XCOORD_P','YCOORD_P'], axis=1)
		sums_df.reset_index(inplace=True)

		means_df = lu_df.groupby('TAZ_P').mean()[['PPRICDYP','PPRICHRP']]
		means_df.reset_index(inplace=True)

	df = pd.merge(sums_df, means_df)

	df['source'] = fname

	return df

def process_dataset(h5file, scenario_name):
	# Load h5 data as dataframes
    dataset = h5_to_df(h5file, table_list=['Household','Trip','Tour','Person','HouseholdDay','PersonDay'], name=scenario_name)

    dataset = apply_lables(dataset)
    
    # hh_county = hh(dataset, geog_file=county_taz)
    # write_csv(hh_county,fname='hh_county.csv')

    # hh_rgc = hh(dataset, geog_file=rgc_taz)
    # write_csv(hh_rgc,fname='hh_rgc.csv')

    # # Trips based on location in regional center
    # trip_df = trip(dataset, geog_file=rgc_taz, geog_field='hhtaz')
    # write_csv(trip_df,fname='trip_rgc_homeloc.csv')

    # trip_df = trip(dataset, geog_file=county_taz, geog_field='hhtaz')
    # write_csv(trip_df,fname='trip_county_homeloc.csv')

    # # Trips based on destination location in regional center
    # trip_df = trip(dataset, geog_file=rgc_taz, geog_field='dtaz')
    # write_csv(trip_df,fname='trip_rgc_dest.csv')

    # trip_df = trip(dataset, geog_file=county_taz, geog_field='dtaz')
    # write_csv(trip_df,fname='trip_county_dest.csv')

    # TAZ Costs
    # df = costs(dataset, geog_file=county_taz, geog_field='hhtaz')
    # write_csv(df, fname='costs.csv')

    # df = income(dataset, geog_file=county_taz, geog_field='hhtaz')
    # write_csv(df, fname='income.csv')

    # Person totals
    df = person(dataset, geog_file=county_taz, geog_field='hhtaz')
    write_csv(df, fname='person_mean.csv')

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

    output_dir = r'outputs/geog'

    comparison_run_dir = r'D:\Brice\sc_real_income_2040'

    file_dict = {
        '2014': os.getcwd(), 
        '2040_tolling': os.path.join(comparison_run_dir),
                    }

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if overwrite:
	    for fname in os.listdir(output_dir):
	        if os.path.isfile(os.path.join(output_dir,fname)):
	            os.remove(os.path.join(output_dir,fname))

	# Process all h5 files
    for name, file_dir in file_dict.iteritems():

		daysim_h5 = h5py.File(os.path.join(file_dir,r'outputs/daysim_outputs.h5'))

		print 'processing h5: ' + name

		# process_dataset(h5file=daysim_h5, scenario_name=name)
		# del daysim_h5 # drop from memory to save space for next comparison

		df = landuse(landuse_file=os.path.join(file_dir,r'inputs/accessibility/parcels_urbansim.txt'), fname=name)
		write_csv(df, fname='landuse.csv')