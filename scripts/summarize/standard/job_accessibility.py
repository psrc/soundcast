# Calculate weighted average numbers of jobs available to a parcel by mode, within a max distance

import os, sys, shutil
import re
import numpy as np
import pandas as pd
import pandana as pdna
from input_configuration import base_year
import inro.emme.database.emmebank as _eb

def get_transit_information(bank):
    '''Extract transit travel times from skim matrices, between all zones'''

    # Bus and rail travel times are the sum of access, wait time, and in-vehicle times; Bus and rail have separate paths
    bus_time = bank.matrix('auxwa').get_numpy_data() + bank.matrix('twtwa').get_numpy_data() + bank.matrix('ivtwa').get_numpy_data() 
    rail_time = bank.matrix('auxwr').get_numpy_data() + bank.matrix('twtwr').get_numpy_data() + bank.matrix('ivtwr').get_numpy_data() 
    
    # Take the shortest transit time between bus or rail
    transit_time = np.minimum(bus_time, rail_time)
    transit_time = transit_time[0:3700, 0:3700]
    transit_time_df = pd.DataFrame(transit_time)
    transit_time_df['from'] = transit_time_df.index
    transit_time_df = pd.melt(transit_time_df, id_vars= 'from', value_vars=list(transit_time_df.columns[0:3700]), var_name = 'to', value_name='travel_time')

    # Join with parcel data; add 1 to get zone ID because emme matrices are indexed starting with 0
    transit_time_df['to'] = transit_time_df['to'] + 1 
    transit_time_df['from'] = transit_time_df['from'] + 1

    return transit_time_df

def process_transit_attribute(transit_time_data, time_max,  attr_list, origin_df, dest_df):

    # Select OD pairs with travel time under time_max threshold
    transit = transit_time_data[transit_time_data.travel_time <= time_max]
    # Remove intrazonal transit trips; assuming access will not be via transit within zones
    transit = transit[transit['from'] != transit['to']]

    # Calculate total jobs at destination TAZs
    dest_transit = transit.merge(dest_df, left_on='to', right_on='TAZ_P', how = 'left')
    dest_transit = pd.DataFrame(dest_transit.groupby(dest_transit['from'])[attr_list].sum())
    dest_transit.reset_index(inplace=True)

    origin_dest = origin_df.merge(dest_transit, left_on='TAZ_P', right_on='from', how='left') 
    # groupby destination information by origin geo id 
    origin_dest_emp = pd.DataFrame(origin_dest.groupby('PARCELID')[attr_list+['HH_P']].sum())
    origin_dest_emp.reset_index(inplace=True)

    return origin_dest_emp

def assign_nodes_to_dataset(dataset, network, column_name, x_name, y_name):
    """Adds an attribute node_ids to the given dataset."""
    dataset[column_name] = network.get_node_ids(dataset[x_name].values, dataset[y_name].values)
    
def process_net_attribute(network, attr, fun, distances):
    # print "Processing %s" % attr
    newdf = None
    for dist_index, dist in distances.items():        
        res_name = "%s_%s" % (re.sub("_?p$", "", attr), dist_index) # remove '_p' if present
        # print res_name
        res_name_list.append(res_name)
        aggr = network.aggregate(dist, type=fun, decay="flat", name=attr)
        if newdf is None:
            newdf = pd.DataFrame({res_name: aggr, "node_ids": aggr.index.values})
        else:
            newdf[res_name] = aggr
    return newdf

# Get the average jobs available for each household
def get_average_jobs(household_data, geo_boundry, new_columns_name):
    data = household_data.groupby([geo_boundry]).sum()
    data.reset_index(inplace = True)
    for res_name in res_name_list: 
         weighted_res_name = 'HHweighted_' + res_name
         averaged_res_name = new_columns_name + res_name
         data[averaged_res_name] = data[weighted_res_name]/data['HH_P']
    return data

def get_weighted_jobs(household_data, new_column_name):
    for res_name in res_name_list:
          weighted_res_name = new_column_name + res_name
          household_data[weighted_res_name] = household_data[res_name]*household_data['HH_P']
          # print weighted_res_name
    return household_data


parcel_df = pd.read_csv(r'inputs/scenario/landuse/parcels_urbansim.txt', delim_whitespace=True)
parcel_df['parcel_id'] = parcel_df['PARCELID']

#######################################################
# Access to Jobs by Transit (via TAZ-based skims)
#######################################################

# Parcel variables that should be summarized; only total jobs are considered currently but jobs by sector could be included
parcel_attributes_list = ['EMPTOT_P']

# Work with only necessary cols
origin_df = parcel_df[['PARCELID','TAZ_P']]

# Aggregate destinations by TAZ since we are used taz-level skims
dest_df = pd.DataFrame(parcel_df.groupby(['TAZ_P'])[parcel_attributes_list].sum())
dest_df.reset_index(inplace=True)
dest_df['TAZ_P'] = dest_df['TAZ_P'].astype('object')

# extract transit travel time from emme matrices from AM time period
bank = _eb.Emmebank(os.path.join(os.getcwd(), r'Banks/7to8/emmebank'))
transit_time_df = get_transit_information(bank)

# Set threshold travel time
time_max = 45
#transit_hh_emp = process_transit_attribute(transit_time_df, time_max, parcel_attributes_list, origin_df, dest_df)

# Select OD pairs with travel time under time_max threshold
transit_time_df = transit_time_df[transit_time_df.travel_time <= time_max]
# Remove intrazonal transit trips; assuming access will not be via transit within zones
transit_time_df = transit_time_df[transit_time_df['from'] != transit_time_df['to']]

# Calculate total jobs at destination TAZs
dest_transit = transit_time_df.merge(dest_df, left_on='to', right_on='TAZ_P', how = 'left')
dest_transit = pd.DataFrame(dest_transit.groupby(dest_transit['from'])[parcel_attributes_list].sum())
dest_transit.reset_index(inplace=True)

origin_dest = origin_df.merge(dest_transit, left_on='TAZ_P', right_on='from', how='left') 
# groupby destination information by origin geo id 
transit_jobs_df = pd.DataFrame(origin_dest.groupby('PARCELID')[parcel_attributes_list].sum())
transit_jobs_df.reset_index(inplace=True)

# Write to file; join in the bike and walk calculations
rename_dict = {}
for col in parcel_attributes_list:
    rename_dict[col] = col + '_access_by_transit_' + str(time_max) + '_min'
transit_jobs_df.rename(columns=rename_dict, inplace=True)

#######################################################
# Walk and Bike Access to Jobs (via all-streets network)
#######################################################
nodes = pd.read_csv(r'inputs/base_year/all_streets_nodes.csv')
nodes.set_index('node_id', inplace= True)   # Index required for pandana in py3
links = pd.read_csv(r'inputs/base_year/all_streets_links.csv',index_col=None)

parcel_geog = pd.read_sql_table('parcel_'+base_year+'_geography', 'sqlite:///inputs/db/soundcast_inputs.db')
parcel_df = parcel_df.merge(parcel_geog,left_on='PARCELID', right_on='ParcelID')

distances = { # miles to feet; 
             1: 5280, # 1 mile
             3: 15840 # 3 miles
             }

parcel_attributes = {"sum": parcel_attributes_list}

global res_name_list
res_name_list = []

# assign impedance
imp = pd.DataFrame(links.Shape_Length)
imp = imp.rename(columns = {'Shape_Length':'distance'})

# create pandana network
net = pdna.network.Network(nodes.x, nodes.y, links.from_node_id, links.to_node_id, imp)

for dist in distances:
    net.precompute(dist)
    
# assign network nodes to parcels, for buffer variables
assign_nodes_to_dataset(parcel_df, net, 'node_ids', 'XCOORD_P', 'YCOORD_P')
x, y = parcel_df.XCOORD_P, parcel_df.YCOORD_P
parcel_df['node_ids'] = net.get_node_ids(x, y)

# start processing attributes
df_bike_walk = None
for fun, attrs in parcel_attributes.items():    
    for attr in attrs:
        net.set(parcel_df.node_ids, variable=parcel_df[attr], name=attr)    
        res = process_net_attribute(net, attr, fun, distances)
        if df_bike_walk is None:
            df_bike_walk = res
        else:
            df_bike_walk = pd.merge(df_bike_walk, res, on="node_ids", copy=False)

rename_dict = {}
for col in parcel_attributes_list:
    for dist in distances.keys():
        rename_dict[col+'_'+str(dist)] = col + '_access_by_walk_bike_' + str(dist) + '_mile'
df_bike_walk.rename(columns=rename_dict, inplace=True)
df_bike_walk['PARCELID'] = df_bike_walk['node_ids']

# Merge datasets and write to file
df = df_bike_walk.merge(transit_jobs_df, on='PARCELID')
df.drop('node_ids', axis=1, inplace=True)

# Create outputs dir 
dir = r'outputs/access'
if os.path.exists(dir):
    shutil.rmtree(dir)
os.makedirs(dir)

df.to_csv(r'outputs/access/jobs_access.csv', index=False)