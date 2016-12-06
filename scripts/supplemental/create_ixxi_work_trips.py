import pandas as pd
import numpy as np
import h5py
import sys 
import os
#os.chdir('D:/Stefan/TWG/Estimated_Models_Pre_Calibration')
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.path.join(os.getcwd(),"scripts/trucks"))
from emme_configuration import *
from input_configuration import *
from EmmeProject import *
from truck_configuration import *

output_dir = r'outputs/supplemental/'
my_project = EmmeProject(r'projects\Supplementals\Supplementals.emp')

tod_factors = {'5to6' : .04, '6to7' : .075, '7to8' : 0.115, '8to9' : 0.091, '9to10' : 0.051, '10to14' : 0.179, '14to15' : 0.056, '15to16' : 0.071, '16to17' : 0.106, '17to18' : 0.101, 
        '18to20' : 0.06, '20to5' : 0.055}

# list of jblm taz's
jblm_taz_list = [3061, 3070, 3348, 3349, 3352, 3353, 3355, 3356]

# dictionary to hold taz id and total enlisted to use to update externals
jbml_enlisted_taz_dict = {}

# it might make sense to put these file locations in a config somewhere
parcel_file =  "inputs\\accessibility\\parcels_urbansim.txt"
military_file = "inputs\\accessibility\\enlisted_personnel.csv"
non_worker_file = r'inputs\supplemental\generation\externals_unadjusted.csv'


def network_importer(EmmeProject):
    for scenario in list(EmmeProject.bank.scenarios()):
            EmmeProject.bank.delete_scenario(scenario)
        #create scenario
    EmmeProject.bank.create_scenario(1002)
    EmmeProject.change_scenario()
        #print key
    EmmeProject.delete_links()
    EmmeProject.delete_nodes()
    EmmeProject.process_modes('inputs/networks/' + mode_file)
    EmmeProject.process_base_network('inputs/networks/' + truck_base_net_name)

def h5_to_data_frame(h5_file, group_name):
    col_dict = {}
    for col in h5_file[group_name].keys():
        my_array = np.asarray(h5_file[group_name][col])
        col_dict[col] = my_array
    return pd.DataFrame(col_dict)

# bank needs a network
network_importer(my_project)

# input files
parcels_urbansim = pd.read_csv(parcel_file, sep = " ")
parcels_military = pd.read_csv(military_file)
non_worker_external = pd.read_csv(non_worker_file)


######## Add enlisted jobs to parcels:

#military file has a record for each block so need to sum, but keep first zone
f = {}
for col in parcels_military.columns:
    if col == 'Zone' :
        f[col] = ['first']
    elif col <> 'ParcelID':
        f[col] = ['sum']
parcels_military = parcels_military.groupby('ParcelID').agg(f).reset_index()

# go through each parcel and add enlisted job to the parcel file
for row in parcels_military.iterrows():
    parcel_id = int(row[1]['ParcelID'])
    taz_id = int(row[1]['Zone'])
    enlisted_jobs = float(row[1][scenario_name])
    if taz_id in jblm_taz_list:
        jbml_enlisted_taz_dict[taz_id] = enlisted_jobs
    # add enlisted jobs to existing gov jobs at the parcel
    parcels_urbansim.ix[parcels_urbansim.PARCELID==parcel_id, 'EMPGOV_P'] = float(parcels_urbansim.ix[parcels_urbansim.PARCELID==parcel_id, 'EMPGOV_P']) + enlisted_jobs
    # add enlisted jobs to existing total jobs at the parcel
    print 'old total ' + str(float(parcels_urbansim.ix[parcels_urbansim.PARCELID==parcel_id, 'EMPTOT_P']))
    parcels_urbansim.ix[parcels_urbansim.PARCELID==parcel_id, 'EMPTOT_P'] = float(parcels_urbansim.ix[parcels_urbansim.PARCELID==parcel_id, 'EMPTOT_P']) + enlisted_jobs
    print 'new total ' + str(float(parcels_urbansim.ix[parcels_urbansim.PARCELID==parcel_id, 'EMPTOT_P']))
   
parcels_urbansim.to_csv(parcel_file, sep = ' ', index = False)
###############

######## Create Trip Tables for IXXI jobs:
# Get Zones
zonesDim = len(my_project.current_scenario.zone_numbers)
zones = my_project.current_scenario.zone_numbers
dictZoneLookup = dict((value,index) for index,value in enumerate(zones))

# read External work trips
work = pd.read_excel('inputs/supplemental/distribution/External_Work_NonWork_Inputs.xlsx','External_Workers')
# keep only the needed columns
work = work [['PSRC_TAZ','External_Station','Total_IE', 'Total_EI', 'SOV_Veh_IE', 'SOV_Veh_EI','HOV2_Veh_IE','HOV2_Veh_EI','HOV3_Veh_IE','HOV3_Veh_EI']]

# group trips by O-D TAZ's
w_grp = work.groupby(['PSRC_TAZ','External_Station']).sum()

# external enlisted are not included in worker flow file, so we are adding them in for JBML. assume that 30% jblm enlisted come from thurston county:
for taz in jblm_taz_list:
    # 30% come from the two thurston county externals
    enlisted = jbml_enlisted_taz_dict[taz] * .3
    
    # use 90% for I-5 external- 3733, put them all in SOV for now
    if not (taz, 3733) in list(w_grp.index.values):
        w_grp.ix[(taz,3733),:] = 0
    w_grp.ix[(taz,3733),'Total_EI'] = w_grp.ix[(taz,3733),'Total_EI'] + (.90 * enlisted)
    w_grp.ix[(taz,3733),'SOV_Veh_EI'] = w_grp.ix[(taz,3733),'SOV_Veh_EI'] + (.90 * enlisted)
    
    # use 90% for I-5 external- 3733, put them all in SOV for now
    if not (taz, 3734) in list(w_grp.index.values):
        w_grp.ix[(taz,3734),:] = 0
    w_grp.ix[(taz,3734),'Total_EI'] = w_grp.ix[(taz,3734),'Total_EI'] + (.10 * enlisted)
    w_grp.ix[(taz,3734),'SOV_Veh_EI'] = w_grp.ix[(taz,3734),'SOV_Veh_EI'] + (.10 * enlisted)

# update the exernal non worker inpout for the gravity model:
non_worker_external.ix[non_worker_external.taz==3733, 'hsppro'] = float(non_worker_external.ix[non_worker_external.taz==3733, 'hsppro'] - (.90 * .30 * sum(jbml_enlisted_taz_dict.values())))
non_worker_external.ix[non_worker_external.taz==3734, 'hsppro'] = float(non_worker_external.ix[non_worker_external.taz==3734, 'hsppro'] - (.10 * .30 * sum(jbml_enlisted_taz_dict.values())))

# export to .csv
non_worker_external.to_csv(r'inputs\supplemental\generation\externals.csv', index = False)

# create empty numpy matrices for SOV, HOV2 and HOV3
w_SOV = np.zeros((zonesDim,zonesDim), np.float16)
w_HOV2 = np.zeros((zonesDim,zonesDim), np.float16)
w_HOV3 = np.zeros((zonesDim,zonesDim), np.float16)

# populate the numpy trips matrices
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

# create h5 files

for tod, factor in tod_factors.iteritems():
    my_store = h5py.File(output_dir + '/' + 'external_work_' + tod + '.h5', "w")
    for mode, matrix in matrix_dict.iteritems():
        matrix = matrix * factor
        my_store.create_dataset(str(mode), data=matrix)
    my_store.close()	

###############

######Create ixxi file
w_grp.reset_index(inplace= True)
w_grp.reset_index(inplace= True)
observed_ixxi = w_grp.groupby('PSRC_TAZ').sum()
observed_ixxi = observed_ixxi.reindex(zones, fill_value=0)
observed_ixxi.reset_index(inplace = True)

parcel_df = pd.read_csv(r'inputs\accessibility\parcels_urbansim.txt',  sep = ' ')
hh_persons = h5py.File(r'inputs\hh_and_persons.h5', "r")
parcel_grouped = parcel_df.groupby('TAZ_P')
emp_by_taz = pd.DataFrame(parcel_grouped['EMPTOT_P'].sum())
emp_by_taz.reset_index(inplace = True)

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
final_df = observed_ixxi.merge(final_df, how= 'left', left_on = 'PSRC_TAZ', right_on = 'TAZ_P')
final_df['Worker_IXFrac'] = final_df.Total_IE/final_df.workers
final_df['Jobs_XIFrac'] = final_df.Total_EI/final_df.EMPTOT_P

final_df.loc[final_df['Worker_IXFrac'] > 1, 'Worker_IXFrac'] = 1
final_df.loc[final_df['Jobs_XIFrac'] > 1, 'Jobs_XIFrac'] = 1

final_df = final_df.replace([np.inf, -np.inf], np.nan) 
final_df = final_df.fillna(0)
final_cols = ['PSRC_TAZ', 'Worker_IXFrac', 'Jobs_XIFrac']

for col_name in final_df.columns:
    if col_name not in final_cols:
        final_df.drop(col_name, axis=1, inplace=True)
final_df = final_df.round(3)

final_df.to_csv('inputs/psrc_worker_ixxifractions.dat', sep = '\t', index = False, header = False)

###############
