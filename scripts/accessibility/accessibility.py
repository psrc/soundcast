import pandana as pdna
import pandas as pd
import numpy as np
import os
import re
import sys
from pyproj import Proj, transform


def assign_nodes_to_dataset(dataset, network, column_name, x_name, y_name):
    """Adds an attribute node_ids to the given dataset."""
    dataset[column_name] = network.get_node_ids(
        dataset[x_name].values, dataset[y_name].values
    )


def process_net_attribute(state, network, attr, fun):
    newdf = None
    for dist_index, dist in state.network_settings.accessibility_distances.items():
        res_name = "%s_%s" % (
            re.sub("_?p$", "", attr),
            dist_index,
        )  # remove '_p' if present
        aggr = network.aggregate(dist, type=fun, decay="exp", name=attr)
        if newdf is None:
            newdf = pd.DataFrame({res_name: aggr, "node_ids": aggr.index.values})
        else:
            newdf[res_name] = aggr
    return newdf


def process_dist_attribute(state, parcels, network, name, x, y):
    network.set_pois(name, x, y)
    res = network.nearest_pois(state.network_settings.max_dist, name, num_pois=1, max_distance=999)
    res[res != 999] = (res[res != 999] / 5280.0).astype(res.dtypes)  # convert to miles
    res_name = "dist_%s" % name
    parcels[res_name] = res.loc[parcels.node_ids].values
    return parcels


def process_parcels(state, parcels, transit_df, net, intersections_df):
    # Add a field so you can compute the weighted average number of spaces later
    parcels["daily_weighted_spaces"] = parcels["parkdy_p"] * parcels["ppricdyp"]
    parcels["hourly_weighted_spaces"] = parcels["parkhr_p"] * parcels["pprichrp"]

    parcel_attributes = {
    "sum": [
        "hh_p",
        "stugrd_p",
        "stuhgh_p",
        "stuuni_p",
        "empmed_p",
        "empofc_p",
        "empedu_p",
        "empfoo_p",
        "empgov_p",
        "empind_p",
        "empsvc_p",
        "empoth_p",
        "emptot_p",
        "empret_p",
        "parkdy_p",
        "parkhr_p",
        "nparks",
        "aparks",
        "daily_weighted_spaces",
        "hourly_weighted_spaces",
        ],
        "ave": ["ppricdyp", "pprichrp"],
    }

    transit_modes = {
        "lbus": "bus",
        "ebus": "express",
        "fry": "ferry",
        "crt": "commuter_rail",
        "lrt": "light_rail",
        "brt": "brt",
    }

    # Start processing attributes
    newdf = None
    for fun, attrs in parcel_attributes.items():
        for attr in attrs:
            net.set(parcels.node_ids, variable=parcels[attr], name=attr)
            res = process_net_attribute(state, net, attr, fun)
            if newdf is None:
                newdf = res
            else:
                newdf = pd.merge(newdf, res, on="node_ids", copy=False)

    # sum of bus stops in buffer
    for name in ["tstops"]:
        net.set(transit_df["node_ids"].values, transit_df[name], name=name)
        newdf = pd.merge(
            newdf, process_net_attribute(state, net, name, "sum"), on="node_ids", copy=False
        )

    # sum of intersections in buffer
    for name in ["nodes1", "nodes3", "nodes4"]:
        net.set(intersections_df["node_ids"].values, intersections_df[name], name=name)
        newdf = pd.merge(
            newdf, process_net_attribute(state, net, name, "sum"), on="node_ids", copy=False
        )

    # Parking prices are weighted average, weighted by the number of spaces in the buffer, divided by the total spaces
    newdf["ppricdyp_1"] = newdf["daily_weighted_spaces_1"] / newdf["parkdy_1"]
    newdf["ppricdyp_2"] = newdf["daily_weighted_spaces_2"] / newdf["parkdy_2"]
    newdf["pprichrp_1"] = newdf["hourly_weighted_spaces_1"] / newdf["parkhr_1"]
    newdf["pprichrp_2"] = newdf["hourly_weighted_spaces_2"] / newdf["parkhr_2"]

    parcels.reset_index(level=0, inplace=True)
    parcels = pd.merge(parcels, newdf, on="node_ids", copy=False)

    # set the number of pois on the network for the distance variables (transit + 1 for parks)
    net.init_pois(len(transit_modes) + 1, state.network_settings.max_dist, 1)

    # calc the distance from each parcel to nearest transit stop by type
    for new_name, attr in transit_modes.items():
        # get the records/locations that have this type of transit:
        transit_type_df = transit_df.loc[(transit_df[attr] == 1)]
        if transit_type_df[attr].sum() > 0:
            parcels = process_dist_attribute(
                state, parcels, net, new_name, transit_type_df["x"], transit_type_df["y"]
            )
        else:
            parcels[
                "dist_%s" % new_name
            ] = 999  # use max dist if no stops exist for this submode
        # Some parcels share the same network node and therefore have 0 distance. Recode this to .01.
        field_name = "dist_%s" % new_name
        parcels.loc[parcels[field_name] == 0, field_name] = 0.01
    # distance to park: set to 999 and do not use because parcels data is unreliable
    parcels["dist_park"] = 999.0

    return parcels


def clean_up(parcels):

    # Daysim requires a specific order of columns
    col_list = [
        "parcelid",
        "xcoord_p",
        "ycoord_p",
        "sqft_p",
        "taz_p",
        "lutype_p",
        "hh_p",
        "stugrd_p",
        "stuhgh_p",
        "stuuni_p",
        "empedu_p",
        "empfoo_p",
        "empgov_p",
        "empind_p",
        "empmed_p",
        "empofc_p",
        "empret_p",
        "empsvc_p",
        "empoth_p",
        "emptot_p",
        "parkdy_p",
        "parkhr_p",
        "ppricdyp",
        "pprichrp",
        "hh_1",
        "stugrd_1",
        "stuhgh_1",
        "stuuni_1",
        "empedu_1",
        "empfoo_1",
        "empgov_1",
        "empind_1",
        "empmed_1",
        "empofc_1",
        "empret_1",
        "empsvc_1",
        "empoth_1",
        "emptot_1",
        "parkdy_1",
        "parkhr_1",
        "ppricdy1",
        "pprichr1",
        "nodes1_1",
        "nodes3_1",
        "nodes4_1",
        "tstops_1",
        "nparks_1",
        "aparks_1",
        "hh_2",
        "stugrd_2",
        "stuhgh_2",
        "stuuni_2",
        "empedu_2",
        "empfoo_2",
        "empgov_2",
        "empind_2",
        "empmed_2",
        "empofc_2",
        "empret_2",
        "empsvc_2",
        "empoth_2",
        "emptot_2",
        "parkdy_2",
        "parkhr_2",
        "ppricdy2",
        "pprichr2",
        "nodes1_2",
        "nodes3_2",
        "nodes4_2",
        "tstops_2",
        "nparks_2",
        "aparks_2",
        "dist_lbus",
        "dist_ebus",
        "dist_crt",
        "dist_fry",
        "dist_lrt",
        "dist_brt",
        "raw_dist_hct",
        "raw_dist_transit",
    ]

    # Drop columns used for weighted average calculations
    parcels.drop(columns=[
        "daily_weighted_spaces",
        "hourly_weighted_spaces",
        "daily_weighted_spaces_1",
        "daily_weighted_spaces_2",
        "hourly_weighted_spaces_1",
        "hourly_weighted_spaces_2"
    ], inplace=True)

    parcels = parcels.rename(
        columns={
            "ppricdyp_1": "ppricdy1",
            "pprichrp_1": "pprichr1",
            "ppricdyp_2": "ppricdy2",
            "pprichrp_2": "pprichr2",
        }
    )

    for col in ['ppricdy1','ppricdy2','pprichr1','pprichr2']:
        parcels[col] = parcels[col].fillna(0)

    # Daysim uses dist_lbus as actually meaning the minimum distance to any transit submode
    parcels["dist_lbus"] = parcels[
        ["dist_lbus", "dist_ebus", "dist_crt", "dist_fry", "dist_lrt"]
    ].min(axis=1)

    parcels = parcels[col_list]

    parcels["xcoord_p"] = parcels["xcoord_p"].copy().astype(int)

    return parcels


def run(state):
    # read in data
    parcels = pd.read_csv("outputs/landuse/parcels_urbansim.txt", sep=" ", index_col=None)

    # check for missing data!
    for col_name in parcels.columns:
        # daysim does not use emprsc_p
        if col_name != "emprsc_p":
            if parcels[col_name].sum() == 0:
                print(col_name + " column sum is zero! Exiting program.")
                sys.exit(1)

    # Not using this field, causes bug in Daysim
    parcels.aparks = 0
    parcels.nparks = 0

    # nodes must be indexed by node_id column, which is the first column
    nodes = pd.read_csv("inputs/base_year/all_streets_nodes.csv", index_col="node_id")
    links = pd.read_csv("inputs/base_year/all_streets_links.csv", index_col=None)

    # get rid of circular links
    links = links.loc[(links.from_node_id != links.to_node_id)]

    # assign impedance
    imp = pd.DataFrame(links.Shape_Length)
    imp = imp.rename(columns={"Shape_Length": "distance"})
    links[["from_node_id", "to_node_id"]] = links[
        ["from_node_id", "to_node_id"]
    ].astype("int")

    # create pandana network
    net = pdna.network.Network(
        nodes.x, nodes.y, links.from_node_id, links.to_node_id, imp
    )
    for dist_index, dist in state.network_settings.accessibility_distances.items():
        net.precompute(dist)

    # get transit stops
    transit_df = pd.read_csv("inputs/scenario/networks/transit_stops.csv")
    transit_df["tstops"] = 1

    # intersections:
    # combine from and to columns
    all_nodes = pd.DataFrame(
        pd.concat([net.edges_df["from"], net.edges_df["to"]], axis=0),
        columns=["node_ids"],
    )

    # get the frequency of each node, which is the number of intersecting ways
    intersections_df = pd.DataFrame(all_nodes["node_ids"].value_counts())
    intersections_df = intersections_df.rename(columns={"count": "edge_count"})
    intersections_df.reset_index(0, inplace=True)
    # intersections_df = intersections_df.rename(columns={"index": "node_ids"})

    # add a column for each way count
    intersections_df["nodes1"] = np.where(intersections_df["edge_count"] == 1, 1, 0)
    intersections_df["nodes3"] = np.where(intersections_df["edge_count"] == 3, 1, 0)
    intersections_df["nodes4"] = np.where(intersections_df["edge_count"] > 3, 1, 0)

    # assign network nodes to parcels, for buffer variables
    assign_nodes_to_dataset(parcels, net, "node_ids", "xcoord_p", "ycoord_p")

    # assign network nodes to transit stops, for buffer variable
    assign_nodes_to_dataset(transit_df, net, "node_ids", "x", "y")

    # run all accessibility measures
    parcels = process_parcels(state, parcels, transit_df, net, intersections_df)

    # Report a raw distance to HCT and all transit before calibration

    parcels["raw_dist_hct"] = parcels[
        ["dist_ebus", "dist_crt", "dist_fry", "dist_lrt", "dist_brt"]
    ].min(axis=1)
    parcels["raw_dist_transit"] = parcels[
        ["dist_lbus", "dist_ebus", "dist_crt", "dist_fry", "dist_lrt", "dist_brt"]
    ].min(axis=1)

    # reduce percieved walk distance for light rail and ferry. This is used to calibrate to 2014 boardings & transfer rates. 
    parcels.loc[parcels.dist_lrt<=1, 'dist_lrt'] = parcels['dist_lrt'] * state.network_settings.light_rail_walk_factor
    parcels['dist_fry'] * state.network_settings.ferry_walk_factor
    parcels_done = clean_up(parcels)

    parcels_done.to_csv("outputs/landuse/buffered_parcels.txt", index=False, sep=" ")