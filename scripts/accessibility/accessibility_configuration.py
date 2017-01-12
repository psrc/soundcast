parcels_file_name = 'inputs/accessibility/parcels_urbansim.txt'
output_parcels = 'inputs/buffered_parcels.txt'
transit_stops_name = 'inputs/accessibility/transit_stops_2014.csv'
nodes_file_name = 'inputs/accessibility/all_streets_nodes_2014.csv'
links_file_name = 'inputs/accessibility/all_streets_links_2014.csv'

max_dist = 24140.2 # 3 miles in meters

distances = { # in meters; 
              # keys correspond to suffices of the resulting parcel columns
              # ORIGINAL VALUES !!
             1: 2640, # 0.5 mile
             2: 5280 # 1 mile

             }

# These will be disaggregated from the parcel data to the network.
# Keys are the functions applied when aggregating over buffers.

parcel_attributes = {
              "sum": ["HH_P", "STUGRD_P", "STUHGH_P", "STUUNI_P", 
                      "EMPMED_P", "EMPOFC_P", "EMPEDU_P", "EMPFOO_P", "EMPGOV_P", "EMPIND_P", 
                      "EMPSVC_P", "EMPOTH_P", "EMPTOT_P", "EMPRET_P",
                      "PARKDY_P", "PARKHR_P", "NPARKS", "aparks", "daily_weighted_spaces", "hourly_weighted_spaces"],
              "ave": [ "PPRICDYP", "PPRICHRP"],
              }


col_order =[u'parcelid', u'xcoord_p', u'ycoord_p', u'sqft_p', u'taz_p', u'lutype_p', u'hh_p',
       u'stugrd_p', u'stuhgh_p', u'stuuni_p', u'empedu_p', u'empfoo_p',
       u'empgov_p', u'empind_p', u'empmed_p', u'empofc_p', u'empret_p',
       u'empsvc_p', u'empoth_p', u'emptot_p', u'parkdy_p', u'parkhr_p',
       u'ppricdyp', u'pprichrp', u'hh_1', u'stugrd_1', u'stuhgh_1',
       u'stuuni_1', u'empedu_1', u'empfoo_1', u'empgov_1', u'empind_1',
       u'empmed_1', u'empofc_1', u'empret_1', u'empsvc_1', u'empoth_1',
       u'emptot_1', u'parkdy_1', u'parkhr_1', u'ppricdy1', u'pprichr1',
       u'nodes1_1', u'nodes3_1', u'nodes4_1', u'tstops_1', u'nparks_1',
       u'aparks_1', u'hh_2', u'stugrd_2', u'stuhgh_2', u'stuuni_2',
       u'empedu_2', u'empfoo_2', u'empgov_2', u'empind_2', u'empmed_2',
       u'empofc_2', u'empret_2', u'empsvc_2', u'empoth_2', u'emptot_2',
       u'parkdy_2', u'parkhr_2', u'ppricdy2', u'pprichr2', u'nodes1_2',
       u'nodes3_2', u'nodes4_2', u'tstops_2', u'nparks_2', u'aparks_2',
       u'dist_lbus', u'dist_ebus', u'dist_crt', u'dist_fry', u'dist_lrt',
       u'dist_park']

# These are already on network (from add-ons).
# Keys correspond to the resulting parcel columns (minus suffix).
# Values correspond the names in the add-on dataset.
transit_attributes = ["tstops"]
intersections = ["nodes1", "nodes3", "nodes4"]


transit_modes = {"lbus": "bus", "ebus": "express", 
       "fry": "ferry", "crt": "commuter_rail", "lrt": "light_rail"} # will compute nearest distance to these