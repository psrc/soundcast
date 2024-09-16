import os, sys

sys.path.append(os.getcwd())
# from input_configuration import *
# import toml
# config = toml.load(os.path.join(os.getcwd(), 'configuration/input_configuration.toml'))

parcels_file_name = "inputs/scenario/landuse/parcels_urbansim.txt"
output_parcels = "outputs/landuse/buffered_parcels.txt"
nodes_file_name = "inputs/base_year/all_streets_nodes.csv"
links_file_name = "inputs/base_year/all_streets_links.csv"
transit_stops_name = "inputs/scenario/networks/transit_stops.csv"

max_dist = 24140.2  # 3 miles in meters

distances = {  # in meters;
    # keys correspond to suffices of the resulting parcel columns
    # ORIGINAL VALUES !!
    1: 2640,  # 0.5 mile
    2: 5280,  # 1 mile
}

# These will be disaggregated from the parcel data to the network.
# Keys are the functions applied when aggregating over buffers.

parcel_attributes = {
    "sum": [
        "HH_P",
        "STUGRD_P",
        "STUHGH_P",
        "STUUNI_P",
        "EMPMED_P",
        "EMPOFC_P",
        "EMPEDU_P",
        "EMPFOO_P",
        "EMPGOV_P",
        "EMPIND_P",
        "EMPSVC_P",
        "EMPOTH_P",
        "EMPTOT_P",
        "EMPRET_P",
        "PARKDY_P",
        "PARKHR_P",
        "NPARKS",
        "APARKS",
        "daily_weighted_spaces",
        "hourly_weighted_spaces",
    ],
    "ave": ["PPRICDYP", "PPRICHRP"],
}


col_order = [
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

# These are already on network (from add-ons).
# Keys correspond to the resulting parcel columns (minus suffix).
# Values correspond the names in the add-on dataset.
transit_attributes = ["tstops"]
intersections = ["nodes1", "nodes3", "nodes4"]

transit_modes = {"lbus": "bus", "ebus": "express", 
       "fry": "ferry", "crt": "commuter_rail", "lrt": "light_rail", "brt": "brt"} # will compute nearest distance to these

light_rail_walk_factor = 1

ferry_walk_factor = .5
