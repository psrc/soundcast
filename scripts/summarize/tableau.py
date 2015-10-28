import sqlite3 as lite
import sys, os
import h5py
import pandas as pd
import datetime
from scripts.EmmeProject import *
from input_configuration import results_db, scenario_name, main_log_file
sys.path.append(os.path.join(os.getcwd(),"inputs"))

main_dir = os.path.abspath('')

fac_type_dict = {'highway' : 'ul3 = 1 or ul3 = 2',
	                 'arterial' : 'ul3 = 3 or ul3 = 4 or ul3 = 6',
	                 'connectors' : 'ul3 = 5'}

def process_h5(data_table, h5_file, columns):
    ''' Convert DaySim tables (e.g., person, household files) to dataframe ''' 
    df = pd.DataFrame()     # initialize empty data frame
    
    for col in columns:
        df[col] = h5_file[data_table][col].value
        print 'Processing data column: ' + col
    return df

def get_vmt_vht(my_project, tods):
	# Collect VMT and VHT by Time of Day and Facility Type from Emme

	tod_dict = {}
	for tod in tods:
	    print 'Process VMT/VHT on ' + str(tod)
	    my_project.change_active_database(tod)
	    network = my_project.current_scenario.get_network()

	    fac_dict = {}

	    for key, value in fac_type_dict.iteritems():
	        fac_dict[key] = {}
	        for expr in ['@vmt','@vht']:
	            my_project.network_calculator(
	                "link_calculation", 
	                result=None, 
	                expression=expr,  
	                selections_by_link=value)
	            fac_dict[key][expr] = my_project.network_calc_result['sum']   
		
		tod_dict[tod] = fac_dict
	
	return tod_dict


def get_unique_screenlines(EmmeProject):
    network = EmmeProject.current_scenario.get_network()
    unique_screenlines = []
    for link in network.links():
        if link.type <> 90 and link.type not in unique_screenlines:
            unique_screenlines.append(str(link.type))
    return unique_screenlines


def get_runid(table, con, runid):
	'''Update run ID from existing database'''
	try:
		return len(pd.read_sql('select * from ' + table, con))
	except:
		return 0

def get_date():
	'''Get last time stamp from run log.
	   Log time stamps are consistently formatted & exist for each line in the log
	   For runs without a log, or on error, get current time. '''
	try:
		timestamp = str(pd.read_csv(main_log_file).iloc[-1]).split(' ')
		date = timestamp[0]
		time = timestamp[1] + " " + timestamp[2]
	except:
		date = datetime.now().strftime("%m/%d/%Y")
		time = datetime.now().strftime("%I:%M:%S %p")
	return date, time

def stamp(df, con, table):
	'''Add run information to a table row'''
	df['scenario_name'],df['runid'],df['date'],df['time'] = \
	[scenario_name,get_runid(table, con,'runid'),get_date()[0],get_date()[1]]
	return df

def main():

	daysim_main = h5py.File(main_dir + r'/outputs/daysim_outputs.h5', "r+")

	# Connect to sqlite3 db
	con = None
	con = lite.connect(results_db)

	# Columns to extract from Daysim outputs
	daysim_metrics = [u'mode', u'travcost', u'travdist', u'travtime']

	# Corresponding to order of Daysim results (should be a mapped dictionary)
	mode_columns = ['Walk','Bike','SOV','HOV2','HOV3+','Transit','School Bus']

	# Convert daysim outputs H5 to a dataframe
	base_df = process_h5(data_table='Trip', h5_file=daysim_main, columns=daysim_metrics)

	# Process tables that show results by mode
	for metric in [u'travcost', u'travdist', u'travtime']:
		df = base_df.groupby('mode').mean()[[metric]].T
		df.columns = mode_columns
		df = stamp(df, con=con, table=metric)
		df.to_sql(name=metric, con=con, if_exists='append', chunksize=1000)

	# List of tables to be added to the SQL database
	db_tables = ['VMT_TOD', 'VMT_Facility', 'Delay_TOD', 'Speed_TOD', 'Speed_Facility',
				 'ModeShare', 'Screenlines', 'Transit']

	# Look up other results by TOD, using the allday bank
	############################ 
	#########################
	####################
	# make local
	my_project = EmmeProject(r'D:\soundcast\soundcast\projects\LoadTripTables\LoadTripTables.emp')


	# All TOD banks should be in the LoadTripTables project
	tods = [bank.title() for bank in my_project.data_explorer.databases()]

	# Return VMT and VMT by time of day and facility class
	vmt_vht = get_vmt_vht(my_project, tods)

	# Process vmt and vht into db rows


	# VMT/VHT by Time of Day
	fac_vmt = {}
	fac_vht = {}

	for tod in tods:
	    fac_dict_vmt = {}
	    fac_dict_vht = {}

	    # Total for all times of day by facility type
	    for fac_type in fac_type_dict.keys():
	        fac_dict_vmt[fac_type] = vmt_vht[tod][fac_type]['@vmt']
	        fac_dict_vht[fac_type] = vmt_vht[tod][fac_type]['@vht']
	        
	    fac_vmt[tod] = fac_dict_vmt
	    fac_vht[tod] = fac_dict_vht


	# Convert dict to df and write to db

	vmt_tod_df = pd.DataFrame(pd.DataFrame(fac_vmt).sum()).T
	vmt_tod_df = stamp(vmt_tod_df, con=con, table='VMT_TOD')
	vmt_tod_df.to_sql(name='VMT_TOD', con=con, if_exists='append', chunksize=1000)

	vht_tod_df = pd.DataFrame(pd.DataFrame(fac_vht).sum()).T
	vht_tod_df = stamp(vht_tod_df, con=con, table='VHT_TOD')
	vht_tod_df.to_sql(name='VHT_TOD', con=con, if_exists='append', chunksize=1000)

	# Facilities
	vmt_fac_df = pd.DataFrame(pd.DataFrame(fac_vmt).T.sum()).T	
	vmt_fac_df = stamp(vmt_fac_df, con=con, table='VMT_Facility')
	vmt_fac_df.to_sql(name='VMT_Facility', con=con, if_exists='append', chunksize=1000)

	vht_fac_df = pd.DataFrame(pd.DataFrame(fac_vht).T.sum()).T
	vht_fac_df = stamp(vht_fac_df, con=con, table='VHT_Facility')
	vht_fac_df.to_sql(name='VHT_Facility', con=con, if_exists='append', chunksize=1000)

	# Speed (will be similar to vht and vmt but uses average instead of sum)


	# Screenlines

	# Transit Boardings

	# Mode Share



if __name__=="__main__":
	main()
