import pandana as pdna
from pandana.loaders import osm
import numpy as np
import os
import pandas as pd
import misc

def load_network(precompute=None, file_name=network_name):
    # load OSM from hdf5 file
    store = pd.HDFStore(os.path.join(misc.data_dir(), file_name), "r")
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
    store = pd.HDFStore(os.path.join(misc.data_dir(), file_name), "r")
    network.addons = {}    
    for attr in map(lambda x: x.replace('/', ''), store.keys()):
        network.addons[attr] = pd.DataFrame({"node_id": network.node_ids.values}, index=network.node_ids.values)
        tmp = store[attr].drop_duplicates("node_id")
        tmp["has_poi"] = np.ones(tmp.shape[0], dtype="bool8")
        network.addons[attr] = pd.merge(network.addons[attr], tmp, how='left', on="node_id")
        network.addons[attr].set_index('node_id', inplace=True)
    
def assign_nodes_to_dataset(dataset, network, x_name="long", y_name="lat"):
    """Adds an attribute node_ids to the given dataset."""
    x, y = dataset["long"], dataset["lat"]   
    # set attributes to nodes
    dataset["node_ids"] = network.get_node_ids(x, y)    
    
def x_node_intersections(waynodes, x=[1,2,3,4], last_open=False):
    """
    Returns a set of all the x-node intersections.

    Parameters
    ----------
    waynodes : pandas.DataFrame
        Mapping of way IDs to node IDs as returned by `ways_in_bbox`.

    Returns
    -------
    intersections : set
        Node IDs that appear in x ways.

    """
    df = None
    counts = waynodes.node_id.value_counts()
    res = {}
    for xx in x:
        if last_open and xx == x[-1]:
            res["%s-way" % xx] = counts >= xx
        else:
            res["%s-way" % xx] = counts == xx
    res["counts"] = counts
    df = pd.concat(res, axis=1, ignore_index=False)
    return df
