import pandana as pdna
from accessibility_configuration import *
from emme_configuration import *
#from accessibility_utils import load_network, load_network_addons, assign_nodes_to_dataset
import pandas as pd
import numpy as np
import os
import re
import misc
#import dataset
#import simulation as sim
from pyproj import Proj, transform

def load_network(precompute=None, file_name=network_name):
    # load OSM from hdf5 file
    store = pd.HDFStore(file_name, "r")
    nodes = store.nodes
    edges = store.edges
    nodes.index.name = "index" # something that Synthicity wanted to fix
    # create the network
    net=pdna.Network(nodes["x"], nodes["y"], edges["from"], edges["to"], edges[["distance"]])
    if precompute is not None:
        for dist in precompute:
            net.precompute(dist)
    return net

def load_network_addons(network, file_name=network_add_ons):
    store = pd.HDFStore(file_name, "r")
    network.addons = {}    
    for attr in map(lambda x: x.replace('/', ''), store.keys()):
        network.addons[attr] = pd.DataFrame({"node_id": network.node_ids.values}, index=network.node_ids.values)
        tmp = store[attr].drop_duplicates("node_id")
        tmp["has_poi"] = np.ones(tmp.shape[0], dtype="bool8")
        network.addons[attr] = pd.merge(network.addons[attr], tmp, how='left', on="node_id")
        network.addons[attr].set_index('node_id', inplace=True)
    
def assign_nodes_to_dataset(dataset, network, x_name="long", y_name="lat"):
    """Adds an attribute node_ids to the given dataset."""
    long, lat = reproject_to_wgs84(parcels.XCOORD_P.values, parcels.YCOORD_P.values)
    parcels["long"] = pd.Series(long)
    parcels["lat"] = pd.Series(lat)
    x, y = dataset["long"], dataset["lat"]   
    # set attributes to nodes
    dataset["node_ids"] = network.get_node_ids(x, y)   
    

def reproject_to_wgs84(longitude, latitude, ESPG = "+init=EPSG:2926", conversion = 0.3048006096012192):
    '''
    Converts the passed in coordinates from their native projection (default is state plane WA North-EPSG:2926)
    to wgs84. Returns a two item tuple containing the longitude (x) and latitude (y) in wgs84. Coordinates
    must be in meters hence the default conversion factor- PSRC's are in state plane feet.  
    '''    #print longitude, latitude
    # Remember long is x and lat is y!
    prj_wgs = Proj(init='epsg:4326')
    prj_sp = Proj(ESPG)

    # Need to convert feet to meters:
    longitude = longitude * conversion
    latitude = latitude * conversion
    x, y = transform(prj_sp, prj_wgs, longitude, latitude)

    return x, y

def process_net_attribute(network, attr, fun):
    print "Processing %s" % attr
    newdf = None
    for dist_index, dist in distances.iteritems():        
        res_name = "%s_%s" % (re.sub("_?p$", "", attr), dist_index) # remove '_p' if present
        aggr = network.aggregate(dist, type=fun, decay="exponential", name=attr)
        if newdf is None:
            newdf = pd.DataFrame({res_name: aggr, "node_ids": aggr.index.values})
        else:
            newdf[res_name] = aggr
    return newdf

def process_dist_attribute(parcels, network, name, x, y):
    network.set_pois(name, x, y)
    res = network.nearest_pois(max_dist, name, num_pois=1, max_distance=999)
    res[res <> 999] = (res[res <> 999]/1000. * 0.621371).astype(res.dtypes) # convert to miles
    res_name = "dist_%s" % name
    parcels[res_name] = res.loc[parcels.node_ids].values
    return parcels

def process_parcels(parcels, transit_df):
    

    # Add a field so you can compute the weighted average number of spaces later
    parcels['daily_weighted_spaces'] = parcels['PARKDY_P']*parcels['PPRICDYP']
    parcels['hourly_weighted_spaces'] = parcels['PARKHR_P']*parcels['PPRICHRP']

    # Start processing attributes
    newdf = None
    for fun, attrs in parcel_attributes.iteritems():    
        for attr in attrs:
            net.set(parcels.node_ids, variable=parcels[attr], name=attr)    
            res = process_net_attribute(net, attr, fun)
            if newdf is None:
                newdf = res
            else:
                newdf = pd.merge(newdf, res, on="node_ids", copy=False)

    for new_name, attr in network_attributes.iteritems():    
        net.set(net.node_ids, variable=net.addons[attr]["has_poi"].values, name=new_name)
        newdf = pd.merge(newdf, process_net_attribute(net, new_name, "sum"), on="node_ids", copy=False)
    
    for new_name, attr in intersections.iteritems():
        net.set(net.node_ids, variable=net.addons["intersections"][attr].values, name=new_name)
        newdf = pd.merge(newdf, process_net_attribute(net, new_name, "sum"), on="node_ids", copy=False)

    # Parking prices are weighted average, weighted by the number of spaces in the buffer, divided by the total spaces
    newdf['PPRICDYP_1'] = newdf['daily_weighted_spaces_1']/newdf['PARKDY_P_1']
    newdf['PPRICDYP_2'] = newdf['daily_weighted_spaces_2']/newdf['PARKDY_P_2']
    newdf['PPRICHRP_1'] = newdf['hourly_weighted_spaces_1']/newdf['PARKHR_P_1']
    newdf['PPRICHRP_2'] = newdf['hourly_weighted_spaces_2']/newdf['PARKHR_P_2']

    parcels.reset_index(level=0, inplace=True)
    parcels = pd.merge(parcels, newdf, on="node_ids", copy=False)

    net.init_pois(len(pois)+1, max_dist, 1)

    for new_name, attr in pois.iteritems():
        print new_name
        # get the records/locations that have this type of transit:
        transit_type_df = transit_df.loc[(transit_df[attr] == 1)]
        parcels=process_dist_attribute(parcels, net, new_name, transit_type_df["stop_lon"], transit_type_df["stop_lat"])

    # distance to park
    parcel_idx_park = np.where(parcels.NPARKS > 0)[0]
    parcels=process_dist_attribute(parcels, net, "park", parcels.long[parcel_idx_park], parcels.lat[parcel_idx_park])

    return parcels
  

def clean_up(parcels):
    # we just had these columns to get the weighted average, now drop them
    del parcels['daily_weighted_spaces']
    del parcels['hourly_weighted_spaces']
    del parcels['daily_weighted_spaces_1']
    del parcels['daily_weighted_spaces_2']
    del parcels['hourly_weighted_spaces_1']
    del parcels['hourly_weighted_spaces_2']
    
    # stupidly the naming convention suddenly changes for Daysim, so we have to be consistent
    rename = {}
    for column in parcels.columns:
        if '_P_' in column:
            new_col = re.sub('_P', '', column)
            rename[column] = new_col
    parcels = parcels.rename(columns = rename)
    parcels = parcels.rename(columns ={'PPRICDYP_1': 'PPRICDY1', 'PPRICHRP_1': 'PPRICHR1','PPRICDYP_2': 'PPRICDY2','PPRICHRP_2': 'PPRICHR2'})

    # Daysim needs the column names to be lower case
    parcels.columns = map(str.lower, parcels.columns)
    parcels=parcels.fillna(0)
    parcels_final = pd.DataFrame()
    
    # currently Daysim just uses dist_lbus as actually meaning the minimum distance to transit, so we will match that setup for now.
    print 'updating the distance to local bus field to actually hold the minimum to any transit because that is how Daysim is currently reading the field' 
    parcels['dist_lbus'] = parcels[['dist_lbus', 'dist_ebus', 'dist_crt', 'dist_fry', 'dist_lrt']].min(axis=1)


    for col in col_order:
        parcels_final[col] = parcels[col]
    
    parcels_final[u'xcoord_p'] = parcels_final[u'xcoord_p'].astype(int)
    return parcels_final


#def main():
    #read in data
parcels = pd.DataFrame.from_csv(parcels_file_name, sep = " ", index_col = None )
transit_df = pd.DataFrame.from_csv(transit_stops_name,  index_col = False)

    # load network & the various addons and assign parcels to the network 
net = load_network(precompute=distances)
load_network_addons(network=net)
assign_nodes_to_dataset(parcels, net)

parcels = process_parcels(parcels, transit_df)

parcels_done = clean_up(parcels)
parcels_done.to_csv(output_parcels, index = False, sep = ' ')

#if __name__ == "__main__":
#    main()
