import os, sys, shutil, math, h5py
import pandas as pd
sys.path.append(os.getcwd())
from standard_summary_configuration import *

labels = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/variable_labels.csv'))
districts = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/district_lookup.csv'))

table_list = ['Household','Trip','Tour','Person','HouseholdDay','PersonDay']

# look up psrc time of day 
tod_list = ['5to6','6to7','7to8','8to9','9to10','10to14','14to15','15to16','16to17','17to18','18to20']

tod_lookup = {  0:'20to5',
                1:'20to5',
                2:'20to5',
                3:'20to5',
                4:'20to5',
                5:'5to6',
                6:'6to7',
                7:'7to8',
                8:'8to9',
                9:'9to10',
                10:'10to14',
                11:'10to14',
                12:'10to14',
                13:'10to14',
                14:'14to15',
                15:'15to16',
                16:'16to17',
                17:'17to18',
                18:'18to20',
                19:'18to20',
                20:'18to20',
                21:'20to5',
                22:'20to5',
                23:'20to5',
                24:'20to5'}

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

def agg_measures(dataset):
    df = pd.DataFrame()

    # VMT per capita
    driver_trips = dataset['Trip'][dataset['Trip']['dorp'] == 1]
    vmt_per_cap = (driver_trips['travdist']*driver_trips['trexpfac']).sum()/dataset['Person']['psexpfac'].sum()
    df = add_row(df, row_name='vmt_per_cap', description='VMT per Person', value=vmt_per_cap)
    
    # Average trips per person
    trips_per_person = dataset['Trip']['trexpfac'].sum()/dataset['Person']['psexpfac'].sum()
    df = add_row(df, row_name='trips_per_person', description='Average Trips per Person', value=trips_per_person)

    # add datasource field
    df['source'] = dataset['name']
    
    return df

def household(dataset):
    
    hh = dataset['Household']
    agg_fields = ['hhsize','hhvehs','hhftw']
    hh_df = pd.DataFrame(hh.groupby(agg_fields)['hhexpfac'].sum())
    
    hh_df['source'] = dataset['name']
    
    return hh_df

def person(dataset):
    
    hh = dataset['Household']
    person = dataset['Person']

    person_hh = pd.merge(person, hh, on='hhno')

    # district_df = pd.DataFrame(district.groupby('district_name').min())
    person_hh = pd.merge(person_hh,districts[['taz','district_name']],left_on='hhtaz',right_on='taz', how='left')

    df = pd.DataFrame(person_hh.groupby(['pptyp','district_name']).sum()['psexpfac'])
    
    df['pptyp'] = df.index.get_level_values(0)
    df['district_name'] = df.index.get_level_values(1)
    
    districts_df = districts.groupby('district_name').min()[['lat_district','lon_district']]
    df.index = df['district_name']
    
    df = df.join(districts_df,how='left')
    df.reset_index(inplace=True,drop=True)
    
    df['source'] = dataset['name']
    
    return df

def person_day(dataset):
    
    # total number of persons by purpose and person type
    person = dataset['Person']
    personday = dataset['PersonDay']

    # join with person records to get person type
    df = pd.merge(person,personday,on=['hhno','pno'])

    # calculate weighted tours for each group
    purp_fields = ['wk','sc','es','pb','sh','ml','so']
    purp_dict = {'wk':'work', 'sc':'school', 'es':'escort','pb':'personal business','sh':'shop','ml':'meal','so':'social'}

    for field in purp_fields:
        df['wt_'+field] = df[field+'tours']*df['pdexpfac']

    df = pd.DataFrame(df.groupby('pptyp').sum()[['psexpfac','pdexpfac']+['wt_'+field for field in purp_fields]])
    for field in purp_fields:
        df[purp_dict[field]] = df['wt_'+field]/df['psexpfac']
        df.drop('wt_'+field,axis=1,inplace=True)

    df.drop(['psexpfac','pdexpfac'],axis=1,inplace=True)
    
    df = pd.DataFrame(df.stack())
    df.columns = ['values']
    df['pptyp'] = df.index.get_level_values(0)
    df['measure'] = df.index.get_level_values(1)
    df.reset_index(inplace=True,drop=True)
    
    df['source'] = dataset['name']
    
    return df

def tours(dataset, time_field):
    """
    Specify a time field to segment the data (e.g., 'tlvorig' for time left the origin)
    """
    
    tour = dataset['Tour']
    person = dataset['Person']
        
    # total tours
    # join with person file and district names based on destination
    tour_person = pd.merge(tour,person,on=['hhno','pno'])
    tour_person = pd.merge(tour_person,districts[['taz','district_name']],left_on='tdtaz',right_on='taz',how='left')
    
    # Convert time field to hour
    tour_person[time_field+'_hr'] = tour_person[time_field].apply(lambda row: int(math.floor(row/60)))

    # Calculate tour duration
    tour_person.ix[tour_person.tlvorig > tour_person.tarorig, 'tarorig'] = tour_person.ix[tour_person.tlvorig > tour_person.tarorig, 'tarorig']+1440
    tour_person['duration'] = tour_person.tarorig - tour_person.tlvorig
    
    # Tours by person type, purpose, mode, destination district, and time of day
    agg_fields = ['pptyp','pdpurp','tmodetp',time_field+'_hr','district_name']
    tours_df = pd.DataFrame(tour_person.groupby(agg_fields)['toexpfac'].sum())
    
    # average trip distance and time
    tours_df = tours_df.join(pd.DataFrame(tour_person.groupby(agg_fields)['tautodist'].mean()))
    tours_df = tours_df.join(pd.DataFrame(tour_person.groupby(agg_fields)['tautotime'].mean()))
    tours_df = tours_df.join(pd.DataFrame(tour_person.groupby(agg_fields)['duration'].mean()))
    # average trip 
    
    tours_df = tours_df.join(pd.DataFrame(person.groupby('pptyp').sum()['psexpfac']))
    
    # Add the district lat and lon values
    tours_df['pptyp'] = tours_df.index.get_level_values(0)
    tours_df['pdpurp'] = tours_df.index.get_level_values(1)
    tours_df['tmodetp'] = tours_df.index.get_level_values(2)
    tours_df[time_field+'_hr'] = tours_df.index.get_level_values(3)
    tours_df['district_name'] = tours_df.index.get_level_values(4)
    tours_df.reset_index(inplace=True, drop=True)

    district_df = districts.groupby('district_name').min()[['lat_district','lon_district']]
    district_df['district_name'] = district_df.index

    tours_df = pd.merge(tours_df,district_df)
    
    # add datasource field
    tours_df['source'] = dataset['name']
    
    return tours_df

def trips(dataset):
    
    trip = dataset['Trip']
    trip = trip[trip['travdist'] >= 0]
    person = dataset['Person']
    hh = dataset['Household']
        
    # total trips
    # join with person file and district names based on destination
    trip_person = pd.merge(trip,person,on=['hhno','pno'], how='left')

    # join with household to add income
    trip_person = pd.merge(trip_person, hh, on='hhno', how='left')
    
    trip_person['deptm_hr'] = trip_person['deptm'].apply(lambda row: int(math.floor(row/60)))

    trip_person['income_group'] = pd.cut(trip_person['hhincome'],
        bins=income_bins,
        labels=income_bin_labels)
    
    # Calcualte delay field
    if 'sov_ff_time' in trip.columns:
        trip_person['delay'] = trip['travtime']-(trip['sov_ff_time']/100.0)

    # Tours by person type, purpose, mode, and destination district
    agg_fields = ['pptyp','dpurp','mode','deptm_hr']
    trips_df = pd.DataFrame(trip_person.groupby(agg_fields)['trexpfac'].sum())
    
    # average trip distance, time, and delay (weighted)
    trip_person['travdist_wt'] = trip_person['travdist']*trip_person['trexpfac']
    trip_person['travtime_wt'] = trip_person['travtime']*trip_person['trexpfac']
    if 'sov_ff_time' in trip.columns:
        trip_person['delay_wt'] = trip_person['delay']*trip_person['trexpfac']

    travdist_df = pd.DataFrame(trip_person.groupby(agg_fields).sum()['travdist_wt']/trip_person.groupby(agg_fields).sum()['trexpfac'])
    travdist_df.rename(columns={0:'travdist'},inplace=True)
    trips_df = trips_df.join(travdist_df)

    travtime_df = pd.DataFrame(trip_person.groupby(agg_fields).sum()['travtime_wt']/trip_person.groupby(agg_fields).sum()['trexpfac'])
    travtime_df.rename(columns={0:'travtime'},inplace=True)
    trips_df = trips_df.join(travtime_df)

    if 'sov_ff_time' in trip.columns:
        travtime_df = pd.DataFrame(trip_person.groupby(agg_fields).sum()['delay_wt']/trip_person.groupby(agg_fields).sum()['trexpfac'])
        travtime_df.rename(columns={0:'delay'},inplace=True)
        trips_df = trips_df.join(travtime_df)
    else:
        trips_df['delay'] = 0
    
    # add datasource field
    trips_df['source'] = dataset['name']
    
    return trips_df

def taz_trips(dataset):
    """
    Trips based on otaz
    """
    trip = dataset['Trip']
    trip = trip[trip['travdist'] >= 0]
    person = dataset['Person']
    hh = dataset['Household']
        
    # total trips
    # join with person file and district names based on destination
    trip_person = pd.merge(trip,person,on=['hhno','pno'], how='left')

    # join with household to add income
    trip_person = pd.merge(trip_person, hh, on='hhno', how='left')

    # Tours by person type, purpose, mode, and destination district
    agg_fields = ['pathtype','pptyp','dpurp','mode','otaz']
    trips_df = pd.DataFrame(trip_person.groupby(agg_fields)['trexpfac'].sum())

    # Median income
    trip_person['inc_wt'] = trip_person['hhincome']*trip_person['trexpfac']
    inc_df = pd.DataFrame(trip_person.groupby(agg_fields).sum()['inc_wt']/trip_person.groupby(agg_fields).sum()['trexpfac'])
    inc_df.rename(columns={0:'inc_wt'},inplace=True)
    trips_df = trips_df.join(inc_df)

    # add datasource field
    trips_df['source'] = dataset['name']
    
    return trips_df

def taz_tours(dataset):
    
    tour = dataset['Tour']
    
#   tour_dest = pd.merge(tour,districts[['taz','district_name','lat','lon']],left_on='tdtaz',right_on='taz',how='left')
    tour_dest = pd.DataFrame(tour.groupby('tdtaz').sum()['toexpfac'])
    tour_dest['taz'] = tour_dest.index
    tour_dest.reset_index(inplace=True, drop=True)
    
    
#     tour_origin = pd.merge(tour,districts[['taz','district_name','lat','lon']],left_on='totaz',right_on='taz',how='left')
    tour_origin = pd.DataFrame(tour.groupby('totaz').sum()['toexpfac'])
    tour_origin['taz'] = tour_origin.index
    tour_origin.reset_index(inplace=True, drop=True)
    
    df = pd.merge(tour_dest,tour_origin,on='taz', suffixes=['_dest','_origin'])
    df = pd.merge(df,districts, on='taz',how='left' )
    
    df['source'] = dataset['name']
    
    return df

def taz_avg(dataset):

	trip = dataset['Trip']
	hh = dataset['Household']
	person = dataset['Person']

	person_hh = pd.merge(person, hh, on='hhno', how='left')
	trip = pd.merge(trip, person_hh, on=['pno','hhno'], how='left')

	print 'total VMT by home TAZ'
	# total VMT by home TAZ
	taz_vmt = trip[['hhtaz','travdist']].groupby('hhtaz').sum()
	taz_pop = person_hh[['hhtaz','psexpfac']].groupby('hhtaz').sum()
	taz_df = pd.DataFrame(taz_vmt['travdist'] / taz_pop['psexpfac'])
	taz_df.columns = ['Average VMT per Capita']
	taz_df = taz_df.reset_index()

    # Non-Auto Mode Share

	trip.ix[trip['mode'].isin(['Bike', 'Walk', 'Transit']), 'Non-Auto'] = 'Non-Auto'
	trip.ix[~trip['mode'].isin(['Bike', 'Walk', 'Transit']), 'Non-Auto'] = 'Auto'
	df = pd.DataFrame(trip[trip['Non-Auto'] == 'Non-Auto'][['hhtaz','Non-Auto','trexpfac']].groupby(['hhtaz']).sum()['trexpfac'])
	df = df.reset_index()
	df.columns = ['hhtaz','non-auto trips']
	df_trip = trip[['hhtaz','trexpfac']].groupby('hhtaz').sum()['trexpfac']
	df_trip = df_trip.reset_index()

	df = pd.merge(df_trip, df, on='hhtaz') 
	df['Percent Non-Auto'] = df['non-auto trips'] / df['trexpfac']
	df = df[['hhtaz','Percent Non-Auto']]

	# Join mode share and VMT per capita
	taz_df = pd.merge(taz_df, df, on='hhtaz')

	# Calculate percent walking or biking for transportation
	bike_walk_trips = trip[trip['mode'].isin(['Bike','Walk']) | ((trip['mode'] == 'Transit') & (trip['dorp'] > 0))]
	df = bike_walk_trips.groupby(['hhno','pno']).count()
	df = df.reset_index()
	df = df[['hhno','pno']]
	df['bike_walk'] = 1
	df = pd.merge(person_hh,df,on=['hhno','pno'], how='left')
	df['bike_walk'] = df['bike_walk'].fillna(0)
	df['indicator'] = 1
	df = df[['hhtaz','bike_walk','indicator']].groupby(['hhtaz']).sum()
	df = df.reset_index()
	df['Percent Biking or Walking'] = df['bike_walk'] / df['indicator']

	# Merge with taz_df
	taz_df = pd.merge(taz_df, df[['Percent Biking or Walking','hhtaz']], on='hhtaz')

	# Delay

	# only perform for non-survey runs, check delay exists
	if 'sov_ff_time' in trip.columns:
		trip_auto = trip[trip['mode'].isin(['SOV','HOV2','HOV3+']) & (trip['dorp'] == 1)]
		trip_auto['delay'] = trip_auto['travtime'] - trip_auto['sov_ff_time']/100.0
		df = trip_auto[['hhtaz','delay']].groupby('hhtaz').sum()[['delay']].reset_index()
		df = pd.merge(df, hh[['hhtaz','hhsize']].groupby('hhtaz').sum()[['hhsize']].reset_index(),on='hhtaz')
		df['Delay per Capita per Day'] = df['delay']/df['hhsize']
	else:
		trip_auto = trip[trip['mode'].isin(['SOV','HOV2','HOV3+']) & (trip['dorp'] == 1)]
		trip_auto['delay'] = -99
		df = trip_auto[['hhtaz','delay']].groupby('hhtaz').sum()[['delay']].reset_index()
		df = pd.merge(df, hh[['hhtaz','hhsize']].groupby('hhtaz').sum()[['hhsize']].reset_index(),on='hhtaz')
		df['Delay per Capita per Day'] = -99


	taz_df = pd.merge(taz_df, df[['hhtaz','Delay per Capita per Day']], on='hhtaz')

	taz_df['source'] = dataset['name']

	return taz_df

def time_of_day(dataset):
    """
    tours and trips by time of day hour
    """
    trip = dataset['Trip']
    tour = dataset['Tour']
    
    # Trip start hour
    trip['deptm_hr'] = trip['deptm'].apply(lambda row: int(math.floor(row/60)))
    trip['arrtm_hr'] = trip['arrtm'].apply(lambda row: int(math.floor(row/60)))
    
    # tour start hour
    tour['tlvorg_hr'] = tour['tlvorig'].apply(lambda row: int(math.floor(row/60)))
    tour['tardest_hr'] = tour['tardest'].apply(lambda row: int(math.floor(row/60)))
    tour['tlvdest_hr'] = tour['tlvdest'].apply(lambda row: int(math.floor(row/60)))
    tour['tarorig_hr'] = tour['tarorig'].apply(lambda row: int(math.floor(row/60)))
    
   
    trip_dep = pd.DataFrame(trip.groupby('deptm_hr').sum()['trexpfac'])
    trip_dep['tod'] = trip_dep.index
    trip_dep.reset_index(inplace=True)
    trip_dep.rename(columns={'trexpfac':'trip_deptm'},inplace=True)
        
    trip_arr = pd.DataFrame(trip.groupby('arrtm_hr').sum()['trexpfac'])
    trip_arr['tod'] = trip_arr.index
    trip_arr.reset_index(inplace=True)
    trip_arr.rename(columns={'trexpfac':'trip_arrtm'},inplace=True)
    
    results_df = pd.merge(trip_dep, trip_arr, on='tod')
    
    results_df['source'] = dataset['name']
    
    return results_df 

def net_summary(net_file, fname):
    
    net_summary_df = pd.read_excel(net_file, sheetname='Network Summary')
    net_summary_df.index = net_summary_df['tod']
    df = pd.DataFrame(net_summary_df.stack())
    df.reset_index(inplace=True)
    df.rename(columns={0:'value','level_1':'fieldname'}, inplace=True)

    # Drop the rows with TP_4k column headers
    df.drop(df[df['fieldname'] == 'TP_4k'].index, inplace=True)
    df.drop(df[df['fieldname'] == 'tod'].index, inplace=True)

    # Split the fields by vmt, vht, delay
    df['facility_type'] = df.fieldname.apply(lambda row: row.split('_')[0])
    df['metric'] = df.fieldname.apply(lambda row: row.split('_')[-1])

    df['source'] = fname.split('.xlsx')[0]
    
    write_csv(df=df, fname='net_summary.csv')

def daily_counts(net_file, fname):
    
    sheetname = 'Daily Counts'
    if sheetname not in pd.ExcelFile(net_file).sheet_names:
        return
    else:
        df = pd.read_excel(net_file, sheetname=sheetname)
            
        # Get total of model @tveh
        # take min of count value because it represents potentially multiple linkes
        df = pd.DataFrame([df.groupby('@scrn').sum()['@tveh'].values,
                           df.groupby('@scrn').min()['count'].values,
                           df.groupby('@scrn').min()['ul3'].values,
                           df.groupby('@scrn').first()['i'].values,
                           df.groupby('@scrn').first()['j'].values,]).T
        df.columns = ['model','observed','facility','i','j']
        df['source'] = fname.split('.xlsx')[0]
                
        write_csv(df=df, fname='traffic_counts.csv')

def hourly_counts(net_file, fname):

	sheetname='Counts Output'
	if sheetname not in pd.ExcelFile(net_file).sheet_names:
		return
	else:
	    df = pd.read_excel(net_file, sheetname=sheetname)

		# separate observed counts
	    df_observed = df[df.columns[['obs' in i for i in df.columns]]]
	    df_obs = pd.DataFrame(df_observed.stack()).reset_index()
	    df_obs.columns=['count_id','tod','observed']
		# Trim time period from tod field
	    df_obs['tod'] = df_obs['tod'].apply(lambda row: str(row.split('_')[-1]))
		# Drop total by time of day rows
	    df_obs = df_obs[df_obs['tod'] != 'obs_total']

		# separate model volumes
	    df_model = df[df.columns[['vol' in i for i in df.columns]]]
	    df_model = pd.DataFrame(df_model.stack()).reset_index()
	    df_model.columns=['count_id','tod','model']
	    df_model['tod'] = df_model['tod'].apply(lambda row: str(row.split('vol')[-1]))

		# Join model and observed data
	    df = pd.merge(df_obs, df_model, on =['count_id','tod'])

		# Link type (hov or general purpose)
	    df['link_type'] = df['count_id'].apply(lambda row: str(row)[-1])	

	    df['source'] = fname.split('.xlsx')[0]

	    write_csv(df=df, fname='hourly_counts.csv')

def transit_summary(net_file, fname):

    sheetname = 'Transit Summaries'
    if sheetname not in pd.ExcelFile(net_file).sheet_names:
        return
    else:
        transit_df = pd.read_excel(net_file, sheetname=sheetname)
        transit_df.index = transit_df['route_code']

        # Add model results
        dict_result = {}
        for field in ['board','time']:
            df = pd.DataFrame(transit_df[[tod+'_'+ field for tod in tod_list]].stack())
            df.rename(columns={0:field}, inplace=True)
            df['tod'] = [i.split('_')[0] for i in df.index.get_level_values(1)]
            df['route_id'] = df.index.get_level_values(0)
            df.reset_index(inplace=True, drop=True)

            dict_result[field] = df

        # Only keep the boardings for now - observed time data is not available at the route level
        df = dict_result['board'].groupby(['route_id','tod']).sum()
        df.reset_index(inplace=True)
        df['source'] = fname.split('.xlsx')[0]

        model = df

        # Join observed data

        df = pd.read_csv(r'scripts\summarize\inputs\network_summary\transit_boardings_2014.csv')
        df.index = df['PSRC_Rte_ID']
       # df.drop([u'Unnamed: 0','PSRC_Rte_ID','SignRt'],axis=1,inplace=True)

        df = pd.DataFrame(df.stack())
        df.reset_index(inplace=True)
        df.rename(columns={0:'board', 'level_1':'hour','PSRC_Rte_ID':'route_id'}, inplace=True)

        # Convert hour to time of day definition
        df['hour'] = df['hour'].apply(lambda row: row.split('_')[-1])
        tod_df = pd.DataFrame(data=tod_lookup.values(),index=tod_lookup.keys(), columns=['tod'])
        tod_df['hour'] = tod_df.index.astype('str')

        df = pd.merge(df,tod_df,on='hour')
        df.drop('hour', axis=1,inplace=True)

        # Group by tod
        df = df.groupby(['tod','route_id']).sum()
        df['tod'] = df.index.get_level_values(0)
        df['route_id'] = df.index.get_level_values(1)
        df.reset_index(inplace=True, drop=True)

        df = pd.merge(model, df, on=['route_id','tod'], suffixes=['_model','_observed'])
        df.rename(columns={'board_model':'model','board_observed':'observed'}, inplace=True)
        df['source'] = fname.split('.xlsx')[0]
        fname_out = 'transit_boardings.csv'
        
        # Add the route description
        df = pd.merge(df,transit_df[['route_code','description']],left_on='route_id',right_on='route_code',how='left')
        df.drop_duplicates(inplace=True)
        
        write_csv(df=df, fname=fname_out)

def light_rail(netfile, name):
	"""Compare light-rail boardings by station"""

	sheetname = 'Light Rail'
	if sheetname not in pd.ExcelFile(netfile).sheet_names:
		return
	else:
		df = pd.read_excel(netfile, sheetname=sheetname)
		df['source'] = name

		write_csv(df=df, fname='light_rail.csv')

def truck_summary(net_file, fname):
    """Process medium and heavy truck counts where observed data is provided"""

    sheetname = 'Truck Counts'
    if sheetname not in pd.ExcelFile(net_file).sheet_names:
        return
    else:
        df = pd.read_excel(net_file, sheetname='Truck Counts')
        df['source'] = fname.split('.xlsx')[0]

        # stack by medium, heavy, and total counts
        med_df = df.drop(['observedHvy','modeledHvy','observedTot','modeledTot'], axis=1)
        med_df.rename(columns={'modeledMed':'model','observedMed':'observed'},inplace=True)
        med_df['truck_type'] = 'medium'

        hvy_df = df.drop(['observedMed','modeledMed','observedTot','modeledTot'], axis=1)
        hvy_df.rename(columns={'modeledHvy':'model','observedHvy':'observed'},inplace=True)
        hvy_df['truck_type'] = 'heavy'

        tot_df = df.drop(['observedMed','modeledMed','observedHvy','modeledHvy'], axis=1)
        tot_df.rename(columns={'modeledTot':'model','observedTot':'observed'},inplace=True)
        tot_df['truck_type'] = 'all'

        df = med_df.append(hvy_df).append(tot_df)
        write_csv(df=df, fname='trucks.csv')

def screenlines(net_file, fname):
    """Process screenline results from model output"""

    sheetname = 'Screenline Volumes'
    if sheetname not in pd.ExcelFile(net_file).sheet_names:
        return
    else:
        df = pd.read_excel(net_file, sheetname=sheetname)
        df['source'] = fname.split('.xlsx')[0]

    # Load observed data and join
    obs = pd.read_csv(r'scripts\summarize\inputs\screenlines.csv')

    obs_col = '2010'
    df = pd.merge(df,obs,left_on='Screenline', right_on='id', how='inner')

    df.rename(columns={'Volumes':'model',obs_col:'observed'}, inplace=True)

    write_csv(df=df, fname='screenlines.csv')

def logsums(name, dir_name):
    # 

    logsum = 'CFULL/SHO'
    logsum_output = 'outputs/grouped/logsums.csv'

    df = pd.read_csv(os.path.join(dir_name, 'aggregate_logsums.1.dat'), delim_whitespace=True, skipinitialspace=True)
    df = df.reset_index()
    df = pd.DataFrame(df[['level_0',logsum]])
    df['source'] = name

    # Separate into accessibility bins
    df['accessibility'] = pd.qcut(df[logsum],5,labels=['lowest','low','moderate','high','highest'])
    bins = pd.qcut(df[logsum],5,retbins=True)[1]

    df.columns = ['taz','logsum','source','accessibility']

    # Attach population
    hh = pd.read_csv(os.path.join(dir_name,'_household.tsv'), sep='\t')
    df_pop = pd.DataFrame(hh.groupby('hhtaz').sum()['hhsize'])
    df_pop['taz'] = df_pop.index
    df = pd.merge(df,df_pop,on='taz',how='left')
    df.columns = [['taz','logsum','source','accessibility','population']]

    # Write to file
    if os.path.exists(logsum_output):
        df_current = pd.read_csv(logsum_output)
        df_current.append(df).to_csv(logsum_output, index=False)
    else:
        df.to_csv(logsum_output, index=False)

def process_dataset(h5file, scenario_name):
    
    # Process all daysim results
    
    # Load h5 data as dataframes
    dataset = h5_to_df(h5file, table_list=['Household','Trip','Tour','Person','HouseholdDay','PersonDay'], name=scenario_name)

    dataset = apply_lables(dataset)
    
    # Calculate aggregate measures csv
    agg_df = agg_measures(dataset)
    write_csv(agg_df,fname='agg_measures.csv')

    hh_df = household(dataset)
    write_csv(hh_df, fname='household.csv')

    ## Tours based on time left origin
    tours_df = tours(dataset,'tlvorig')
    write_csv(tours_df,fname='tours_tlvorig.csv')

    tours_df = tours(dataset, 'tardest')
    write_csv(tours_df,fname='tours_tardest.csv')

    tours_df = tours(dataset, 'tlvdest')
    write_csv(tours_df,fname='tours_tlvdest.csv')

    taz_df = taz_tours(dataset)
    write_csv(taz_df,fname='taz_tours.csv')
    
    trips_df = trips(dataset)
    write_csv(trips_df, fname='trips.csv')

    trip_taz_df = taz_trips(dataset)
    write_csv(trip_taz_df, fname='trips_taz.csv')
    
    person_day_df = person_day(dataset)
    write_csv(person_day_df, fname='person_day.csv')
    
    person_df = person(dataset)
    write_csv(person_df, 'person.csv')
    
    tod_df = time_of_day(dataset)
    write_csv(tod_df, fname='time_of_day.csv')

    taz_avg_df = taz_avg(dataset)
    write_csv(taz_avg_df, fname='taz_avg.csv')

def write_csv(df,fname):
    '''
    Write dataframe to file; append existing file
    '''
    if not os.path.isfile(os.path.join(output_dir,fname)):
        df.to_csv(os.path.join(output_dir,fname))
    else: # append without writing the header
        df.to_csv(os.path.join(output_dir,fname), mode ='a', header=False)

if __name__ == '__main__':

    # Use root directory name as run name
 #    run_name = os.getcwd().split('\\')[-1]

 #    # Create output directory, overwrite existing results
 #    output_dir = r'outputs/grouped'
 #    if os.path.exists(output_dir):
 #        shutil.rmtree(output_dir)
 #    os.makedirs(output_dir)

 #    # Create list of runs to compare, starting with current run
 #    run_dir_dict = {
 #        run_name: os.getcwd(), 
 #    }

 #    # Add runs, if set in standard_summary_configuration.py
 #    if len(comparison_runs.keys()) > 0:
 #        for comparison_name, comparison_dir in comparison_runs.iteritems():
 #            run_dir_dict[comparison_name] = comparison_dir

	# # Create daysim summaries
 #    for name, run_dir in run_dir_dict.iteritems():

	# 	daysim_h5 = h5py.File(os.path.join(run_dir,r'outputs/daysim/daysim_outputs.h5'))
	# 	print 'processing h5: ' + name
	# 	process_dataset(h5file=daysim_h5, scenario_name=name)
	# 	del daysim_h5 # drop from memory to save space for next comparison

 #    # Compare daysim to survey if set in standard_summary_configuration.py
 #    if compare_survey:
 #        process_dataset(h5file=h5py.File(r'scripts\summarize\inputs\calibration\survey.h5'), scenario_name='survey')

 #    # Create network and accessibility summaries
 #    for name, run_dir in run_dir_dict.iteritems():
 #        file_dir = os.path.join(run_dir,r'outputs/network/network_summary_detailed.xlsx')
 #        print 'processing excel: ' + name
 #        transit_summary(file_dir, name)
 #        daily_counts(file_dir, name)
 #        # hourly_counts(file_dir, name)
 #        net_summary(file_dir, name)
 #        truck_summary(file_dir, name)
 #        screenlines(file_dir, name)
 #        light_rail(file_dir, name)
 #        file_dir = os.path.join(run_dir,r'outputs/daysim')
 #        logsums(name, file_dir)

    ## Write notebooks based on these outputs to HTML
    for nb in ['topsheet','metrics']:
        try:
            os.system("jupyter nbconvert --ExecutePreprocessor.timeout=600 --to=html --ExecutePreprocessor.kernel_name=python scripts/summarize/notebooks/"+nb+".ipynb")
        except:
            print 'Unable to produce topsheet, see: scripts/summarize/standard/group.py'

        # Move these files to output
        if os.path.exists(r"outputs/"+nb+".html"):
            os.remove(r"outputs/"+nb+".html")
        os.rename(r"scripts/summarize/notebooks/"+nb+".html", r"outputs/"+nb+".html")