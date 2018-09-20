#################################### NETWORK SUMMARY ####################################
network_summary_files = ['6to7_transit', '7to8_transit', '8to9_transit', '9to10_transit',
                         'counts_output', 'network_summary']
network_summary_project = 'Projects/LoadTripTables/LoadTripTables.emp'
project = 'Projects/LoadTripTables/LoadTripTables.emp'
report_output_location = 'Outputs/network'
fac_type_dict = {'highway' : 'ul3 = 1 or ul3 = 2',
                 'arterial' : 'ul3 = 3 or ul3 = 4 or ul3 = 6',
                 'connectors' : 'ul3 = 5'}
extra_attributes_dict = {'@tveh' : 'total vehicles', 
                         '@mveh' : 'medium trucks', 
                         '@hveh' : 'heavy trucks', 
                         '@vmt' : 'vmt',\
                         '@vht' : 'vht', 
                         '@trnv' : 'buses in auto equivalents',
                         '@ovol' : 'observed volume', 
                         '@bveh' : 'number of buses'}
transit_extra_attributes_dict = {'@board' : 'total boardings', '@timtr' : 'transit line time'}

income_bins = [-9999,25000,100000,9999999999]
income_bin_labels = ['low','medium','high']

tod_lookup = {'5to6' : 5, '6to7' : 6, '7to8' : 7, '8to9' : 8, '9to10' : 9, 
              '10to14' : 10, '14to15' : 14, '15to16' : 15, '16to17' : 16, 
              '17to18' : 17, '18to20' : 18, '20to5' : 20}

county_id = {1: 'King',
            2: 'Kitsap',
            3: 'Pierce',
            4: 'Snohomish'}

veh_totals = {'2014': 3176086, '2040': 3982578.1, '2050': 4326300}

# Base year distribution of vehicle ownership by county
vehs_by_county = {
    'King': 1625471,
    'Kitsap': 231231,
    'Pierce': 675660,
    'Snohomish': 643724
}

# List of pollutants to be summarized for summer
# All other are to be summarized for winter season
summer_list = [87]


speed_bins = [-999999, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5, 67.5, 72.5, 999999] 
speed_bins_labels =  range(1, len(speed_bins))

fac_type_lookup = {0:0, 1:4, 2:4, 3:5, 4:5, 5:5, 6:3, 7:5, 8:0}

# Map pollutant name and ID
pollutant_map = {
    '1': 'Total Gaseous HCs',
    '2': 'CO',
    '3': 'NOx',
    '5': 'Methane',
    '6': 'N20',
    '79': 'Non-methane HCs',
    '87': 'VOCs',             
    '90': 'Atmospheric CO2',
    '91': 'Total Energy',
    '98': 'CO2 Equivalent',
    'PM10': 'PM10 Total',
    'PM25': 'PM25 Total',
    '100': 'PM10 Exhaust',
    '106': 'PM10 Brakewear',
    '107': 'PM10 Tirewear',
    '110': 'PM25 Exhaust',
    '112': 'Elemental Carbon',
    '115': 'Sulfate Particulate',
    '116': 'PM25 Brakewear',
    '117': 'PM25 Tirewear',   
    '118': 'Composite NonECPM',
    '119': 'H20 Aerosol'
}

# Input Files:
counts_file = r'scripts/summarize/inputs/network_summary/TrafficCounts_Mid.txt'
aadt_counts_file = r'scripts/summarize/inputs/network_summary/soundcast_aadt.csv'
tptt_counts_file = r'scripts/summarize/inputs/network_summary/soundcast_tptt.csv'
# Output Files: 
daily_network_fname = 'outputs/network/daily_network_results.csv'
net_summary_file = 'network_summary.csv'
counts_output_file = 'counts_output.csv'
screenlines = 'screenline_volumes.csv'
screenlines_file = 'scripts/summarize/inputs/network_summary/screenlines_2014.csv'
uc_list = ['@svtl1', '@svtl2', '@svtl3', '@h2tl1', '@h2tl2', '@h2tl3', 
           '@h3tl1', '@h3tl2', '@h3tl3', '@lttrk', '@mveh', '@hveh', '@bveh']

output_list = ['prod_att.csv', 'gq_prod_att.csv', 'network_summary.csv', 'counts_output.csv', 'daysim_outputs.h5',
               'screenline_volumes']

########## Land Use Summary ##################################################
out_lu_summary = r'outputs/landuse/landuse_summary.xlsx'
households_persons_file = r'inputs/scenario/landuse/hh_and_persons.h5'

######## Truck Counts ########################################################
truck_counts_file = r'scripts/summarize/inputs/network_summary/truck_counts_2014.csv' 

######## Observed Transit Boardings############################################
observed_boardings_file = 'scripts/summarize/inputs/network_summary/transit_boardings_2014.csv'
light_rail_boardings = r'scripts/summarize/inputs/network_summary/light_rail_boardings.csv'

# Grouped outputs

# To compare with 1 or more runs, add key as run name, value as location to main soundcast directory
# e.g., comparison_runs = {'soundcast_base': 'C:/user/soundcast_base_run', 
#                          'soundcast_2040': 'C:/user/soundcast_2040'}
comparison_runs = {}
compare_survey = True    # compare daysim results in Tableau and topsheet outputs

#### Transit Groupings ###############################################################
transit_time_group_file= 'scripts/summarize/inputs/network_summary/transit_time_groups.csv'
route_group_file = 'scripts/summarize/inputs/network_summary/transit_route_groups.csv'
special_routes_file = 'scripts/summarize/inputs/network_summary/transit_special_routes.csv'


##### Output File Locations ######################################################
network_summary_dir = 'outputs/network/network_summary.xlsx'
validation_summary_dir = 'outputs/network/validation.xlsx'
transit_summary_dir = 'outputs/transit/transit_summary.xlsx'

roadway_summary = 'outputs/network/roadway_summary.xlsx'
transit_summary_out = 'outputs/transit/transit_summary.xlsx'

# Bikes
bike_link_vol = 'outputs/bike/bike_volumes.csv'
bike_count_data = 'inputs/base_year/bike_count_links.csv'
edges_file = 'inputs/scenario/bike/edges_0.txt'

# Parcel Summary
buffered_parcels = 'buffered_parcels.txt'   # Parcel data
parcel_urbcen_map = 'parcels_in_urbcens.csv'    # lookup for parcel to RGC
parcel_file_out = 'landuse/parcel_summary.xlsx'    # summary output file name
parcels_file_name = 'inputs/scenario/landuse/parcels_urbansim.txt'
nodes_file_name = 'inputs/accessibility/all_streets_nodes_2014.csv'
links_file_name = 'inputs/accessibility/all_streets_links_2014.csv'
transit_access_outfile = 'outputs/transit/freq_transit_access.csv'
max_dist = 24140.2