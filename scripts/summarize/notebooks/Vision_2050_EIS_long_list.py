import pandas as pd
import os
import collections
import h5py
import sys
import time

# Relative path between notebooks and goruped output directories
# for testing

#os.chdir(r"H:\vision2050\soundcast\non_integrated\2014\scripts\summarize\notebooks")
os.chdir(r"H:\vision2050\soundcast\integrated\draft_runs\stc\stc_run_3_2018_08_17_13_06\2050\scripts\summarize\notebooks")

#os.chdir(r"H:\vision2050\soundcast\non_integrated\2050\draft_versions\dug\2050_dug_b_181005_run_4_2018_10_02_11_57\scripts\summarize\notebooks")
#os.chdir(r"H:\vision2050\soundcast\non_integrated\2050\draft_versions\dug\2050_dug_jobhh_balance_181004_run1_2018_10_01_20_37_\scripts\summarize\notebooks")

#os.chdir(r"H:\vision2050\soundcast\non_integrated\2050\draft_versions\h2o2\2050_h2o2_181005_run_6_2018_10_02_12_01\scripts\summarize\notebooks")
#os.chdir(r"H:\vision2050\soundcast\non_integrated\2050\draft_versions\h2o2\2050_h2o2_b_181008_run_2_2018_10_05_14_50\scripts\summarize\notebooks")

#os.chdir(r"H:\vision2050\soundcast\non_integrated\2050\draft_versions\tod\2050_tod_181004_run_3_2018_10_02_14_30_\scripts\summarize\inputs")
#os.chdir(r"H:\vision2050\soundcast\non_integrated\2050\draft_versions\tod\2050_tod_b_181008_run_12_2018_10_05_15_04\scripts\summarize\notebooks")

#os.chdir(r"H:\vision2050\soundcast\non_integrated\2050\draft_versions\dug_water\2050_dug_water\scripts\summarize\notebooks")
#os.chdir(r"H:\vision2050\soundcast\non_integrated\2050\draft_versions\dug_water\2050_dug_water_jobhh_balance_181014\scripts\summarize\notebooks")




#os.chdir(r"H:\vision2050\soundcast\integrated\draft_runs\dug\dug_run_1_2018_08_17_15_45\2050\scripts\summarize\notebooks")

relative_path = '../../../outputs'
output_vision_file = os.path.join(relative_path, 'Vision2050_longlist.csv')
taz_reg_geog = '../../../scripts/summarize/inputs/TAZ_Reg_Geog.csv'
county_taz = '../../../scripts/summarize/inputs/county_taz.csv'
equity_taz = '../../../scripts/summarize/inputs/equity_geog.csv'
h5file = h5py.File(os.path.join(relative_path, 'daysim/daysim_outputs.h5'))

mode_dict = {0: 'Other', 1:'Walk',2:'Bike',3:'SOV',4:'HOV2',5:'HOV3+',6:'Transit',8:'School Bus'}
agency_lookup = {
        '1': 'King County Metro',
        '2': 'Pierce Transit',
        '3': 'Community Transit',
        '4': 'Kitsap Transit',
        '5': 'Washington Ferries',
        '6': 'Sound Transit',
        '7': 'Everett Transit'
    }

weekday_to_annual = 300
minutes_to_hour = 60
geog_list = ['rg_proposed', 'geog_name', 'People Of Color', 'Low Income']

def h5_to_df(h5file, table_list):
    output_dict = {}
    
    for table in table_list:
        df = pd.DataFrame()
        for field in h5file[table].keys():
            df[field] = h5file[table][field][:]
            
        output_dict[table] = df
    
    return output_dict

def dist_geo(trip, geog_level, output_dict, name):
    dist_df_geog = trip[['travdist', geog_level]].groupby(geog_level).mean()['travdist'].reset_index()
    for index, row in dist_df_geog.iterrows():
        output_dict[(name, row[geog_level], 'Total')]=row['travdist']

def mode_geo(trip, geog_level, output_dict, name):
    mode_df_geog = trip[[geog_level, 'mode', 'hhno']].groupby([geog_level, 'mode']).count()['hhno'].reset_index()
    mode_geog = mode_df_geog.groupby([geog_level ,'mode']).sum()['hhno']/mode_df_geog.groupby(geog_level).sum()['hhno']
    mode_geog=mode_geog.reset_index()
    mode_geog.columns = [geog_level, 'mode', 'Mode Share']
    mode_geog.replace({'mode':mode_dict}, inplace=True)

    for index, row in mode_geog.iterrows():
        output_dict[(name, row[geog_level], row['mode'])]=row['Mode Share']

    return output_dict

def delay_geo(trip, geog_level, output_dict, name, person):
    print geog_level
    delay_geog = pd.DataFrame(trip[['delay', geog_level]].groupby(geog_level).sum()['delay']/person[['psexpfac', geog_level]].groupby(geog_level).sum()['psexpfac'])
    print delay_geog
    delay_geog.reset_index(inplace=True)
    delay_geog.columns = [geog_level,'delay']

    for index, row in delay_geog.iterrows():
        output_dict[(name,row[geog_level], 'Total')]=row['delay']*(weekday_to_annual/minutes_to_hour)


def vmt_per_capita(driver_trips, geog_level, output_dict, name, person):
    print 'vmt_per_capita'
    driver_trips_geog = pd.DataFrame(driver_trips[[geog_level, 'travdist']].groupby(geog_level).sum()['travdist']/person[[geog_level, 'psexpfac']].groupby(geog_level).sum()['psexpfac'])
    driver_trips_geog.reset_index(inplace=True)
    driver_trips_geog.columns = [geog_level,'vmt']

    for index, row in driver_trips_geog.iterrows():
        output_dict[(name, row[geog_level], 'Total')]=row['vmt']

def vht_per_capita(driver_trips, geog_level, output_dict, name, person):
    driver_trips_geog = pd.DataFrame(driver_trips[[geog_level, 'travtime']].groupby(geog_level).sum()['travtime']/person[[geog_level, 'psexpfac']].groupby(geog_level).sum()['psexpfac'])
    driver_trips_geog.reset_index(inplace=True)
    driver_trips_geog.columns = [geog_level,'vht']

    for index, row in driver_trips_geog.iterrows():
        output_dict[(name, row[geog_level], 'Total')]=row['vht']/minutes_to_hour

def walk_bike_geo(df, geog_level, output_dict,person):
    df_geog_share=pd.DataFrame(df.groupby(geog_level).sum()['bike_walk_t']/person.groupby(geog_level).sum()['psexpfac'])
    df_geog_total=pd.DataFrame(df.groupby(geog_level).sum()['bike_walk_t'])
    df_geog_share.reset_index(inplace=True)
    df_geog_total.reset_index(inplace=True)

    df_geog_share.columns = [geog_level, 'wbt']
    df_geog_total.columns = [geog_level, 'wbt']

    for index, row in df_geog_share.iterrows():
        output_dict[('Share of Residents Walking, Biking,or Using Transit',row[geog_level], 'Share')]=row['wbt']
    for index, row in df_geog_total.iterrows():
        output_dict[('Total of Residents Walking, Biking,or Using Transit',row[geog_level], 'Total')]=row['wbt']

def merge_persons(person, hh, taz_geog, county_taz, equity_geog):
    person =pd.merge(person[['hhno','pno', 'psexpfac']],hh[['hhno','hhtaz']], on = 'hhno', suffixes=['','_x'])
    person = pd.merge(person, taz_geog, left_on = 'hhtaz', right_on = 'taz_p')
    person = pd.merge(person, county_taz, left_on = 'hhtaz', right_on = 'taz')
    person = pd.merge(person, equity_geog, left_on = 'hhtaz', right_on = 'taz_p')
    return person

def merge_trips(trip, person, taz_geog, county_taz, equity_geog):
    trip = pd.merge(trip[['hhno', 'pno', 'opurp', 'dpurp', 'travdist', 'travtime', 'mode', 'dorp', 'dtaz', 'sov_ff_time']], person, on = ['hhno', 'pno'], suffixes=['','_x'], how = 'inner' )
    trip = pd.merge(trip, taz_geog, left_on = 'dtaz', right_on ='taz_p', suffixes = ['', '_tripdest'])
    trip = pd.merge(trip, county_taz, left_on = 'dtaz', right_on ='taz', suffixes = ['', '_tripdest'])
    trip = pd.merge(trip, equity_geog, left_on = 'dtaz', right_on = 'taz_p', suffixes = ['', '_tripdest'])
    return trip

def network_results(network_df):
    # System performance measures
    # VMT
    network_df['all_facility_vmt'] = network_df['arterial_vmt']+ network_df['connectors_vmt']+ network_df['highway_vmt']
    total_vmt = network_df['all_facility_vmt'].sum()
    output_dict = {}
    output_dict = collections.OrderedDict(output_dict)
    output_dict[('Daily VMT','Regional', 'Total')] = total_vmt

    #VHT
    network_df['all_facility_vht'] = network_df['arterial_vht']+ network_df['connectors_vht']+ network_df['highway_vht']
    total_vht = network_df['all_facility_vht'].sum()
    output_dict[('Daily VHT', 'Regional', 'Total')] = total_vht

    # Delay
    network_df['all_facility_delay'] = network_df['arterial_delay']+ network_df['connectors_delay']+ network_df['highway_delay']
    total_delay = network_df['all_facility_delay'].sum()
    output_dict[('Daily Delay', 'Regional', 'Total')] = total_delay

    # Total Delay Hours Daily by Facility Type
    df_fac = pd.DataFrame(network_df.sum()[['arterial_delay','highway_delay']])
    df_fac = df_fac.reset_index()
    df_fac.columns = ['Facility Type', 'Delay']
    #df_fac.index = df_fac['Facility Type']
    #df_fac.drop('Facility Type', axis=1, inplace=True)
    df_fac.loc['Total'] = df_fac.sum()
    output_dict[('Daily Arterial Delay Hours', 'Regional', 'Total')] = df_fac['Delay'].loc[df_fac['Facility Type'] == 'arterial_delay'].values[0]
    output_dict[('Daily Highway Delay Hours', 'Regional', 'Total')] = df_fac['Delay'].loc[df_fac['Facility Type'] == 'highway_delay'].values[0]

    # Daily Transit Boardings
    transit_df = pd.read_excel(r'../../../outputs/network/network_summary_detailed.xlsx', sheetname='Transit Summaries')
    tod_list = ['5to6','6to7','7to8','8to9','9to10','10to14','14to15','15to16','16to17','17to18','18to20']
    transit_df = transit_df[[tod+'_board' for tod in tod_list]+['route_code']]
    transit_df = transit_df.fillna(0)
    transit_df['line_total'] = transit_df[[tod+'_board' for tod in tod_list]].sum(axis=1)
    df = pd.read_excel(r'../../../outputs/network/network_summary_detailed.xlsx', sheetname='Transit Summaries')
    tod_list = ['5to6','6to7','7to8','8to9','9to10','10to14','14to15','15to16','16to17','17to18','18to20']
    df = df[[tod+'_board' for tod in tod_list]+['route_code']]
    df = df.fillna(0)
    df['line_total'] = df[[tod+'_board' for tod in tod_list]].sum(axis=1)

    #Boardings by transit agency
    df['agency'] = df['route_code'].astype('str').apply(lambda row: row[0])
    df['agency'] = df['agency'].map(agency_lookup)
    # the agency name isn't working for some reason, so just give total
    df = pd.DataFrame(df.groupby('agency').sum()['line_total']).reset_index()
    for index, row in df.iterrows():
        output_dict[('Daily Transit Boardings', row['agency'], 'Total')] = row['line_total']

    output_dict[('Daily Transit Boardings', 'Regional', 'Total')]=transit_df['line_total'].sum()

    return output_dict

def mode_results(trip, person, output_dict):
    # Split into HBW/Non-HBW
    trip['Trip Type'] = 'Not Home-Based Work'
    trip.ix[(((trip['opurp']==0) & (trip['dpurp']==1)) | ((trip['opurp']==1) & (trip['dpurp']==0))),'Trip Type']= 'Home-Based Work'
    hbw_trips = trip.loc[trip['Trip Type']=='Home-Based Work']
    nhbw_trips = trip.loc[trip['Trip Type']=='Not Home-Based Work']

   

    # Average Trip Distance by Geography/Commute/Non-Commute
    output_dict[('Commute Trip Length', 'Regional', 'Total')]=hbw_trips['travdist'].mean()
    
    # Trip distance by geography
    for geog in geog_list:
        dist_geo(hbw_trips, geog, output_dict, 'Commute Trip Length')
        dist_geo(nhbw_trips, geog, output_dict, 'Other Trip Length')

    # All Trip Mode Share
    mode_df = trip[['hhno', 'mode']].groupby('mode').count()['hhno'].reset_index()
    mode_df['Mode Share']= mode_df['hhno']/mode_df.sum()['hhno']
    mode_df.replace({'mode':mode_dict}, inplace=True)

    for index, row in mode_df.iterrows():
        output_dict[('All Trip Mode Share', 'Regional', row['mode'])]=row['Mode Share']

    # Commute Trip Mode Share
    mode_df = hbw_trips[['hhno', 'mode']].groupby('mode').count()['hhno'].reset_index()
    mode_df['Mode Share']= mode_df['hhno']/mode_df.sum()['hhno']
    mode_df.replace({'mode':mode_dict}, inplace=True)

    for index, row in mode_df.iterrows():
        output_dict[('Commute Trip Mode Share', 'Regional', row['mode'])]=row['Mode Share']

    # Non-Commute Trip Mode Share
    mode_df = nhbw_trips[['hhno', 'mode']].groupby('mode').count()['hhno'].reset_index()
    mode_df['Mode Share']= mode_df['hhno']/mode_df.sum()['hhno']
    mode_df.replace({'mode':mode_dict}, inplace=True)

    for index, row in mode_df.iterrows():
        output_dict[('Non-Commute Trip Mode Share', 'Regional', row['mode'])]=row['Mode Share']

    # Mode share by geography
    for geog in geog_list:
        mode_geo(trip, geog+'_tripdest', output_dict, 'All Trip Mode Share')
        mode_geo(hbw_trips, geog+'_tripdest', output_dict, 'Commute Trip Mode Share')
        mode_geo(nhbw_trips, geog+'_tripdest', output_dict, 'Non-Commute Trip Mode Share')

    return output_dict



def person_vehicle_results(trip, person, output_dict):
    # Delay per person (Annual Hours)

    trip['delay'] = trip['travtime']-(trip['sov_ff_time']/100.0)
    driver_trips = trip[['rg_proposed', 'geog_name', 'People Of Color', 'Low Income', 'travdist', 'travtime', 'delay']].loc[trip['dorp']==1]
    output_dict[('Average Auto Delay per Resident', 'Regional', 'Total')] = (driver_trips['delay'].sum()/person['psexpfac'].sum())*weekday_to_annual/minutes_to_hour


    # VMT per resident per day
    output_dict[('Average VMT per Resident', 'Regional', 'Total')]=driver_trips['travdist'].sum()/ person['psexpfac'].sum()

    # VHT per resident per day
    output_dict[('Average VHT per Resident', 'Regional', 'Total')]=(driver_trips['travtime'].sum()/ (person['psexpfac'].sum()))/minutes_to_hour

    print 'calculating driver trip information by geography'
    # Driver Trip information by geography
    for geog in geog_list:
        delay_geo(driver_trips,geog, output_dict, 'Average Auto Delay per Resident', person)
        vmt_per_capita(driver_trips, geog, output_dict, 'Average VMT per Resident',person)
        vht_per_capita(driver_trips,geog, output_dict, 'Average VHT per Resident', person)

    return output_dict

def walk_bike_results(trip, person, output_dict):
    # Number and Percent of People Walking, Biking, or Transiting
    bike_walk_t_trips = trip[trip['mode'].isin([1,2,6])]

    df = bike_walk_t_trips.groupby(['hhno','pno']).count()
    df = df.reset_index()
    df = df[['hhno','pno']]
    df['bike_walk_t'] = 1

    df['bike_walk_t'] = df['bike_walk_t'].fillna(0)

    output_dict[('Share of Residents Walking, Biking, and Using Transit', 'Regional', 'Total')]=float(df['bike_walk_t'].sum())/person['psexpfac'].sum()
    output_dict[('Total of Residents Walking, Biking, and Using Transit', 'Regional', 'Total')]=df['bike_walk_t'].sum()


    # Number and Percent of People Walking, Biking, or Transiting by geographic category
    df = bike_walk_t_trips.groupby(['hhno','pno', 'rg_proposed', 'geog_name', 'People Of Color', 'Low Income']).count()
    df = df.reset_index()
    df = df[['hhno','pno','rg_proposed', 'geog_name','People Of Color', 'Low Income']]
    df['bike_walk_t'] = 1

    df['bike_walk_t'] = df['bike_walk_t'].fillna(0)

    for geog in geog_list:
     walk_bike_geo(df, geog, output_dict, person)
    
    return output_dict


if __name__ == "__main__":
    start_time = time.time()
    # Load network results
    print 'working on network summary'
    network_df = pd.read_excel(os.path.join(relative_path,'network/') + r'network_summary_detailed.xlsx',
                      sheetname='Network Summary')
    output_dict = network_results(network_df)
    network_time = time.time() 
    network_elapsed = network_time - start_time
    print 'network summary took '+ str(network_elapsed)

    print 'loading and merging person trip data files'
    dataset = h5_to_df(h5file, table_list=['Trip','Person', 'Household'])

    person = dataset['Person']
    trip = dataset['Trip']
    hh = dataset['Household']

    taz_geog = pd.read_csv(taz_reg_geog)
    county_taz = pd.read_csv(county_taz)
    equity_geog = pd.read_csv(equity_taz)


    print 'calculating person-based measures'
    person= merge_persons(person, hh, taz_geog, county_taz, equity_geog)
    trip = merge_trips(trip, person, taz_geog, county_taz, equity_geog)

    data_read_time = time.time()
    data_read_elapsed = data_read_time - network_time
    
    print 'data read and merging took '+ str(data_read_elapsed)
    output_dict =mode_results(trip, person, output_dict)

    mode_time = time.time()
    mode_elapsed = mode_time - data_read_time 

    print 'mode calculations took '+ str(mode_elapsed)
    output_dict =person_vehicle_results(trip, person, output_dict)

    person_vehicle_time = time.time()

    person_elapsed = person_vehicle_time - mode_time

    print 'Delay and VMT calculationts took ' + str(person_elapsed)
    output_dict =walk_bike_results(trip, person, output_dict)

    output_df = pd.DataFrame(output_dict.keys(), index = output_dict.values()).reset_index()
    output_df.columns = ['Value', 'Data Item', 'Geography', 'Grouping']


    output_df=output_df[output_df['Grouping']!='Other']
    output_df = output_df.sort_values(by = ['Data Item', 'Geography', 'Grouping'])
    output_df.to_csv(output_vision_file)
