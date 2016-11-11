import pandas as pd
import numpy as np
import h5py
import sys 
import os
#os.chdir('D:/Stefan/soundcast_obs_externals/soundcast')
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from emme_configuration import *
from EmmeProject import *

output_dir = r'outputs/supplemental/'
my_project = EmmeProject(r'projects\Supplementals\Supplementals.emp')

tod_factors = {'5to6' : .04, '6to7' : .075, '7to8' : 0.115, '8to9' : 0.091, '9to10' : 0.051, '10to14' : 0.179, '14to15' : 0.056, '15to16' : 0.071, '16to17' : 0.106, '17to18' : 0.101, 
        '18to20' : 0.06, '20to5' : 0.055}

# Get Zones
zonesDim = len(my_project.current_scenario.zone_numbers)
zones = my_project.current_scenario.zone_numbers
dictZoneLookup = dict((value,index) for index,value in enumerate(zones))

#Read External work trips
work = pd.read_excel('inputs/supplemental/External_Work_NonWork_Inputs.xlsx','External_Workers')
#Keep only the needed columns
work = work [['PSRC_TAZ','External_Station','Total_IE', 'Total_EI', 'SOV_Veh_IE', 'SOV_Veh_EI','HOV2_Veh_IE','HOV2_Veh_EI','HOV3_Veh_IE','HOV3_Veh_EI']]

#Group trips by O-D TAZ's
w_grp = work.groupby(['PSRC_TAZ','External_Station']).sum()
#Create empty numpy matrices for SOV, HOV2 and HOV3
w_SOV = np.zeros((zonesDim,zonesDim), np.float16)
w_HOV2 = np.zeros((zonesDim,zonesDim), np.float16)
w_HOV3 = np.zeros((zonesDim,zonesDim), np.float16)
#Populate the numpy trips matrices
for i in work['PSRC_TAZ'].value_counts().keys():
    for j in work.groupby('PSRC_TAZ').get_group(i)['External_Station'].value_counts().keys(): #all the external stations for each internal PSRC_TAZ
        #SOV
        w_SOV[dictZoneLookup[i],dictZoneLookup[j]] = w_grp.loc[(i,j),'SOV_Veh_IE']
        w_SOV[dictZoneLookup[j],dictZoneLookup[i]] = w_grp.loc[(i,j),'SOV_Veh_EI']
        #HOV2
        w_HOV2[dictZoneLookup[i],dictZoneLookup[j]] = w_grp.loc[(i,j),'HOV2_Veh_IE']
        w_HOV2[dictZoneLookup[j],dictZoneLookup[i]] = w_grp.loc[(i,j),'HOV2_Veh_EI']
        #HOV3
        w_HOV3[dictZoneLookup[i],dictZoneLookup[j]] = w_grp.loc[(i,j),'HOV3_Veh_IE']
        w_HOV3[dictZoneLookup[j],dictZoneLookup[i]] = w_grp.loc[(i,j),'HOV3_Veh_EI']
sov = w_SOV + w_SOV.transpose()
hov2 = w_HOV2 + w_HOV2.transpose()
hov3 = w_HOV3 + w_HOV3.transpose()

matrix_dict = {}
matrix_dict = {'svtl' : sov, 'h2tl' : hov2, 'h3tl' : hov3}

#Create h5 files

for tod, factor in tod_factors.iteritems():
    my_store = h5py.File(output_dir + '/' + 'external_work_' + tod + '.h5', "w")
    for mode, matrix in matrix_dict.iteritems():
        matrix = matrix * factor
        my_store.create_dataset(str(mode), data=matrix)
    my_store.close()	

######Create ixxi file
observed_ixxi = work.groupby('PSRC_TAZ').sum()
observed_ixxi = observed_ixxi.reindex(zones, fill_value=0)
observed_ixxi.reset_index(inplace = True)

parcel_df = pd.read_csv(r'inputs\accessibility\parcels_urbansim.txt',  sep = ' ')
hh_persons = h5py.File(r'inputs\hh_and_persons.h5', "r")
parcel_grouped = parcel_df.groupby('TAZ_P')
emp_by_taz = pd.DataFrame(parcel_grouped['EMPTOT_P'].sum())
emp_by_taz.reset_index(inplace = True)

def h5_to_data_frame(h5_file, group_name):
    col_dict = {}
    for col in h5_file[group_name].keys():
        my_array = np.asarray(h5_file[group_name][col])
        #print my_array
        col_dict[col] = my_array
    return pd.DataFrame(col_dict)


person_df = h5_to_data_frame(hh_persons, 'Person')
print len(person_df)
person_df = person_df.loc[(person_df.pwtyp > 0)]
hh_df = h5_to_data_frame(hh_persons, 'Household')
merged = person_df.merge(hh_df, how= 'left', on = 'hhno')
print len(merged)
merged_grouped = merged.groupby('hhtaz')

workers_by_taz = pd.DataFrame(merged_grouped['pno'].count())
workers_by_taz.rename(columns={'pno' :'workers'}, inplace = True)
workers_by_taz.reset_index(inplace = True)

final_df = emp_by_taz.merge(workers_by_taz, how= 'left', left_on = 'TAZ_P', right_on = 'hhtaz')
#final_df = final_df.merge(observed_ixxi, how= 'left', left_on = 'TAZ_P', right_on = 'PSRC_TAZ')
final_df = observed_ixxi.merge(final_df, how= 'left', left_on = 'PSRC_TAZ', right_on = 'TAZ_P')
final_df['Worker_IXFrac'] = final_df.Total_IE/final_df.workers
final_df['Jobs_XIFrac'] = final_df.Total_EI/final_df.EMPTOT_P

final_df.loc[final_df['Worker_IXFrac'] > 1, 'Worker_IXFrac'] = 1
final_df.loc[final_df['Jobs_XIFrac'] > 1, 'Jobs_XIFrac'] = 1

#final_df = taz_index_df.merge(final_df, how='left', left_on = 'Zone_id', right_on = 'TAZ_P')

final_df = final_df.replace([np.inf, -np.inf], np.nan) 
final_df = final_df.fillna(0)
final_df.index.rename('ZoneID', inplace = True)
final_df.reset_index(inplace = True)
final_cols = ['ZoneID', 'Worker_IXFrac', 'Jobs_XIFrac']
for col_name in final_df.columns:
    if col_name not in final_cols:
        final_df.drop(col_name, axis=1, inplace=True)
final_df = final_df.round(3)

#final_df.to_csv('D:/psrc_worker_ixxifractions.dat', sep = '\t', index = False)
final_df.to_csv('inputs/psrc_worker_ixxifractions.dat', sep = '\t', index = False, header = False)
