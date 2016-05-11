import pandas as pd
import sys
import os
from input_configuration import *
sys.path.append(os.path.join(os.getcwd(),"scripts"))


#it might make sense to put these file locations in a config somewhere
parcel_file =  "inputs\\accessibility\\parcels_urbansim.txt"
military_file = "inputs\\accessibility\\parcels_military.csv"
jblm_file = "inputs\\accessibility\\\distribute_jblm_jobs.csv"

parcels_urbansim = pd.read_csv(parcel_file, sep = " ")



parcels_military = pd.read_csv(military_file)
parcels_military.dropna(subset = ['Parcel_ID'])

#these are regular jobs that need to be redistributed to other JBLM taz's, which currently do not have parcels so we aree
#making dummy ones. 
jblm_govt_jobs = pd.read_csv(jblm_file)
if base_year == 2010:
    lone_jblm_parcel = 1500003
else:
    lone_jblm_parcel = 2

all_parcels = parcels_urbansim.merge(parcels_military, how='outer', left_on='PARCELID', right_on="Parcel_ID")
all_parcels.fillna(0, inplace =True)

# for updating the parcels that already exist and have ids, add the values from military jobs
all_parcels['EMPGOV_P'] = all_parcels['EMPGOV_P'] + all_parcels['Emp']
all_parcels['EMPTOT_P'] = all_parcels['EMPTOT_P'] + all_parcels['Emp']

# if a parcel_id is new in the column Parcel_ID,
# add the parcel as the max parcel id  + 1 currently on the parcels table
# fill the X Y s and the EmpGov_P field

max_id =int(all_parcels['PARCELID'].max())
new_max = max_id + 1
max_index = all_parcels.index.max()

all_parcels.fillna(0, inplace =True)

# add the new imaginary parcels to the dataset for the parcels that are military but don't have parcel ids
for index, row in all_parcels.iterrows():
    if row['Parcel_ID'] == -1:
        row['PARCELID'] = new_max
        new_max = new_max + 1
        row['EMPGOV_P'] = row['Emp']
        row['EMPTOT_P'] = row['Emp']
        row['XCOORD_P'] = row['x']
        row['YCOORD_P'] = row['y']
        row['TAZ_P'] = row['TAZ']




# get rid of the extra columns from the military parcels
for colname in parcels_military.columns:
    all_parcels = all_parcels.drop(colname, 1)

for colname in all_parcels.columns:
    all_parcels[colname] = all_parcels[colname].astype(int)


#jblm stuff:
all_parcels = all_parcels.merge(jblm_govt_jobs, how='outer', left_on='PARCELID', right_on="Parcel_ID")

all_parcels.fillna(0, inplace =True)

jblm_parcel_record = all_parcels.loc[all_parcels['PARCELID'] == lone_jblm_parcel]

total_jblm_jobs = int(jblm_parcel_record['EMPGOV_P'])

new_total = int(total_jblm_jobs/5)

for index, row in all_parcels.iterrows():
    if row['PARCELID'] == lone_jblm_parcel:
        row['EMPGOV_P'] = new_total
        row['EMPTOT_P'] = row['EMPEDU_P'] + row['EMPFOO_P'] + row['EMPGOV_P'] + row['EMPIND_P'] + row['EMPMED_P'] + row['EMPOFC_P'] + row['EMPOTH_P'] + row['EMPRET_P'] + row['EMPRSC_P'] + row['EMPSVC_P']
    elif row['Parcel_ID'] == -1:
        row['PARCELID'] = new_max
        new_max = new_max + 1
        row['EMPGOV_P'] = new_total
        row['EMPTOT_P'] = new_total
        row['XCOORD_P'] = row['x']
        row['YCOORD_P'] = row['y']
        row['TAZ_P'] = row['TAZ']

for colname in jblm_govt_jobs.columns:
    all_parcels = all_parcels.drop(colname, 1)

for colname in all_parcels.columns:
    all_parcels[colname] = all_parcels[colname].astype(int)

# for some reason, there are some zeroes on the parcels file at the end that we don't want
all_parcels = all_parcels[all_parcels.PARCELID !=0]

all_parcels.to_csv(parcel_file, sep = ' ', index = False)
print 'Parcels successfully updated with military jobs.'