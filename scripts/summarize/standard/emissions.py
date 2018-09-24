import os, shutil
import numpy as np
import pandas as pd
from input_configuration import *
from emme_configuration import *
from standard_summary_configuration import *

def grams_to_tons(value):
   
    value = value/453.592
    value = value/2000
    
    return value

def calc_start_emissions():

    # Import emissions rates per vehicle 
    starts = pd.read_csv(r'scripts/summarize/inputs/network_summary/start_emission_rates.csv')

    # Filter out rates for model year
    starts['yearID'] = starts['yearID'].astype('str')
    starts = starts[starts['yearID'] == model_year]

    # Select winter rates for pollutants other than those listed in summer_list
    df_summer = starts[starts['pollutantID'].isin(summer_list)]
    df_summer = df_summer[df_summer['monthID'] == 7]
    df_winter = starts[~starts['pollutantID'].isin(summer_list)]
    df_winter = df_winter[df_winter['monthID'] == 1]
    starts = df_winter.append(df_summer)

    # Sum total emissions across all times of day, by county, for each pollutant
    starts = starts.groupby(['pollutantID','county']).sum()[['ratePerVehicle']].reset_index()

    # Estimate vehicle population for AQ purposes (not using Soundcast estimates)
    # Ref: X:\Trans\AIRQUAL\T2040 2018 Update\EmissionCalcs\Start Emissions\Estimate Vehicle Population_updatedfor2018.xlsx
    # Pivoting from 2014 Vehicle population data and 2040 projections -> updated to 2050 using this process
    base_county_veh = pd.DataFrame.from_dict(vehs_by_county, orient='index')
    base_county_veh.columns = ['vehicles']

    # Scale county vehicles by total change
    veh_scale = 1+(veh_totals[model_year]-veh_totals[base_year])/veh_totals[base_year]

    # Apply scale factor to the base vehicle sum by county
    scen_county_veh = base_county_veh*veh_scale
    scen_county_veh.reset_index(inplace=True)
    scen_county_veh.columns = ['county','vehicles']

    # Calculate totals by pollutant and county
    df = pd.merge(starts, scen_county_veh, on='county', how='left')

    df['start_grams'] = df['ratePerVehicle']*df['vehicles']
    df['start_tons'] = grams_to_tons(df['start_grams'])
    df['pollutant'] = df['pollutantID'].astype('str')

    # Sum across all counties
    df = df.groupby('pollutant').sum()[['start_tons']].reset_index()

    return df

def calc_iz_emissions(df_iz, rates):
    """ Calculate intrazonal running emissions. """

    # Map county to each zone
    county_df = pd.read_csv(r'scripts/summarize/inputs/county_taz.csv')
    df_iz = pd.merge(df_iz, county_df, how='left', on='taz')

    pollutant_list = np.unique(rates['pollutantId'])
    month_list = np.unique(rates['monthId'])

    for tod in tod_lookup.keys():
        df_iz['sov'+'_'+tod] = df_iz['svtl1'+'_'+tod]+df_iz['svtl2'+'_'+tod]+df_iz['svtl3'+'_'+tod]
        df_iz['hov2'+'_'+tod] = df_iz['h2tl1'+'_'+tod]+df_iz['h2tl2'+'_'+tod]+df_iz['h2tl3'+'_'+tod]
        df_iz['hov3'+'_'+tod] = df_iz['h3tl1'+'_'+tod]+df_iz['h3tl2'+'_'+tod]+df_iz['h3tl3'+'_'+tod]
        df_iz['tot_vol'+'_'+tod] = df_iz['sov'+'_'+tod]+df_iz['hov2'+'_'+tod]+df_iz['hov3'+'_'+tod]+df_iz['metrk'+'_'+tod]+df_iz['hvtrk'+'_'+tod]
        
    # Use assumed speed bin and roadway type
    speedbin = 4
    roadtype = 5

    # Initialize dictionary of intrazonal (iz) emissions totals
    iz_emissions = {k: 0 for k in pollutant_list}
    df_iz['tot_vmt'] = 0

    # Loop through each pollutant
    for pollutant in pollutant_list:
        for tod in tod_lookup.keys():
            if pollutant in summer_list:
                month = 7
            else:
                month = 1

            # Calculate VMT as volume times intrazonal distance
            df_iz['tot_vmt']  = df_iz['tot_vol'+'_'+tod]*df_iz['izdist']

            # Filter rates for given roadtype, speed, month, pollutant, and TOD
            df = rates[(rates['roadtypeId'] == roadtype) & 
                       (rates['avgspeedbinId'] == speedbin) & 
                       (rates['monthId'] == month) & 
                       (rates['pollutantId'] == int(pollutant)) &
                       (rates['hourId'] == tod_lookup[tod])]

            # Map county ID to name to match rates and soundcast output
            df['geog_name'] = df['countyId'].map(county_id)
            
            # Join total intrazonal VMT with emissions rates
            df = pd.merge(df_iz[['tot_vmt','geog_name']],df[['geog_name','gramsPerMile']],on='geog_name')
            df['emissions_total'] = df['tot_vmt']*df['gramsPerMile']

            # Sum across time period by pollutant
            iz_emissions[pollutant] += grams_to_tons(df['emissions_total'].sum())

    df_iz = pd.DataFrame.from_dict(iz_emissions, orient='index').reset_index()
    df_iz.columns = ['pollutant','intrazonal_tons']
    df_iz['pollutant'] = df_iz['pollutant'].astype('str')

    return df_iz

def calc_running_emissions(rates):
    """ Calcualte inter-zonal running emission rates from network outputs
    """
    
    # Running emissions from link-level results
    df = pd.read_csv(r'outputs/network/network_results.csv')
    county_flag_df = pd.read_csv(r'inputs/scenario/networks/county_flag_' + model_year + '.csv')
    df = pd.merge(df,county_flag_df,how='left',left_on='ij',right_on='ID')
    df['geog_name'] = df['NAME']

    pollutant_list = np.unique(rates['pollutantId'])
    month_list = np.unique(rates['monthId'])

    df['congested_speed'] = (df['length']/df['auto_time'])*60
    df['facility_type'] = df['data3']

    # remove links with facility type = 0
    df = df[df['facility_type'] > 0]

    # Calculate bus, medium, and heavy truck VMT
    df['bus_vmt'] = df['@bveh']*df['length']
    df['sov_vol'] = df['@svtl1']+df['@svtl2']+df['@svtl3']
    df['hov2_vol'] = df['@h2tl1']+df['@h2tl2']+df['@h2tl3']
    df['hov3_vol'] = df['@h3tl1']+df['@h3tl2']+df['@h3tl3']
    df['total_volume'] = df['sov_vol']+df['hov2_vol']+df['hov3_vol']+df['@mveh']+df['@hveh']+df['@bveh']
    df['total_vmt'] = df['total_volume']*df['length']
    df['hourId'] = df['tod'].map(tod_lookup).astype('int')

    # recode speed into moves bins
    df['avgspeedbinId'] = pd.cut(df['congested_speed'], speed_bins, labels=speed_bins_labels).astype('int')
    df['roadtypeId'] = df["facility_type"].map(fac_type_lookup).astype('int')

    df['index'] = df.index
    
    join_cols = ['avgspeedbinId','roadtypeId','hourId','geog_name']

    # Load running emission rates for the model year
    rates = pd.read_csv(r'scripts/summarize/inputs/network_summary/running_emission_rates.csv')
    rates['yearId'] = rates['yearId'].astype('str')
    rates = rates[rates['yearId'] == model_year]
    rates['geog_name'] = rates['countyId'].map(county_id)

    # Select rates based on season
    df_summer = rates[rates['pollutantId'].isin(summer_list)]
    df_summer = df_summer[df_summer['monthId'] == 7]
    df_winter = rates[~rates['pollutantId'].isin(summer_list)]
    df_winter = df_winter[df_winter['monthId'] == 1]
    rates = df_winter.append(df_summer)

    # Merge all rates to the main df
    df_pivot = pd.merge(df, rates, on=join_cols, how='left')

    # For now, drop rows with nulls
    df_pivot = df_pivot[-df_pivot['pollutantId'].isnull()]
    df_pivot['pollutantId'] = df_pivot['pollutantId'].astype('int').astype('str')
    df_pivot = df_pivot.pivot_table('gramsPerMile',join_cols,'pollutantId').reset_index()

    # Merge back to original df
    results_df = pd.merge(df[join_cols+['total_vmt','ij','index']], df_pivot, on=join_cols, how='left')

    # Calculate total columns
    pollutant_totals_list = []
    for pollutant in pollutant_list:
        results_df[str(pollutant)+'_total'] = results_df[str(pollutant)]*results_df['total_vmt']
        pollutant_totals_list.append(str(pollutant)+'_total')
        
    # write to csv
    results_df.to_csv(r'outputs/emissions/link_running_emissions.csv', index=False)
    
    summary_df = pd.DataFrame(results_df[pollutant_totals_list].sum())
    summary_df.columns = ['running_grams']
    summary_df['pollutant'] = [i.split('_')[0] for i in summary_df.index]
    summary_df.reset_index(drop=True, inplace=True)
    summary_df['running_tons'] = summary_df['running_grams']/453.592/2000
    
    return summary_df

def calculate_emissions(df_iz_vol, rates):
    """ Summarize total emissions from starts, intrazonal, and running emissions
        and export summary file. 
    """
    
    # Calcualte start emissions
    start_df = calc_start_emissions()

    # Calcualte  intrazonal emissions
    iz_df = calc_iz_emissions(df_iz_vol, rates)
    running_df = calc_running_emissions(rates)

    # Combine all emission sources 
    df = pd.merge(iz_df, running_df,how='left', on='pollutant').fillna(0)
    df = pd.merge(df, start_df,how='left', on='pollutant').fillna(0)
    df['daily_tons'] = df['intrazonal_tons'] + df['running_tons'] + df['start_tons']

    # Calculate total PM10 and PM2.5
    pm10 = df[df['pollutant'].isin(['100','106','107'])].sum()
    pm10['pollutant'] = 'PM10'
    pm25 = df[df['pollutant'].isin(['110','116','117'])].sum()
    pm25['pollutant'] = 'PM25'
    df = df.append(pm10, ignore_index=True)
    df = df.append(pm25, ignore_index=True)

    # Sort final output table by pollutant ID
    df_a = df[(df['pollutant'] != 'PM10') & (df['pollutant'] != 'PM25')]
    df_a['pollutant'] = df_a['pollutant'].astype('int')
    df_a = df_a.sort_values('pollutant')
    df_a['pollutant'] = df_a['pollutant'].astype('str')
    df_b = df[-((df['pollutant'] != 'PM10') & (df['pollutant'] != 'PM25'))]

    df = pd.concat([df_a,df_b])
    df['pollutant_name'] = df['pollutant'].map(pollutant_map)
    df = df[['pollutant','start_tons','intrazonal_tons','running_tons','daily_tons','pollutant_name']]

    df.to_csv(r'outputs/emissions/emissions_summary.csv', index=False)

def main():

    print 'Calculating emissions...'

    # Create fresh output directory
    emissions_output_dir = r'outputs/emissions'
    if os.path.exists(emissions_output_dir):
        shutil.rmtree(emissions_output_dir)
    os.makedirs(emissions_output_dir)

    # Load intrazonal volume data
    df_iz_vol = pd.read_csv(r'outputs/network/iz_vol.csv')

    # Load running emission rates for model year and replace county ID with name
    rates = pd.read_csv(r'scripts/summarize/inputs/network_summary/running_emission_rates.csv')
    rates['yearId'] = rates['yearId'].astype('str')
    rates = rates[rates['yearId'] == model_year]
    rates['geog_name'] = rates['countyId'].map(county_id)

    # Calculate start, intra-, and inter-zonal emissions 
    calculate_emissions(df_iz_vol=df_iz_vol, rates=rates)

if __name__ == '__main__':
    main()