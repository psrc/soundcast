import pandas as pd
import numpy as np
import os, sys
import h5py
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import *
from input_configuration import *
from bike_configuration import *

# Get the auto time and length of each link
def get_link_attribute(attr, network):
    ''' Return dataframe of link attribute and link ID'''
    link_dict = {}
    for i in network.links():
        link_dict[i.id] = i[attr]
    df = pd.DataFrame({'link_id': link_dict.keys(), attr: link_dict.values()})
    return df

def bike_facility_weight(my_project, link_df):
    '''Compute perceived travel distance impacts from bike facilities
       In the geodatabase, bike facility of 2=bicycle track and 8=separated path
       These are redefined as "premium" facilities
       Striped bike lanes receive a 2nd tier designatinon of "standard"
       All other links remain unchanged'''

    network = my_project.current_scenario.get_network()

    # Load the extra attribute data for bike facility type 
    # and replace geodb typology with the 2-tier definition
    df = get_link_attribute('@bkfac', network)
    df = df.merge(link_df)
    df = df.replace(bike_facility_crosswalk)

    # Replace the facility ID with the estimated  marginal rate of substituion
    # value from Broach et al., 2012 (e.g., replace 'standard' with -0.108)
    df['facility_wt'] = df['@bkfac']
    df = df.replace(facility_dict)

    return df

def volume_weight(my_project, df):
    ''' For all links without bike lanes, apply a factor for the adjacent traffic (AADT).'''

    # Separate auto volume into bins
    df['volume_wt'] = pd.cut(df['@tveh'], bins=aadt_bins, labels=aadt_labels, right=False)
    df['volume_wt'] = df['volume_wt'].astype('int')

    # Replace bin label with weight value
    df = df.replace(to_replace=aadt_dict)

    return df

def process_attributes(my_project):
	'''Import bike facilities and slope attributes for an Emme network'''
	network = my_project.current_scenario.get_network()

	for attr in ['@bkfac', '@upslp']:
		if attr not in my_project.current_scenario.attributes('LINK'):
			my_project.current_scenario.create_extra_attribute('LINK',attr)

	import_attributes = my_project.m.tool("inro.emme.data.network.import_attribute_values")
	filename = r'inputs/bikes/emme_attr.in'
	import_attributes(filename, 
	                  scenario = my_project.current_scenario,
	                  revert_on_error=False)

def process_slope_weight(df, my_project):
    ''' Calcualte slope weights on an Emme network dataframe
        and merge with a bike attribute dataframe to get total perceived 
        biking distance from upslope, facilities, and traffic volume'''

    network = my_project.current_scenario.get_network()

    # load in the slope term from the Emme network
    upslope_df = get_link_attribute('@upslp', network)

    # Join slope df with the length df
    upslope_df = upslope_df.merge(df)

    # Separate the slope into bins with the penalties as indicator values
    upslope_df['slope_wt'] = pd.cut(upslope_df['@upslp'], bins=slope_bins, labels=slope_labels, right=False)
    upslope_df['slope_wt'] = upslope_df['slope_wt'].astype('float')
    upslope_df = upslope_df.replace(to_replace=slope_dict)

    return upslope_df

def write_generalized_time(df):
	''' Export normalized link biking weights as Emme attribute file. '''

	# Rename total weight column for import as Emme attribute
	df['@bkwt'] = df['total_wt']

	# Reformat and save as a text file in Emme format
	df['inode'] = df['link_id'].str.split('-').str[0]
	df['jnode'] = df['link_id'].str.split('-').str[1]

	filename = r'inputs/bikes/bkwt.in'
	df[['inode','jnode', '@bkwt']].to_csv(filename, sep=' ', index=False)

	print "results written to inputs/bikes/bkwt.in"

def calc_bike_weight(my_project, link_df):
	''' Calculate perceived travel time weight for bikes
	    based on facility attributes, slope, and vehicle traffic.'''

	# Import link attributes for elevation gain and bike facilities
	process_attributes(my_project)

	# Calculate weight of bike facilities
	bike_fac_df = bike_facility_weight(my_project, link_df)

	# Calculate weight from daily traffic volumes
	vol_df = volume_weight(my_project, bike_fac_df)

	# Calculate weight from elevation gain (for all links)
	df = process_slope_weight(df=vol_df, my_project=my_project)

	# Calculate total weights
	# add inverse of premium bike coeffient to set baseline as a premium bike facility with no slope (removes all negative weights)
	# add 1 so this weight can be multiplied by original link travel time to produced "perceived travel time"
	df['total_wt'] = 1 - np.float(facility_dict['facility_wt']['premium']) + df['facility_wt'] + df['slope_wt'] + df['volume_wt']

	# Write link data for analysis
	df.to_csv(r'outputs/bike_attr.csv')

	# export total link weight as an Emme attribute file ('@bkwt.in')
	write_generalized_time(df=df)

def bike_assignment(my_project, tod):
	''' Assign bike trips using links weights based on slope, traffic, and facility type, for a given TOD.'''

	my_project.change_active_database(tod)

	# Create attributes for bike weights (inputs) and final bike link volumes (outputs)
	for attr in ['@bkwt', '@bvol']:
		if attr not in my_project.current_scenario.attributes('LINK'):
			my_project.current_scenario.create_extra_attribute('LINK',attr)   

	# Create matrices for bike assignment and skim results
	for matrix in ['bkpt', 'bkat', ]:
		if matrix not in [i.name for i in my_project.bank.matrices()]:
			my_project.create_matrix(matrix, '', 'FULL')

	# Load in bike weight link attributes
	import_attributes = my_project.m.tool("inro.emme.data.network.import_attribute_values")
	filename = r'inputs\bikes\bkwt.in'
	import_attributes(filename, 
	                scenario = my_project.current_scenario,
	                revert_on_error=False)

	# Invoke the Emme assignment tool
	extended_assign_transit = my_project.m.tool("inro.emme.transit_assignment.extended_transit_assignment")
	bike_spec = json.load(open(r'inputs\skim_params\bike_assignment.json'))
	extended_assign_transit(bike_spec)

	print 'bike assignment complete, now skimming'

	skim_bike = my_project.m.tool("inro.emme.transit_assignment.extended.matrix_results")
	bike_skim_spec = json.load(open(r'inputs\skim_params\bike_skim_setup.json'))
	skim_bike(bike_skim_spec)

	# Add bike volumes to bvol network attribute
	bike_network_vol = my_project.m.tool("inro.emme.transit_assignment.extended.network_results")

	# Skim for final bike assignment results
	bike_network_spec = json.load(open(r'inputs\skim_params\bike_network_setup.json'))
	bike_network_vol(bike_network_spec)

	# Export skims to h5
	for matrix in ["mfbkpt", "mfbkat"]:
		print 'exporting skim: ' + str(matrix)
		export_skims(my_project, matrix_name=matrix, tod=tod)

	print "bike assignment complete"

def export_skims(my_project, matrix_name, tod):
	'''Write skim matrix to h5 container'''

	my_store = h5py.File(r'inputs/' + tod + '.h5', "r+")

	matrix_value = my_project.bank.matrix(matrix_name).get_numpy_data()
	
	if matrix_name in my_store['Skims'].keys():
		my_store["Skims"][matrix_name][:] = matrix_value
	else:
		try:
			my_store["Skims"].create_dataset(name=matrix_name, data=matrix_value)
		except:
			'unable to export skim: ' + str(matrix_name)

	my_store.close()

def get_aadt(my_project):
	'''Extract AADT from daily bank'''

	# Add daily bank to current project
	if 'daily' not in [db.title() for db in my_project.data_explorer.databases()]:
		my_project.data_explorer.add_database('banks/daily/emmebank')
	
	my_project.change_active_database('daily')

	# Create dataframe of daily link vehicles and length
	network = my_project.current_scenario.get_network()
	length_df = get_link_attribute('length', network)
	daily_vol = get_link_attribute('@tveh', network) 
	link_df = pd.merge(length_df, daily_vol)

	return link_df   

def write_link_counts(my_project, tod):
	'''Write bike link volumes to file for comparisons to counts '''

	my_project.change_active_database(tod)

	network = my_project.current_scenario.get_network()

	# Load bike count data from file
	bike_counts = pd.read_csv(bike_count_data)

	# Load edges file to join proper node IDs
	edges_df = pd.read_csv(edges_file)

	df = bike_counts.merge(edges_df, on=['INode','JNode'])

	list_model_vols = []

	for row in df.index:
		i = df.iloc[row]['NewINode']
		j = df.loc[row]['NewJNode']
		link = network.link(i, j)
		x = {}
		x['EmmeINode'] = i
		x['EmmeJNode'] = j
		x['gdbINode'] = df.iloc[row]['INode']
		x['gdbeJNode'] = df.iloc[row]['JNode']
		if link != None:
			x['bvol' + tod] = link['@bvol']
		else:
			x['bvol' + tod] = None
		list_model_vols.append(x)
	print len(list_model_vols)

	df_count =  pd.DataFrame(list_model_vols)

	if os.path.exists(bike_link_vol):
		'''append column to existing TOD results'''
		df = pd.read_csv(bike_link_vol)
		df['bvol'+tod] = df_count['bvol'+tod]
		df.to_csv(bike_link_vol,index=False) 
	else:
		df_count.to_csv(bike_link_vol,index=False) 

def main():
	
	print 'running bike model'

	# Check for daily bank; create if it does not exist
	if not os.path.isfile('banks/daily/emmebank'):
		subprocess.call([sys.executable, 'scripts/summarize/standard/daily_bank.py'])

	# Remove any existing results
	if os.path.exists(bike_link_vol):
		try:
		    os.remove(bike_link_vol)
		except OSError:
		    pass

	filepath = r'projects/' + master_project + r'/' + master_project + '.emp'
	my_project = EmmeProject(filepath)

	# Extract AADT from daily bank
	link_df = get_aadt(my_project)

	# Calculate generalized biking travel time for each link
	calc_bike_weight(my_project, link_df)

	# Assign all AM trips (unable to assign trips without transit networks)
	for tod in bike_assignment_tod:
		print 'assigning bike trips for: ' + str(tod)
		bike_assignment(my_project, tod)

		# Write link volumes
		write_link_counts(my_project, tod)

if __name__ == "__main__":
	main()