import os, sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
import collections
import h5py
import re
import time
import pandas as pd
import numpy as np 
import pandana as pdna
import inro.emme.database.emmebank as _eb
from pyproj import Proj, transform
from input_configuration import base_year


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

def get_weighted_jobs(household_data, new_column_name):
    for res_name in res_name_list:
          weighted_res_name = new_column_name + res_name
          household_data[weighted_res_name] = household_data[res_name]*household_data['HH_P']
          # print weighted_res_name
    return household_data

def get_average_jobs(household_data, geo_boundry, new_columns_name):
    data = household_data.groupby([geo_boundry]).sum()
    data.reset_index(inplace = True)
    for res_name in res_name_list: 
         weighted_res_name = 'HHweighted_' + res_name
         averaged_res_name = new_columns_name + res_name
         data[averaged_res_name] = data[weighted_res_name]/data['HH_P']
    return data

def get_average_jobs_transit(transit_data, geo_attr, parcel_attributes_list):
    """ Calculate the weighted average number of jobs available across a geography. """

    for attr in parcel_attributes_list: 
        # print 'process attribute: ', attr
        
        # Calculated weight values
        weighted_attr = 'HHweighted_' + attr
        transit_data[weighted_attr] = transit_data['HH_P']*transit_data[attr]
    
    # Group results by geographic defintion
    transit_data_groupby = transit_data.groupby([geo_attr]).sum()
    # Make sure geography has at least 1 household so we can compute a weighted average
    transit_data_groupby['HH_P'] = transit_data_groupby['HH_P'].replace(0,1)
    transit_data_groupby.reset_index(inplace = True)
    for attr in parcel_attributes_list: 
        weighted_attr = 'HHweighted_' + attr
        averaged_attr = 'HHaveraged_' + attr
        transit_data_groupby[averaged_attr] = transit_data_groupby[weighted_attr]/transit_data_groupby['HH_P']
    return transit_data_groupby

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

def bike_walk_jobs_access(links, nodes, parcel_df, parcel_geog, distances, geo_list):
    """ Calculate weighted average numbers of jobs available to a parcel by mode, within a max distance."""

    parcel_attributes = {"sum": ['EMPTOT_P']}

    # assign impedance
    imp = pd.DataFrame(links.Shape_Length)
    imp = imp.rename(columns = {'Shape_Length':'distance'})

    # create pandana network
    net = pdna.network.Network(nodes.x, nodes.y, links.from_node_id, links.to_node_id, imp)

    for dist in distances:
        # print dist
        net.precompute(dist)

    # assign network nodes to parcels, for buffer variables
    assign_nodes_to_dataset(parcel_df, net, 'node_ids', 'XCOORD_P', 'YCOORD_P')
    x, y = parcel_df.XCOORD_P, parcel_df.YCOORD_P
    parcel_df['node_ids'] = net.get_node_ids(x, y)

    # start processing attributes
    newdf = None
    for fun, attrs in parcel_attributes.items():    
        for attr in attrs:
            net.set(parcel_df.node_ids, variable=parcel_df[attr], name=attr)    
            res = process_net_attribute(net, attr, fun, distances)
            if newdf is None:
                newdf = res
            else:
                newdf = pd.merge(newdf, res, on="node_ids", copy=False)

    # parcel level jobs - weighted
    new_parcel_df = pd.merge(newdf, parcel_df[['node_ids', 'HH_P'] + geo_list], on="node_ids", copy=False)

    # Append results to initally empty df
    df = pd.DataFrame()

    for geo in geo_list:
        # print 'processing', geo
        new_parcel_df = get_weighted_jobs(new_parcel_df, 'HHweighted_')
        # flag the minority tracts
        new_parcel_df_groupby = get_average_jobs(new_parcel_df, geo, 'HHaveraged_')

        _df = new_parcel_df_groupby[[geo] + ['HHaveraged_EMPTOT_P_1','HHaveraged_EMPTOT_P_3']]
        _df.columns = ['geography_value', 'jobs_1_mile_walk','jobs_3_mile_bike']
        _df['geography_group'] = geo
        df = df.append(_df)

    #df = pd.melt(df, 'Geography', var_name='Data Item')
    #df['Grouping'] = 'Total'
    #df.rename(columns={'value':'Value'},inplace=True)

    return df

def transit_jobs_access(geo_df, parcel_attributes_list, minority_df, time_max, geo_list, model_path, geo_boundry):
    """ Calculate weighted average numbers of jobs available to a parcel by mode, within a max distance."""
    tract_dict = geo_df.set_index(['parcel_id']).to_dict()['census_tract']
    taz_dict = geo_df.set_index(['parcel_id']).to_dict()['TAZ_P']
    county_dict = geo_df.set_index(['parcel_id']).to_dict()['county_id']

    # organize origin information
    origin_df = pd.DataFrame(geo_df.groupby(['parcel_id'])['HH_P'].sum())
    origin_df.reset_index(inplace=True)
    origin_df['taz_id'] = origin_df['parcel_id'].map(taz_dict) #need TAZ to join with transit time table 

    # organize destination information
    dest_df = pd.DataFrame(geo_df.groupby(['TAZ_P'])[parcel_attributes_list].sum())
    dest_df.reset_index(inplace=True)
    dest_df['TAZ_P'] = dest_df['TAZ_P'].astype('object')

    # extract transit travel time from emme matrices from AM time period
    bank = _eb.Emmebank(os.path.join(model_path, 'Banks/7to8/emmebank'))
    transit_time_df = get_transit_information(bank)
    transit_hh_emp = process_transit_attribute(transit_time_df, time_max, parcel_attributes_list, origin_df, dest_df, tract_dict, county_dict, taz_dict)

    # flag the minority tracts
    transit_hh_emp = transit_hh_emp.merge(minority_df, left_on = 'census_tract', right_on = 'GEOID10', how = 'left')

    # Append results to initally empty df
    df = pd.DataFrame()

    for geo in geo_list:

        average_jobs_df = get_average_jobs_transit(transit_hh_emp, geo_boundry[geo], parcel_attributes_list) 

        _df = average_jobs_df[[geo_boundry[geo]] + ['HHaveraged_EMPTOT_P']]
        _df['geography_group'] = geo
        _df.columns = ['Geography', 'Value','geography_group']
        df = df.append(_df)

    df['Grouping'] = 'Total'
    df = label_df(df)
    df['Data Item'] = 'Jobs within 45-min Transit Trip'

    return df

def main():

    output_dir = r'outputs/access'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Define time buffer for transit - caclulate available jobs at this travel time or less
    time_max = 45

    geo_list = ['CountyName','region','GrowthCenterName', 'rg_proposed']
    equity_geogs = ['youth','elderly','english','racial','poverty','disability']
    for equity_geog in equity_geogs:
        for geog_type in ['_geog_vs_reg_total','_geog_vs_50_percent']:
            geo_list.append(equity_geog+geog_type)

    parcel_attributes_list = ['EMPTOT_P']
    
    global res_name_list
    res_name_list = []

    distances = { # miles to feet; 
                 #1: 2640, # 0.5 mile
                 1: 5280, # 1 mile
                 3: 15840 # 3 miles
                 }

    parcel_df = pd.read_csv(r'inputs/scenario/landuse/parcels_urbansim.txt', delim_whitespace=True)
    #parcel_df['region'] = 1
    nodes = pd.read_csv(r'inputs/base_year/all_streets_nodes.csv')
    nodes.set_index('node_id', inplace= True)    # required for newer version of pandana
    links = pd.read_csv(r'inputs/base_year/all_streets_links.csv', index_col=None)

    # Load geography lookups and join to parcel data
    parcel_geog = pd.read_sql_table('parcel_'+base_year+'_geography', 'sqlite:///inputs/db/soundcast_inputs.db')
    parcel_geog['region'] = 1
    parcel_df = pd.merge(parcel_df, parcel_geog, left_on='PARCELID', right_on='ParcelID', how='left')
    #geo_df = parcel_df.copy()    # Store clean version of parcels for use with transit calcs

    #######################################################
    # Access to Jobs by Walking and Biking (via all-streets network)
    #######################################################

    df = bike_walk_jobs_access(links, nodes, parcel_df, parcel_geog, distances, geo_list)
    df.to_csv(os.path.join(output_dir,'walk_bike_jobs_access.csv'))

    #######################################################
    # Access to Jobs by Transit (via TAZ-based skims)
    #######################################################

    # Parcel variables that should be summarized; only total jobs are considered currently but jobs by sector could be included
    parcel_attributes_list = ['EMPTOT_P']

    # Work with only necessary cols
    origin_df = parcel_df[['PARCELID','TAZ_P','HH_P']]

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
    dest_transit = transit_time_df.merge(dest_df, left_on='to', right_on='TAZ_P', how='left')
    dest_transit = dest_transit.groupby(dest_transit['from'])[parcel_attributes_list].sum()
    
    dest_transit.reset_index(inplace=True)

    origin_dest = origin_df.merge(dest_transit, left_on='TAZ_P', right_on='from', how = 'left') 

    # groupby destination information by origin geo id 
    origin_dest_emp = pd.DataFrame(origin_dest.groupby('PARCELID')[parcel_attributes_list+['HH_P']].sum())
    origin_dest_emp.reset_index(inplace=True)

    # get the origin geography level household info
    transit_hh_emp = origin_dest_emp.merge(parcel_geog[geo_list+['ParcelID']], left_on='PARCELID', right_on='ParcelID', how='left')

        # Append results to initally empty df
    df = pd.DataFrame()
    for geo in geo_list:

        average_jobs_df = get_average_jobs_transit(transit_hh_emp, geo, parcel_attributes_list) 

        _df = average_jobs_df[[geo] + ['HHaveraged_EMPTOT_P']]
        _df.loc[:,'geography_group'] = geo
        _df.columns = ['geography', 'value','geography_group']
        df = df.append(_df)

    df.to_csv(os.path.join(output_dir,'transit_jobs_access.csv'))

if __name__ == "__main__":
    main()
