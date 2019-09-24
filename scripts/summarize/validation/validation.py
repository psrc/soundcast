# Validation for observed data

#### TODO ####
# Validation data should be stored in the database!

import os, shutil
import pandas as pd
from input_configuration import base_year

# output directory
os.chdir('C:/sc_2018_osm')
validation_output_dir = 'outputs/validation'

# Create a clean output directory
if os.path.exists(validation_output_dir):
    shutil.rmtree(validation_output_dir)
os.makedirs(validation_output_dir)

agency_lookup = {
    1: 'King County Metro',
    2: 'Pierce Transit',
    3: 'Community Transit',
    4: 'Kitsap Transit',
    5: 'Washington Ferries',
    6: 'Sound Transit',
    7: 'Everett Transit'
}

########################################
# Transit Boardings by Line
########################################

# Load observed data and filter for given base year
df_obs = pd.read_csv(r'R:\e2projects_two\2018_base_year\counts\transit\obs_daily_transit_boardings.csv')
df_obs['year'] = df_obs['year'].astype('str')
df_obs['route_id'] = df_obs['route_id'].astype('int')
df_obs = df_obs[df_obs['year'] == base_year]

# Load model data
df_model = pd.read_csv(r'outputs\transit\transit_line_results.csv')

# Calculate modeled daily boarding by line
df_model_daily = df_model.groupby('route_code').sum()[['boardings']].reset_index()

# Merge modeled with observed boarding data
df = df_model_daily.merge(df_obs, left_on='route_code', right_on='route_id', how='left')
df['agency_name'] = df['agency_id'].map(agency_lookup)
df.rename(columns={'boardings': 'model_boardings', 'daily_boardings': 'observed_boardings'}, inplace=True)
df['diff'] = df['model_boardings']-df['observed_boardings']
df['perc_diff'] = df['diff']/df['observed_boardings']

# Write to file
df.to_csv(os.path.join(validation_output_dir,'daily_boardings_by_line.csv'), index=False)

# Boardings by agency
df_agency = df.groupby(['agency_name']).sum().reset_index()
df_agency['diff'] = df_agency['model_boardings']-df_agency['observed_boardings']
df_agency['perc_diff'] = df_agency['diff']/df_agency['observed_boardings']
df_agency.to_csv(os.path.join(validation_output_dir,'daily_boardings_by_agency.csv'), 
                 index=False, columns=['agency_name','observed_boardings','model_boardings','diff','perc_diff'])

# Boardings by time of day

# Boardings by agency and time of day

########################################
# Transit Boardings by Line
########################################

########################################
# Traffic Volumes
########################################

# Count data
counts = pd.read_csv(r'R:\e2projects_two\2018_base_year\counts\highway\hourly_counts.csv')
counts['year'] = counts['year'].astype('str')
counts = counts[counts['year'] == base_year]

# Model results
model_vol_df = pd.read_csv(r'outputs\network\network_results.csv')

# Get the flag ID from network attributes
df = pd.read_csv(r'\\modelsrv1\c$\sc_2018_osm\inputs\scenario\networks\extra_attributes\am_link_attributes.in\extra_links.txt', delim_whitespace=True)

# Get daily and model volumes
daily_counts = counts.groupby('flag').sum()[['vehicles']].reset_index()
model_daily_vol_df = model_vol_df.groupby(['i_node','j_node']).sum()[['@tveh']].reset_index()
df = pd.merge(model_daily_vol_df, df[['inode','jnode','@countid','@facilitytype','@countyid']], left_on=['i_node','j_node'], right_on=['inode','jnode'])
df_daily = df.groupby('@countid').sum()[['@tveh']].reset_index()

# Merge observed with model
df_daily = df_daily.merge(daily_counts, left_on='@countid', right_on='flag')
# Merge with attributes
df_daily.rename(columns={'@tveh': 'model_volume','vehicles': 'observed_volume'}, inplace=True)
df_daily['diff'] = df_daily['model_volume']-df_daily['observed_volume']
df_daily['perc_diff'] = df_daily['diff']/df_daily['observed_volume']

df_daily = df_daily.merge(df, on='@countid')
df_daily.to_csv(os.path.join(validation_output_dir,'daily_volume.csv'), 
                 index=False, columns=['inode','jnode','@countid','@countyid','@facilitytype','model_volume','observed_volume','diff','perc_diff'])

# Counts by county and facility type
### FIXME: add county and facility labels; make sure facility types are combined appropriately
df_county_facility_counts = df_daily.groupby(['@countyid','@facilitytype']).sum()[['observed_volume','model_volume']].reset_index()
df_county_facility_counts.to_csv(os.path.join(validation_output_dir,'daily_volume_county_facility.csv'))

# hourly counts