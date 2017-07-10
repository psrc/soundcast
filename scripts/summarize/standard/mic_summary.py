import os, sys, math, h5py
import pandas as pd
sys.path.append(os.getcwd())
from standard_summary_configuration import *

labels = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/variable_labels.csv'))
districts = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/district_lookup.csv'))
mic_taz = pd.read_csv(r'scripts/summarize/inputs/mic_taz.csv')
# Get MIC data from land use file

table_list = ['Household','Trip','Tour','Person','HouseholdDay','PersonDay']

overwrite = True

output_csv_list = ['mic']

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

def mic(scenario_name, working_dir):
	'''
	Calculate truck trips and job totals by MIC 
	'''
	# Truck trips to/from this zone
	lu_file = pd.read_csv(os.path.join(working_dir,r'inputs\accessibility\parcels_urbansim.txt'), sep=' ')

	metrk = pd.read_csv(os.path.join(working_dir,r'outputs\mfmetrk.csv'))
	metrk.index = metrk['Unnamed: 0']
	metrk = metrk.drop('Unnamed: 0', axis=1)
	metrk.columns = metrk.columns.astype('int')

	hvtrk = pd.read_csv(os.path.join(working_dir,r'outputs\mfhvtrk.csv'))
	hvtrk.index = hvtrk['Unnamed: 0']
	hvtrk = hvtrk.drop('Unnamed: 0', axis=1)
	hvtrk.columns = hvtrk.columns.astype('int')

	tazlist = mic_taz.groupby('TAZ').count().index.values

	df = pd.DataFrame([metrk.ix[:,tazlist].sum(),hvtrk.ix[:,tazlist].sum()]).T
	df.columns = ['medium_trucks','heavy_trucks']
	df['TAZ'] = df.index
	df = pd.merge(df, mic_taz, on='TAZ', how='left')
	df = pd.merge(df.groupby('MIC').sum()[['medium_trucks','heavy_trucks']].reset_index(),
                 df.groupby('MIC').min()[['lat','lon']].reset_index())

	# Attach employment by RGC
	if 'TAZ_P' in lu_file.columns:
		taz_col = 'TAZ_P'
		emp_col = 'EMPTOT_P'
	else:
		taz_col = 'taz_p'
		emp_col = 'emptot_p'
	lu = pd.merge(lu_file, mic_taz, left_on=taz_col, right_on='TAZ')
	lu_mic = lu.groupby('MIC').sum()
	lu_mic['MIC'] = lu_mic.index

	df_out = pd.merge(df,lu_mic[[emp_col,'MIC']],on='MIC')

	df_out['source'] = scenario_name

	return df_out

def process_dataset(scenario_name, working_dir):
	# Load h5 data as dataframes
    # dataset = h5_to_df(h5file, table_list=['Household','Trip','Tour','Person','HouseholdDay','PersonDay'], name=scenario_name)

    # dataset = apply_lables(dataset)
    
    mic_df = mic(scenario_name=scenario_name, working_dir=working_dir)
    write_csv(mic_df, fname='mic.csv')

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

    comparison_run_dir = r'D:\brice\sc_2040demand_2014net'

    network_file_dict = {
        run_name: os.getcwd(),
        '2040': comparison_run_dir
    }

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if overwrite:
	    for fname in output_csv_list:
	        if os.path.isfile(os.path.join(output_dir,fname+'.csv')):
	            os.remove(os.path.join(output_dir,fname+'.csv'))

	# Process all network outputs
    for name, file_dir in network_file_dict.iteritems():
        print name
        process_dataset(scenario_name=name, working_dir=file_dir)