#################################### NETWORK SUMMARY ####################################
network_summary_project = 'Projects/LoadTripTables/LoadTripTables.emp'
project = 'Projects/LoadTripTables/LoadTripTables.emp'
report_output_location = 'Outputs'
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

#transit_tod = {'6to7' : {'4k_tp' : 'am', 'num_of_hours' : 1}, 
#               '7to8' :  {'4k_tp' : 'am', 'num_of_hours' : 1}, 
#               '8to9' :  {'4k_tp' : 'am', 'num_of_hours' : 1}, 
#               '9to10' : {'4k_tp' : 'md', 'num_of_hours' : 1}, 
#               '10to14' : {'4k_tp' : 'md', 'num_of_hours' : 4}, 
#               '14to15' : {'4k_tp' : 'md', 'num_of_hours' : 1}}
# Input Files:
counts_file = 'TrafficCounts_Mid.txt'
# Output Files: 
net_summary_file = 'network_summary.csv'
counts_output_file = 'counts_output.csv'
screenlines_file = 'screenline_volumes.csv'
uc_list = ['@svtl1', '@svtl2', '@svtl3', '@h2tl1', '@h2tl2', '@h2tl3', 
           '@h3tl1', '@h3tl2', '@h3tl3', '@lttrk', '@mveh', '@hveh', '@bveh']

output_list = ['prod_att.csv', 'gq_prod_att.csv', 'network_summary.csv', 'counts_output.csv', 'daysim_outputs.h5',
               'screenline_volumes']

# Alternative run for map comparisons
map_daysim_alt = r'P:\TransportationFutures2040\outputs\daysim_outputs.h5'

results_db = 'R:\SoundCast\db\soundcastRuns.sl3'

########## Land Use Summary ##################################################
out_lu_summary = r'outputs/landuse_summary.xlsx'
households_persons_file = r'inputs\hh_and_persons.h5'

######## Truck Counts ########################################################
truck_counts_file = r'scripts/summarize/inputs/network_summary/truck_counts_2014.csv' 

######## Observed Transit Boardings############################################
observed_boardings_file = 'scripts/summarize/inputs/network_summary/transit_boardings_2014.csv'
