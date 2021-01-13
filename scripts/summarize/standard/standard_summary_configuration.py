#################################### NETWORK SUMMARY ####################################

network_results_path = r'outputs/network/network_results.csv'
iz_vol_path = r'outputs/network/iz_vol.csv'
transit_line_path = r'outputs/transit/transit_line_results.csv'
transit_node_path = r'outputs/transit/transit_node_results.csv'
transit_segment_path = r'outputs/transit/transit_segment_results.csv'
boardings_by_agency_path = r'outputs/transit/daily_boardings_by_agency.csv'
special_routes_path = r'outputs/transit/daily_boardings_special_routes.csv'
boardings_by_tod_agency_path = r'outputs/transit/boardings_by_tod_agency.csv'
boardings_by_stop_path = r'outputs/transit/boardings_by_stop.csv'
light_rail_boardings_path = r'outputs/transit/light_rail_boardings.csv'

attribute_list = ['auto_volume','data1','data2','data3','type',
'num_lanes','length','auto_time','@medium_truck','@heavy_truck','@tveh',
'@sov_inc1','@sov_inc2','@sov_inc3',
'@hov2_inc1','@hov2_inc2','@hov2_inc3','@hov3_inc1','@hov3_inc2','@hov3_inc3',
'@av_sov_inc1','@av_sov_inc2','@av_sov_inc3',
'@av_hov2_inc1','@av_hov2_inc2','@av_hov2_inc3','@av_hov3_inc1','@av_hov3_inc2','@av_hov3_inc3',
'@tnc_inc1','@tnc_inc2','@tnc_inc3','@bvol','@mveh','@hveh','@bveh',
'type','num_lanes','volume_delay_func','@countyid']


transit_extra_attributes_dict = {'@board' : 'total boardings', '@timtr' : 'transit line time'}

income_bins = [-9999,25000,100000,9999999999]
income_bin_labels = ['low','medium','high']

tod_lookup = {'5to6' : 5, '6to7' : 6, '7to8' : 7, '8to9' : 8, '9to10' : 9, 
              '10to14' : 10, '14to15' : 14, '15to16' : 15, '16to17' : 16, 
              '17to18' : 17, '18to20' : 18, '20to5' : 20}

agency_lookup = {
    1: 'King County Metro',
    2: 'Pierce Transit',
    3: 'Community Transit',
    4: 'Kitsap Transit',
    5: 'Washington Ferries',
    6: 'Sound Transit',
    7: 'Everett Transit'
}

county_map = {
        33: 'King',
        35: 'Kitsap',
        53: 'Pierce',
        61: 'Snohomish'
    }

special_route_lookup = {
    1671: 'A-Line Rapid Ride',
    1672: 'B-Line Rapid Ride',
    1673: 'C-Line Rapid Ride',
    1674: 'D-Line Rapid Ride',
    1675: 'E-Line Rapid Ride',
    4950: 'Central Link',
    6995: 'Tacoma Link',
    6998: 'Sounder South',
    6999: 'Sounder North',
    3701: 'Swift Blue Line'
}

# Transit Line OD Table list 
transit_line_dict = {118331: 'E Line SB',
					 119150: 'Link NB',
					 119166: 'Sounder NB',
					 118355: 'Metro 40 SB',
					 118332: 'WSF Bainbridge to Seattle',
					 118342: 'WSF Bremerton to Seattle',
					 118363: 'Passenger Ferry Bremerton to Seattle',
					 118585: 'Passenger Ferry Vashon Island to Seattle',
					 118225: 'Passenger Ferry West Seattle to Seattle',
					 118337: 'C Line to Downtown Seattle'
					 }

################################################
# Emissions calculations
################################################
county_id = {	1: 'King',
				2: 'Snohomish',
				3: 'Pierce',
				4: 'Kitsap'}

veh_totals = {'2014': 3176086, '2018': 3300162, '2040': 3982578.1, '2050': 4437371}


# Base year distribution of vehicle ownership by county
vehs_by_county = {
    'King': 1625471,
    'Kitsap': 231231,
    'Pierce': 675660,
    'Snohomish': 643724
}

# Base year distribution of vehicles by type (2014)
# Note that the totals by county above (for 2014) 
# include buses, so the totals below do not match up
# The difference is buses

# For GHG Analysis see:
# X:\Trans\AIRQUAL\T2040 2018 Update\EmissionCalcs\Start Emissions\Starts_2040_GHG.xlsx

# Total vehicles predicted from Auto Ownership model for base year 2018 
tot_veh_model_base_year = 3007232

###
### FIXME: put in db
###
vehs_by_type = {
    'king': {
        'light': 1433538,
        'medium': 174597,
        'heavy': 10574
    },
    'kitsap': {
        'light': 199872,
        'medium': 28830,
        'heavy': 1342
    },
    'pierce': {
        'light': 585681,
        'medium': 82607,
        'heavy': 4305
    },
    'snohomish': {
        'light': 559557,
        'medium': 77685,
        'heavy': 3884
    },
}

# List of pollutants to be summarized for summer
# All other are to be summarized for winter season
# using wintertime rates for all start emission rates except for VOCs
# per X:\Trans\AIRQUAL\T2040 2018 Update\EmissionCalcs\Start Emissions\Starts_2040.xls
summer_list = [87]

speed_bins = [-999999, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5, 67.5, 72.5, 999999] 
speed_bins_labels =  range(1, len(speed_bins))

fac_type_lookup = {0:0, 1:4, 2:4, 3:5, 4:5, 5:5, 6:3, 7:5, 8:0}

# Map pollutant name and ID
###
### FIXME: put in db
###
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

################################################################
# Summary input files and output directory names
################################################################

# Input Files
###
### FIXME: put in db
###
counts_file = 'inputs/base_year/observed/TrafficCounts_Mid.txt'
aadt_counts_file = 'inputs/base_year/observed/observed_aadt.csv'
tptt_counts_file = 'inputs/base_year/observed/observed_tptt.csv'
loop_counts_file = 'inputs/base_year/observed/observed_loop_counts.csv'
screenlines_file = 'inputs/base_year/observed/observed_screenline_volumes.csv'
truck_counts_file = 'inputs/base_year/observed/observed_truck_counts.csv' 
observed_boardings_file = 'inputs/base_year/observed/observed_transit_boardings.csv'
light_rail_boardings = 'inputs/base_year/observed/observed_light_rail_boardings.csv'
screenline_counts_file = 'inputs/base_year/observed/observed_screenline_counts.txt'
daily_counts_file = 'inputs/base_year/observed/observed_daily_counts.csv'

# Output Files 
network_summary_dir = 'outputs/network/network_summary.xlsx'
validation_summary_dir = 'outputs/network/validation.xlsx'
transit_summary_dir = 'outputs/transit/transit_summary.xlsx'

uc_list = ['@sov_inc1','@sov_inc2','@sov_inc3',
            '@hov2_inc1','@hov2_inc2','@hov2_inc3',
            '@hov3_inc1','@hov3_inc2','@hov3_inc3',
            '@av_sov_inc1','@av_sov_inc2','@av_sov_inc3',
            '@av_hov2_inc1','@av_hov2_inc2','@av_hov2_inc3',
            '@av_hov3_inc1','@av_hov3_inc2','@av_hov3_inc3',
            '@tnc_inc1','@tnc_inc2','@tnc_inc3','@mveh','@hveh','@bveh']

######## Observed Transit Boardings############################################

# Grouped outputs

# To compare with 1 or more runs, add key as run name, value as location to main soundcast directory
# e.g., comparison_runs = {'soundcast_base': 'C:/user/soundcast_base_run', 
#                          'soundcast_2040': 'C:/user/soundcast_2040'}
comparison_runs = {}
compare_survey = True    # compare daysim results in Tableau and topsheet outputs

#### Transit Groupings ###############################################################
transit_time_group_file= 'inputs/model/lookup/transit_time_groups.csv'
route_group_file = 'inputs/model/lookup/transit_route_groups.csv'
special_routes_file = 'inputs/model/lookup/transit_special_routes.csv'

# Bikes
bike_link_vol = 'outputs/bike/bike_volumes.csv'
bike_count_data = 'inputs/base_year/observed/bike_count_links.csv'
edges_file = 'inputs/scenario/bike/edges_0.txt'

# Parcel Summary
parcel_urbcen_map = 'parcels_in_urbcens.csv'    # lookup for parcel to RGC
parcel_file_out = 'landuse/parcel_summary.xlsx'    # summary output file name
parcels_file_name = 'inputs/scenario/landuse/parcels_urbansim.txt'
nodes_file_name = 'inputs/accessibility/all_streets_nodes_2014.csv'
links_file_name = 'inputs/accessibility/all_streets_links_2014.csv'
transit_access_outfile = 'outputs/transit/freq_transit_access.csv'
max_dist = 24140.2