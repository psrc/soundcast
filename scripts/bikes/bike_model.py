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


def get_aadt(my_project):
	'''Return a dataframe of total daily traffic on each network link'''
	network = my_project.current_scenario.get_network()

	# Get dataframes for link length
	length_df = get_link_attribute('length', network)
	# Get extra attribute @tveh, which is daily total volume
	################################
	#####################
	# MULTIPLYING BY 10 BECAUSE THIS IS ONLY 7TO8 AM
	daily_vol = get_link_attribute('@tveh', network) 
	#################

	link_df = pd.merge(length_df, daily_vol)

	return link_df

def bike_facility_perception(my_project, link_df):
    '''Compute perceived travel distance impacts from bike facilities
       In the geodatabase, bike facility of 2=bicycle track and 8=separated path
       These are redefined as "premium" facilities
       Striped bike lanes receive a 2nd tier designatinon of "standard"
       All other links remain unchanced'''

    network = my_project.current_scenario.get_network()

    # Load the extra attribute data for bike facility type 
    # and replace geodb typology with the 2-tier definition
    df = get_link_attribute('@bkfac', network)
    df = df.merge(link_df)
    df = df.replace(bike_facility_crosswalk)

    # Evaluate links with bike records only
#     df = df[df['@bkfac'] != "none"]

    # Replace the facility ID with the estimated  marginal rate of substituion
    # value from Broach et al., 2012 (e.g., replace 'standard' with -0.108)
    df['facility_perception'] = df['@bkfac']
    df = df.replace(facility_dict)

#     Multiply the estimated substituion value by link length to get perceived distance 
#     reduction, and add this reduction to original length
#     df['facility_perception'] = df['length'] + df['facility_perception']*df['length']

    return df

def volume_perception(my_project, df):
    ''' For all links without bike lanes, apply a factor for the adjacent traffic (AADT) 
        This is implying that links with standard or premium bike facilities are unaffected by'''


#     # Filter for links without a premium or standard bike facility and join to a df with AADT values
#     df = df[df['@bkfac'] == 'none']
#     df = df.merge(link_df)

    # @tveh represents the AADT for each link
#     df['volume_perception'] = df['@tveh']

    # Separate the auto volume into bins with the penalties as indicator values
    df['volume_perception'] = pd.cut(df['@tveh'], bins=aadt_bins, labels=aadt_labels, right=False)
    df['volume_perception'] = df['volume_perception'].astype('int')

    # Replace the existing AADT value with the estimated perception value
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

def combine_facility_and_vol_perceptions(vol_df, bike_df):
	''' Join volume and bike facility perception dataframes '''

	vol_df = vol_df[['@bkfac', 'link_id', 'length', 'volume_perception']]
    
    # add zero values for facility perception on vol_df
    # (no vol perceptions are assigned to links with notable bike facilities)
	vol_df['facility_perception'] = np.zeros(len(vol_df))

	# Add zero values for volume perception on bike_df
	# (no facility perceptions are assigned to links with notable bike facilites)

	# Evaluate links with bike records only
	bike_df = bike_df[bike_df['@bkfac'] != "none"]

	bike_df = bike_df[['@bkfac', 'link_id', 'length', 'facility_perception']]
	bike_df['volume_perception'] = np.zeros(len(bike_df))

	# concatenate bike_df and vol_df
	df_concat = pd.concat(objs=[vol_df, bike_df])

	return df_concat

def process_slope_perception(df, my_project):
    ''' Calcualte slope perception on an Emme network dataframe
        and merge with a bike attribute dataframe to get total perceived 
        biking distance from upslope, facilities, and traffic volume'''

    network = my_project.current_scenario.get_network()

    # load in the slope term from the Emme network
    upslope_df = get_link_attribute('@upslp', network)

    # Join slope df with the length df
    upslope_df = upslope_df.merge(df)

    # Separate the slope into bins with the penalties as indicator values
    upslope_df['slope_penalty'] = pd.cut(upslope_df['@upslp'], bins=slope_bins, labels=slope_labels, right=False)
    upslope_df['slope_penalty'] = upslope_df['slope_penalty'].astype('float')
    upslope_df = upslope_df.replace(to_replace=slope_dict)

    # The incremental impact of the slope
#     upslope_df['upslope_perception'] = upslope_df['slope_penalty']*upslope_df['length']

#     # Join data to bike_attr_df to get total perceived distance
#     upslope_df = upslope_df.merge(bike_attr_df)

#     # Combine the upslope perception with the combined perception of facility type and AADT
#     upslope_df['total_dist_perception'] = upslope_df['upslope_perception'] + bike_attr_df['perceived_dist']

    return upslope_df

def write_generalized_time(df):
	''' For assignment, generalized perceived time is a link constraint
		This is computed as additional percieved distance (miles) divided by 
		average bike speed, times 60 to convert to minutes'''

	
	# Rename bike generalized time into a handle for import into Emme
	df['@bkpgt'] = df['total_time_perception']

	# Generalized time is further normalized since no negative values can be used
	# as link constraints in Emme transit assignment
	# Add the min generalized time (most negative) from all generalized time values
	min_time = abs(df['@bkpgt'].min())
	print "original min time " + str(min_time)
	df['@bkpgt'] = df['@bkpgt'] + min_time
	print abs(df['@bkpgt'].min())

	# Reformat and save as a text file in Emme format
	df['inode'] = df['link_id'].str.split('-').str[0]
	df['jnode'] = df['link_id'].str.split('-').str[1]

	filename = r'inputs/bikes/bkpgt.in'
	df[['inode','jnode', '@bkpgt']].to_csv(filename, sep=' ', index=False)

	print "results written to inputs/bikes/bkpgt.in"

def generalized_biking_time(my_project, link_df):
	''' Calculate perceived travel time for bikes
	    based on facility attributes, slope, and vehicle traffic. '''

	# Import link attributes for elevation gain and bike facilities
	process_attributes(my_project)

	# Calcualte distance perception of bike facilities
	# (Returns df of perceived distance for links with bike facilities)
	bike_fac_df = bike_facility_perception(my_project, link_df)

	# Distance perception from daily traffic volumes (
	# (Returns df of perceived distance for links w/out bike facilites) 
	vol_df = volume_perception(my_project, bike_fac_df)



	# Combine df of perceived distance for links with and without bike lanes
	# bike_attr_df = combine_facility_and_vol_perceptions(vol_df, bike_fac_df)

	# Calcualte distance perception from elevation gain (for all links)
	df = process_slope_perception(df=vol_df, my_project=my_project)

	# calculate total perceived distance
	df['total_dist_perception'] = (df['facility_perception'] + df['volume_perception'] + df['slope_penalty'])*df['length']

	# # marginal perceived distance increase (total perceived minus link length)
	# df['marginal_dist_perceived'] = (df['facility_perception'] + df['volume_perception'] + df['slope_penalty'])*df['length'] - df['length']

	# Convert perceived distance to time 
	df['total_time_perception'] = df['total_dist_perception']/avg_bike_speed*60

	# Convert distance perception to (normalized) generalized time increase 
	# and export as an Emme attribute file ('bkgpt.in')
	# (Zero addtl. gen. time represents s link with premium bike facility [e.g., separated path])
	write_generalized_time(df=df)

def bike_assignment(my_project):

	# Create attributes for perceived bike generalized time and bike volumes
	for attr in ['@bkpgt', '@bvol']:
		if attr not in my_project.current_scenario.attributes('LINK'):
			my_project.current_scenario.create_extra_attribute('LINK',attr)   

	# Create matrices for bike assignment and skim results
	for matrix in ['biket', 'bivt', 'baux', 'pbiv']:
		if matrix not in [i.name for i in my_project.bank.matrices()]:
			my_project.create_matrix(matrix, '', 'FULL')

	# Load in the bkpgt attributes
	import_attributes = my_project.m.tool("inro.emme.data.network.import_attribute_values")
	filename = r'inputs\bikes\bkpgt.in'
	import_attributes(filename, 
	                scenario = my_project.current_scenario,
	                revert_on_error=False)

	extended_assign_transit = my_project.m.tool("inro.emme.transit_assignment.extended_transit_assignment")
	bike_spec = json.load(open(r'inputs\skim_params\bike_assignment.json'))
	extended_assign_transit(bike_spec)

	print 'assignment complete, now skimming'

	skim_bike = my_project.m.tool("inro.emme.transit_assignment.extended.matrix_results")
	bike_skim_spec = json.load(open(r'inputs\skim_params\bike_skim_setup.json'))
	skim_bike(bike_skim_spec)

	# Add bike volumes to bvol network attribute
	bike_network_vol = my_project.m.tool("inro.emme.transit_assignment.extended.network_results")
	# bike_network_spec = json.load(open(r'C:\Users\Brice\bike-model\soundcast\inputs\skim_params\bike_network_setup.json'))
	bike_network_spec = json.load(open(r'inputs\skim_params\bike_network_setup.json'))
	bike_network_vol(bike_network_spec)

	# Export skims to h5
	for matrix in ["mfpbiv", "mfbaux", "mfpivt", "mfbiket"]:
		try:
			export_skims(my_project, matrix_name=matrix)
		except:
			print str(matrix) + ' exists'

	print "bike assignment complete"

def export_skims(my_project, matrix_name):
	'''Write skim matrices to h5'''

	my_store = h5py.File(r'inputs/' + bike_assignment_tod + '.h5', "r+")

	matrix_value = my_project.bank.matrix(matrix_name).get_numpy_data()
	my_store["Skims"].create_dataset(name=matrix_name, data=matrix_value)

	my_store.close()

def main():
	
	tod = '7to8'
	# Assigning one AM period for now
	filepath = r'projects//' + tod + r'/' + tod + '.emp'
	my_project = EmmeProject(filepath)

	# Add the daily emmebank to the project to extract AADT
	try:
		my_project.data_explorer.add_database(r'\Banks\Daily\emmebank')
	except:
		print "daily bank already included in the project"

	# Change active database to daily bank to extract link AADT
	# the daily db has a title of 7to8 because its copied from 7to8
	# we need to change this code in daily_bank.py sometime. For now it seems to recognize that 7to8
	# is a separate bank
	my_project.change_active_database('7to8')    
	
	# Extract link attributes to calculate generalized biking time
	link_df = get_aadt(my_project)
	link_df['@tveh'] = link_df['@tveh']*12    # to get AADT

	# Change back to AM time period
	my_project.change_active_database('7to8')   

	# Calculate generalized biking travel time for each link
	generalized_biking_time(my_project, link_df)

	# Assign trips using generalized biking time as a link weight
	bike_assignment(my_project)

if __name__ == "__main__":
	main()