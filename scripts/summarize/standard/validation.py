# Validation for observed data

#### TODO ####
# Validation data should be stored in the database!

import os, shutil
import pandas as pd
from sqlalchemy import create_engine
from input_configuration import base_year
from emme_configuration import sound_cast_net_dict, MIN_EXTERNAL, MAX_EXTERNAL 

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
special_route_list = [6998,6999,1997,1998,6995,6996,1973,1975,
                        4200,4201,4202,1671,1672,1673,1674,1675,1676,1040,1007,6550,
                        5001,5002,5003,5004,5005,5006,5007]

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
    df_line_obs = df_obs.copy()

    # Load model results and calculate modeled daily boarding by line
    df_transit_line = pd.read_csv(r'outputs\transit\transit_line_results.csv')
    df_model = df_transit_line.copy()
    df_model_daily = df_model.groupby('route_code').agg({   'description': 'first',
                                                            'boardings': 'sum'}).reset_index()

    # Merge modeled with observed boarding data
    df = df_model_daily.merge(df_obs, left_on='route_code', right_on='route_id', how='left')
    df.rename(columns={'boardings': 'modeled_5to20', 'observed_20to5': 'observed_5to20'}, inplace=True)
    df['diff'] = df['modeled_5to20']-df['observed_5to20']
    df['perc_diff'] = df['diff']/df['observed_5to20']
    df[['modeled_5to20','observed_5to20']] = df[['modeled_5to20','observed_5to20']].fillna(-1)

    # Write to file
    df.to_csv(os.path.join(validation_output_dir,'daily_boardings_by_line.csv'), index=False)

    # Boardings by agency
    df_agency = df.groupby(['agency']).sum().reset_index()
    df_agency['diff'] = df_agency['modeled_5to20']-df_agency['observed_5to20']
    df_agency['perc_diff'] = df_agency['diff']/df_agency['observed_5to20']
    df_agency.to_csv(os.path.join(validation_output_dir,'daily_boardings_by_agency.csv'), 
                        index=False, columns=['agency','observed_5to20','modeled_5to20','diff','perc_diff'])

    # Boardings for special lines
    df_special = df[df['route_code'].isin(special_route_list)]
    df_special.to_csv(os.path.join(validation_output_dir,'daily_boardings_key_routes.csv'), 
                        index=False, columns=['description','route_code','agency','observed_5to20','modeled_5to20','diff','perc_diff'])

    ########################################
    # Transit Boardings by Stop
    ########################################
	
    # Light Rail
    df_obs = pd.read_sql("SELECT * FROM light_rail_station_boardings WHERE year=" + str(base_year), con=conn)

    # Scale boardings for model period 5to20, based on boardings along entire line
    light_rail_list = [6996]
    daily_factor = df_line_obs[df_line_obs['route_id'].isin(light_rail_list)]['daily_factor'].values[0]
    df_obs['observed_5to20'] = df_obs['boardings']/daily_factor

    df = pd.read_csv(r'outputs\transit\boardings_by_stop.csv')
    df = df[df['i_node'].isin(df_obs['emme_node'])]
    df = df.merge(df_obs, left_on='i_node', right_on='emme_node')
    df.rename(columns={'total_boardings':'modeled_5to20'},inplace=True)
    df['observed_5to20'] = df['observed_5to20'].astype('float')
    df.index = df['station_name']
    df_total = df.copy()[['observed_5to20','modeled_5to20']]
    df_total.ix['Total',['observed_5to20','modeled_5to20']] = df[['observed_5to20','modeled_5to20']].sum().values
    df_total.to_csv(r'outputs\validation\light_rail_boardings.csv', index=True)

    # Light Rail Transfers
    df_transfer = df.copy() 
    df_transfer['observed_transfer_rate'] = df_transfer['observed_transfer_rate'].fillna(-99).astype('float')
    df_transfer['modeled_transfer_rate'] = df_transfer['transfers']/df_transfer['modeled_5to20']
    df_transfer['diff'] = df_transfer['modeled_transfer_rate']-df_transfer['observed_transfer_rate']
    df_transfer['percent_diff'] = df_transfer['diff']/df_transfer['observed_transfer_rate']
    df_transfer = df_transfer[['modeled_transfer_rate','observed_transfer_rate','diff','percent_diff']]
    df_transfer.to_csv(r'outputs\validation\light_rail_transfers.csv', index=True)


    ########################################
    # Traffic Volumes
    ########################################

    # Count data
    counts = pd.read_sql("SELECT * FROM hourly_counts WHERE year=" + str(base_year), con=conn)

    # Model results
    df_network = pd.read_csv(r'outputs\network\network_results.csv')
    model_vol_df = df_network.copy()
    model_vol_df['@facilitytype'] = model_vol_df['@facilitytype'].map(facility_type_lookup)

    # Get daily and model volumes
    daily_counts = counts.groupby('flag').sum()[['vehicles']].reset_index()
    df_daily = model_vol_df.groupby(['@countid']).sum()[['@tveh']].reset_index()

    # Merge observed with model
    df_daily = df_daily.merge(daily_counts, left_on='@countid', right_on='flag')

    # Merge with attributes
    df_daily.rename(columns={'@tveh': 'modeled','vehicles': 'observed'}, inplace=True)
    df_daily['diff'] = df_daily['modeled']-df_daily['observed']
    df_daily['perc_diff'] = df_daily['diff']/df_daily['observed']
    df_daily[['modeled','observed']] = df_daily[['modeled','observed']].astype('int')
    df_daily = df_daily.merge(model_vol_df, on='@countid', how='left')
    df_daily['county'] = df_daily['@countyid'].map(county_lookup)
    df_daily.to_csv(os.path.join(validation_output_dir,'daily_volume.csv'), 
                        index=False, columns=['@countid','@countid','county','@facilitytype','modeled','observed','diff','perc_diff'])

    # Counts by county and facility type
    df_county_facility_counts = df_daily.groupby(['county','@facilitytype']).sum()[['observed','modeled']].reset_index()
    df_county_facility_counts.to_csv(os.path.join(validation_output_dir,'daily_volume_county_facility.csv'))

    # hourly counts
    # Create Time of Day (TOD) column based on start hour, group by TOD
    counts['tod'] = counts['start_hour'].map(tod_lookup)
    counts_tod = counts.groupby(['tod','flag']).sum()[['vehicles']].reset_index()

    # Join by time of day and flag ID
    #model_df = pd.merge(model_vol_df, extra_attr_df[['inode','jnode','@countid','@facilitytype','@countyid']], left_on=['i_node','j_node'], right_on=['inode','jnode'])

    df = pd.merge(model_vol_df, counts_tod, left_on=['@countid','tod'], right_on=['flag','tod'])
    df.rename(columns={'@tveh': 'modeled', 'vehicles': 'observed'}, inplace=True)
    df['county'] = df['@countyid'].map(county_lookup)
    df.to_csv(os.path.join(validation_output_dir,'hourly_volume.csv'), 
                columns=['flag','inode','jnode','auto_time','type','@facilitytype','county','tod','observed','modeled',], index=False)

    # Roll up results to assignment periods
    df['time_period'] = df['tod'].map(sound_cast_net_dict)

    ########################################
    # Ferry Boardings by Bike
    ########################################    
    df_transit_seg = pd.read_csv(r'outputs\transit\transit_segment_results.csv')
    df_transit_seg = df_transit_seg[df_transit_seg['tod'] == '7to8']
    df_transit_seg = df_transit_seg.drop_duplicates(['i_node','line_id'])
    df_transit_line = df_transit_line[df_transit_line['tod'] == '7to8']

    _df = df_transit_line.merge(df_transit_seg, on='line_id', how='left')
    _df = _df.drop_duplicates('line_id')

    df_ij = _df.merge(df_network, left_on='i_node', right_on='i_node', how='left')
    # select only ferries
    df_ij = df_ij[df_ij['@facilitytype'].isin([15,16])]
    # both link and transit line modes should only include passenger (p) or general ferries (f)
    for colname in ['modes','mode']:
        df_ij['_filter'] = df_ij[colname].apply(lambda x: 1 if 'f' in x or 'p' in x else 0)
        df_ij = df_ij[df_ij['_filter'] == 1]
        
    df_total = df_ij.groupby('route_code').sum()[['@bvol']].reset_index()
    df_total = df_total.merge(df_ij[['description','route_code']], on='route_code').drop_duplicates('route_code')
    df_total.to_csv(r'outputs\validation\bike_ferry_boardings.csv', index=False)

    ########################################
    # Vehicle Screenlines 
    ########################################

    # Screenline is defined in "type" field for network links, all values other than 90 represent a screenline

    # Daily volume screenlines
    #df = model_vol_df.merge(model_vol_df[['i_node','j_node','type']], on=['i_node','j_node'], how='left').drop_duplicates()
    #df = model_vol_df.copy()
    #df = df.groupby('type').sum()[['@tveh']].reset_index()

    # Observed screenline data
    df_obs = pd.read_sql("SELECT * FROM observed_screenline_volumes WHERE year=" + str(base_year), con=conn)
    df_obs['observed'] = df_obs['observed'].astype('float')

    df_model = pd.read_csv(r'outputs\network\network_results.csv')
    df_model = model_vol_df.copy()
    df_model['screenline_id'] = df_model['type'].astype('str')
    # Auburn screenline is the combination of 14 and 15, change label for 14 and 15 to a combined label
    df_model.ix[df_model['screenline_id'].isin(['14','15']),'screenline_id'] = '14/15'
    _df = df_model.groupby('screenline_id').sum()[['@tveh']].reset_index()

    _df = _df.merge(df_obs, on='screenline_id')
    _df.rename(columns={'@tveh':'modeled'},inplace=True)
    _df = _df[['name','observed','modeled']]
    _df['diff'] = _df['modeled']-_df['observed']
    _df = _df.sort_values('observed',ascending=False)
    _df.to_csv(r'outputs\validation\screenlines.csv', index=False)
    
    ########################################
    # External Volumes
    ########################################

    # External stations
    external_stations = xrange(MIN_EXTERNAL,MAX_EXTERNAL+1)
    df_model = df_model[df_model['@countid'].isin(external_stations)]
    _df = df_model.groupby('@countid').sum()[['@tveh']].reset_index()

    # Join to observed
    # By Mode
    df_obs = pd.read_sql("SELECT * FROM observed_external_volumes WHERE year=" + str(base_year), con=conn)
    newdf = _df.merge(df_obs,left_on='@countid' ,right_on='external_station')
    newdf.rename(columns={'@tveh':'modeled','AWDT':'observed'},inplace=True)
    newdf['observed'] = newdf['observed'].astype('float')
    newdf['diff'] = newdf['modeled'] - newdf['observed']
    newdf = newdf[['external_station','location','observed','modeled','diff']].sort_values('observed',ascending=False)
    newdf.to_csv(r'outputs\validation\external_volumes.csv',index=False)
	
	
	########################################
	# Corridor Speeds
	########################################
	
    df_model = model_vol_df.copy()
    df_model['@corridorid'] = df_model['@corridorid'].astype('int')

    df_obs = pd.read_sql_table('observed_corridor_speed', conn) 

    df_obs[['Flag1','Flag2','Flag3','Flag4','Flag5','Flag6']] = df_obs[['Flag1','Flag2','Flag3','Flag4','Flag5','Flag6']].fillna(-1).astype('int')

    tod_cols = [u'ff_spd', u'5am_spd', u'6am_spd',
    	   u'7am_spd', u'8am_spd', u'9am_spd', u'3pm_spd', u'4pm_spd', u'5pm_spd',
    	   u'6pm_spd', u'7pm_spd']

    _df_obs = pd.melt(df_obs, id_vars='Corridor_Number', value_vars=tod_cols, var_name='tod', value_name='observed_speed')
    _df_obs = _df_obs[_df_obs['tod'] != 'ff_spd']


    # Set TOD
    tod_dict = {
    	'5am_spd': '12to5',
    	'6am_spd': '5to6',
    	'7am_spd': '6to7',
    	'8am_spd': '7to8',
    	'9am_spd': '8to9',
    	'3pm_spd': '14to15',
    	'4pm_spd': '15to16',
    	'5pm_spd': '16to17',
    	'6pm_spd': '17to18',
    	'7pm_spd': '18to20',
    }
    _df_obs['tod'] = _df_obs['tod'].map(tod_dict)

    _df = _df_obs.merge(df_obs, on=['Corridor_Number'])
    _df.drop(tod_cols, axis=1, inplace=True)

    # Get the corridor number from the flag file
    flag_lookup_df = pd.melt(df_obs[['Corridor_Number','Flag1', 'Flag2','Flag3','Flag4','Flag5','Flag6']], 
    		id_vars='Corridor_Number', value_vars=['Flag1', 'Flag2','Flag3','Flag4','Flag5','Flag6'], 
    		var_name='flag_number', value_name='flag_value')

    df_speed = df_model.merge(flag_lookup_df,left_on='@corridorid',right_on='flag_value')

    # Note that we need to separate out the Managed HOV lanes
    df_speed = df_speed[df_speed['@is_managed'] == 0]

    df_speed = df_speed.groupby(['Corridor_Number','tod']).sum()[['auto_time','length']].reset_index()
    df_speed['model_speed'] = (df_speed['length']/df_speed['auto_time'])*60
    df_speed = df_speed[(df_speed['model_speed'] < 80) & ((df_speed['model_speed'] > 0))]

    # Join to the observed data
    df_speed = df_speed.merge(_df,on=['Corridor_Number','tod'])

    df_speed.plot(kind='scatter', y='model_speed', x='observed_speed')
    df_speed.to_csv(r'outputs\validation\corridor_speeds.csv', index=False)

    ########################################
    # ACS Comparisons
    ########################################

    # Commute Mode Share by Workplace Geography
    # Model Data
    df_model = pd.read_csv(r'outputs\agg\census\tour_place.csv')
    df_model = df_model[df_model['pdpurp'] == 'Work']
    df_model = df_model.groupby(['t_o_place','t_d_place','tmodetp']).sum()[['toexpfac']].reset_index()
    # rename columns
    df_model.loc[df_model['tmodetp'] == 'SOV','mode'] = 'auto'
    df_model.loc[df_model['tmodetp'] == 'HOV2','mode'] = 'auto'
    df_model.loc[df_model['tmodetp'] == 'HOV3+','mode'] = 'auto'
    df_model.loc[df_model['tmodetp'] == 'Transit','mode'] = 'transit'
    df_model.loc[df_model['tmodetp'] == 'Walk','mode'] = 'walk_and_bike'
    df_model.loc[df_model['tmodetp'] == 'Bike','mode'] = 'walk_and_bike'
    df_model = df_model.groupby(['mode','t_d_place']).sum()[['toexpfac']].reset_index()

    # Observed Data
    df = pd.read_sql("SELECT * FROM acs_commute_mode_by_workplace_geog WHERE year=" + str(base_year), con=conn)
    df = df[df['geography'] == 'place']
    df = df[df['mode'] != 'worked_at_home']
    df['geog_name'] = df['geog_name'].apply(lambda row: row.split(' city')[0])

    # FIXME: 
    # no HOV modes - is SOV including all auto trips?
    df.loc[df['mode']=='sov','mode'] = 'auto'

    # Merge modeled and observed
    df = df.merge(df_model, left_on=['geog_name','mode'], right_on=['t_d_place','mode'])
    df.rename(columns={'trips': 'observed', 'toexpfac': 'modeled', 'geog_name': 'work_place'}, inplace=True)
    df = df[['work_place','mode','modeled','observed']]
    df['percent_diff'] = (df['modeled']-df['observed'])/df['observed']
    df['diff'] = df['modeled']-df['observed']

    df.to_csv(r'outputs\validation\acs_commute_share_by_workplace_geog.csv',index=False)

    # Commute Mode Share by Home Tract
    df_model = pd.read_csv(r'outputs\agg\census\tour_dtract.csv')

    df_model[['to_tract','td_tract']] = df_model[['to_tract','td_tract']].astype('str')
    df_model['to_tract'] = df_model['to_tract'].apply(lambda row: row.split('.')[0])
    df_model['td_tract'] = df_model['td_tract'].apply(lambda row: row.split('.')[0])

    df_model = df_model[df_model['pdpurp'] == 'Work']
    df_model = df_model.groupby(['to_tract','tmodetp']).sum()[['toexpfac']].reset_index()

    # # Group all HOV together
    df_model['mode'] = df_model['tmodetp']
    df_model.loc[df_model['tmodetp'] == 'HOV2', 'mode'] = 'HOV'
    df_model.loc[df_model['tmodetp'] == 'HOV3+', 'mode'] = 'HOV'
    df_model = df_model.groupby(['to_tract','mode']).sum().reset_index()

    df_model['to_tract']=df_model['to_tract'].astype('int64')
    df_model['modeled'] = df_model['toexpfac']

    # Load the census data
    df_acs = pd.read_sql("SELECT * FROM acs_commute_mode_home_tract WHERE year=" + str(base_year), con=conn)
    
    # Select only tract records
    df_acs = df_acs[df_acs['place_type'] == 'tr']

    # Only include modes for people that travel to work (exclude telecommuters and others)
    mode_map = {'Drove Alone': 'SOV',
                'Carpooled': 'HOV',
                'Walked': 'Walk',
                'Other': 'Other',
               'Transit':'Transit'}

    df_acs['mode'] = df_acs['variable_description'].map(mode_map)
    df_acs = df_acs[-df_acs['mode'].isnull()]

    # Drop the Other mode for now
    df_acs = df_acs[df_acs['mode'] != 'Other']

    # Merge the model and observed data
    df = df_acs[['mode','geoid','place_name','estimate','margin_of_error']].merge(df_model,left_on=['geoid','mode'], 
                                                                             right_on=['to_tract','mode'])
    df.rename(columns={'estimate': 'observed', 'trexpfac': 'modeled'}, inplace=True)
    df[['observed','modeled']] = df[['observed','modeled']].astype('float')

    # Add geography columns based on tract
    parcel_geog = pd.read_sql("SELECT * FROM parcel_"+str(base_year)+"_geography", con=conn) 

    tract_geog = parcel_geog.groupby('Census2010Tract').first()[['CountyName','CityRGProposed','CityRGExisting','GrowthCenterName','TAZ',
                                              'FAZLargeAreaName','ZoneAreaType','District']].reset_index()
    df = df.merge(tract_geog, left_on='geoid', right_on='Census2010Tract', how='left')
    df.to_csv(r'outputs\validation\acs_commute_share_by_home_tract.csv', index=False)

if __name__ == '__main__':
    main()