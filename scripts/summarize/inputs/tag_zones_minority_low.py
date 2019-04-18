import pandas as pd


parcels_tract = pd.read_csv(r'J:\Projects\V2050\SEIS\Data_Support\Equity_Geography\parcels_to_tract.csv')
parcels_zone =  pd.read_csv(r'R:\SoundCast\Inputs\lodes\vision\2050_just_friends_beta\landuse\parcels_urbansim.txt', sep = ' ')
census_data = pd.read_csv(r'J:\Projects\V2050\SEIS\Data_Support\Equity_Geography\2015-and-2016-5yr-ACS-Equity-Populations-20181009.csv')


parcels_census = pd.merge(parcels_tract, census_data, left_on= 'census_tract', right_on = 'GEOID10')
census_zone = pd.merge(parcels_census, parcels_zone, left_on ='parcel_id', right_on = 'parcelid')

census_zone = census_zone[['taz_p', 'GEOID10', 'minority_geog', 'poverty_geog']]

zone_minority = census_zone.groupby('taz_p').median().reset_index()

zone_minority.to_csv('C:\soundcast_dev\scripts\summarize\inputs\equity_geog.csv')