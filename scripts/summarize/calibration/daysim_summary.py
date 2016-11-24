import os, sys, math, h5py
import pandas as pd

USAGE = """

	python daysim_summary.py input_dir output_dir

	Produces stacked csv summaries of h5-formatted h5 files.
	All h5 and xlsx files in input_dir are summarized. 
    Format must be soundcast output (daysim_outputs.h5) or survey files (survey.h5).
    Any number of h5 files may be included in a summary.

    Output is set of csv aggregations of h5 data, to be stored in output_dir. 

    Rename h5 and xlsx files to represent secenario or survey name. These will be imported to the dataset.

"""

labels = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/variable_labels.csv'))
districts = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/district_lookup.csv'))

table_list = ['Household','Trip','Tour','Person','HouseholdDay','PersonDay']
output_csv_list = ['agg_measures','trips','taz_tours','tours','time_of_day','person_day','person']

# Overwrite existing output?
overwrite = True

# look up psrc time of day 
tod_list = ['5to6','6to7','7to8','8to9','9to10','10to14','14to15','16to17','17to18','18to20']

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
                23:'20to5' }

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

def tours(dataset):
    
    tour = dataset['Tour']
    person = dataset['Person']
        
    # total tours
    # join with person file and district names based on destination
    tour_person = pd.merge(tour,person,on=['hhno','pno'])
    tour_person = pd.merge(tour_person,districts[['taz','district_name']],left_on='tdtaz',right_on='taz',how='left')
    
    
    tour_person['tlvorig_hr'] = tour_person['tlvorig'].apply(lambda row: int(math.floor(row/60)))
    
    # Tours by person type, purpose, mode, destination district, and time of day
    agg_fields = ['pptyp','pdpurp','tmodetp','tlvorig_hr','district_name']
    tours_df = pd.DataFrame(tour_person.groupby(agg_fields)['toexpfac'].sum())
    
    # average trip distance and time
    tours_df = tours_df.join(pd.DataFrame(tour_person.groupby(agg_fields)['tautodist'].mean()))
    tours_df = tours_df.join(pd.DataFrame(tour_person.groupby(agg_fields)['tautotime'].mean()))
    # average trip 
    
    tours_df = tours_df.join(pd.DataFrame(person.groupby('pptyp').sum()['psexpfac']))
    
    # Add the district lat and lon values
    tours_df['pptyp'] = tours_df.index.get_level_values(0)
    tours_df['pdpurp'] = tours_df.index.get_level_values(1)
    tours_df['tmodetp'] = tours_df.index.get_level_values(2)
    tours_df['tlvorig_hr'] = tours_df.index.get_level_values(3)
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
        
    # total trips
    # join with person file and district names based on destination
    trip_person = pd.merge(trip,person,on=['hhno','pno'], how='left')
    
    trip_person['deptm_hr'] = trip_person['deptm'].apply(lambda row: int(math.floor(row/60)))
    
   
    # Tours by person type, purpose, mode, and destination district
    agg_fields = ['pptyp','dpurp','mode','deptm_hr']
    trips_df = pd.DataFrame(trip_person.groupby(agg_fields)['trexpfac'].sum())
    
    # average trip distance and time (weighted)
    trip_person['travdist_wt'] = trip_person['travdist']*trip_person['trexpfac']
    trip_person['travtime_wt'] = trip_person['travtime']*trip_person['trexpfac']
    
    travdist_df = pd.DataFrame(trip_person.groupby(agg_fields).sum()['travdist_wt']/trip_person.groupby(agg_fields).sum()['trexpfac'])
    travdist_df.rename(columns={0:'travdist'},inplace=True)
    trips_df = trips_df.join(travdist_df)

    travtime_df = pd.DataFrame(trip_person.groupby(agg_fields).sum()['travtime_wt']/trip_person.groupby(agg_fields).sum()['trexpfac'])
    travtime_df.rename(columns={0:'travtime'},inplace=True)
    trips_df = trips_df.join(travtime_df)    
    
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

def traffic_counts(net_file, fname):
    # note that for now network_summary_detailed is manually updated with soundcast_counts output
    # for traffic counts - should be automated in future to do this immediately
    
    df = pd.read_excel(net_file, sheetname='Counts Output')
        
    # Get total of model @tveh
    # take min of count value because it represents potentially multiple linkes
    df = pd.DataFrame([df.groupby('@scrn').sum()['@tveh'].values,
                       df.groupby('@scrn').min()['@count'].values,
                       df.groupby('@scrn').min()['ul3'].values,
                       df.groupby('@scrn').first()['i'].values,
                       df.groupby('@scrn').first()['j'].values,]).T
    df.columns = ['model','observed','facility','i','j']
    df['source'] = fname.split('.xlsx')[0]
    
    # Add geography
    geog = pd.read_csv(r'data/midpoint_edges_0.txt')
    df = pd.merge(df,geog[['NewINode','NewJNode','lat','lon','county','LARGE_AREA']],
                  left_on=['i','j'], right_on=['NewINode','NewJNode'], how='left')
    
    write_csv(df=df, fname='traffic_counts.csv')

def transit_summary(net_file, fname):
    
    transit_df = pd.read_excel(net_file, sheetname='Transit Summaries')
    transit_df.index = transit_df['route_code']
    # fname = 'transit_boardings.csv'

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

    df = pd.read_csv(r'C:\Users\Brice\soundcast-summary\daysim\data\transit_boardings_2014.csv')
    df.index = df['PSRC_Rte_ID']
    df.drop([u'Unnamed: 0','PSRC_Rte_ID','SignRt'],axis=1,inplace=True)

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

    tours_df = tours(dataset)
    write_csv(tours_df,fname='tours.csv')
    
    taz_df = taz_tours(dataset)
    write_csv(taz_df,fname='taz_tours.csv')
    
    trips_df = trips(dataset)
    write_csv(trips_df, fname='trips.csv')
    
    person_day_df = person_day(dataset)
    write_csv(person_day_df, fname='person_day.csv')
    
    person_df = person(dataset)
    write_csv(person_df, 'person.csv')
    
    tod_df = time_of_day(dataset)
    write_csv(tod_df, fname='time_of_day.csv')

def write_csv(df,fname):
    '''
    Write dataframe to file; append existing file
    '''
#     df.to_csv(os.path.join(output_dir,fname),mode='a')
    if not os.path.isfile(os.path.join(output_dir,fname)):
        df.to_csv(os.path.join(output_dir,fname))
    else: # append without writing the header
        df.to_csv(os.path.join(output_dir,fname), mode ='a', header=False)

if __name__ == '__main__':

    if len(sys.argv) != 3:
        print USAGE
        print sys.argv
        sys.exit(2)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    if overwrite:
	    for fname in output_csv_list:
	        if os.path.isfile(os.path.join(output_dir,fname+'.csv')):
	            os.remove(os.path.join(output_dir,fname+'.csv'))

	# Process all files with h5 extension in input_dir
    for fname in os.listdir(input_dir):
		print fname
		if fname.endswith('.h5'):

			daysim_h5 = h5py.File(os.path.join(input_dir,fname))

			print 'processing ' + fname

			process_dataset(h5file=daysim_h5, scenario_name=fname.split('.')[0])
			del daysim_h5 # drop from memory to save space for next comparison

    # Create network summaries
    output_csv_list = ['transit_boardings','traffic_counts','net_summary']


    if overwrite:
        for fname in output_csv_list:
            if os.path.isfile(os.path.join(output_dir,fname+'.csv')):
                os.remove(os.path.join(output_dir,fname+'.csv'))

    for fname in os.listdir(input_dir):
        if fname.endswith('.xlsx'):
            net_file = os.path.join(input_dir,fname)

            print 'processing ' + fname

            transit_summary(net_file, fname)
            traffic_counts(net_file, fname)
            net_summary(net_file, fname)