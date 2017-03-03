import os, sys, math, h5py
import pandas as pd
from standard_summary_configuration import *

labels = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/variable_labels.csv'))
districts = pd.read_csv(os.path.join(os.getcwd(), r'scripts/summarize/inputs/calibration/district_lookup.csv'))
rgc_taz = pd.read_csv(r'scripts\summarize\inputs\rgc_taz.csv')

table_list = ['Household','Trip','Tour','Person','HouseholdDay','PersonDay']

def hh(h5file):

	hh = hh['Household']
    
    # Join RGC geography based on household TAZ location
    hh = pd.merge(hh,rgc_taz,left_on='hhtaz', right_on='taz')

    hh['income_bins'] = pd.cut(hh['hhincome'],bins=income_bins,labels=income_bin_labels)

    df = pd.DataFrame(hh.groupby(['center','hhsize','income_bins','hhvehs','hownrent','hrestype']).sum()['hhexpfac'])
	df = df.fillna(0)
	df.reset_index(inplace=True)

    df['source'] = dataset['name']
    
    return df

def process_dataset(h5file, scenario_name):
	# Load h5 data as dataframes
    dataset = h5_to_df(h5file, table_list=['Household','Trip','Tour','Person','HouseholdDay','PersonDay'], name=scenario_name)

    dataset = apply_lables(dataset)
    
    # Calculate aggregate measures csv
    hh = agg_measures(dataset)
    write_csv(agg_df,fname='agg_measures.csv')

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

    # Use root directory name as run name
    run_name = os.getcwd().split('\\')[-1]

    output_dir = r'outputs/rgc'

    comparison_run_dir = r'P:\Stefan\soundcast_20peak_2offpeak\outputs'

    h5_file_dict = {
        run_name: r'outputs/daysim_outputs.h5', 
        comparison_name: os.path.join(comparison_run_dir,'daysim_outputs.h5'),
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