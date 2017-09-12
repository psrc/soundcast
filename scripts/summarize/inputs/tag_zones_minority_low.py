import pandas as pd


census_file_old = pd.read_csv(r'R:\T2040_Update_2018\Special Needs Geography\parcel_to_minority.txt')
low_inc_file = pd.read_csv(r'R:\T2040_Update_2018\Special Needs Geography\ACS_15_5YR_Low-income_50%.csv')
minority_file = pd.read_csv(r'R:\T2040_Update_2018\Special Needs Geography\ACS_15_5YR_Minority_50%.csv')

census_tract_parcel = census_file_old.filter(['GEOID', 'parcelid', 'taz_p'], axis=1)

low_inc= pd.merge(low_inc_file, census_tract_parcel, on = 'GEOID')
low_inc_taz =  low_inc.groupby('taz_p').max().reset_index()
low_inc_taz2 = low_inc_taz.filter(['taz_p', 'LowIncomeTracts'])


minority = pd.merge(minority_file, census_tract_parcel, on = 'GEOID')
minority_taz =  minority.groupby('taz_p').max().reset_index()
minority_taz2 = minority_taz.filter(['taz_p', 'MinorityTract'])

low_inc_minority_taz = pd.merge(low_inc_taz2, minority_taz2, on ='taz_p')

low_inc_minority_taz.columns = ['TAZ', 'Low Income', 'Minority']

low_inc_minority_taz.to_csv(r'R:\T2040_Update_2018\Special Needs Geography\special_needs_taz.csv')
