import pandana as pdna
import pandas as pd
import numpy as np
import os, sys
os.chdir(r"D:\stefan\sc_calibration\soundcast")
#from accessibility_configuration import *
from emme_configuration import *
import re
import sys
from pyproj import Proj, transform
import h5py 

parcels_file_name = 'inputs/accessibility/parcels_urbansim.txt'
nodes_file_name = 'inputs/accessibility/all_streets_nodes_2014.csv'
links_file_name = 'inputs/accessibility/all_streets_links_2014.csv'
max_dist = 24140.2

def assign_nodes_to_dataset(dataset, network, column_name, x_name, y_name):
    """Adds an attribute node_ids to the given dataset."""
    dataset[column_name] = network.get_node_ids(dataset[x_name].values, dataset[y_name].values)
   
def h5_to_df(h5_set, columns = None):
    col_dict = {}
    if columns == None:
        columns = h5_set.keys()
    for col in columns:
        my_array = np.asarray(h5_set[col])
        print col, len(my_array)
        col_dict[col] = my_array
    df = pd.DataFrame(col_dict)
    return df
# read in data
transit_df = pd.DataFrame.from_csv('inputs/accessibility/freq_transit_stops_2040.csv')
parcels = pd.DataFrame.from_csv(parcels_file_name, sep = " ", index_col = None )
# need to get the number of people per parcel
hh_and_persons = h5py.File('inputs/hh_and_persons.h5', "r")
hh_df = h5_to_df(hh_and_persons["Household"], ['hhparcel', 'hhsize'])
hh_df = pd.DataFrame(hh_df.groupby('hhparcel').hhsize.sum(), index = None)
hh_df.reset_index(inplace = True)
# join to parcels
parcels = parcels.merge(hh_df, how = 'left', left_on = 'PARCELID', right_on = 'hhparcel')
# nodes must be indexed by node_id column, which is the first column
nodes = pd.DataFrame.from_csv(nodes_file_name)
links = pd.DataFrame.from_csv(links_file_name, index_col = None )

# get rid of circular links
links = links.loc[(links.from_node_id <> links.to_node_id)]

# assign impedance
imp = pd.DataFrame(links.Shape_Length)
imp = imp.rename(columns = {'Shape_Length':'distance'})

# create pandana network
net = pdna.network.Network(nodes.x, nodes.y, links.from_node_id, links.to_node_id, imp)

# get transit stops
#transit_df['tstops'] = 1

# assign network nodes to parcels, for buffer variables
assign_nodes_to_dataset(parcels, net, 'node_ids', 'XCOORD_P', 'YCOORD_P')

# assign network nodes to transit stops, for buffer variable
#assign_nodes_to_dataset(transit_df, net, 'node_ids', 'x', 'y')
net.init_pois(1, max_dist, 1)
net.set_pois('tstops', transit_df.x, transit_df.y)
res = net.nearest_pois(max_dist, 'tstops', num_pois=1, max_distance=999999)
res[res <> 999999] = (res[res <> 999999]/5280.).astype(res.dtypes) # convert to miles
res_name = 'dist_tstops'
parcels[res_name] = res.loc[parcels.node_ids].values
   
        #Some parcels share the same network node and therefore have 0 distance. Recode this to .01.
field_name = "dist_tstops"
parcels.ix[parcels[field_name]==0, field_name] = .01
test = parcels[(parcels.dist_tstops<=.5)]



















