# Load buffered parcel data and summarize by Regional Growth Center
import pandana as pdna
import pandas as pd
import numpy as np
import os, sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),'scripts/accessibility'))
from accessibility_configuration import *
from standard_summary_configuration import *
from emme_configuration import *
import input_configuration
import re
import sys
from pyproj import Proj, transform
import h5py 

print "running parcel summary"

def assign_nodes_to_dataset(dataset, network, column_name, x_name, y_name):
    """Adds an attribute node_ids to the given dataset."""
    dataset[column_name] = network.get_node_ids(dataset[x_name].values, dataset[y_name].values)
   
def process_dist_attribute(parcels, network, name, x, y):
    network.set_pois(name, x, y)
    res = network.nearest_pois(max_dist, name, num_pois=1, max_distance=999)
    res[res != 999] = (res[res != 999]/5280.).astype(res.dtypes) # convert to miles
    res_name = "dist_%s" % name
    parcels[res_name] = res.loc[parcels.node_ids].values

    return parcels

def parcel_summary():
	"""
	Summarize parcels by RGC for quick check of min, mean, max.
	"""
	main_dir = os.path.abspath('')
	try:
	    parcels = pd.read_table(main_dir + "/inputs/" + buffered_parcels, sep=' ')
	except:
	    print "Missing 'buffered_parcels.dat'"

	try:
	    map = pd.read_csv(main_dir + "/scripts/summarize/inputs/" + parcel_urbcen_map)
	except:
	    print "Missing 'parcels_in_urbcens.csv'"

	# Join the urban center location to the parcels file
	parcels = pd.merge(parcels, map, left_on='parcelid', right_on='hhparcel')
	print "Loading parcel data to summarize..."

	# Summarize parcel fields by urban center
	mean_by_urbcen = pd.DataFrame(parcels.groupby('NAME').mean())
	min_by_urbcen = pd.DataFrame(parcels.groupby('NAME').min())
	max_by_urbcen = pd.DataFrame(parcels.groupby('NAME').max())
	std_by_urbcen = pd.DataFrame(parcels.groupby('NAME').std())

	# Write results to separate worksheets in an Excel file
	excel_writer = pd.ExcelWriter(main_dir + '/outputs/' + parcel_file_out)

	mean_by_urbcen.to_excel(excel_writer=excel_writer, sheet_name='Mean')
	min_by_urbcen.to_excel(excel_writer=excel_writer, sheet_name='Min')
	max_by_urbcen.to_excel(excel_writer=excel_writer, sheet_name='Max')
	std_by_urbcen.to_excel(excel_writer=excel_writer, sheet_name='Std Dev')

def transit_access():
	transit_df = pd.DataFrame.from_csv(transit_stops_name)
	
	# Load parcel data
	parcels = pd.DataFrame.from_csv(parcels_file_name, sep = " ", index_col=None )

	# Check for missing data
	for col_name in parcels.columns:
	    # daysim does not use EMPRSC_P
		if col_name != 'EMPRSC_P':
			if parcels[col_name].sum() == 0:
				print col_name + ' column sum is zero! Exiting program.'
				sys.exit(1)

	# nodes must be indexed by node_id column, which is the first column
	nodes = pd.DataFrame.from_csv(nodes_file_name)
	links = pd.DataFrame.from_csv(links_file_name, index_col = None )

	# assign impedence
	imp = pd.DataFrame(links.Shape_Length)
	imp = imp.rename(columns = {'Shape_Length':'distance'})

	# create pandana network
	net = pdna.network.Network(nodes.x, nodes.y, links.from_node_id, links.to_node_id, imp)
	for dist in distances:
		net.precompute(dist)

	# set the number of pois on the network for the distance variables (transit + 1 for parks)
	net.init_pois(len(transit_modes)+1, max_dist, 1)

	# assign network nodes to parcels, for buffer variables
	assign_nodes_to_dataset(parcels, net, 'node_ids', 'XCOORD_P', 'YCOORD_P')

	# calc the distance from each parcel to nearest transit stop by type
	for attr in ['frequent']:
		print attr
		# get the records/locations that have this type of transit:
		transit_type_df = transit_df.loc[(transit_df[attr] == 1)]
		parcels = process_dist_attribute(parcels, net, attr, transit_type_df["x"], transit_type_df["y"])
		#Some parcels share the same network node and therefore have 0 distance. Recode this to .01.
		field_name = "dist_%s" % attr
		parcels.ix[parcels[field_name]==0, field_name] = .01

	parcels.to_csv(transit_access_outfile)

if __name__ == '__main__':
	parcel_summary()
	transit_access()