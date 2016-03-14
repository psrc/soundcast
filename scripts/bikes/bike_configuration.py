
#################################### BIKE MODEL ####################################
bike_assignment_tod = ['6to7', '7to8','8to9','9to10', '10to14', '14to15']

# Distance perception penalties for link AADT from Broach et al., 2012
# 1 is AADT 10k-20k, 2 is 20k-30k, 3 is 30k+
# No penalty applied for AADT < 10k
aadt_dict = {'volume_wt': {
								1: 0.368, 
                                2: 1.40, 
                                3: 7.157}}

# AADT segmentation breaks to apply volume penalties
aadt_bins = [0,10000,20000,30000,9999999]
aadt_labels = [0,1,2,3] # Corresponding "bucket" labels for AADT segmentation for aadt_dict

# Crosswalk of bicycle facilities from geodatabase to a 2-tier typology - premium, standard (and none)
# "Premium" represents trails and fully separated bike facilities
# "Standard" represents painted bike lanes only
bike_facility_crosswalk = {'@bkfac': {  0:'none', 1:'standard', 2:'premium', 
                                        3:'none', 4:'none', 5:'none', 6:'none', 
                                        7:'none', 8:'standard', 9:'none'}}  ## need to confirm these

# Perception factor values corresponding to these tiers, from Broch et al., 2012
facility_dict = {'facility_wt': {	'premium': -0.160,
                                    'standard': -0.108, 
                                    'none': 0}}

# Perception factor values for 3-tiered measure of elevation gain per link
slope_dict = {'slope_wt': {1: .371,     # between 2-4% grade
                                2: 1.203,    # between 4-6% grade
                                3: 3.239}}   # greater than 6% grade

# Bin definition of total elevation gain (per link)
slope_bins = [-1,0.02,0.04,0.06,1]
slope_labels = [0,1,2,3]                

avg_bike_speed = 10 # miles per hour

# Outputs directory
bike_link_vol = 'outputs/bike_volumes.csv'
bike_count_data = 'inputs/bikes/bike_counts.csv'
edges_file = 'inputs/bikes/edges_0.txt'

# Multiplier for storing skim results
bike_skim_mult = 100    # divide by 100 to store as int