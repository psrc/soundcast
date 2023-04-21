import pandas as pd
import h5py
import itertools
import collections
import xlsxwriter
import os, sys
import numpy as np
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.path.join(os.getcwd(),"scripts\summarize"))
import datetime
# from input_configuration import *
import h5toDF
import toml
config = toml.load(os.path.join(os.getcwd(), 'configuration/input_configuration.toml'))


#for_testing - hard coding the paths for now- fix later!
model_dir = 'C:\\soundcastrepo\\'
bike_output_file = "C:\\soundcastrepo\\outputs\\BikeOutputs.xlsx"


def get_variables_trips(output_df,trip_variables, hh_variables, person_variables):
    trip_data = output_df['Trip'][trip_variables]
    hh_data = output_df['Household'][hh_variables]
    person_data = output_df['Person'][person_variables]
    tour_data = output_df['Tour'][['hhno', 'pno', 'id']]
    tour_data.rename(columns = {'id': 'tour_id'}, inplace = True)

    merge_hh_person = pd.merge(hh_data, person_data, 'inner', on = 'hhno')
    merge_hh_person.reset_index()
    tour_data.reset_index()
    merge_hh_tour = pd.merge(merge_hh_person, tour_data, 'inner', on =('hhno', 'pno'))
    merge_trip_hh = pd.merge(merge_hh_tour, trip_data, 'outer', on= 'tour_id')
    return merge_trip_hh  

def get_variables_trips_survey(output_df,trip_variables_survey, person_variables_survey, hh_variables):
    trip_data = output_df['Trip'][trip_variables_survey]
    person_data = output_df['Person'][person_variables_survey]
    hh_data = output_df['Household'][hh_variables]


    merge_hh_person = pd.merge(hh_data, person_data, 'inner', on = 'hhno')
    merge_hh_person.reset_index()
    merge_trip_hh = pd.merge(trip_data, merge_hh_person, 'inner',  on =('hhno', 'pno'))
    return merge_trip_hh


# Get the data
SURVEY_DAYS =2


zone_district = pd.DataFrame.from_csv(model_dir+districtfile, index_col = None)

#Model Outputs
trip_variables = ['otaz', 'dtaz', 'travtime', 'travcost',  'travdist', 'pno', 'mode', 'tour_id', 'opcl', 'dpcl', 'dorp', 'dpurp']
hh_variables = ['hhno', 'hhincome', 'hhvehs', 'hhtaz']
person_variables = ['hhno', 'pno', 'pagey', 'pgend', 'id']
outputs = h5toDF.convert(model_dir + h5_results_file,model_dir+guidefile, 'outputs')
trips_output = get_variables_trips(outputs, trip_variables, hh_variables, person_variables)
trips_output =  pd.merge(trips_output, zone_district, left_on = 'dtaz', right_on = 'TAZ')
bikes_output = trips_output.loc[(trips_output['mode']=='Bike')]


#Household Survey
trip_variables_survey = ['otaz', 'dtaz', 'travtime', 'travcost',  'travdist', 'pno', 'mode', 'opcl', 'dpcl', 'dorp', 'dpurp', 'hhno', 'trexpfac']
person_variables_survey = ['hhno', 'pno', 'pagey', 'pgend']
survey = h5toDF.convert(model_dir +h5_comparison_file, model_dir+guidefile, 'survey')
trips_survey = get_variables_trips_survey(survey, trip_variables_survey , person_variables_survey, hh_variables)
trips_survey =  pd.merge(trips_survey, zone_district, left_on = 'dtaz', right_on = 'TAZ')
bikes_survey = trips_survey.loc[(trips_survey['mode']=='Bike')]
bike_survey_geo = pd.merge(bikes_output, zone_district, left_on = 'dtaz', right_on = 'TAZ')

#Do some summaries###########

# Bike Mode Share

# by Purpose
model_bike_purp = bikes_output.groupby('dpurp').count()['hhno']
model_tot_purp = trips_output.groupby('dpurp').count()['hhno']

survey_bike_purp = bikes_survey.groupby('dpurp').sum()['trexpfac']
survey_tot_purp = trips_survey.groupby('dpurp').sum()['trexpfac']

# by County
model_bike_cty = bikes_output.groupby('County').count()['hhno']
model_tot_cty= trips_output.groupby('County').count()['hhno']

survey_bike_cty = bikes_survey.groupby('County').sum()['trexpfac']
survey_tot_cty = trips_survey.groupby('County').sum()['trexpfac']

# by District
model_bike_distr= bikes_output.groupby('New DistrictName').count()['hhno']
model_tot_distr= trips_output.groupby('New DistrictName').count()['hhno']

survey_bike_distr = bikes_survey.groupby('New DistrictName').sum()['trexpfac']
survey_tot_distr = trips_survey.groupby('New DistrictName').sum()['trexpfac']

# by Gender
model_bike_gend= bikes_output.groupby('pgend').count()['hhno']
model_tot_gend = trips_output.groupby('pgend').count()['hhno']

survey_bike_gend = bikes_survey.groupby('pgend').sum()['trexpfac']
survey_tot_gend = trips_survey.groupby('pgend').sum()['trexpfac']


# by Age Group

age_bins = [0, 16, 35, 64, 80]
model_bike_age =pd.cut(bikes_output['pagey'], bins = age_bins)
model_bike_age_counts = pd.value_counts(model_bike_age)
model_tot_age = pd.cut(trips_output['pagey'], bins = age_bins)
model_tot_age_counts = pd.value_counts(model_tot_age)

survey_bike_age = pd.cut(bikes_survey['pagey'], bins = age_bins)
survey_bike_age_counts = pd.value_counts(survey_bike_age)
survey_tot_age = pd.cut(trips_survey['pagey'], bins = age_bins)
survey_tot_age_counts = pd.value_counts(survey_tot_age)


# Bike Trip Length Distribution#################
distance_bins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 100]
model_bike_dist =pd.cut(bikes_output['travdist'], bins = distance_bins)
model_bike_dist_counts = pd.value_counts(model_bike_dist)

#not worrying about the weights for now
survey_bike_dist = pd.cut(bikes_survey['travdist'], bins = distance_bins)
survey_bike_dist_counts = pd.value_counts(survey_bike_dist)

# Average Bike Trip Length
# For the survey add a weight value:
bikes_survey['weighted_distance'] = bikes_survey['travdist']* bikes_survey['trexpfac']

model_bike_dist = bikes_output['travdist'].mean()
survey_bike_dist = (bikes_survey['weighted_distance'].sum())/(bikes_survey['trexpfac'].sum())

# By Purpose
model_bike_dist_purp = bikes_output.groupby('dpurp').mean()['travdist']
survey_bike_dist_purp = (bikes_survey.groupby('dpurp').sum()['weighted_distance'])/(bikes_survey.groupby('dpurp').sum()['trexpfac'])

# By District
model_bike_dist_distr = bikes_output.groupby('New DistrictName').mean()['travdist']
survey_bike_dist_distr = (bikes_survey.groupby('New DistrictName').sum()['weighted_distance'])/(bikes_survey.groupby(['New DistrictName']).sum()['trexpfac'])

# by County
model_bike_dist_county = bikes_output.groupby('County').mean()['travdist']
survey_bike_dist_county = (bikes_survey.groupby('County').sum()['weighted_distance'])/(bikes_survey.groupby('County').sum()['trexpfac'])

#Write all the stuff out
# There is definitely a more elegant way of doing this.  I'm just making it work for now. Like we could put all the items into a big dataframe or dictionary
# and write out the whole dataframe or dictionary
REPORT_ROW_GAP = 15

bike_writer = pd.ExcelWriter(bike_output_file, engine = 'xlsxwriter')
START_ROW = 1

pd.DataFrame(model_bike_purp).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(model_tot_purp).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_bike_purp).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_tot_purp).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

REPORT_ROW_GAP = 8
pd.DataFrame(model_bike_cty).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(model_tot_cty).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_bike_cty).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_tot_cty).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

REPORT_ROW_GAP = 20
pd.DataFrame(model_bike_distr).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(model_tot_distr).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_bike_distr).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_tot_distr).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

REPORT_ROW_GAP = 4
pd.DataFrame(model_bike_gend).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(model_tot_gend).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_bike_gend).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_tot_gend).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

REPORT_ROW_GAP = 6
pd.DataFrame(model_bike_age_counts).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(model_tot_age_counts).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_bike_age_counts).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_tot_age_counts).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

REPORT_ROW_GAP = 5
pd.DataFrame([model_bike_dist, survey_bike_dist]).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP




REPORT_ROW_GAP = 20

pd.DataFrame(model_bike_dist_counts).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_bike_dist_counts).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

REPORT_ROW_GAP = 12

pd.DataFrame(model_bike_dist_purp).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_bike_dist_purp).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP


REPORT_ROW_GAP = 6

pd.DataFrame(model_bike_dist_county).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_bike_dist_county).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

REPORT_ROW_GAP = 20

pd.DataFrame(model_bike_dist_distr).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

pd.DataFrame(survey_bike_dist_distr).to_excel(excel_writer = bike_writer, sheet_name =  'Raw Bike Data', na_rep = 0, startrow = START_ROW)
START_ROW = START_ROW + REPORT_ROW_GAP

bike_writer.close()