# Validation for observed data

#### TODO ####
# Validation data should be stored in the database!

import os, shutil
import pandas as pd
from sqlalchemy import create_engine
from input_configuration import base_year
from emme_configuration import sound_cast_net_dict

# output directory

validation_output_dir = 'outputs/validation'

# Create a clean output directory
if os.path.exists(validation_output_dir):
    shutil.rmtree(validation_output_dir)
os.makedirs(validation_output_dir)

### FIXME: move to a config file
agency_lookup = {
    1: 'King County Metro',
    2: 'Pierce Transit',
    3: 'Community Transit',
    4: 'Kitsap Transit',
    5: 'Washington Ferries',
    6: 'Sound Transit',
    7: 'Everett Transit'
}
# List of route IDs to separate for analysis
special_route_list = [6998,6999,1997,1998,6995,6996,1973,1975,4200,4201,4202,1671,1672,1673,1674,1675,1676,1040,1007,6550]

facility_type_lookup = {
    1:'Freeway',   # Interstate
    2:'Freeway',   # Ohter Freeway
    4:'Ramp',
    5:'Principal Arterial',
    19:'HOV',    # HOV Only Freeway
    999:'HOV'    # HOV Flag
    }
	
county_lookup = {
    33: 'King',
    53: 'Pierce',
    61: 'Snohomish'	
    }

tod_lookup = {  0:'20to5',
                1:'20to5',
                2:'20to5',
                3:'20to5',
                4:'20to5',
                5:'5to6',
                6:'6to7',
                7:'7to8',
                8:'8to9',
                9:'9to10',
                10:'10to14',
                11:'10to14',
                12:'10to14',
                13:'10to14',
                14:'14to15',
                15:'15to16',
                16:'16to17',
                17:'17to18',
                18:'18to20',
                19:'18to20',
                20:'18to20',
                21:'20to5',
                22:'20to5',
                23:'20to5',
                24:'20to5'}

def main():

    conn = create_engine('sqlite:///inputs/db/soundcast_inputs.db')

    ########################################
    # Transit Boardings by Line
    ########################################

    # Load observed data for given base year
    df_obs = pd.read_sql("SELECT * FROM observed_transit_boardings WHERE year=" + str(base_year), con=conn)
    df_obs['route_id'] = df_obs['route_id'].astype('int')

    # Load model results and calculate modeled daily boarding by line
    df_model = pd.read_csv(r'outputs\transit\transit_line_results.csv')
    df_model_daily = df_model.groupby('route_code').sum()[['boardings']].reset_index()

    # Merge modeled with observed boarding data
    df = df_model_daily.merge(df_obs, left_on='route_code', right_on='route_id', how='left')
    df['agency_name'] = df['agency_id'].map(agency_lookup)
    df.rename(columns={'boardings': 'modeled', 'daily_boardings': 'observed'}, inplace=True)
    df['diff'] = df['modeled']-df['observed']
    df['perc_diff'] = df['diff']/df['observed']
    df[['modeled','observed']] = df[['modeled','observed']].fillna(-1)

    # Write to file
    df.to_csv(os.path.join(validation_output_dir,'daily_boardings_by_line.csv'), index=False)

    # Boardings by agency
    df_agency = df.groupby(['agency_name']).sum().reset_index()
    df_agency['diff'] = df_agency['modeled']-df_agency['observed']
    df_agency['perc_diff'] = df_agency['diff']/df_agency['observed']
    df_agency.to_csv(os.path.join(validation_output_dir,'daily_boardings_by_agency.csv'), 
                     index=False, columns=['agency_name','observed','modeled','diff','perc_diff'])

    # Boardings by time of day


    # Boardings by agency and time of day (Peak/Off-Peak, by 5 assignment periods


    # Boardings for special lines
    df_special = df[df['route_code'].isin(special_route_list)]
    df_special.to_csv(os.path.join(validation_output_dir,'daily_boardings_key_routes.csv'), 
                     index=False, columns=['description','agency_name','observed','modeled','diff','perc_diff'])

    ########################################
    # Transit Boardings by Stop
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
    extra_attr_df = pd.read_csv(r'inputs\scenario\networks\extra_attributes\am_link_attributes.in\extra_links_1.txt', delim_whitespace=True)
    extra_attr_df['@facilitytype'] = extra_attr_df['@facilitytype'].map(facility_type_lookup)

    # Get daily and model volumes
    daily_counts = counts.groupby('flag').sum()[['vehicles']].reset_index()
    model_daily_vol_df = model_vol_df.groupby(['i_node','j_node']).sum()[['@tveh']].reset_index()
    df = pd.merge(model_daily_vol_df, extra_attr_df[['inode','jnode','@countid','@facilitytype','@countyid']], left_on=['i_node','j_node'], right_on=['inode','jnode'])
    df_daily = df.groupby('@countid').sum()[['@tveh']].reset_index()

    # Merge observed with model
    df_daily = df_daily.merge(daily_counts, left_on='@countid', right_on='flag')
    # Merge with attributes
    df_daily.rename(columns={'@tveh': 'modeled','vehicles': 'observed'}, inplace=True)
    df_daily['diff'] = df_daily['modeled']-df_daily['observed']
    df_daily['perc_diff'] = df_daily['diff']/df_daily['observed']
    df_daily[['modeled','observed']] = df_daily[['modeled','observed']].astype('int')
    df_daily = df_daily.merge(df, on='@countid')
    df_daily['county'] = df_daily['@countyid'].map(county_lookup)
    df_daily.to_csv(os.path.join(validation_output_dir,'daily_volume.csv'), 
                     index=False, columns=['inode','jnode','@countid','county','@facilitytype','modeled','observed','diff','perc_diff'])

    # Counts by county and facility type
    df_county_facility_counts = df_daily.groupby(['county','@facilitytype']).sum()[['observed','modeled']].reset_index()
    df_county_facility_counts.to_csv(os.path.join(validation_output_dir,'daily_volume_county_facility.csv'))

    # hourly counts
    # Create Time of Day (TOD) column based on start hour, group by TOD
    counts['tod'] = counts['start_hour'].map(tod_lookup)
    counts_tod = counts.groupby(['tod','flag']).sum()[['vehicles']].reset_index()

    # Join by time of day and flag ID
    model_df = pd.merge(model_vol_df, extra_attr_df[['inode','jnode','@countid','@facilitytype','@countyid']], left_on=['i_node','j_node'], right_on=['inode','jnode'])

    df = pd.merge(model_df, counts_tod, left_on=['@countid','tod'], right_on=['flag','tod'])
    df.rename(columns={'@tveh': 'modeled', 'vehicles': 'observed'}, inplace=True)
    df_daily['county'] = df_daily['@countyid'].map(county_lookup)
    df.to_csv(os.path.join(validation_output_dir,'hourly_volume.csv'), 
              columns=['flag','inode','jnode','auto_time','type','@facilitytype','county','tod','observed','modeled',], index=False)

    # Roll up results to assignment periods
    df['time_period'] = df['tod'].map(sound_cast_net_dict)

    ########################################
    # Vehicle Screenlines 
    ########################################

    # Screenline is defined in "type" field for network links, all values other than 90 represent a screenline

    # Daily volume screenlines
    df = model_daily_vol_df.merge(model_vol_df[['i_node','j_node','type']], on=['i_node','j_node'], how='left').drop_duplicates()
    df = df.groupby('type').sum()[['@tveh']].reset_index()

    # Observed screenline data


if __name__ == '__main__':
    main()