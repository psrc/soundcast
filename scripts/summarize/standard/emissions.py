import os, shutil
import numpy as np
import pandas as pd
from input_configuration import *
from emme_configuration import *
from standard_summary_configuration import *

def grams_to_tons(value):
	""" Convert grams to tons."""

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

    # Sum across all counties
    df = df.groupby('pollutantID').sum()[['start_tons']]
    df['pollutant'] = df.index
    df.reset_index(drop=True, inplace=True)

    # Format table and calculate PM2.5, PM10 totals
    df = finalize_emissions(df)

    # df.to_csv(r'outputs\emissions\start_emissions.csv', index=False) 

    return df

def calc_iz_emissions(df_iz, rates):
	""" Calculate intrazonal running emissions."""

	# Map each zone to county
	county_df = pd.read_csv(r'scripts\summarize\inputs\county_taz.csv')
	df_iz = pd.merge(df_iz, county_df, how='left', on='taz')

	# Sum up SOV, HOV2, and HOV3 volumes across user classes 1, 2, and 3 by time of day
	# Calcualte VMT for these trips too; rename truck volumes for clarity
	for tod in tod_lookup.keys():
	    df_iz['sov_'+tod+'_vol'] = df_iz['svtl1_'+tod]+df_iz['svtl2_'+tod]+df_iz['svtl3_'+tod]
	    df_iz['hov2_'+tod+'_vol'] = df_iz['h2tl1_'+tod]+df_iz['h2tl2_'+tod]+df_iz['h2tl3_'+tod]
	    df_iz['hov3_'+tod+'_vol'] = df_iz['h3tl1_'+tod]+df_iz['h3tl2_'+tod]+df_iz['h3tl3_'+tod]
	    df_iz['mediumtruck_'+tod+'_vol'] = df_iz['metrk_'+tod]
	    df_iz['heavytruck_'+tod+'_vol'] = df_iz['hvtrk_'+tod]

	    # Calculate VMT as intrazonal distance times volumes 
	    df_iz['sov_'+tod+'_vmt'] = df_iz['sov_'+tod+'_vol']*df_iz['izdist']
	    df_iz['hov2_'+tod+'_vmt'] = df_iz['hov2_'+tod+'_vol']*df_iz['izdist']
	    df_iz['hov3_'+tod+'_vmt'] = df_iz['hov3_'+tod+'_vol']*df_iz['izdist']
	    df_iz['mediumtruck_'+tod+'_vmt'] = df_iz['mediumtruck_'+tod+'_vol']*df_iz['izdist']
	    df_iz['heavytruck_'+tod+'_vmt'] = df_iz['heavytruck_'+tod+'_vol']*df_iz['izdist']
	
	# Group totals by vehicle type, time-of-day, and county
	df = df_iz.groupby('geog_name').sum().T
	df.reset_index(inplace=True)
	df = df[df['index'].apply(lambda row: 'vmt' in row)]
	df.columns = ['index','King','Kitsap','Pierce','Snohomish']

	# Calculate total VMT by time of day and vehicle type
	# Ugly dataframe reformatting to unstack data
	df['tod'] = df['index'].apply(lambda row: row.split('_')[1])
	df['vehicle_type'] = df['index'].apply(lambda row: row.split('_')[0])
	df.drop('index', axis=1,inplace=True)
	df.index = df[['tod','vehicle_type']]
	df.drop(['tod','vehicle_type'],axis=1,inplace=True)
	df = pd.DataFrame(df.unstack()).reset_index()
	df['tod'] = df['level_1'].apply(lambda row: row[0])
	df['vehicle_type'] = df['level_1'].apply(lambda row: row[1])
	df.drop('level_1', axis=1, inplace=True)
	df.columns = ['geog_name','VMT','tod','vehicle_type']

	# Use hourly periods from emission rate files
	df['hourId'] = df['tod'].map(tod_lookup).astype('int')

	# Export this file for use with other rate calculations
	# Includes total VMT for each group for which rates are available
	df.to_csv(r'outputs/emissions/intrazonal_vmt_grouped.csv', index=False)

	# Join emissions rates to VMT totals
	iz_rates = rates.copy()

	# Select rates based on season (use either summer or winter rates)
	df_summer = iz_rates[iz_rates['pollutantId'].isin(summer_list)]
	df_summer = df_summer[df_summer['monthId'] == 7]
	df_winter = iz_rates[~iz_rates['pollutantId'].isin(summer_list)]
	df_winter = df_winter[df_winter['monthId'] == 1]
	iz_rates = df_winter.append(df_summer)

	# Use assumed standard speed bin and roadway type for all intrazonal trips
	speedbin = 4
	roadtype = 5

	iz_rates = iz_rates[(iz_rates['avgspeedbinId'] == speedbin) &
	                    (iz_rates['roadtypeId'] == roadtype)]

	# Merge data
	df = pd.merge(df, iz_rates, on=['geog_name','hourId'], how='left')
	df['intrazonal_total'] = df['VMT']*df['gramsPerMile']

	df = df.groupby(['pollutantId','vehicle_type']).sum()
	df.reset_index(inplace=True)

	# Calculate total emissions by pollutant and vehicle type
	df = df.pivot_table('intrazonal_total','pollutantId','vehicle_type',aggfunc='sum')
	df = grams_to_tons(df)
	df.columns = ['heavy_truck_intrazonal_tons', 'hov2_intrazonal_tons','hov3_intrazonal_tons', 'medium_truck_intrazonal_tons','sov_intrazonal_tons']

	df['pollutant'] = df.index
	df.reset_index(drop=True, inplace=True)
	df = finalize_emissions(df, '')

	# df.to_csv(r'outputs\emissions\intrazonal_emissions_summary.csv')

	return df

def calc_running_emissions(rates):
	""" Calcualte inter-zonal running emission rates from network outputs
	"""

	# List of vehicle types to include in results; note that bus is included here but not for intrazonals
	vehicle_type_list = ['sov','hov2','hov3','bus','medium_truck','heavy_truck']

	# Load link-level volumes by time of day and network county flags
	df = pd.read_csv(r'outputs/network/network_results.csv')
	county_flag_df = pd.read_csv(r'inputs/scenario/networks/county_flag_' + model_year + '.csv')
	df = pd.merge(df,county_flag_df,how='left',left_on='ij',right_on='ID')
	df['geog_name'] = df['NAME']

	# Remove links with facility type = 0 from the calculation
	df['facility_type'] = df['data3']    # Rename for human readability
	df = df[df['facility_type'] > 0]

	# Calculate VMT by bus, SOV, HOV2, HOV3+, medium truck, heavy truck
	df['sov_vol'] = df['@svtl1']+df['@svtl2']+df['@svtl3']
	df['sov_vmt'] = df['sov_vol']*df['length']
	df['hov2_vol'] = df['@h2tl1']+df['@h2tl2']+df['@h2tl3']
	df['hov2_vmt'] = df['hov2_vol']*df['length']
	df['hov3_vol'] = df['@h3tl1']+df['@h3tl2']+df['@h3tl3']
	df['hov3_vmt'] = df['hov3_vol']*df['length']
	df['bus_vmt'] = df['@bveh']*df['length']
	df['medium_truck_vmt'] = df['@mveh']*df['length']
	df['heavy_truck_vmt'] = df['@hveh']*df['length']

	# Convert TOD periods into hours used in emission rate files
	df['hourId'] = df['tod'].map(tod_lookup).astype('int')

	# Calculate congested speed to separate time-of-day link results into speed bins
	df['congested_speed'] = (df['length']/df['auto_time'])*60
	df['avgspeedbinId'] = pd.cut(df['congested_speed'], speed_bins, labels=speed_bins_labels).astype('int')

	# Relate soundcast facility types to emission rate definitions (e.g., minor arterial, freeway)
	df['roadtypeId'] = df["facility_type"].map(fac_type_lookup).astype('int')

	# Take total across columns where distinct emission rate are available
	# This calculates total VMT, by vehicle type (e.g., HOV3 VMT for hour 8, freeway, King County, 55-59 mph)
	join_cols = ['avgspeedbinId','roadtypeId','hourId','geog_name']
	df = df.groupby(join_cols).sum()
	df = df[['sov_vmt','hov2_vmt','hov3_vmt','bus_vmt','medium_truck_vmt','heavy_truck_vmt']]
	df = df.reset_index()

	# Write this file for calculation with different emission rates
	df.to_csv(r'outputs/emissions/interzonal_vmt_grouped.csv', index=False)

	# Calculate regional emissions inventory
	# Select rates based on season (use either summer or winter rates)
	df_summer = rates[rates['pollutantId'].isin(summer_list)]
	df_summer = df_summer[df_summer['monthId'] == 7]
	df_winter = rates[~rates['pollutantId'].isin(summer_list)]
	df_winter = df_winter[df_winter['monthId'] == 1]
	rates = df_winter.append(df_summer)

	# Join season-specific rates to total VMT by category to get total VMT by vehicle type
	df = pd.merge(df, rates, on=join_cols, how='left')

	# Calcualte total emissions by group in grams for all vehicle types 
	for vehicle_type in vehicle_type_list:
	    df[vehicle_type+'_interzonal'] = df[vehicle_type+'_vmt']*df['gramsPerMile']
	    
	# Calculate total emissions in grams for all pollutants
	df = df.groupby('pollutantId').sum()[[i+'_interzonal' for i in vehicle_type_list]]

	# Convert from grams to tons for all totals
	df = grams_to_tons(df)

	# Clean up results to be joined with other totals
	df['pollutant'] = df.index
	df.reset_index(drop=True, inplace=True)
	df = finalize_emissions(df, '_tons')

	return df

def finalize_emissions(df, col_suffix=""):
	""" 
	Compute PM10 and PM2.5 totals, sort index by pollutant value, and pollutant name.
	For total columns add col_suffix (e.g., col_suffix='intrazonal_tons')
	"""

	pm10 = df[df['pollutant'].isin([100,106,107])].sum()
	pm10['pollutant'] = 'PM10'
	pm25 = df[df['pollutant'].isin([110,116,117])].sum()
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

	common_cols = ['pollutant','pollutant_name']   # do not add suffix to these columns
	df.columns = [i+col_suffix for i in df.columns if i not in common_cols]+common_cols

	return df

def calculate_emissions(df_iz_vol, rates):
    """ Summarize total emissions from starts, intrazonal, and running emissions
        and export summary file. 
    """
    
    # Calcualte start emissions; write results to CSV
    start_df = calc_start_emissions()

    # Calcualte disaggregate (link-level) intrazonal emissions; write results to CSV
    iz_df = calc_iz_emissions(df_iz_vol, rates)
    
    # Calculate disaggregate running (interzonal) emissions; write results to CSV
    running_df = calc_running_emissions(rates)

    # Combine starts, intrazonal, and interzonal results
    df = pd.merge(iz_df, running_df, how='left', on=['pollutant','pollutant_name']).fillna(0)
    df = pd.merge(df, start_df,how='left', on=['pollutant','pollutant_name']).fillna(0)

    df.to_csv(r'outputs/emissions/emissions_summary_detailed.csv', index=False)

    # Generate brief summary of total starting, intrazonal, and interzonal emissions
    df_brief = df.copy()
    df_brief['total_intrazonal_tons'] = df_brief['heavy_truck_intrazonal_tons']+df_brief['medium_truck_intrazonal_tons']\
                                   +df_brief['sov_intrazonal_tons']+df_brief['hov2_intrazonal_tons']+df_brief['hov3_intrazonal_tons']
    df_brief['total_interzonal_tons'] = df_brief['heavy_truck_interzonal_tons']+df_brief['medium_truck_interzonal_tons']\
                                   +df_brief['sov_interzonal_tons']+df_brief['hov2_interzonal_tons']+df_brief['hov3_interzonal_tons']\
                                   +df_brief['bus_interzonal_tons']
    df_brief['total_daily_tons'] = df_brief['start_tons']+df_brief['total_intrazonal_tons']+df_brief['total_interzonal_tons']
    df_brief = df_brief[['start_tons','total_intrazonal_tons','total_interzonal_tons',
                                    'total_daily_tons','pollutant','pollutant_name']]
    df_brief.to_csv(r'outputs\emissions\emissions_summary.csv',index=False)

def calculate_tons_by_veh_type(df, df_rates):
    df.rename(columns={'geog_name':'county', 'avgspeedbinId': 'avgSpeedBinID', 'roadtypeId': 'roadTypeID', 'hourId': 'hourID'},
              inplace=True)

    df['county'] = df['county'].apply(lambda row: row.lower())
    
    # Calculate total VMT by vehicle group
    df['light'] = df['sov_vmt']+df['hov2_vmt']+df['hov3_vmt']
    df['medium'] = df['medium_truck_vmt']
    df['heavy'] = df['heavy_truck_vmt']
    # What about buses??
    df.drop(['sov_vmt','hov2_vmt','hov3_vmt','medium_truck_vmt','heavy_truck_vmt','bus_vmt'], inplace=True, axis=1)

    # Melt to pivot vmt by vehicle type columns as rows
    df = pd.melt(df, id_vars=['avgSpeedBinID','roadTypeID','hourID','county'], var_name='veh_type', value_name='vmt')

    newdf = pd.merge(df, df_rates, on=['avgSpeedBinID','roadTypeID','hourID','county','veh_type'], how='left', left_index=False)
    # Calculate total grams of emission 
    newdf['grams_tot'] = newdf['grams_per_mile']*newdf['vmt']
    newdf['tons_tot'] = grams_to_tons(newdf['grams_tot'])
    
    return newdf

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

    # Calculate separate emissions using rates by vehicle type

    # create directory for these output files
	output_dir = r'outputs/emissions/by_vehicle_type'
	if not os.path.exists(output_dir):
		os.makedirs(output_dir)

	# Calculate interzonal emissions by vehicle type
	df_running_rates = pd.read_csv(r'scripts/summarize/inputs/network_summary/running_emission_rates_by_veh_type.csv')

	df_running_rates.rename(columns={'sum(ratePerDistance)': 'grams_per_mile'}, inplace=True)
	df_running_rates['year'] = df_running_rates['year'].astype('str')
	df_running_rates = df_running_rates[df_running_rates['year'] == year]

	df_inter = pd.read_csv(r'outputs/emissions/interzonal_vmt_grouped.csv')
	df_inter = calculate_tons_by_veh_type(df_inter, df_running_rates)

	# Write raw output to file
	df_inter.to_csv(os.path.join(output_dir,'interzonal_emissions_by_veh_type.csv'), index=False)

	# Calculate intrazonal emissions by vehicle type
	df_intra = pd.read_csv(r'outputs/emissions/intrazonal_vmt_grouped.csv')
	df_intra.rename(columns={'vehicle_type':'veh_type', 'VMT': 'vmt', 'hourId': 'hourID', 'geog_name': 'county'},inplace=True)
	df_intra.drop('tod', axis=1, inplace=True)
	df_intra['county'] = df_intra['county'].apply(lambda row: row.lower())

	df_intra_light = df_intra[df_intra['veh_type'].isin(['sov','hov2','hov3'])]
	df_intra_light = df_intra_light.groupby(['county','hourID']).sum()[['vmt']].reset_index()
	df_intra_light['veh_type'] = 'light'

	df_intra_medium = df_intra[df_intra['veh_type'] == 'mediumtruck']
	df_intra_medium['veh_type'] = 'medium'
	df_intra_heavy = df_intra[df_intra['veh_type'] == 'heavytruck']
	df_intra_heavy['veh_type'] = 'heavy'

	df_intra = df_intra_light.append(df_intra_medium)
	df_intra = df_intra.append(df_intra_heavy)

	# For intrazonals, assume standard speed bin and roadway type for all intrazonal trips
	speedbin = 4
	roadtype = 5

	iz_rates = df_running_rates[(df_running_rates['avgSpeedBinID'] == speedbin) &
	                    (df_running_rates['roadTypeID'] == roadtype)]

	df_intra = pd.merge(df_intra, iz_rates, on=['hourID','county','veh_type'], how='left', left_index=False)
	# Calculate total grams of emission 
	df_intra['grams_tot'] = df_intra['grams_per_mile']*df_intra['vmt']
	df_intra['tons_tot'] = grams_to_tons(df_intra['grams_tot'])

	# Write raw output to file
	df_intra.to_csv(os.path.join(output_dir,'intrazonal_emissions_by_veh_type.csv'), index=False)

	# Calculate start emissions
	start_rates_df = pd.read_csv(r'scripts/summarize/inputs/network_summary/start_emission_rates_by_veh_type.csv')

	base_county_veh = pd.DataFrame.from_dict(vehs_by_type, orient='index')

	# Scale county vehicles by total change
	veh_scale = 1+(veh_totals[model_year]-veh_totals[base_year])/veh_totals[base_year]

	# # Apply scale factor to the base vehicle sum by county
	scen_county_veh = base_county_veh*veh_scale

	vehicles_df = pd.DataFrame(scen_county_veh.unstack()).reset_index()
	vehicles_df.columns = ['veh_type','county','vehicles']

	# Join with rates to calculate total emissions
	start_emissions_df = pd.merge(vehicles_df, start_rates_df, on=['veh_type','county'])
	start_emissions_df['start_grams'] = start_emissions_df['vehicles']*start_emissions_df['ratePerVehicle'] 
	start_emissions_df['start_tons'] = grams_to_tons(start_emissions_df['start_grams'])
	start_emissions_df = start_emissions_df.groupby(['pollutantID','veh_type','county']).sum().reset_index()

	# Write raw output to file
	start_emissions_df.to_csv(os.path.join(output_dir,'start_emissions_by_veh_type.csv'), index=False)

	# Combine all rates and export as CSV
	df_inter_group = df_inter.groupby(['pollutantID','county','veh_type']).sum()[['tons_tot']].reset_index()
	df_inter_group.rename(columns={'tons_tot': 'interzonal_tons'}, inplace=True)
	df_intra_group = df_intra.groupby(['pollutantID','county','veh_type']).sum()[['tons_tot']].reset_index()
	df_intra_group.rename(columns={'tons_tot': 'intrazonal_tons'}, inplace=True)
	df_start_group = start_emissions_df.groupby(['pollutantID','county','veh_type']).sum()[['start_tons']].reset_index()

	summary_df = pd.merge(df_inter_group, df_intra_group)
	summary_df = pd.merge(summary_df, df_start_group)

	summary_df.to_csv(os.path.join(output_dir,'emissions_by_veh_type_summary.csv'),index=False)

if __name__ == '__main__':
    main()