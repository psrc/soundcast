import sqlite3 as lite
import sys, os
import h5py
import pandas as pd
# from EmmeProject import *
from input_configuration import results_db, scenario_name, base_inputs

main_dir = os.path.abspath('')

def process_h5(data_table, h5_file, columns):
    ''' Convert DaySim tables (e.g., person, household files) to dataframe ''' 
    df = pd.DataFrame()     # initialize empty data frame
    
    for col in columns:
        df[col] = h5_file[data_table][col].value
        print 'Processing data column: ' + col
    return df

def main():

	daysim_main = h5py.File(main_dir + r'/outputs/daysim_outputs.h5', "r+")

	# Connect to sqlite3 db
	con = None
	con = lite.connect(results_db)

	# Columns to extract from Daysim outputs
	trip_cols = [	u'dadtyp', u'deptm', u'dorp', u'dpcl', u'dpurp', u'dtaz', 
					u'hhno', u'mode', u'oadtyp', u'opcl', u'opurp', u'otaz', 
					u'pathtype', u'pno', u'travcost', u'travdist', u'travtime', 
					u'vot']

	mode_columns = ['Walk','Bike','SOV','HOV2','HOV3+','Transit','School Bus']

	# Convert daysim outputs H5 to a dataframe
	base_df = process_h5('Trip', daysim_main, trip_cols)

	# Travel Cost by Mode
	a = base_df.groupby('mode').mean()[['travcost']]

	# Transpose to get in row format
	a = a.T
	a.columns = mode_columns

	# Add run context columns to the table
	a['model'] ,a['runid'], a['date'], a['model_year'] = ['Soundcast',1,'10/15/2015',scenario_name]
	a.to_sql(name='Travel Cost by Mode', con=con, if_exists='append', chunksize=1000)

	# Mode Share
	b = base_df.groupby('mode').count()[['dtaz']]/len(base_df)

	# Transpose to get in row format
	b = b.T
	b.columns = mode_columns

	b['model'] ,b['runid'], b['date'], b['model_year'] = ['Soundcast',2,'10/25/2015',scenario_name]
	b.to_sql(name='Mode Share', con=con, if_exists='append', chunksize=1000)

if __name__=="__main__":
	main()
