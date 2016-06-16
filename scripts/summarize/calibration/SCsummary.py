#Copyright [2014] [Puget Sound Regional Council]

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import os
import sys
sys.path.append(os.path.join(os.getcwd(),"scripts\summarize"))
import numpy as np
import pandas as pd
import xlsxwriter
import time
from h5toDF import *
from xlautofit import *
import math
from input_configuration import *
from summary_functions import *
from calibration_summary_configuration import *



def DistrictSummary(data1, data2, name1, name2, location, districtfile):
    print('---Begin District to District Summary compilation---')
    start = time.time()

    trip_ok_1 = data1['Trip'][['travdist', 'otaz', 'dtaz', 'trexpfac']].query('travdist>0 and travdist<200')
    trip_ok_2 = data2['Trip'][['travdist', 'otaz', 'dtaz', 'trexpfac']].query('travdist>0 and travdist<200')
    DistrictDict = {}
    for i in range(len(districtfile['TAZ'])):
        if districtfile['TAZ'][i] not in DistrictDict and math.isnan(districtfile['TAZ'][i]) is False:
            DistrictDict.update({int(districtfile['TAZ'][i]):districtfile['New DistrictName'][i]})
    trip_ok_1['Origin'] = trip_ok_1['otaz'].map(DistrictDict)
    trip_ok_2['Origin'] = trip_ok_2['otaz'].map(DistrictDict)
    trip_ok_1['Destination'] = trip_ok_1['dtaz'].map(DistrictDict)
    trip_ok_2['Destination'] = trip_ok_2['dtaz'].map(DistrictDict)
    trip_od1 = trip_ok_1[['Origin', 'Destination', 'trexpfac']].groupby(['Origin', 'Destination']).sum()['trexpfac'].round(0)
    trip_od2 = trip_ok_2[['Origin', 'Destination', 'trexpfac']].groupby(['Origin', 'Destination']).sum()['trexpfac'].round(0)
    trip_od1 = pd.DataFrame.from_items([('Trips', trip_od1)])
    trip_od2 = pd.DataFrame.from_items([('Trips', trip_od2)])
    trip_od1 = trip_od1.reset_index()
    trip_od2 = trip_od2.reset_index()
    tripod1 = trip_od1.pivot('Origin', 'Destination', 'Trips')
    tripod2 = trip_od2.pivot('Origin', 'Destination', 'Trips')
    tripoddiff = tripod1 - tripod2
    tripodpd = tripoddiff / tripod2 * 100
    for column in tripodpd.columns:
        tripodpd[column] = tripodpd[column].round(2)

    print('District to District data frames created in ' + str(round(time.time() - start, 1)) + ' seconds')

    writer = pd.ExcelWriter(location + '/DistrictReport.xlsx', engine = 'xlsxwriter')
    tripod1.to_excel(excel_writer = writer, sheet_name = 'Number of Trips by District', na_rep = 0, startrow = 1)
    tripod2.to_excel(excel_writer = writer, sheet_name = 'Number of Trips by District', na_rep = 0, startrow = 16)
    tripoddiff.to_excel(excel_writer = writer, sheet_name = 'Number of Trips by District', na_rep = 0, startrow = 31)
    tripodpd.to_excel(excel_writer = writer, sheet_name = 'Number of Trips by District', na_rep = 0, startrow = 46)
    writer.save()

    colwidths = getmaxwidths(location + '/DistrictReport.xlsx')

    writer = pd.ExcelWriter(location + '/DistrictReport.xlsx', engine = 'xlsxwriter')
    workbook = writer.book
    merge_format = workbook.add_format({'align': 'center', 'bold': True, 'border': 1})
    cond_format = workbook.add_format({'font_color': '#880000', 'bold': 'True'})
    tripod1.to_excel(excel_writer = writer, sheet_name = 'Number of Trips by District', na_rep = 0, startrow = 1)
    tripod2.to_excel(excel_writer = writer, sheet_name = 'Number of Trips by District', na_rep = 0, startrow = 16)
    tripoddiff.to_excel(excel_writer = writer, sheet_name = 'Number of Trips by District', na_rep = 0, startrow = 31)
    tripodpd.to_excel(excel_writer = writer, sheet_name = 'Number of Trips by District', na_rep = 0, startrow = 46)
    sheet = 'Number of Trips by District'
    worksheet = writer.sheets[sheet]
    worksheet.merge_range(0, 0, 0, 11, name1, merge_format)
    worksheet.merge_range(15, 0, 15, 11, name2, merge_format)
    worksheet.merge_range(30, 0, 30, 11, 'Difference', merge_format)
    worksheet.merge_range(45, 0, 45, 11, '% Difference', merge_format)
    worksheet.write(1, 0, 'Destination ->', merge_format)
    worksheet.write(16, 0, 'Destination ->', merge_format)
    worksheet.write(31, 0, 'Destination ->', merge_format)
    worksheet.write(46, 0, 'Destination ->', merge_format)
    for colnum in range(worksheet.dim_colmax + 1):
        worksheet.set_column(colnum, colnum, colwidths[sheet][colnum])
    worksheet.conditional_format('B49:L59', {'type': 'cell', 'criteria': '>=', 'value': 100, 'format': cond_format})
    worksheet.conditional_format('B49:L59', {'type': 'cell', 'criteria': '<=', 'value': -50, 'format': cond_format})
    worksheet.freeze_panes(0, 1)
    writer.save()
    print('---District to District Summary compiled in ' + str(round(time.time() - start, 1)) + ' seconds---')


def WorkFAZSummary(data1, data2, name1, name2, location, districtfile):
    print('---Begin Work District to District Summary compilation---')
    start = time.time()

    merge_per_hh_1 = pd.merge(data1['Person'][['pwtaz', 'psexpfac', 'hhno', 'pwtyp']],
                              data1['Household'][['hhtaz', 'hhno']],
                              on = 'hhno')
    worker_1 = merge_per_hh_1.query('pwtyp>0')

    FAZ_TAZ_lookup = pd.read_excel(FAZ_TAZ)

    worker_1_h_FAZ = pd.merge(worker_1, FAZ_TAZ_lookup, left_on = 'hhtaz', right_on = 'zone_id')
    worker_1_h_w_FAZ = pd.merge(worker_1_h_FAZ, FAZ_TAZ_lookup, left_on = 'pwtaz', right_on = 'zone_id')
    worker_1_h_w_agg = worker_1_h_w_FAZ.groupby(['large_area_name_x', 'large_area_name_y']).sum()['psexpfac']
    worker_1_h_w_agg = worker_1_h_w_agg.reset_index()
    worker_1_h_w_agg.columns = ['HomeFAZ', 'WorkFAZ', 'NumWorkers']

    LEHD_wrkrs = pd.read_excel(LEHD_work_flows)
    LEHD_model = pd.merge(LEHD_wrkrs, worker_1_h_w_agg, how='right', on = ['HomeFAZ', 'WorkFAZ'])
    LEHD_model['Difference (Model-LEHD)'] = LEHD_model['NumWorkers'] - LEHD_model['LEHDWorkers']
    LEHD_model['Percent Difference (Model-LEHD)/LEHD'] = LEHD_model['Difference (Model-LEHD)']/LEHD_model['LEHDWorkers']
    writer = pd.ExcelWriter(location + '/WorkFAZReport.xlsx', engine = 'xlsxwriter')
    LEHD_model.to_excel(excel_writer = writer, sheet_name = 'Work Locations by FAZ', na_rep = 0, startrow = 1)
    writer.close()
 


def DayPattern(data1, data2, name1, name2, location):
    print('---Begin Day Pattern Report Compilation---')
    start = time.time()
    Person_1_total = get_total(data1['Person']['psexpfac'])
    Person_2_total = get_total(data2['Person']['psexpfac'])
    Tour_1_total = get_total(data1['Tour']['toexpfac'])
    Tour_2_total = get_total(data2['Tour']['toexpfac'])

    cp1 = time.time()
    print('Preliminary data frames created in ' + str(round(cp1 - start, 1)) + ' seconds')

    #Tours per person
    tpp1 = Tour_1_total / Person_1_total
    tpp2 = Tour_2_total / Person_2_total
    tpp  = pd.DataFrame(index = ['Tours'])
    tpp[name1] = tpp1
    tpp[name2] = tpp2
    tpp = get_differences(tpp, name1, name2, 2)

    cp2 = time.time()
    print('Tours per Person data frame created in ' + str(round(cp2 - cp1, 1)) + ' seconds')

    #Percent of Tours by Purpose
    ptbp1 = 100 * data1['Tour'][['pdpurp','toexpfac']].groupby('pdpurp').sum()['toexpfac'] / Tour_1_total
    ptbp2 = 100 * data2['Tour'][['pdpurp','toexpfac']].groupby('pdpurp').sum()['toexpfac'] / Tour_2_total
    ptbp = pd.DataFrame()
    ptbp['Percent of Tours (' + name1 + ')'] = ptbp1
    ptbp['Percent of Tours (' + name2 + ')'] = ptbp2
    ptbp = get_differences(ptbp,'Percent of Tours (' + name1 + ')','Percent of Tours (' + name2 + ')', 2)
    ptbp = recode_index(ptbp, 'pdpurp', 'Tour Purpose')

    cp3 = time.time()
    print('Percent of Tours by Purpose data frame created in ' + str(round(cp3 - cp2, 1)) + ' seconds')

    #Tours per Person by Purpose
    tpbp1 = data1['Tour'][['pdpurp','toexpfac']].groupby('pdpurp').sum()['toexpfac'] / Person_1_total
    tpbp2 = data2['Tour'][['pdpurp','toexpfac']].groupby('pdpurp').sum()['toexpfac'] / Person_2_total
    tpbp = pd.DataFrame()
    tpbp['Tours per Person (' + name1 + ')'] = tpbp1
    tpbp['Tours per Person (' + name2 + ')'] = tpbp2
    tpbp = get_differences(tpbp, 'Tours per Person (' + name1 + ')', 'Tours per Person (' + name2 + ')', 2)
    tpbp = recode_index(tpbp, 'pdpurp', 'Tour Purpose')

    cp4 = time.time()
    print('Tours per Person by Purpose data frame created in ' + str(round(cp4 - cp3, 1)) + ' seconds')

    #Tours per Person by Purpose and Person Type/Number of Stops
    PersonsDay1 = pd.merge(data1['Person'][['hhno', 'pno', 'pptyp', 'psexpfac']], data1['PersonDay'][['hhno', 'pno', 'pdexpfac']], on= ['hhno', 'pno'])
    PersonsDay2 = pd.merge(data2['Person'][['hhno', 'pno', 'pptyp', 'psexpfac']], data2['PersonDay'][['hhno', 'pno', 'pdexpfac']], on= ['hhno', 'pno'])
    tpd = {}
    stops = {}
    for purpose in data1['Tour']['pdpurp'].value_counts().index:
        dfstart = time.time()
        if purpose == 'Work':
            tc = 'wktours'
            sc = 'wkstops'
        elif purpose == 'Social':
            tc = 'sotours'
            sc = 'sostops'
        elif purpose == 'School':
            tc = 'sctours'
            sc = 'scstops'
        elif purpose == 'Escort':
            tc = 'estours'
            sc = 'esstops'
        elif purpose == 'Personal Business':
            tc = 'pbtours'
            sc = 'pbstops'
        elif purpose == 'Shop':
            tc = 'shtours'
            sc = 'shstops'
        elif purpose == 'Meal':
            tc = 'mltours'
            sc = 'mlstops'
        #Add a column to PersonsDay for the current purpose
        PersonsDay1[tc] = data1['PersonDay'][tc]
        PersonsDay2[tc] = data2['PersonDay'][tc]
        toursPersPurp1 = weighted_average(PersonsDay1, tc, 'psexpfac', 'pptyp')
        toursPersPurp2 = weighted_average(PersonsDay2, tc, 'psexpfac', 'pptyp')
        #Delete added column to make future iterations faster
        del PersonsDay1[tc]
        del PersonsDay2[tc]
        toursPersPurp = pd.DataFrame.from_items([(name1, toursPersPurp1), (name2, toursPersPurp2)])
        toursPersPurp = get_differences(toursPersPurp, name1, name2, 2)
        toursPersPurp = recode_index(toursPersPurp, 'pptyp','Person Type')
        print(purpose + ' Tours by Person Type data frame created in ' + str(round(time.time() - dfstart, 1)) + ' seconds')

        #Number of stops by purpose
        dfstart = time.time()
        tpd.update({purpose: toursPersPurp}) #This dictionary is for creating the Excel file
        person_day_hh1 = pd.merge(data1['PersonDay'][['hhno', sc, 'pdexpfac']], data1['Household'][['hhno']], on = ['hhno'])
        person_day_hh2 = pd.merge(data2['PersonDay'][['hhno', sc, 'pdexpfac']], data2['Household'][['hhno']], on = ['hhno'])
        no_stops1 = 100 * person_day_hh1.query(sc + ' == 0')['pdexpfac'].sum() / person_day_hh1['pdexpfac'].sum()
        no_stops2 = 100 * person_day_hh2.query(sc + ' == 0')['pdexpfac'].sum() / person_day_hh2['pdexpfac'].sum()
        has_stops1 = 100 - no_stops1
        has_stops2 = 100 - no_stops2
        ps = pd.DataFrame() 
        ps['% of Tours (' + name1 + ')'] = [no_stops1, has_stops1]
        ps['% of Tours (' + name2 + ')'] = [no_stops2, has_stops2]
        ps[purpose + ' Tours'] = ['0', '1+']
        ps = ps.set_index(purpose + ' Tours')
        ps = get_differences( ps, '% of Tours (' + name1 + ')', '% of Tours (' + name2 + ')', 2)
        stops.update({purpose:ps})
        print('Number of Stops for ' + purpose + 'Tours data frame created in ' + str(round(time.time() - dfstart, 1)) + ' seconds')

    cp5 = time.time()

    #Work-Based Subtour Generation
    #Total trips per person
    atp1 = get_total(data1['Trip']['trexpfac']) / Person_1_total
    atp2 = get_total(data2['Trip']['trexpfac']) / Person_2_total
    atl1 = weighted_average(data1['Trip'].query('travdist > 0 and travdist < 200'), 'travdist', 'trexpfac')
    atl2 = weighted_average(data2['Trip'].query('travdist > 0 and travdist < 200'), 'travdist', 'trexpfac')
    ttp1 = [atp1, atl1]
    ttp2 = [atp2, atl2]
    label = ['Average Trips Per Person', 'Average Trip Length']
    ttp = pd.DataFrame.from_items([('', label), (name1, ttp1), (name2, ttp2)])
    ttp = ttp.set_index('')
    ttp = get_differences(ttp, name1, name2, 2)

    cp6 = time.time()
    print('Total Trips Per Person data frame created in ' + str(round(cp6 - cp5, 1)) + ' seconds')

    #Trip Rates by Purpose
    trp1 = data1['Trip'][['dpurp', 'trexpfac']].groupby('dpurp').sum()['trexpfac'] / Person_1_total
    trp2 = data2['Trip'][['dpurp', 'trexpfac']].groupby('dpurp').sum()['trexpfac'] / Person_2_total
    trp = pd.DataFrame()
    trp['Trips per Person (' + name1 + ')'] = trp1
    trp['Trips per Person (' + name2 + ')'] = trp2
    trp = get_differences(trp, 'Trips per Person (' + name1 + ')', 'Trips per Person (' + name2 + ')', 2)
    trp = recode_index(trp, 'dpurp', 'Destination Purpose')

    cp7 = time.time()
    print('Trip Rates by Purpose data frame created in ' + str(round(cp7 - cp6, 1)) + ' seconds')

    #Compile file
    writer = pd.ExcelWriter(location + '/DayPatternReport.xlsx', engine='xlsxwriter') #Defines the name of the file and that xlsxwriter will be used to write it
    tpp.to_excel(excel_writer = writer, sheet_name = 'Daily Activity Pattern', na_rep = 'NA', startrow = 1) #Put the first data frame into excel
    workbook = writer.book
    worksheet = writer.sheets['Daily Activity Pattern']
    ptbp.to_excel(excel_writer = writer, sheet_name = 'Daily Activity Pattern', na_rep = 'NA', startrow = 5)
    tpbp.to_excel(excel_writer = writer, sheet_name = 'Daily Activity Pattern', na_rep = 'NA', startrow = 15)
    purposes = data2['Tour']['pdpurp'].value_counts().index
    for i in range(len(purposes)): #There are two data frames for each tour purpose, so this loops over them
        tpd[purposes[i]].to_excel(excel_writer = writer, sheet_name = 'Tours by Purpose', na_rep = 'NA', startrow = 1, startcol = 6 * i)
        worksheet = writer.sheets['Tours by Purpose']
        stops[purposes[i]].to_excel(excel_writer = writer, sheet_name = 'Tours by Purpose', na_rep = 'NA', startrow = 13, startcol = 6 * i)
        if i != len(purposes):
            worksheet.write(0, 6 * i + 5, ' ') #This puts a filler column between each data frame, which is needed when getting the column widths
    ttp.to_excel(excel_writer = writer, sheet_name = 'Work-Based Subtour Generation', na_rep = 'NA', startrow = 1)
    worksheet = writer.sheets['Work-Based Subtour Generation']
    trp.to_excel(excel_writer = writer, sheet_name = 'Work-Based Subtour Generation', na_rep = 'NA', startrow = 6)
    writer.save() #save the file

    colwidths = getmaxwidths(location + '/DayPatternReport.xlsx') #Gets the column widths
    colors = ['#004488', '#00C0C0']

    writer = pd.ExcelWriter(location + '/DayPatternReport.xlsx', engine='xlsxwriter') #The file is deleted and recreated, this time with formatting
    tpp.to_excel(excel_writer = writer, sheet_name = 'Daily Activity Pattern', na_rep = 'NA', startrow = 1)
    workbook = writer.book
    worksheet = writer.sheets['Daily Activity Pattern']
    merge_format = workbook.add_format({'align': 'center', 'bold': True, 'border': 1}) #Defines formatting
    worksheet.merge_range(0, 0, 0, 4, 'Tours Per Person', merge_format) #Merges some cells, writes something, and applies formating
    worksheet.merge_range(4, 0, 4, 4, 'Percent of Tours by Purpose', merge_format)
    ptbp.to_excel(excel_writer = writer, sheet_name = 'Daily Activity Pattern', na_rep = 'NA', startrow = 5)
    worksheet.merge_range(15, 0, 15, 4, 'Tours per Person by Purpose', merge_format)
    tpbp.to_excel(excel_writer = writer, sheet_name = 'Daily Activity Pattern', na_rep = 'NA', startrow = 16)
    purposes = data1['Tour']['pdpurp'].value_counts().index
    for i in range(len(purposes)):
        tpd[purposes[i]].to_excel(excel_writer = writer, sheet_name = 'Tours by Purpose', na_rep = 'NA', startrow = 1, startcol = 6 * i)
        worksheet = writer.sheets['Tours by Purpose']
        worksheet.merge_range(0, 6 * i , 0, 6 * i + 4, purposes[i] + ' Tours by Person Type', merge_format)
        worksheet.merge_range(12, 6 * i, 12, 6 * i + 4, 'Number of Stops', merge_format)
        stops[purposes[i]].to_excel(excel_writer = writer, sheet_name = 'Tours by Purpose', na_rep = 'NA', startrow = 13, startcol = 6 * i)
        if i != len(purposes):
            worksheet.write(0, 6 * i + 5, ' ')
    ttp.to_excel(excel_writer = writer, sheet_name = 'Work-Based Subtour Generation', na_rep = 'NA', startrow = 1)
    worksheet = writer.sheets['Work-Based Subtour Generation']
    worksheet.merge_range(0, 0, 0, 4, 'Total Trips', merge_format)
    worksheet.merge_range(5, 0, 5, 4,'Trip Rates by Purpose', merge_format)
    trp.to_excel(excel_writer = writer, sheet_name = 'Work-Based Subtour Generation', na_rep = 'NA', startrow = 6)

    #Add charts
    for sheet in writer.sheets:
        worksheet = writer.sheets[sheet]
        for colnum in range(worksheet.dim_colmax + 1):
            worksheet.set_column(colnum, colnum, colwidths[sheet][colnum])
        if sheet == 'Tours by Purpose':
            for i in range(len(purposes)):
                chart = workbook.add_chart({'type': 'column'})
                for col_num in range(6 * i + 1, 6 * i + 3):
                    chart.add_series({'name': [sheet, 1, col_num],
                                        'categories': [sheet, 3, 6 * i, 10, 6 * i],
                                        'values': [sheet, 3, col_num, 10, col_num],
                                        'fill': {'color': colors[col_num % 6 - 1]}})
                    chart.set_legend({'position': 'top'})
                    chart.set_size({'x_scale': 1.4, 'y_scale': 1.25})
                worksheet.insert_chart(18, 6 * i, chart)
        if sheet == 'Work-Based Subtour Generation':
            chart = workbook.add_chart({'type': 'column'})
            for col_num in range(1, 3):
                chart.add_series({'name': [sheet, 6, col_num],
                                    'categories': [sheet, 8, 0, 16, 0],
                                    'values': [sheet, 8, col_num, 16, col_num],
                                    'fill': {'color': colors[col_num - 1]}})
            chart.set_legend({'position': 'top'})
            chart.set_size({'x_scale': 2, 'y_scale': 1.25})
            worksheet.insert_chart(18, 0, chart)
    writer.save()

    end = time.time()

    print('---Day Pattern Report successfully compiled in ' + str(round(time.time() - start, 1)) + ' seconds---')

def DaysimReport(data1, data2, name1, name2, location, districtfile):
    print('---Begin DaySim Report Compilation---')
    start = time.time()
    merge_per_hh_1 = pd.merge(data1['Person'][['pwtyp', 'psexpfac', 'pwpcl', 'pwaudist','pstyp', 'pspcl', 'psaudist', 'hhno']],
                              data1['Household'][['hhtaz', 'hhparcel', 'hhno']],
                              on = 'hhno')
    merge_per_hh_2 = pd.merge(data2['Person'][['pwtyp', 'psexpfac', 'pwpcl', 'pwaudist','pstyp', 'pspcl', 'psaudist', 'hhno']],
                              data2['Household'][['hhtaz', 'hhparcel', 'hhno']],
                              on = 'hhno')
    label = []
    value1 = []
    value2 = []
    Person_1_total = get_total(merge_per_hh_1['psexpfac'])
    Person_2_total = get_total(merge_per_hh_2['psexpfac'])
    label.append('Number of People')
    value1.append(int(round(Person_1_total, 0)))
    value2.append(int(round(Person_2_total, 0)))
    Trip_1_total = get_total(data1['Trip']['trexpfac'])
    Trip_2_total = get_total(data2['Trip']['trexpfac'])
    label.append('Number of Trips')
    value1.append(int(round(Trip_1_total, 0)))
    value2.append(int(round(Trip_2_total, 0)))
    Tour_1_total = get_total(data1['Tour']['toexpfac'])
    Tour_2_total = get_total(data2['Tour']['toexpfac'])
    label.append('Number of Tours')
    value1.append(int(round(Tour_1_total, 0)))
    value2.append(int(round(Tour_2_total, 0)))
    trip_ok_1 = data1['Trip'][['travdist', 'trexpfac', 'dorp']].query('travdist > 0 and travdist < 200')
    trip_ok_2 = data2['Trip'][['travdist', 'trexpfac', 'dorp']].query('travdist > 0 and travdist < 200')

    cp1 = time.time()
    print('Preliminary data frames and variables created in ' + str(round(cp1 - start, 1)) + ' seconds')

    ##Basic Summaries
    #Total Households, Persons, and Trips
    tp1 = data1['Person']['psexpfac'].sum()
    tp2 = data2['Person']['psexpfac'].sum()
    th1 = data1['Household']['hhexpfac'].sum()
    th2 = data2['Household']['hhexpfac'].sum()
    ttr1 = trip_ok_1['trexpfac'].sum()
    ttr2 = trip_ok_2['trexpfac'].sum()
    ahhs1 = tp1 / th1
    ahhs2 = tp2 / th2
    ntr1 = ttr1 / tp1
    ntr2 = ttr2 / tp2
    atl1 = weighted_average(trip_ok_1, 'travdist', 'trexpfac')
    atl2 = weighted_average(trip_ok_2, 'travdist', 'trexpfac')
    driver_trips1 = trip_ok_1[['dorp', 'travdist', 'trexpfac']].query('dorp == "Driver"')
    driver_trips2 = trip_ok_2[['dorp', 'travdist', 'trexpfac']].query('dorp == "Driver"')
    vmpp1sp = (driver_trips1['travdist'].multiply(driver_trips1['trexpfac'])).sum()
    vmpp2sp = (driver_trips2['travdist'].multiply(driver_trips2['trexpfac'])).sum()
    vmpp1 = vmpp1sp / Person_1_total
    vmpp2 = vmpp2sp / Person_2_total

    #Work Location
    wrkrs1 = merge_per_hh_1[['pwtyp', 'hhtaz', 'psexpfac', 'pwpcl', 'pwaudist', 'hhparcel']].query('pwtyp == "Paid Full-Time Worker" or pwtyp == "Paid Part-Time Worker"')
    wrkrs2 = merge_per_hh_2[['pwtyp', 'hhtaz', 'psexpfac', 'pwpcl', 'pwaudist', 'hhparcel']].query('pwtyp == "Paid Full-Time Worker" or pwtyp == "Paid Part-Time Worker"')
    wrkr_1_hzone = pd.merge(wrkrs1, districtfile, left_on = 'hhtaz', right_on = 'TAZ')
    wrkr_2_hzone = pd.merge(wrkrs2, districtfile, left_on = 'hhtaz', right_on = 'TAZ')
    total_workers_1 = wrkrs1['psexpfac'].sum()
    total_workers_2 = wrkrs2['psexpfac'].sum()
    workers_1 = wrkr_1_hzone.query('pwpcl != hhparcel and pwaudist > 0 and pwaudist < 200')
    workers_2 = wrkr_2_hzone.query('pwpcl != hhparcel and pwaudist > 0 and pwaudist < 200')
    workers_1['Share (%)'] = workers_1['psexpfac'] / workers_1['psexpfac'].sum()
    workers_2['Share (%)'] = workers_2['psexpfac'] / workers_2['psexpfac'].sum()
    workers1_avg_dist = weighted_average(workers_1, 'pwaudist', 'psexpfac')
    workers2_avg_dist = weighted_average(workers_2, 'pwaudist', 'psexpfac')

    #School Location
    st1 = merge_per_hh_1[['pstyp', 'hhtaz', 'psexpfac', 'pspcl', 'psaudist', 'hhparcel']].query('pstyp == "Full-Time Student" or pstyp == "Part-Time Student"')
    st2 = merge_per_hh_2[['pstyp', 'hhtaz', 'psexpfac', 'pspcl', 'psaudist', 'hhparcel']].query('pstyp == "Full-Time Student" or pstyp == "Part-Time Student"')
    st_1_hzone = pd.merge(st1, districtfile, 'outer', left_on = 'hhtaz', right_on = 'TAZ')
    st_2_hzone = pd.merge(st2, districtfile, 'outer', left_on = 'hhtaz', right_on = 'TAZ')
    total_students_1 = st1['psexpfac'].sum()
    total_students_2 = st2['psexpfac'].sum()
    students_1 = st_1_hzone.query('pspcl != hhparcel and psaudist > 0 and psaudist < 200')
    students_2 = st_2_hzone.query('pspcl != hhparcel and psaudist > 0 and psaudist < 200')
    students_1['Share (%)'] = students_1['psexpfac'] / students_1['psexpfac'].sum()
    students_2['Share (%)'] = students_2['psexpfac'] / students_2['psexpfac'].sum()
    students1_avg_dist = weighted_average(students_1, 'psaudist', 'psexpfac')
    students2_avg_dist = weighted_average(students_2, 'psaudist', 'psexpfac')

    #Glue DataFrame Together
    thp = pd.DataFrame(index = ['Total Persons', 'Total Households', 'Average Household Size', 'Average Trips Per Person', 'Average Trip Length', 'Vehicle Miles per Person', 'Average Distance to Work (Non-Home)', 'Average Distance to School (Non-Home)'])
    thp[name1] = [tp1, th1, ahhs1, ntr1, atl1, vmpp1, workers1_avg_dist, students1_avg_dist]
    thp[name2] = [tp2, th2, ahhs2, ntr2, atl2, vmpp2, workers2_avg_dist, students2_avg_dist]
    thp = get_differences(thp, name1, name2, [0, 0, 1, 1, 1, 1, 1, 1])

    cp2 = time.time()
    print('Basic Summaries data frame created in ' + str(round(cp2 - cp1, 1)) + ' seconds')

    #Transit Pass Ownership
    ttp1 = data1['Person']['ptpass'].multiply(data1['Person']['psexpfac']).sum()
    ttp2 = data2['Person']['ptpass'].multiply(data2['Person']['psexpfac']).sum()
    ppp1 = ttp1 / Person_1_total
    ppp2 = ttp2 / Person_2_total
    tpass = pd.DataFrame(index = ['Total Passes', 'Passes per Person'])
    tpass[name1] = [ttp1, ppp1]
    tpass[name2] = [ttp2, ppp2]
    tpass = get_differences(tpass, name1, name2, [0, 3])

    cp3 = time.time()
    print('Transit Pass Ownership data frame created in ' + str(round(cp3 - cp2, 1)) + ' seconds')


    ao1 = 100 * data1['Household'][['hhvehs','hhexpfac']].groupby('hhvehs').sum()['hhexpfac'] / data1['Household']['hhexpfac'].sum()
    for i in range(5, len(ao1)):
        ao1[4] = ao1[4] + ao1[i]
        ao1 = ao1.drop([i])

    ao = pd.DataFrame()
     #Auto Ownership

    # read in ACS dataset
    autos= pd.read_excel(acs_data,sheetname = 'AutosTotal')
    acs_auto_share = pd.DataFrame(autos['Total'] * 100)

    ao['Percent of Households (' + name1 + ')'] = ao1
    ao['Percent of Households (ACS)'] = acs_auto_share 
    ao = get_differences(ao, 'Percent of Households (' + name1 + ')','Percent of Households (ACS)', 1)
    aonewcol = ['0', '1', '2', '3', '4+']
    ao['Number of Vehicles in Household'] = aonewcol
    ao = ao.reset_index()
    del ao['hhvehs']
    ao = ao.set_index('Number of Vehicles in Household')

    cp4 = time.time()
    print('Auto Ownership data frame created in ' + str(round(cp4 - cp3, 1)) + ' seconds')

    #Transit Boardings
    board = pd.DataFrame(index=['Boardings'])
    board['Implied Transit Boardings (Assuming 1.3 Boardings/Trip)'] = 1.3 * data1['Trip'].query('mode == "Transit"')['trexpfac'].sum()
    board['Total Observed Transit Boardings (2011)'] = 647127
    board = get_differences(board, 'Implied Transit Boardings (Assuming 1.3 Boardings/Trip)' , 'Total Observed Transit Boardings (2011)', 0)

    cp5 = time.time()
    print('Transit Boardings data frame created in ' + str(round(cp5 - cp4, 1)) + ' seconds')

    #File Compile
    writer = pd.ExcelWriter(location + '/DaysimReport.xlsx', engine = 'xlsxwriter')
    thp.to_excel(excel_writer = writer, sheet_name = 'Basic Summaries', na_rep = 'NA')
    tpass.to_excel(excel_writer = writer, sheet_name = 'Transit Pass Ownership', na_rep = 'NA')
    ao.to_excel(excel_writer = writer, sheet_name = 'Automobile Ownership', na_rep = 'NA')
    board.to_excel(excel_writer = writer, sheet_name = 'Transit Boardings', na_rep = 'NA')
    writer.save()

    colwidths = getmaxwidths(location + '/DaysimReport.xlsx')
    colors = ['#004488', '#00C0C0']

    writer = pd.ExcelWriter(location + '/DaysimReport.xlsx', engine = 'xlsxwriter')
    thp.to_excel(excel_writer = writer, sheet_name = 'Basic Summaries', na_rep = 'NA')
    tpass.to_excel(excel_writer = writer, sheet_name = 'Transit Pass Ownership', na_rep = 'NA')
    ao.to_excel(excel_writer = writer, sheet_name = 'Automobile Ownership', na_rep = 'NA')
    board.to_excel(excel_writer = writer, sheet_name = 'Transit Boardings', na_rep = 'NA')
    workbook = writer.book    
    sheet = 'Basic Summaries'
    worksheet = writer.sheets[sheet]
    for colnum in range(worksheet.dim_colmax + 1):
        worksheet.set_column(colnum, colnum, colwidths[sheet][colnum])
    worksheet.freeze_panes(0, 1)
    chart = workbook.add_chart({'type':'column'})
    for col_num in range(1, 3):
        chart.add_series({'name': [sheet, 0, col_num],
                            'categories': [sheet, 3, 0, worksheet.dim_rowmax, 0],
                            'values': [sheet, 3, col_num, worksheet.dim_rowmax, col_num],
                            'fill': {'color': colors[col_num - 1]}})
    chart.set_legend({'position': 'top'})
    chart.set_size({'x_scale': 2, 'y_scale': 1.75})
    worksheet.insert_chart('B11', chart)
    sheet = 'Transit Pass Ownership'
    worksheet = writer.sheets[sheet]
    for colnum in range(worksheet.dim_colmax + 1):
        worksheet.set_column(colnum, colnum, colwidths[sheet][colnum])
    worksheet.freeze_panes(0, 1)
    chart = workbook.add_chart({'type': 'column'})
    for col_num in range(1, 3):
        chart.add_series({'name': [sheet, 0, col_num],
                            'categories': [sheet, 1, 0, 1, 0],
                            'values': [sheet, 1, col_num, 1, col_num],
                            'fill': {'color': colors[col_num - 1]}})
    chart.set_legend({'position': 'top'})
    chart.set_size({'x_scale': 2, 'y_scale': 2.25})
    worksheet.insert_chart('B5', chart)
    sheet = 'Automobile Ownership'
    worksheet = writer.sheets[sheet]
    for colnum in range(worksheet.dim_colmax + 1):
        worksheet.set_column(colnum, colnum, colwidths[sheet][colnum])
    worksheet.freeze_panes(0, 1)
    chart = workbook.add_chart({'type': 'column'})
    for col_num in range(1, 3):
        chart.add_series({'name':[sheet, 0, col_num],
                            'categories': [sheet, 2, 0, worksheet.dim_rowmax, 0],
                            'values': [sheet, 2, col_num, worksheet.dim_rowmax, col_num],
                            'fill': {'color': colors[col_num - 1]}})
    chart.set_title({'name': 'Percentage of Households with Number of Automobiles'})
    chart.set_legend({'position': 'top'})
    chart.set_size({'x_scale': 2, 'y_scale': 2})
    chart.set_x_axis({'name': 'Number of Cars'})
    worksheet.insert_chart('B9', chart)
    sheet = 'Transit Boardings'
    worksheet = writer.sheets[sheet]
    for colnum in range(worksheet.dim_colmax + 1):
        worksheet.set_column(colnum, colnum, colwidths[sheet][colnum])
    writer.save()

    end = time.time()

    print('---DaySim Report successfully compiled in ' + str(round(time.time() - start, 1)) + ' seconds---')

def DestChoice(data1, data2, name1, name2, location, districtfile):
    print('---Begin Destination Choice Report compilation---')
    start = time.time()

    #Filter out unreasonable trip/tour lengths
    #survey data does not include drive to transit trips, remove- how can we do this without referencing max internal zone?    
    tour_ok_1 = data1['Tour'].query('tautodist>0 and tautodist<200')[['hhno', 'pno', 'tour', 'day', 'tautodist', 'toexpfac', 'pdpurp', 'tmodetp', 'tdtaz']]
    tour_ok_2 = data2['Tour'].query('tautodist>0 and tautodist<200')[['hhno', 'pno', 'tour', 'day', 'tautodist', 'toexpfac', 'pdpurp', 'tmodetp', 'tdtaz']] 
    trip_ok_1 = data1['Trip'].query('travdist>0 and travdist<200')[['hhno', 'pno', 'tour', 'day', 'travdist', 'trexpfac', 'dpurp', 'mode', 'dtaz']]
    trip_ok_2 = data2['Trip'].query('travdist>0 and travdist<200')[['hhno', 'pno', 'tour', 'day', 'travdist', 'trexpfac', 'dpurp', 'mode', 'dtaz']] 

    #Get total trips and tours
    Trip_1_total = get_total(trip_ok_1['trexpfac'])
    Trip_2_total = get_total(trip_ok_2['trexpfac'])
    Tour_1_total = get_total(tour_ok_1['toexpfac'])
    Tour_2_total = get_total(tour_ok_2['toexpfac'])

    cp1 = time.time()
    print('Preliminary data frames and variables created in ' + str(round(cp1 - start, 1)) + ' seconds')

    #Average distance by tour purpose

    #Merge tour and trip files
    tourtrip1 = pd.merge(tour_ok_1[['hhno', 'pno', 'tour', 'day', 'tautodist', 'toexpfac', 'pdpurp', 'tmodetp']],
                       trip_ok_1[['hhno', 'pno', 'tour', 'day', 'trexpfac']],
                       on = ['hhno', 'pno', 'tour', 'day'])
    tourtrip2 = pd.merge(tour_ok_2[['hhno', 'pno', 'tour', 'day', 'tautodist', 'toexpfac', 'pdpurp', 'tmodetp']],
                       trip_ok_2[['hhno', 'pno', 'tour', 'day', 'trexpfac']],
                       on = ['hhno', 'pno', 'tour', 'day'])

    #Compute weighted average of trip length grouped by purpose
    triptotal1 = weighted_average(tourtrip1[['tautodist', 'toexpfac', 'pdpurp']], 'tautodist', 'toexpfac', 'pdpurp')
    triptotal2 = weighted_average(tourtrip2[['tautodist', 'toexpfac', 'pdpurp']], 'tautodist', 'toexpfac', 'pdpurp')

    #Create data frame
    atl1 = pd.DataFrame.from_items([('Average Tour Length (' + name1 + ')', triptotal1)])
    atl2 = pd.DataFrame.from_items([('Average Tour Length (' + name2 + ')', triptotal2)])
    atl = pd.merge(atl1, atl2, 'outer', left_index = True, right_index = True)
    atl = get_differences(atl, 'Average Tour Length (' + name1 + ')', 'Average Tour Length (' + name2 + ')', 2)
    atl = recode_index(atl, 'pdpurp', 'Tour Purpose')

    cp2 = time.time()
    print('Average Distance by Tour Purpose data frame created in ' + str(round(cp2- cp1, 1)) + ' seconds')

    #Number of trips by tour purpose

    #Count number of trips on each tour
    notrips1 = tourtrip1[['hhno', 'pno', 'tour', 'day', 'trexpfac']].groupby(['hhno', 'pno', 'tour', 'day']).count()['trexpfac']
    notrips2 = tourtrip2[['hhno', 'pno', 'tour', 'day', 'trexpfac']].groupby(['hhno', 'pno', 'tour', 'day']).count()['trexpfac']
    notrips1 = notrips1.reset_index()
    notrips2 = notrips2.reset_index()
    notrips1 = notrips1.rename(columns = {'trexpfac':'notrips'})
    notrips2 = notrips2.rename(columns = {'trexpfac':'notrips'})

    #Merge number of trips with the tour file
    toursnotrips1 = pd.merge(tour_ok_1[['toexpfac', 'pdpurp', 'hhno', 'pno', 'tour', 'tmodetp']], notrips1, on = ['hhno', 'pno', 'tour'])
    toursnotrips2 = pd.merge(tour_ok_2[['toexpfac', 'pdpurp', 'hhno', 'pno', 'tour', 'tmodetp']], notrips2, on = ['hhno', 'pno', 'tour'])

    #Get the average number of trips per tour
    tourtotal1 = weighted_average(toursnotrips1, 'notrips', 'toexpfac', 'pdpurp')
    tourtotal2 = weighted_average(toursnotrips2, 'notrips', 'toexpfac', 'pdpurp')

    #Create data frame
    nttp1 = pd.DataFrame.from_items([('Avg # Trips/Tour (' + name1 + ')', tourtotal1)])
    nttp2 = pd.DataFrame.from_items([('Avg # Trips/Tour (' + name2 + ')', tourtotal2)])
    nttp = pd.merge(nttp1, nttp2, 'outer', left_index = True, right_index = True)
    nttp = get_differences(nttp, 'Avg # Trips/Tour (' + name1 + ')', 'Avg # Trips/Tour (' + name2 + ')', 1)
    nttp = recode_index(nttp, 'pdpurp', 'Tour Purpose')

    cp3 = time.time()
    print('Number of trips by tour purpose data frame created in ' + str(round(cp3 - cp2, 1)) + ' seconds')



    #Average Distance by Trip Purpose
    atripdist1 = weighted_average(trip_ok_1, 'travdist', 'trexpfac', 'dpurp')
    atripdist2 = weighted_average(trip_ok_2, 'travdist', 'trexpfac', 'dpurp')
    atripdist = pd.DataFrame()
    atripdist['Average Distance (' + name1 + ')'] = atripdist1.round(2)
    atripdist['Average Distance (' + name2 + ')'] = atripdist2.round(2)
    atripdist = get_differences(atripdist, 'Average Distance (' + name1 + ')', 'Average Distance (' + name2 + ')', 2)
    atripdist = recode_index(atripdist, 'dpurp', 'Trip Purpose')

    cp4 = time.time()
    print('Average Distance by Trip Purpose data frame created in ' + str(round(cp4 - cp3, 1)) + ' seconds')

    #Average Distance by Tour Mode
    triptotalm1 = weighted_average(tourtrip1, 'tautodist', 'trexpfac', 'tmodetp')
    triptotalm2 = weighted_average(tourtrip2, 'tautodist', 'trexpfac', 'tmodetp')
    atlm1 = pd.DataFrame.from_items([('Average Trip Length (' + name1 + ')', triptotalm1)])
    atlm2 = pd.DataFrame.from_items([('Average Trip Length (' + name2 + ')', triptotalm2)])
    atlm = pd.merge(atlm1, atlm2, 'outer', left_index = True, right_index = True)
    atlm = get_differences(atlm, 'Average Trip Length (' + name1 + ')', 'Average Trip Length (' + name2 + ')', 2)
    atlm = recode_index(atlm, 'tmodetp', 'Tour Mode')

    cp5 = time.time()
    print('Average Distance by Tour Mode data frame created in ' + str(round(cp5 - cp4, 1)) + ' seconds')

    #Number of Trips by Tour Mode
    tourtotalm1 = weighted_average(toursnotrips1, 'notrips', 'toexpfac', 'tmodetp')
    tourtotalm2 = weighted_average(toursnotrips2, 'notrips', 'toexpfac', 'tmodetp')
    nttpm1 = pd.DataFrame.from_items([('Avg # Trips/Tour (' + name1 + ')', tourtotalm1.round(2))])
    nttpm2 = pd.DataFrame.from_items([('Avg # Trips/Tour (' + name2 + ')', tourtotalm2.round(2))])
    nttpm = pd.merge(nttpm1, nttpm2, 'outer', left_index = True, right_index = True)
    nttpm = get_differences(nttpm, 'Avg # Trips/Tour (' + name1 + ')', 'Avg # Trips/Tour (' + name2 + ')', 2)
    nttpm = recode_index(nttpm, 'tmodetp', 'Tour Mode')

    cp6 = time.time()
    print('Number of Trips by Tour Mode data frame created in ' + str(round(cp6 - cp5, 1)) + ' seconds')

    #Average Distance by Trip Mode
    atripdist1m = weighted_average(trip_ok_1, 'travdist', 'trexpfac', 'mode')
    atripdist2m = weighted_average(trip_ok_2, 'travdist', 'trexpfac', 'mode')
    atripdistm = pd.DataFrame()
    atripdistm['Average Distance (' + name1 + ')'] = atripdist1m
    atripdistm['Average Distance (' + name2 + ')'] = atripdist2m
    atripdistm = get_differences(atripdistm, 'Average Distance (' + name1 + ')', 'Average Distance (' + name2 + ')', 1)
    atripdistm = recode_index(atripdistm, 'mode', 'Trip Mode')

    cp7 = time.time()
    print('Average Distance by Trip Mode data frame created in ' + str(round(cp7 - cp6, 1)) + ' seconds')

    ###Tours and Trips by Destination District
    ##Percent of Tours by Destination District

    #Merge the tour file with the district file
    toursdest1 = pd.merge(tour_ok_1[['tdtaz', 'toexpfac']], districtfile, 'outer', left_on = 'tdtaz', right_on = 'TAZ')
    toursdest2 = pd.merge(tour_ok_2[['tdtaz', 'toexpfac']], districtfile, 'outer', left_on = 'tdtaz', right_on = 'TAZ')

    #Get the share of tours for each district
    dist1 = toursdest1.groupby('New DistrictName').sum()['toexpfac']
    dist2 = toursdest2.groupby('New DistrictName').sum()['toexpfac']
    tourdestshare1 = dist1 / Tour_1_total * 100
    tourdestshare2 = dist2 / Tour_2_total * 100

    #Create data frame
    tourdest = pd.DataFrame()
    tourdest['% of Tours (' + name1 + ')'] = tourdestshare1
    tourdest['% of Tours (' + name2 + ')'] = tourdestshare2
    tourdest = get_differences(tourdest, '% of Tours (' + name1 + ')', '% of Tours (' + name2 + ')', 2)

    cp8 = time.time()
    print('Percent of Tours by Destination District data frame created in ' + str(round(cp8 - cp7, 1)) + ' seconds')

    #Percent of Trips by Destination District

    #Merge the trip file with the district file
    tripsdest1 = pd.merge(trip_ok_1[['dtaz', 'trexpfac']], districtfile, left_on = 'dtaz', right_on = 'TAZ')
    tripsdest2 = pd.merge(trip_ok_2[['dtaz', 'trexpfac']], districtfile, left_on = 'dtaz', right_on = 'TAZ')

    #Get the share of trips for each district
    tdist1 = tripsdest1.groupby('New DistrictName').sum()['trexpfac']
    tdist2 = tripsdest2.groupby('New DistrictName').sum()['trexpfac']
    tripdestshare1 = tdist1 / Trip_1_total * 100
    tripdestshare2 = tdist2 / Trip_2_total * 100

    #Create data frame
    tripdest = pd.DataFrame()
    tripdest['% of Trips (' + name1 + ')'] = tripdestshare1
    tripdest['% of Trips (' + name2 + ')'] = tripdestshare2
    tripdest = get_differences(tripdest, '% of Trips (' + name1 + ')', '% of Trips (' + name2 + ')', 2)

    cp9 = time.time()
    print('Percent of Trips by Destination District data frame created in ' + str(round(cp9 - cp8, 1)) + ' seconds')

    #People, workers, and students by District
    HHPer1 = pd.merge(data1['Person'][['hhno', 'psexpfac']], data1['Household'][['hhno', 'hhtaz']], 'outer', on = 'hhno')
    HHPer2 = pd.merge(data2['Person'][['hhno', 'psexpfac']], data2['Household'][['hhno', 'hhtaz']], 'outer', on = 'hhno')
    people_per_taz_1 = HHPer1.groupby('hhtaz').sum()['psexpfac']
    people_per_taz_2 = HHPer2.groupby('hhtaz').sum()['psexpfac']
    people_per_taz = pd.DataFrame.from_items([('Number of People (' + name1 + ')', people_per_taz_1), ('Number of People (' + name2 + ')', people_per_taz_2)])
    people_per_taz_district = pd.merge(people_per_taz, districtfile, left_index = True, right_on = 'TAZ')
    people_per_district = people_per_taz_district[['Number of People (' + name1 + ')', 'Number of People (' + name2 + ')', 'New DistrictName']].groupby('New DistrictName').sum()
    people_per_district = get_differences(people_per_district, 'Number of People (' + name1 + ')', 'Number of People (' + name2 + ')', 0)
    people_per_district['Difference (People)'] = people_per_district['Difference']
    people_per_district['% Difference (People)'] = people_per_district['% Difference']
    del people_per_district['Difference']
    del people_per_district['% Difference']

    workers_per_taz_1 = data1['Person'][['pwtaz', 'psexpfac']].groupby('pwtaz').sum()['psexpfac']
    workers_per_taz_2 = data2['Person'][['pwtaz', 'psexpfac']].groupby('pwtaz').sum()['psexpfac']
    workers_per_taz = pd.DataFrame.from_items([('Number of Workers (' + name1 + ')', workers_per_taz_1), ('Number of Workers (' + name2 + ')', workers_per_taz_2)])
    workers_per_taz_district = pd.merge(workers_per_taz, districtfile, left_index = True, right_on = 'TAZ')
    workers_per_district = workers_per_taz_district[['Number of Workers (' + name1 + ')', 'Number of Workers (' + name2 + ')', 'New DistrictName']].groupby('New DistrictName').sum()
    workers_per_district = get_differences(workers_per_district, 'Number of Workers (' + name1 + ')', 'Number of Workers (' + name2 + ')', 0)
    workers_per_district['Difference (Workers)'] = workers_per_district['Difference']
    workers_per_district['% Difference (Workers)'] = workers_per_district['% Difference']
    del workers_per_district['Difference']
    del workers_per_district['% Difference']

    students_per_taz_1 = data1['Person'][['pstaz', 'psexpfac']].groupby('pstaz').sum()['psexpfac']
    students_per_taz_2 = data2['Person'][['pstaz', 'psexpfac']].groupby('pstaz').sum()['psexpfac']
    students_per_taz = pd.DataFrame.from_items([('Number of Students (' + name1 + ')', students_per_taz_1), ('Number of Students (' + name2 + ')', students_per_taz_2)])
    students_per_taz_district = pd.merge(students_per_taz, districtfile, left_index = True, right_on = 'TAZ')
    students_per_district = students_per_taz_district[['Number of Students (' + name1 + ')', 'Number of Students (' + name2 + ')', 'New DistrictName']].groupby('New DistrictName').sum()
    students_per_district = get_differences(students_per_district, 'Number of Students (' + name1 + ')', 'Number of Students (' + name2 + ')', 0)
    students_per_district['Difference (Students)'] = students_per_district['Difference']
    students_per_district['% Difference (Students)'] = students_per_district['% Difference']
    del students_per_district['Difference']
    del students_per_district['% Difference']

    people_workers_district = pd.merge(people_per_district, workers_per_district, left_index = True, right_index = True)
    people_workers_students_district = pd.merge(people_workers_district, students_per_district, left_index = True, right_index = True)

    cp10 = time.time()
    print('Number of People, Workers, and Students by District data frame created in ' + str(round(cp10-cp9,1)) + ' seconds')

    #Compile the file
    writer = pd.ExcelWriter(location + '/DaysimDestChoiceReport.xlsx', engine = 'xlsxwriter')
    atl.to_excel(excel_writer = writer, sheet_name = 'Average Dist by Tour Purpose', na_rep = 'NA')
    atlm.to_excel(excel_writer = writer, sheet_name = 'Average Dist by Tour Mode', na_rep = 'NA')
    nttp.to_excel(excel_writer = writer, sheet_name = 'Trips per Tour by Tour Purpose', na_rep = 'NA')
    nttpm.to_excel(excel_writer = writer, sheet_name = 'Trips per Tour by Tour Mode', na_rep = 'NA')
    atripdist.to_excel(excel_writer = writer, sheet_name = 'Average Dist by Trip Purpose', na_rep = 'NA')
    atripdistm.to_excel(excel_writer = writer, sheet_name = 'Average Dist by Trip Mode', na_rep = 'NA')
    tourdest.to_excel(excel_writer = writer, sheet_name = '% Tours by Destination District', na_rep = 'NA')
    tripdest.to_excel(excel_writer = writer, sheet_name = '% Trips by Destination District', na_rep = 'NA')
    people_workers_students_district.to_excel(excel_writer=writer,sheet_name='#People by District',na_rep='NA')
    writer.save()

    colwidths = getmaxwidths(location + '/DaysimDestChoiceReport.xlsx')
    colors = ['#004488', '#00C0C0']

    writer = pd.ExcelWriter(location + '/DaysimDestChoiceReport.xlsx', engine = 'xlsxwriter')
    atl.to_excel(excel_writer = writer, sheet_name = 'Average Dist by Tour Purpose', na_rep = 'NA')
    atlm.to_excel(excel_writer = writer, sheet_name = 'Average Dist by Tour Mode', na_rep = 'NA')
    nttp.to_excel(excel_writer = writer, sheet_name = 'Trips per Tour by Tour Purpose', na_rep = 'NA')
    nttpm.to_excel(excel_writer = writer, sheet_name = 'Trips per Tour by Tour Mode', na_rep = 'NA')
    atripdist.to_excel(excel_writer = writer, sheet_name = 'Average Dist by Trip Purpose', na_rep = 'NA')
    atripdistm.to_excel(excel_writer = writer, sheet_name = 'Average Dist by Trip Mode', na_rep = 'NA')
    tourdest.to_excel(excel_writer = writer, sheet_name = '% Tours by Destination District', na_rep = 'NA')
    tripdest.to_excel(excel_writer = writer, sheet_name = '% Trips by Destination District', na_rep = 'NA')
    people_workers_students_district.to_excel(excel_writer=writer,sheet_name='#People by District',na_rep='NA')
    workbook = writer.book
    for sheet in writer.sheets:
        worksheet = writer.sheets[sheet]
        for colnum in range(worksheet.dim_colmax + 1):
            worksheet.set_column(colnum, colnum, colwidths[sheet][colnum])
        worksheet.freeze_panes(0, 1)
        chart = workbook.add_chart({'type': 'column'})
        for col_num in range(1, 3):
            chart.add_series({'name': [sheet, 0, col_num],
                                'categories': [sheet, 2, 0, worksheet.dim_rowmax, 0],
                                'values': [sheet, 2, col_num, worksheet.dim_rowmax, col_num],
                                'fill': {'color': colors[col_num - 1]}})
        chart.set_legend({'position': 'top'})
        chart.set_size({'x_scale': 2, 'y_scale': 1.5})
        worksheet.insert_chart('B15', chart)
    num_workers = workbook.add_chart({'type': 'column'})
    num_workers.add_series({'name': [sheet, 0, 5],
                            'categories': [sheet, 2, 0, worksheet.dim_rowmax, 0],
                            'values': [sheet, 2, 5, worksheet.dim_rowmax, 5],
                            'fill': {'color': colors[0]}})
    num_workers.add_series({'name': [sheet, 0, 6],
                            'categories': [sheet, 2, 0, worksheet.dim_rowmax, 0],
                            'values': [sheet, 2, 6, worksheet.dim_rowmax, 6],
                            'fill': {'color': colors[1]}})
    num_workers.set_legend({'position': 'top'})
    num_workers.set_size({'x_scale':2,'y_scale':1.5})
    worksheet.insert_chart('F15', num_workers)
    num_students = workbook.add_chart({'type': 'column'})
    num_students.add_series({'name': [sheet, 0, 9],
                            'categories': [sheet, 2, 0, worksheet.dim_rowmax, 0],
                            'values': [sheet, 2, 9, worksheet.dim_rowmax, 9],
                            'fill': {'color': colors[0]}})
    num_students.add_series({'name': [sheet, 0, 10],
                            'categories': [sheet, 2, 0, worksheet.dim_rowmax, 0],
                            'values': [sheet, 2, 10, worksheet.dim_rowmax, 10],
                            'fill': {'color': colors[1]}})
    num_students.set_legend({'position': 'top'})
    num_students.set_size({'x_scale':2,'y_scale':1.5})
    worksheet.insert_chart('J15', num_students)
    worksheet.write('A20', 'Transit Lengths are wrong! Ignore')
    writer.save()

    print('---Destination Choice Report successfully compiled in ' + str(round(time.time() - start, 1)) + ' seconds---')

def ModeChoice(data1, data2, name1, name2, location):
    start = time.time()
    print('---Begin Mode Choice Report compilation---')
    
    #Subsection Vehicle Miles Per Person
    tour_ok_1 = data1['Tour'][['tautotime', 'tautodist', 'tautocost', 'tmodetp', 'hhno', 'pno', 'tour', 'day', 'toexpfac', 'pdpurp']].query('tautodist>0 and tautodist<200')
    tour_ok_2 = data2['Tour'][['tautotime', 'tautodist', 'tautocost', 'tmodetp', 'hhno', 'pno', 'tour', 'day', 'toexpfac', 'pdpurp']].query('tautodist>0 and tautodist<200')
    trip_ok_1 = data1['Trip'][['travtime', 'travdist', 'travcost', 'mode', 'hhno', 'pno', 'tour', 'day', 'trexpfac', 'dpurp']].query('travtime>0 and travtime<200')
    trip_ok_2 = data2['Trip'][['travtime', 'travdist', 'travcost', 'mode', 'hhno', 'pno', 'tour', 'day', 'trexpfac', 'dpurp']].query('travtime>0 and travtime<200')
    Trip_1_total = get_total(trip_ok_1['trexpfac'])
    Trip_2_total = get_total(trip_ok_2['trexpfac'])
    Tour_1_total = get_total(tour_ok_1['toexpfac'])
    Tour_2_total = get_total(tour_ok_2['toexpfac'])
    merge_per_hh_1 = pd.merge(data1['Person'][['hhno','psexpfac']], data1['Household'][['hhno']], 'outer', on = 'hhno')
    merge_per_hh_2 = pd.merge(data2['Person'][['hhno','psexpfac']], data2['Household'][['hhno']], 'outer', on = 'hhno')
    label = []
    value1 = []
    value2 = []
    Person_1_total = get_total(merge_per_hh_1['psexpfac'])
    Person_2_total = get_total(merge_per_hh_2['psexpfac'])
    label.append('Number of People')
    value1.append(int(round(Person_1_total, 0)))
    value2.append(int(round(Person_2_total, 0)))

    label.append('Number of Trips')
    value1.append(int(round(Trip_1_total, 0)))
    value2.append(int(round(Trip_2_total, 0)))

    label.append('Number of Tours')
    value1.append(int(round(Tour_1_total, 0)))
    value2.append(int(round(Tour_2_total, 0)))


    vmpp = pd.DataFrame.from_items([('', label), (name1, value1), (name2, value2)])
    vmpp = get_differences(vmpp, name1, name2, 2)
    vmpp = vmpp.set_index('')

    cp1 = time.time()
    print('Number of people, trips, and tours data frame created in ' + str(round(cp1 - start, 1)) + ' seconds')

    ##Subsection Tour Summaries

    #Tour Mode Share
    mode1 = tour_ok_1[['tmodetp','toexpfac']].groupby('tmodetp').sum()['toexpfac']
    mode2 = tour_ok_2[['tmodetp','toexpfac']].groupby('tmodetp').sum()['toexpfac']
    modeshare1 = mode1 / Tour_1_total * 100
    modeshare2 = mode2 / Tour_2_total * 100
    msdf = pd.DataFrame()
    difference = modeshare1 - modeshare2
    modeshare1 = modeshare1.sort_index()
    msdf[name1 + ' Share (%)'] = modeshare1
    modeshare2 = modeshare2.sort_index()
    msdf[name2 + ' Share (%)'] = modeshare2
    msdf = get_differences(msdf, name1 + ' Share (%)', name2 + ' Share (%)', 2)
    msdf = recode_index(msdf, 'tmodetp', 'Mode')

    cp2 = time.time()
    print('Tour Mode Share data frame created in ' + str(round(cp2 - cp1, 1)) + ' seconds')


    #Mode share by purpose
    tourpurpmode1 = pd.DataFrame.from_items([('Purpose', tour_ok_1['pdpurp']), ('Mode', tour_ok_1['tmodetp']), ('Expansion Factor', tour_ok_1['toexpfac'])])
    tourpurpmode2 = pd.DataFrame.from_items([('Purpose', tour_ok_2['pdpurp']), ('Mode', tour_ok_2['tmodetp']), ('Expansion Factor', tour_ok_2['toexpfac'])])
    tourpurp1 = tourpurpmode1.groupby('Purpose').sum()['Expansion Factor']
    tourpurp2 = tourpurpmode2.groupby('Purpose').sum()['Expansion Factor']
    tpm1 = pd.DataFrame({name1 + ' Share (%)': tourpurpmode1.groupby(['Purpose', 'Mode']).sum()['Expansion Factor'] / tourpurp1 * 100}, dtype='float').reset_index()
    tpm2 = pd.DataFrame({name2 + ' Share (%)': tourpurpmode2.groupby(['Purpose', 'Mode']).sum()['Expansion Factor'] / tourpurp2 * 100}, dtype='float').reset_index()
    tpm = pd.merge(tpm1, tpm2, 'outer')
    tpm = tpm.sort(name2 + ' Share (%)')

    #Re-organize data frame for side-by-side comparison
    nrows = tpm['Mode'].value_counts()
    halfcols = tpm['Purpose'].value_counts()
    modenames = halfcols.index
    ncols = [] #Columns for new data frame
    for i in range(len(modenames)):
        ncols.append(modenames[i].encode('ascii', 'replace') + ' (' + name1 + ')')
        ncols.append(modenames[i].encode('ascii', 'replace') + ' (' + name2 + ')')
    mbpcdf = pd.DataFrame()

    #Fills in the data frame with NA
    for column in ncols:   
        filler = pd.Series()
        for purpose in nrows.index:
            filler[purpose] = float('Nan')
        mbpcdf[column] = filler

    #Puts the values in the correct place
    for i in range(len(tpm['Mode'])):
        mbpcdf[tpm['Purpose'][i] + ' (' + name1 + ')'][tpm['Mode'][i]] = round(tpm[name1 + ' Share (%)'][i], 1)
        mbpcdf[tpm['Purpose'][i] + ' (' + name2 + ')'][tpm['Mode'][i]] = round(tpm[name2 + ' Share (%)'][i], 1)

    cp3 = time.time()
    print('Tour Mode Share by Purpose data frame created in '+str(round(cp3 - cp2, 1))+' seconds')

    #Trip Mode by Tour Mode

    #Merge tour and trip data frames
    tourtrip1 = pd.merge(data1['Tour'][['hhno', 'pno', 'tour', 'day', 'tmodetp', 'toexpfac']],
                            data1['Trip'][['hhno', 'pno', 'tour', 'day', 'mode', 'trexpfac']],
                            on = ['hhno', 'pno', 'tour'])
    tourtrip2 = pd.merge(data2['Tour'][['hhno', 'pno', 'tour', 'day', 'tmodetp', 'toexpfac']],
                            data2['Trip'][['hhno', 'pno', 'tour', 'day', 'mode', 'trexpfac']],
                            on = ['hhno', 'pno', 'tour'])

    tourtrip1['Primary Tour Mode'] = tourtrip1['tmodetp']
    tourtrip2['Primary Tour Mode'] = tourtrip2['tmodetp']
    tourtrip1['Trip Mode'] = tourtrip1['mode']
    tourtrip2['Trip Mode'] = tourtrip2['mode']

    #Create pivot tables
    counts1 = tourtrip1[['Primary Tour Mode', 'Trip Mode', 'trexpfac']].groupby(['Primary Tour Mode', 'Trip Mode']).sum()['trexpfac']#creates data frame grouped by trip and primary tour mode
    counts2 = tourtrip2[['Primary Tour Mode', 'Trip Mode', 'trexpfac']].groupby(['Primary Tour Mode', 'Trip Mode']).sum()['trexpfac']
    counts1 = pd.DataFrame.from_items([('Trips', counts1)])
    counts2 = pd.DataFrame.from_items([('Trips', counts2)])
    counts1 = counts1.reset_index()
    counts2 = counts2.reset_index()
    counts1pivot = counts1.pivot(index = 'Primary Tour Mode', columns = 'Trip Mode', values = 'Trips')
    counts2pivot = counts2.pivot(index = 'Primary Tour Mode', columns = 'Trip Mode', values = 'Trips')
    if 'Other' not in counts1pivot.columns.tolist():
        counts1pivot['Other'] = np.nan
    counts1pivot = counts1pivot.reindex(['Other', 'Transit', 'School Bus', 'HOV3+', 'HOV2', 'SOV', 'Bike', 'Walk'])[['Other', 'Transit', 'School Bus', 'HOV3+', 'HOV2', 'SOV', 'Bike', 'Walk']]
    counts2pivot = counts2pivot.reindex(['Other', 'Transit', 'School Bus', 'HOV3+', 'HOV2', 'SOV', 'Bike', 'Walk'])[['Other', 'Transit', 'School Bus', 'HOV3+', 'HOV2', 'SOV', 'Bike', 'Walk']]
    counts1pivot = counts1pivot.fillna(0).transpose()
    counts2pivot = counts2pivot.fillna(0).transpose()
    counts_difference = counts1pivot - counts2pivot
    counts_pd = 100*counts_difference/counts2pivot

    modes = counts1pivot.columns.tolist()

    percent1pivot = pd.DataFrame(index = modes, columns = modes)
    percent2pivot = pd.DataFrame(index = modes, columns = modes)
    share_difference = pd.DataFrame(index = modes, columns = modes)
    share_pd = pd.DataFrame(index = modes, columns = modes)
    toursbymode1 = counts1pivot.sum()
    toursbymode2 = counts2pivot.sum()
    for tour_mode in modes:
        for trip_mode in modes:
            try:
                percent1pivot[tour_mode][trip_mode] = counts1pivot[tour_mode][trip_mode] / toursbymode1[tour_mode] * 100
            except ZeroDivisionError:
                percent1pivot[tour_mode][trip_mode] = float('nan')
            try:
                percent2pivot[tour_mode][trip_mode] = counts2pivot[tour_mode][trip_mode] / toursbymode2[tour_mode] * 100
            except ZeroDivisionError:
                percent2pivot[tour_mode][trip_mode] = float('nan')
            share_difference[tour_mode][trip_mode] = percent1pivot[tour_mode][trip_mode] - percent2pivot[tour_mode][trip_mode]
            try:
                share_pd[tour_mode][trip_mode] = share_difference[tour_mode][trip_mode] / percent2pivot[tour_mode][trip_mode] * 100
            except ZeroDivisionError:
                share_pd[tour_mode][trip_mode] = float('nan')
        roundto = 2
        percent1pivot[tour_mode] = percent1pivot[tour_mode].astype('float').round(roundto)
        percent1pivot = add_index_name(percent1pivot, 'Trip_Mode')
        percent2pivot[tour_mode] = percent2pivot[tour_mode].astype('float').round(roundto)
        percent2pivot = add_index_name(percent2pivot, 'Trip_Mode')
        share_difference[tour_mode] = share_difference[tour_mode].astype('float').round(roundto)
        share_difference = add_index_name(share_difference, 'Trip_Mode')
        share_pd[tour_mode] = share_pd[tour_mode].astype('float').round(roundto)
        share_pd = add_index_name(share_pd, 'Trip_Mode')

    for column in counts1pivot.columns:
        counts1pivot[column] = counts1pivot[column].round(0)
        counts2pivot[column] = counts2pivot[column].round(0)
        counts_difference[column] = counts_difference[column].round(0)
        counts_pd[column] = counts_pd[column].round(2)

    cp4 = time.time()
    print('Trip Mode by Tour Mode data frames created in '+str(round(cp4 - cp3, 1))+' seconds')

    ##Trip Cross-Tabulations

    #Tours by Mode and Travel Time
    df1 = tour_ok_1[['tautotime', 'tautocost', 'tautodist', 'toexpfac', 'tmodetp']]
    df2 = tour_ok_2[['tautotime', 'tautocost', 'tautodist', 'toexpfac', 'tmodetp']]
    toursmtt = pd.DataFrame()
    toursmtt['Mean Auto Time (' + name1 + ')'] = weighted_average(df1, 'tautotime', 'toexpfac', 'tmodetp').round(2)
    toursmtt['Mean Auto Distance (' + name1 + ')'] = weighted_average(df1, 'tautodist', 'toexpfac', 'tmodetp').round(2)
    toursmtt['Mean Auto Cost (' + name1 + ')'] = weighted_average(df1, 'tautocost', 'toexpfac', 'tmodetp').round(2)
    toursmtt['Mean Auto Time (' + name2 + ')'] = weighted_average(df2, 'tautotime', 'toexpfac', 'tmodetp').round(2)
    toursmtt['Mean Auto Distance (' + name2 + ')'] = weighted_average(df2, 'tautodist', 'toexpfac', 'tmodetp').round(2)
    toursmtt['Mean Auto Cost (' + name2 + ')'] = weighted_average(df2, 'tautocost', 'toexpfac', 'tmodetp').round(2)
    toursmtt = recode_index(toursmtt,'tmodetp','Mode')

    cp5 = time.time()
    print('Tours by Mode and Travel Time data frame created in ' + str(round(cp5 - cp4, 1)) + ' seconds')

    #Trips by Mode and Travel Time
    tripdf1 = trip_ok_1[['trexpfac', 'travtime', 'travcost', 'travdist', 'mode']]
    tripdf2 = trip_ok_2[['trexpfac', 'travtime', 'travcost', 'travdist', 'mode']]
    tripsmtt1 = pd.DataFrame()
    tripsmtt2 = pd.DataFrame()
    tripm1 = tripdf1.groupby('mode').sum()['trexpfac']
    tripm2 = tripdf2.groupby('mode').sum()['trexpfac']
    tms1 = tripm1 / Trip_1_total * 100 #Trip mode share
    tms2 = tripm2 / Trip_2_total * 100
    tripsmtt1['Total Trips (' + name1 + ')'] = tripm1.round(0)
    tripsmtt2['Total Trips (' + name2 + ')'] = tripm2.round(0)
    tripsmtt = pd.merge(tripsmtt1, tripsmtt2, 'outer', left_index = True, right_index = True)
    tripsmtt['Mode Share (' + name1 + ') (%)'] = tms1.round(2)
    tripsmtt['Mode Share (' + name2 + ') (%)'] = tms2.round(2)

    #Weighted averages for average travel time, distance, and cost
    tripdf1['atimesp'] = tripdf1['travtime'].multiply(tripdf1['trexpfac'])
    tripdf1['adistsp'] = tripdf1['travdist'].multiply(tripdf1['trexpfac'])
    tripdf1['acostsp'] = tripdf1['travcost'].multiply(tripdf1['trexpfac'])
    tripdf2['atimesp'] = tripdf2['travtime'].multiply(tripdf2['trexpfac'])
    tripdf2['adistsp'] = tripdf2['travdist'].multiply(tripdf2['trexpfac'])
    tripdf2['acostsp'] = tripdf2['travcost'].multiply(tripdf2['trexpfac'])
    tripgrouped1 = tripdf1.groupby('mode').sum()
    tripgrouped2 = tripdf2.groupby('mode').sum()
    tripgrouped1['matime'] = tripgrouped1['atimesp'] / tripgrouped1['trexpfac']
    tripgrouped1['madist'] = tripgrouped1['adistsp'] / tripgrouped1['trexpfac']
    tripgrouped1['macost'] = tripgrouped1['acostsp'] / tripgrouped1['trexpfac']
    tripgrouped2['matime'] = tripgrouped2['atimesp'] / tripgrouped2['trexpfac']
    tripgrouped2['madist'] = tripgrouped2['adistsp'] / tripgrouped2['trexpfac']
    tripgrouped2['macost'] = tripgrouped2['acostsp'] / tripgrouped2['trexpfac']
    tripsmtt['Mean Auto Time (' + name1 + ')'] = tripgrouped1['matime'].round(2)
    tripsmtt['Mean Auto Time (' + name2 + ')'] = tripgrouped2['matime'].round(2)
    tripsmtt['Mean Auto Distance (' + name1 + ')'] = tripgrouped1['madist'].round(2)
    tripsmtt['Mean Auto Distance (' + name2 + ')'] = tripgrouped2['madist'].round(2)
    tripsmtt['Mean Auto Cost (' + name1 + ')'] = tripgrouped1['macost'].round(2)
    tripsmtt['Mean Auto Cost (' + name2 + ')'] = tripgrouped2['macost'].round(2)
    tripsmtt = recode_index(tripsmtt, 'mode', 'Mode')

    cp6 = time.time()
    print('Trips by Mode and Travel Time data frame created in ' + str(round(cp6 - cp5, 1)) + ' seconds')

    #Trips by purpose and travel time
    ttdf1 = trip_ok_1[['travtime','travdist','trexpfac','mode','dpurp']]
    ttdf2 = trip_ok_2[['travtime','travdist','trexpfac','mode','dpurp']]

    #Some weighted averages to get average distance and travel time
    ttdf1['ttsp'] = ttdf1['travtime'].multiply(ttdf1['trexpfac'])
    ttdf2['ttsp'] = ttdf2['travtime'].multiply(ttdf2['trexpfac'])
    ttdf1['tdsp'] = ttdf1['travdist'].multiply(ttdf1['trexpfac'])
    ttdf2['tdsp'] = ttdf2['travdist'].multiply(ttdf2['trexpfac'])
    ttrips1 = ttdf1.groupby(['mode','dpurp']).sum()
    ttrips2 = ttdf2.groupby(['mode','dpurp']).sum()
    ttrips1['mtt'] = (ttrips1['ttsp'] / ttrips1['trexpfac']).round(2)
    ttrips2['mtt'] = (ttrips2['ttsp'] / ttrips2['trexpfac']).round(2)
    ttrips1['mtd'] = (ttrips1['tdsp'] / ttrips1['trexpfac']).round(2)
    ttrips2['mtd'] = (ttrips2['tdsp'] / ttrips2['trexpfac']).round(2)

    #Glue data frame together
    full1 = ttrips1.reset_index()
    full2 = ttrips2.reset_index()
    tptt1 = pd.DataFrame.from_items([('Mode', full1['mode']), ('Purpose', full1['dpurp']), ('Total Trips (' + name1 + ')', full1['trexpfac']), ('Mean Time (' + name1 + ')', full1['mtt']), ('Mean Distance (' + name1 + ')', full1['mtd'])])
    tptt2 = pd.DataFrame.from_items([('Mode', full2['mode']), ('Purpose', full2['dpurp']), ('Total Trips (' + name2 + ')', full2['trexpfac']), ('Mean Time (' + name2 + ')', full2['mtt']), ('Mean Distance (' + name2 + ')', full2['mtd'])])
    tptt = pd.merge(tptt1, tptt2, 'outer')
    tptt = tptt.sort_index(axis = 1, ascending = False)
    tptt = tptt.set_index(['Mode', 'Purpose'])

    cp7 = time.time()
    print('Trips by Purpose and Travel Time data frame created in '+str(round(cp7 - cp6, 1))+' seconds')

    #Write DataFrames to Excel File
    writer = pd.ExcelWriter(location + '/ModeChoiceReport.xlsx', engine = 'xlsxwriter')
    vmpp.to_excel(excel_writer = writer, sheet_name = '# People, Trips, and Tours', na_rep = 'NA')
    msdf.to_excel(excel_writer = writer, sheet_name = 'Tour Mode Share', na_rep = 'NA')
    mbpcdf.to_excel(excel_writer = writer, sheet_name = 'Tour Mode Share by Purpose', na_rep = 'NA')
    counts1pivot.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 1)
    percent1pivot.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 1, startcol = 10)
    counts2pivot.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 13)
    percent2pivot.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 13, startcol = 10)
    counts_difference.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 25)
    share_difference.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 25, startcol = 10)
    counts_pd.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 37)
    share_pd.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 37, startcol = 10)
    worksheet = writer.sheets['Trip Mode by Tour Mode']
    worksheet.write(1, 0, 'Tour Mode ->')
    worksheet.write(1, 10, 'Tour Mode ->')
    worksheet.write(13, 0, 'Tour Mode ->')
    worksheet.write(13, 10, 'Tour Mode ->')
    worksheet.write(25, 0, 'Tour Mode ->')
    worksheet.write(25, 10, 'Tour Mode ->')
    worksheet.write(37, 0, 'Tour Mode ->')
    worksheet.write(37, 10, 'Tour Mode ->')
    worksheet.write(0, 9, ' ')
    toursmtt.to_excel(excel_writer = writer, sheet_name = 'Tours by Mode & Travel Time', na_rep = 'NA')
    tripsmtt.to_excel(excel_writer = writer, sheet_name = 'Trips by Mode & Travel Time', na_rep = 'NA')
    tptt.to_excel(excel_writer = writer, sheet_name = 'Trips by Purpose & Travel Time',na_rep = 'NA')

    writer.save()
    colwidths=getmaxwidths(location+'/ModeChoiceReport.xlsx')

    writer=pd.ExcelWriter(location+'/ModeChoiceReport.xlsx',engine='xlsxwriter')
    workbook=writer.book
    merge_format = workbook.add_format({'bold': True, 'align': 'center', 'border': True})
    value_format = workbook.add_format({'bold': True, 'font_color': '#0000CC'})
    pd_format = workbook.add_format({'bold': True, 'font_color': '#880000'})
    vmpp.to_excel(excel_writer = writer, sheet_name = '# People, Trips, and Tours', na_rep = 'NA')
    msdf.to_excel(excel_writer = writer, sheet_name = 'Tour Mode Share', na_rep = 'NA')
    mbpcdf.to_excel(excel_writer = writer, sheet_name = 'Tour Mode Share by Purpose', na_rep = 'NA')
    counts1pivot.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 1)
    percent1pivot.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 1, startcol = 10)
    counts2pivot.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 13)
    percent2pivot.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 13, startcol = 10)
    counts_difference.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 25)
    share_difference.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 25, startcol = 10)
    counts_pd.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 37)
    share_pd.to_excel(excel_writer = writer, sheet_name = 'Trip Mode by Tour Mode', na_rep = 'NA', startrow = 37, startcol = 10)
    worksheet = writer.sheets['Trip Mode by Tour Mode']
    worksheet.merge_range(0, 0, 0, 8, 'Number of Trips by Trip Mode and Tour Mode (' + name1 + ')', merge_format)
    worksheet.merge_range(0, 10, 0, 18, 'Mode Share by Tour Mode (' + name1 + ') (%)', merge_format)
    worksheet.merge_range(12, 0, 12, 8, 'Number of Trips by Trip Mode and Tour Mode (' + name2 + ')', merge_format)
    worksheet.merge_range(12, 10, 12, 18, 'Mode Share by Tour Mode (' + name2 + ') (%)', merge_format)
    worksheet.merge_range(24, 0, 24, 8, 'Difference in Number of Trips', merge_format)
    worksheet.merge_range(24, 10, 24, 18, 'Difference in Mode Share', merge_format)
    worksheet.merge_range(36, 0, 36, 8, 'Percent Difference in Number of Trips', merge_format)
    worksheet.merge_range(36, 10, 36, 18, 'Percent Difference in Mode Share', merge_format)
    worksheet.write(1, 0, 'Tour Mode ->', merge_format)
    worksheet.write(1, 10, 'Tour Mode ->', merge_format)
    worksheet.write(13, 0, 'Tour Mode ->', merge_format)
    worksheet.write(13, 10, 'Tour Mode ->', merge_format)
    worksheet.write(25, 0, 'Tour Mode ->', merge_format)
    worksheet.write(25, 10, 'Tour Mode ->', merge_format)
    worksheet.write(37, 0, 'Tour Mode ->', merge_format)
    worksheet.write(37, 10, 'Tour Mode ->', merge_format)
    worksheet.write(0, 9, ' ')
    worksheet.conditional_format('L4:S11', {'type': 'cell', 'criteria': '>=', 'value': 20, 'format': value_format})
    worksheet.conditional_format('L16:S23', {'type': 'cell', 'criteria': '>=', 'value': 20, 'format': value_format})
    worksheet.conditional_format('B40:I47', {'type': 'cell', 'criteria': '>=', 'value': 100, 'format': pd_format})
    worksheet.conditional_format('B40:I47', {'type': 'cell', 'criteria': '<=', 'value': -50, 'format': pd_format})
    worksheet.conditional_format('L40:S47', {'type': 'cell', 'criteria': '>=', 'value': 100, 'format': pd_format})
    worksheet.conditional_format('L40:S47', {'type': 'cell', 'criteria': '<=', 'value': -50, 'format': pd_format})
    toursmtt.to_excel(excel_writer = writer, sheet_name = 'Tours by Mode & Travel Time', na_rep = 'NA')
    tripsmtt.to_excel(excel_writer = writer, sheet_name = 'Trips by Mode & Travel Time', na_rep = 'NA')
    tptt.to_excel(excel_writer = writer, sheet_name = 'Trips by Purpose & Travel Time',na_rep = 'NA') 
    colors=['#0c2c56','#005c5c']
    for sheet in writer.sheets:
        worksheet=writer.sheets[sheet]
        worksheet.write('A20', 'Transit Lengths are wrong! Ignore')
        for col_num in range(worksheet.dim_colmax+1):
            worksheet.set_column(col_num,col_num,colwidths[sheet][col_num])
        if sheet != 'Trip Mode by Tour Mode':
            worksheet.freeze_panes(0,1)
        if sheet in ['# People, Trips, and Tours','Mode Share']:
            chart=workbook.add_chart({'type':'column'})
            for col_num in range(1,3):
                if sheet=='# People, Trips, and Tours':
                    chart.add_series({'name':[sheet, 0, col_num],
                                        'categories':[sheet,1,0,worksheet.dim_rowmax,0],
                                        'values':[sheet,1,col_num,worksheet.dim_rowmax,col_num],
                                        'fill':{'color':colors[col_num-1]}})
                    chart.set_legend({'position':'top'})
                    chart.set_size({'x_scale':2,'y_scale':1.75})
                else:
                    chart.add_series({'name':[sheet, 0, col_num],
                                        'categories':[sheet,2,0,worksheet.dim_rowmax,0],
                                        'values':[sheet,2,col_num,worksheet.dim_rowmax,col_num],
                                        'fill':{'color':colors[col_num-1]}})
                    chart.set_legend({'position':'top'})
                    chart.set_size({'x_scale':2,'y_scale':1.75})
            worksheet.insert_chart('B12',chart)
        elif sheet == 'Mode Share by Purpose':
            for i in range(1,8):
                chart=workbook.add_chart({'type':'column'})
                for col_num in range(1,3):
                    c=2*(i-1)+col_num
                    chart.add_series({'name':[sheet,0,c],
                                        'categories':[sheet,1,0,8,0],
                                        'values':[sheet,1,c,8,c],
                                        'fill':{'color':colors[col_num-1]}})
                chart.set_legend({'position':'top'})
                chart.set_size({'x_scale':0.8,'y_scale':0.9})
                chart.set_y_axis({'name':'Mode Share'})
                if i%2==1:
                    worksheet.insert_chart(10,2*i-1,chart)
                else:
                    worksheet.insert_chart(24,2*i-3,chart)
    writer.save()

    print('---Mode Choice Report successfully compiled in ' + str(round(time.time() - start, 1)) + ' seconds---')

def LongTerm(data1, data2, name1, name2, location, districtfile):
    start = time.time()
    print('---Begin Long Term Report compilation---')

    merge_per_hh_1 = pd.merge(data1['Person'][['hhno', 'psexpfac', 'pwpcl', 'pwtyp', 'pgend', 'pagey', 'pwaudist']],
                              data1['Household'][['hhno', 'hhtaz', 'hhparcel']],
                              on = 'hhno')
    merge_per_hh_2 = pd.merge(data2['Person'][['hhno', 'psexpfac', 'pwpcl', 'pwtyp', 'pgend', 'pagey', 'pwaudist']],
                              data2['Household'][['hhno', 'hhtaz', 'hhparcel']],
                              on = 'hhno')

    cp1 = time.time()
    print('Preliminary data frames created in ' + str(round(cp1 - start, 1)) + ' seconds')

    #Total Households and Persons
    th1 = data1['Household']['hhexpfac'].sum()
    th2 = data2['Household']['hhexpfac'].sum()
    tp1 = data1['Person']['psexpfac'].sum()
    tp2 = data2['Person']['psexpfac'].sum()
    ahs1 = tp1 / th1
    ahs2 = tp2 / th2
    ph = pd.DataFrame(index = ['Total Persons', 'Total Households', 'Average Household Size'])
    ph[name1] = [tp1, th1, ahs1]
    ph[name2] = [tp2, th2, ahs2]
    ph = get_differences(ph, name1, name2, [0, 0, 2])

    persons_hh_acs= pd.read_excel(acs_data,sheetname = 'Totals')
    persons_hh_acs_df = pd.DataFrame(persons_hh_acs)
    acs_persons = persons_hh_acs_df.loc[persons_hh_acs_df['DataItem']=='Persons']['Total']
    acs_hh= persons_hh_acs_df.loc[persons_hh_acs_df['DataItem']=='Persons']['Total']
    acs_per_hh= persons_hh_acs_df.loc[persons_hh_acs_df['DataItem']=='Persons']['Total']
    ph['ACS'] = [acs_persons, acs_hh, acs_per_hh]

    cp2 = time.time()
    print('Total Households and Persons data frame created in ' + str(round(cp2 - cp1, 1)) + ' seconds')

    ##Work and School Location
    #Workers at Home
    wrkrs1 = merge_per_hh_1[['pwtyp', 'psexpfac', 'hhtaz', 'pwpcl', 'hhparcel', 'pwaudist', 'pgend', 'pagey']].query('pwtyp == "Paid Full-Time Worker" or pwtyp == "Paid Part-Time Worker"')
    wrkrs2 = merge_per_hh_2[['pwtyp', 'psexpfac', 'hhtaz', 'pwpcl', 'hhparcel', 'pwaudist', 'pgend', 'pagey']].query('pwtyp == "Paid Full-Time Worker" or pwtyp == "Paid Part-Time Worker"')
    wkr_1_hzone = pd.merge(districtfile, wrkrs1, left_on = 'TAZ', right_on = 'hhtaz')
    wkr_2_hzone = pd.merge(districtfile, wrkrs2, left_on = 'TAZ', right_on = 'hhtaz')
    total_workers_1 = wrkrs1['psexpfac'].sum()
    total_workers_2 = wrkrs2['psexpfac'].sum()
    works_at_home_1 = wkr_1_hzone[['pwpcl', 'hhparcel', 'psexpfac', 'County', 'pwaudist', 'pwtyp', 'pgend', 'pagey']].query('pwpcl == hhparcel')
    works_at_home_2 = wkr_2_hzone[['pwpcl', 'hhparcel', 'psexpfac', 'County', 'pwaudist', 'pwtyp', 'pgend', 'pagey']].query('pwpcl == hhparcel')
    work_home_county_1 = works_at_home_1.groupby('County').sum()['psexpfac']
    work_home_county_2 = works_at_home_2[['County', 'psexpfac']].groupby('County').sum()['psexpfac']
    work_home_1 = work_home_county_1.sum()
    work_home_2 = work_home_county_2.sum()
    wh = pd.DataFrame(index = ['Total Workers at Home', 'Total Workers', 'Share at Home (%)'])
    wh[name1] = [work_home_1, total_workers_1, work_home_1 / total_workers_1 * 100]
    work_at_home_acs= pd.read_excel(acs_data,sheetname = 'WorkAtHome')
    region_wah = work_at_home_acs.loc[work_at_home_acs['County'] == 'Region']
    region_wah_values = [region_wah['ACS'], region_wah['total'], region_wah['percent']]
    wh['ACS'] = region_wah_values

    
    wh = get_differences(wh, name1, 'ACS', [0, 0, 1])
    #By county\

   
    work_home_county_1 = work_home_county_1[0:]
    work_home_county_1= work_home_county_1.reset_index() 
    
    work_home_county_1 = pd.DataFrame(work_home_county_1)
    work_home_county_1.columns = ['County', 'Model']

    whbc = pd.DataFrame()
    whbc= work_home_county_1

    county_wah = work_at_home_acs.loc[work_at_home_acs['County'] != 'Region']
    whbc = pd.merge(whbc, county_wah, on = 'County')
    del whbc['total']
    del whbc['percent']

    whbc = get_differences(whbc, 'Model', 'ACS', 0)


    cp3 = time.time()
    print('Workers at Home data frame created in ' + str(round(cp3 - cp2, 1)) + ' seconds')

    #Average Distance to Work in Miles
    workers_1 = wkr_1_hzone[['pwaudist', 'hhparcel', 'pwpcl', 'pwtyp', 'pgend', 'pagey', 'psexpfac']].query('pwaudist > 0 and pwaudist < 200 and hhparcel != pwpcl')
    workers_2 = wkr_2_hzone[['pwaudist', 'hhparcel', 'pwpcl', 'pwtyp', 'pgend', 'pagey', 'psexpfac']].query('pwaudist > 0 and pwaudist < 200 and hhparcel != pwpcl')
    workers_1_ft = workers_1.query('pwtyp == "Paid Full-Time Worker"')
    workers_2_ft = workers_2.query('pwtyp == "Paid Full-Time Worker"')
    workers_1_pt = workers_1.query('pwtyp == "Paid Part-Time Worker"')
    workers_2_pt = workers_2.query('pwtyp == "Paid Part-Time Worker"')
    workers_1_female = workers_1.query('pgend == "Female"')
    workers_2_female = workers_2.query('pgend == "Female"')
    workers_1_male = workers_1.query('pgend == "Male"')
    workers_2_male = workers_2.query('pgend == "Male"')
    workers_1_ageund30 = workers_1.query('pagey < 30')
    workers_2_ageund30 = workers_2.query('pagey < 30')
    workers_1_age30to49 = workers_1.query('pagey >= 30 and pagey < 50')
    workers_2_age30to49 = workers_2.query('pagey >= 30 and pagey < 50')
    workers_1_age50to64 = workers_1.query('pagey >= 50 and pagey < 65')
    workers_2_age50to64 = workers_2.query('pagey >= 50 and pagey < 65')
    workers_1_age65up = workers_1.query('pagey >= 65')
    workers_2_age65up = workers_2.query('pagey >= 65')

    workers_1['Share (%)'] = workers_1['psexpfac'] / workers_1['psexpfac'].sum()
    workers_2['Share (%)'] = workers_2['psexpfac'] / workers_2['psexpfac'].sum()
    workers_1_avg_dist = weighted_average(workers_1, 'pwaudist', 'psexpfac')
    workers_2_avg_dist = weighted_average(workers_2, 'pwaudist', 'psexpfac')
    workers_1_avg_dist_ft = weighted_average(workers_1_ft, 'pwaudist', 'psexpfac')
    workers_2_avg_dist_ft = weighted_average(workers_2_ft, 'pwaudist', 'psexpfac')
    workers_1_avg_dist_pt = weighted_average(workers_1_pt, 'pwaudist', 'psexpfac')
    workers_2_avg_dist_pt = weighted_average(workers_2_pt, 'pwaudist', 'psexpfac')
    workers_1_avg_dist_f = weighted_average(workers_1_female, 'pwaudist', 'psexpfac')
    workers_2_avg_dist_f = weighted_average(workers_2_female, 'pwaudist', 'psexpfac')
    workers_1_avg_dist_m = weighted_average(workers_1_male, 'pwaudist', 'psexpfac')
    workers_2_avg_dist_m = weighted_average(workers_2_male, 'pwaudist', 'psexpfac')
    workers_1_avg_dist_ageund30 = weighted_average(workers_1_ageund30, 'pwaudist', 'psexpfac')
    workers_2_avg_dist_ageund30 = weighted_average(workers_2_ageund30, 'pwaudist', 'psexpfac')
    workers_1_avg_dist_age30to49 = weighted_average(workers_1_age30to49, 'pwaudist', 'psexpfac')
    workers_2_avg_dist_age30to49 = weighted_average(workers_2_age30to49, 'pwaudist', 'psexpfac')
    workers_1_avg_dist_age50to64 = weighted_average(workers_1_age50to64, 'pwaudist', 'psexpfac')
    workers_2_avg_dist_age50to64 = weighted_average(workers_2_age50to64, 'pwaudist', 'psexpfac')
    workers_1_avg_dist_age65up = weighted_average(workers_1_age65up, 'pwaudist', 'psexpfac')
    workers_2_avg_dist_age65up = weighted_average(workers_2_age65up, 'pwaudist', 'psexpfac')
    adw = pd.DataFrame(index = ['Total', 'Full-Time', 'Part-Time', 'Female', 'Male', 'Age Under 30', 'Age 30-49', 'Age 50-64', 'Age Over 65'])
    adw[name1]=[workers_1_avg_dist, workers_1_avg_dist_ft, workers_1_avg_dist_pt, workers_1_avg_dist_f, workers_1_avg_dist_m, workers_1_avg_dist_ageund30, workers_1_avg_dist_age30to49, workers_1_avg_dist_age50to64, workers_1_avg_dist_age65up]
    adw[name2]=[workers_2_avg_dist, workers_2_avg_dist_ft, workers_2_avg_dist_pt, workers_2_avg_dist_f, workers_2_avg_dist_m, workers_2_avg_dist_ageund30, workers_2_avg_dist_age30to49, workers_2_avg_dist_age50to64, workers_2_avg_dist_age65up]
    adw = get_differences(adw, name1, name2, 2)

    wrkrslessonemi_1 = workers_1[['pwaudist', 'psexpfac']].query('pwaudist <= 1')
    wrkrslessonemi_2 = workers_2[['pwaudist', 'psexpfac']].query('pwaudist <= 1')
    workers_1_less_one_mi = 100 * wrkrslessonemi_1['psexpfac'].sum() / workers_1['psexpfac'].sum()
    workers_2_less_one_mi = 100 * wrkrslessonemi_2['psexpfac'].sum() / workers_2['psexpfac'].sum()
    wrkrsgtrtwentymi_1 = workers_1[['pwaudist', 'psexpfac']].query('pwaudist>20')
    wrkrsgtrtwentymi_2 = workers_2[['pwaudist', 'psexpfac']].query('pwaudist>20')
    workers_1_gr_twenty_mi = 100 * wrkrsgtrtwentymi_1['psexpfac'].sum() / workers_1['psexpfac'].sum()
    workers_2_gr_twenty_mi = 100 * wrkrsgtrtwentymi_2['psexpfac'].sum() / workers_2['psexpfac'].sum()

    xcl = pd.DataFrame(index = ['% Workers < 1 Mile to Work', '% Workers > 20 Miles to Work'])
    xcl[name1] = [workers_1_less_one_mi, workers_1_gr_twenty_mi]
    xcl[name2] = [workers_2_less_one_mi, workers_2_gr_twenty_mi]
    xcl = get_differences(xcl, name1, name2, 1)

    cp4 = time.time()
    print('Distance to Work data frames created in ' + str(round(cp4 - cp3, 1)) + ' seconds')

    #Average Distance to School
    students_1 = data1['Person'][['psaudist', 'psexpfac', 'pagey']].query('psaudist > 0.05 and psaudist < 200')
    students_2 = data2['Person'][['psaudist', 'psexpfac', 'pagey']].query('psaudist > 0.05 and psaudist < 200')
    students_1['share'] = students_1['psexpfac'] / students_1['psexpfac'].sum()
    students_2['share'] = students_2['psexpfac'] / students_2['psexpfac'].sum()
    students_1_und5 = students_1.query('pagey < 5')
    students_2_und5 = students_2.query('pagey < 5')
    students_1_512 = students_1.query('pagey >= 5 and pagey < 13')
    students_2_512 = students_2.query('pagey >= 5 and pagey < 13')
    students_1_1318 = students_1.query('pagey >= 13 and pagey < 19')
    students_2_1318 = students_2.query('pagey >= 13 and pagey < 19')
    students_1_19p = students_1.query('pagey >= 19')
    students_2_19p = students_2.query('pagey >= 19')

    students_1_avg_dist = weighted_average(students_1, 'psaudist', 'psexpfac')
    students_2_avg_dist = weighted_average(students_2, 'psaudist', 'psexpfac')
    students_1_dist_und5 = weighted_average(students_1_und5, 'psaudist', 'psexpfac')
    students_2_dist_und5 = weighted_average(students_2_und5, 'psaudist', 'psexpfac')
    students_1_dist_512 = weighted_average(students_1_512, 'psaudist', 'psexpfac')
    students_2_dist_512 = weighted_average(students_2_512, 'psaudist', 'psexpfac')
    students_1_dist_1318 = weighted_average(students_1_1318, 'psaudist', 'psexpfac')
    students_2_dist_1318 = weighted_average(students_2_1318, 'psaudist', 'psexpfac')
    students_1_dist_19p = weighted_average(students_1_19p, 'psaudist', 'psexpfac')
    students_2_dist_19p = weighted_average(students_2_19p, 'psaudist', 'psexpfac')

    ads = pd.DataFrame(index = ['All', 'Under 5', '5 to 12', '13 to 18', 'Over 19'])
    ads[name1] = [students_1_avg_dist, students_1_dist_und5, students_1_dist_512, students_1_dist_1318, students_1_dist_19p]
    ads[name2] = [students_2_avg_dist, students_2_dist_und5, students_2_dist_512, students_2_dist_1318, students_2_dist_19p]
    ads = get_differences(ads, name1, name2, 2)

    cp5 = time.time()
    print('Average Distance to School data frame created in ' + str(round(cp5 - cp4, 1)) + ' seconds')

    ##Transit Pass and Auto Ownership
    #Transit Pass Ownership
    Person_1_total = data1['Person']['psexpfac'].sum()
    Person_2_total = data2['Person']['psexpfac'].sum()
    ttp1 = data1['Person']['ptpass'].multiply(data1['Person']['psexpfac']).sum()
    ttp2 = data2['Person']['ptpass'].multiply(data2['Person']['psexpfac']).sum()
    ppp1 = ttp1 / Person_1_total
    ppp2 = ttp2 / Person_2_total
    tpass = pd.DataFrame(index = ['Total Transit Passes', 'Transit Passes per Person'])
    tpass[name1] = [ttp1, ppp1]
    tpass[name2] = [ttp2, ppp2]
    tpass = get_differences(tpass, name1, name2, [0, 3])

    cp6 = time.time()
    print('Transit Pass Ownership data frame created in ' + str(round(cp6 - cp5, 1)) + ' seconds')

    #Auto Ownership
    ao1 = data1['Household'][['hhvehs', 'hhexpfac']].groupby('hhvehs').sum()['hhexpfac'] / data1['Household']['hhexpfac'].sum() * 100
    for i in range(5, len(ao1)): #This loop groups households that own 4 or more cars into "4+"
        ao1[4] = ao1[4] + ao1[i]
        ao1 = ao1.drop([i])
    ao2 = data2['Household'][['hhvehs', 'hhexpfac']].groupby('hhvehs').sum()['hhexpfac'] / data2['Household']['hhexpfac'].sum() * 100
    for i in range(5, len(ao2)):
        ao2[4] = ao2[4] + ao2[i]
        ao2 = ao2.drop([i])
    ao = pd.DataFrame()
    ao['% of Households (' + name1 + ')'] = ao1
    ao['% of Households (' + name2 + ')'] = ao2
    ao = get_differences(ao, '% of Households (' + name1 + ')','% of Households (' + name2 + ')', 1)
    aonewcol=['0', '1', '2', '3', '4+']
    ao['Number of Vehicles in Household'] = aonewcol
    ao = ao.reset_index()
    del ao['hhvehs']
    ao = ao.set_index('Number of Vehicles in Household')

    cp7 = time.time()
    print('Auto Ownership data frame created in ' + str(round(cp7 - cp6, 1)) + ' seconds')

    #Share households by auto ownership
    hh_taz1 = pd.merge(districtfile, data1['Household'], left_on = 'TAZ', right_on = 'hhtaz')
    hh_taz2 = pd.merge(districtfile, data2['Household'], left_on = 'TAZ', right_on = 'hhtaz')
    aoc1 = hh_taz1[['County', 'hhvehs', 'hhexpfac']].groupby(['County', 'hhvehs']).sum()['hhexpfac']
    autos_by_county= pd.read_excel(acs_data,sheetname = 'AutosCounty')
    acs_auto_share = pd.DataFrame(autos_by_county)


    #aoc2 = hh_taz2[['County', 'hhvehs', 'hhexpfac']].groupby(['County', 'hhvehs']).sum()['hhexpfac']
    counties = []
    for i in range(len(aoc1.index)):
        if aoc1.index[i][0] not in counties:
            counties.append(aoc1.index[i][0])
    aoc = pd.DataFrame(columns = ['0 Cars (' + name1 + ') (%)', '0 Cars (' + 'ACS' + ') (%)', '1 Car (' + name1 + ') (%)', '1 Car (' + 'ACS' + ') (%)', '2 Cars (' + name1 + ') (%)', '2 Cars (' + 'ACS'+ ') (%)', '3 Cars (' + name1 + ') (%)', '3 Cars (' + 'ACS' + ') (%)', '4+ Cars (' + name1 + ') (%)', '4+ Cars (' +'ACS' + ') (%)'], index = counties)
    aoc = aoc.fillna(float(0))
    for i in range(len(aoc1.index)):
        aoc1[i] = aoc1[i] * 100 / hh_taz1[['County', 'hhexpfac']].groupby('County').sum().query('County == "' + aoc1.index[i][0] + '"')['hhexpfac']
        if aoc1.index[i][1] == 0:
            aoc['0 Cars (' + name1 + ') (%)'][aoc1.index[i][0]] = round(aoc1[i], 2)
        elif aoc1.index[i][1] == 1:
            aoc['1 Car (' + name1 + ') (%)'][aoc1.index[i][0]] = round(aoc1[i], 2)
        elif aoc1.index[i][1] == 2:
            aoc['2 Cars (' + name1 + ') (%)'][aoc1.index[i][0]] = round(aoc1[i], 2)
        elif aoc1.index[i][1] == 3:
            aoc['3 Cars (' + name1 + ') (%)'][aoc1.index[i][0]] = round(aoc1[i], 2)
        else:
            aoc['4+ Cars (' + name1 + ') (%)'][aoc1.index[i][0]] = aoc['4+ Cars (' + name1 + ') (%)'][aoc1.index[i][0]] + round(aoc1[i], 2)

    acs0cars = (acs_auto_share['0 Cars']*100).round(2).tolist()
    acs1cars = (acs_auto_share['1 Car']*100).round(2).tolist()
    acs2cars = (acs_auto_share['2 Cars']*100).round(2).tolist()
    acs3cars = (acs_auto_share['3 Cars']*100).round(2).tolist()
    acs4cars = (acs_auto_share['4+ Cars']*100).round(2).tolist()

    aoc['0 Cars (' + 'ACS' + ') (%)'] = acs0cars
    aoc['1 Car (' + 'ACS' + ') (%)'] = acs1cars
    aoc['2 Cars (' + 'ACS' + ') (%)'] = acs2cars
    aoc['3 Cars (' + 'ACS' + ') (%)'] = acs3cars
    aoc['4+ Cars (' + 'ACS' + ') (%)'] = acs4cars


    cp8 = time.time()
    print('Share of Households by Auto Ownership data frame created in ' + str(round(cp8 - cp7, 1)) + ' seconds')

    #Households by income group by auto ownership
    incmap = {} #defining map to recode income
    for i in range(0, 19999):
        incmap.update({i: 'Less than $20,000'})
    for i in range(20000, 39999):
        incmap.update({i: '$20,000-$39,999'})
    for i in range(35000, 59999):
        incmap.update({i: '$40,000-$59,999'})
    for i in range(60000, 74999):
        incmap.update({i: '$60,000-$74,999'})
    for i in range(75000, max([int(data1['Household']['hhincome'].max()), int(data2['Household']['hhincome'].max())]) + 1):
        incmap.update({i:'More than $75,000'})
    data1['Household']['recinc'] = data1['Household']['hhincome'].map(incmap)
    data2['Household']['recinc'] = data2['Household']['hhincome'].map(incmap)
    aoi1 = data1['Household'][['recinc', 'hhvehs', 'hhexpfac']].groupby(['recinc','hhvehs']).sum()['hhexpfac']
    aoi2 = data2['Household'][['recinc', 'hhvehs', 'hhexpfac']].groupby(['recinc','hhvehs']).sum()['hhexpfac']
    aoi = pd.DataFrame(columns = ['0 Cars (' + name1 + ') (%)', '0 Cars (' + name2 + ') (%)', '1 Car (' + name1 + ') (%)', '1 Car (' + name2 + ') (%)', '2 Cars (' + name1 + ') (%)', '2 Cars (' + name2 + ') (%)', '3 Cars (' + name1 + ') (%)', '3 Cars (' + name2 + ') (%)', '4+ Cars (' + name1 + ') (%)', '4+ Cars (' + name2 + ') (%)'],
                       index = ['Less than $20,000', '$20,000-$39,999', '$40,000-$59,999', '$60,000-$74,999', 'More than $75,000'])
    aoi = aoi.fillna(float(0))
    for i in range(len(aoi1.index)):
        aoi1[i] = aoi1[i] * 100 / data1['Household'][['recinc', 'hhexpfac']].groupby('recinc').sum().query('recinc == "' + aoi1.index[i][0] + '"')['hhexpfac']
        if aoi1.index[i][1] == 0:
            aoi['0 Cars (' + name1 + ') (%)'][aoi1.index[i][0]] = round(aoi1[i], 2)
        elif aoi1.index[i][1] == 1:
            aoi['1 Car (' + name1 + ') (%)'][aoi1.index[i][0]] = round(aoi1[i], 2)
        elif aoi1.index[i][1] == 2:
            aoi['2 Cars (' + name1 + ') (%)'][aoi1.index[i][0]] = round(aoi1[i], 2)
        elif aoi1.index[i][1] == 3:
            aoi['3 Cars (' + name1 + ') (%)'][aoi1.index[i][0]] = round(aoi1[i], 2)
        else:
            aoi['4+ Cars (' + name1 + ') (%)'][aoi1.index[i][0]] = aoi['4+ Cars (' + name1 + ') (%)'][aoi1.index[i][0]] + round(aoi1[i], 2)
    for i in range(len(aoi2.index)):
        aoi2[i] = aoi2[i] * 100 / data2['Household'][['recinc', 'hhexpfac']].groupby('recinc').sum().query('recinc == "' + aoi2.index[i][0] + '"')['hhexpfac']
        if aoi2.index[i][1] == 0:
            aoi['0 Cars (' + name2 + ') (%)'][aoi2.index[i][0]] = round(aoi2[i], 1)
        elif aoi2.index[i][1] == 1:
            aoi['1 Car (' + name2 + ') (%)'][aoi2.index[i][0]] = round(aoi2[i], 1)
        elif aoi2.index[i][1] == 2:
            aoi['2 Cars (' + name2 + ') (%)'][aoi2.index[i][0]] = round(aoi2[i], 1)
        elif aoi2.index[i][1] == 3:
            aoi['3 Cars (' + name2 + ') (%)'][aoi2.index[i][0]] = round(aoi2[i], 1)
        else:
            aoi['4+ Cars (' + name2 + ') (%)'][aoi2.index[i][0]] = aoi['4+ Cars (' + name2 + ') (%)'][aoi2.index[i][0]] + round(aoi2[i], 1)

    cp9 = time.time()
    print('Households by Income Group by Auto Ownership data frame created in ' + str(round(cp9 - cp8, 1)) + ' seconds')


    #Compile file
    writer = pd.ExcelWriter(location + '/LongTermReport.xlsx', engine = 'xlsxwriter')
    ph.to_excel(excel_writer = writer, sheet_name = 'Basic Summaries', na_rep = 'NA', startrow = 1)
    workbook = writer.book
    worksheet = writer.sheets['Basic Summaries']
    wh.to_excel(excel_writer = writer, sheet_name = 'Workers at Home', na_rep = 'NA')
    worksheet = writer.sheets['Workers at Home']
    whbc.to_excel(excel_writer = writer, sheet_name = 'Workers at Home', na_rep = 'NA', startrow = 6)
    adw.to_excel(excel_writer = writer, sheet_name = 'Avg Dist to Work and School', na_rep = 'NA', startrow = 1)
    worksheet = writer.sheets['Avg Dist to Work and School']
    xcl.to_excel(excel_writer = writer, sheet_name = 'Avg Dist to Work and School', na_rep = 'NA', startrow = 12)
    worksheet.write(0, 5, ' ')
    ads.to_excel(excel_writer = writer, sheet_name = 'Avg Dist to Work and School', na_rep = 'NA', startrow = 1, startcol = 6)
    tpass.to_excel(excel_writer = writer, sheet_name = 'Transit Pass and Auto Ownership', na_rep = 'NA')
    worksheet = writer.sheets['Transit Pass and Auto Ownership']
    ao.to_excel(excel_writer = writer, sheet_name = 'Transit Pass and Auto Ownership', na_rep = 'NA', startrow = 4)
    aoc.to_excel(excel_writer = writer, sheet_name = 'Transit Pass and Auto Ownership', na_rep = 'NA', startrow = 12)
    worksheet.write(12, 0, 'County')
    aoi.to_excel(excel_writer = writer, sheet_name = 'Transit Pass and Auto Ownership', na_rep = 'NA', startrow = 18)
    worksheet.write(18, 0, 'Household Income')
    writer.save()

    colwidths = getmaxwidths(location + '/LongTermReport.xlsx')
    colors = ['#004488', '#00C0C0']

    writer = pd.ExcelWriter(location + '/LongTermReport.xlsx', engine = 'xlsxwriter')
    ph.to_excel(excel_writer = writer, sheet_name = 'Basic Summaries', na_rep = 'NA', startrow = 1)
    workbook = writer.book
    worksheet = writer.sheets['Basic Summaries']
    merge_format = workbook.add_format({'align': 'center', 'bold': True, 'border': 1})
    worksheet.merge_range(0, 0, 0, 5, 'Total Households and Persons', merge_format)
    wh.to_excel(excel_writer = writer, sheet_name = 'Workers at Home', na_rep = 'NA')
    worksheet = writer.sheets['Workers at Home']
    worksheet.merge_range(5, 0, 5, 5,' ', merge_format)
    whbc.to_excel(excel_writer = writer, sheet_name = 'Workers at Home', na_rep = 'NA', startrow = 6)
    chart = workbook.add_chart({'type': 'column'})
    sheet = 'Workers at Home'
    for col_num in range(1, 3):
        chart.add_series({'name': [sheet, 6, col_num],
                            'categories': [sheet, 8, 0, 11, 0],
                            'values': [sheet, 8, col_num, 11, col_num],
                            'fill': {'color': colors[col_num - 1]}})
    chart.add_series({'name': [sheet, 6, 5],
                        'categories': [sheet, 8, 0, 11, 0],
                        'values':[sheet, 8, 5, 11, 5],
                        'fill': {'color': '#000000'}})
    chart.set_legend({'position': 'top'})
    chart.set_x_axis({'name': 'County'})
    chart.set_y_axis({'name':' Number of Home Workers'})
    worksheet.insert_chart('A14', chart)
    adw.to_excel(excel_writer = writer, sheet_name = 'Avg Dist to Work and School', na_rep = 'NA', startrow = 1)
    worksheet = writer.sheets['Avg Dist to Work and School']
    worksheet.merge_range(0, 0, 0, 4, 'Average Distance to Work', merge_format)
    xcl.to_excel(excel_writer = writer, sheet_name = 'Avg Dist to Work and School', na_rep = 'NA', startrow = 12)
    worksheet.merge_range(0, 6, 0, 10, 'Average Distance to School', merge_format)
    worksheet.write(0, 5, ' ')
    ads.to_excel(excel_writer = writer, sheet_name = 'Avg Dist to Work and School', na_rep = 'NA', startrow = 1, startcol = 6)
    sheet = 'Avg Dist to Work and School'
    chart = workbook.add_chart({'type':'column'})
    for col_num in range(1, 3):
        chart.add_series({'name': [sheet, 1, col_num],
                            'categories': [sheet, 2, 0, 10, 0],
                            'values': [sheet, 2, col_num, 10, col_num],
                            'fill': {'color': colors[col_num - 1]}})
    chart.set_legend({'position': 'top'})
    chart.set_y_axis({'name': 'Average Distance to Work'})
    worksheet.insert_chart('A17', chart)
    chart = workbook.add_chart({'type': 'column'})
    for col_num in range(7, 9):
        chart.add_series({'name': [sheet, 1, col_num],
                            'categories': [sheet, 2, 6, 6, 6],
                            'values': [sheet, 2, col_num, 6, col_num],
                            'fill': {'color': colors[col_num - 7]}})
    chart.set_legend({'position': 'top'})
    chart.set_x_axis({'name': 'Age'})
    chart.set_y_axis({'name': 'Average Distance to School'})
    worksheet.insert_chart('G17', chart)
    tpass.to_excel(excel_writer = writer, sheet_name = 'Transit Pass and Auto Ownership', na_rep = 'NA')
    worksheet = writer.sheets['Transit Pass and Auto Ownership']
    ao.to_excel(excel_writer = writer, sheet_name = 'Transit Pass and Auto Ownership', na_rep = 'NA', startrow = 4)
    aoc.to_excel(excel_writer = writer, sheet_name = 'Transit Pass and Auto Ownership', na_rep = 'NA', startrow = 12)
    worksheet.write(12, 0, 'County', merge_format)
    aoi.to_excel(excel_writer = writer, sheet_name = 'Transit Pass and Auto Ownership', na_rep = 'NA', startrow = 18)
    worksheet.write(18, 0, 'Household Income', merge_format)
    worksheet.freeze_panes(0, 1)
    for sheet in writer.sheets:
        worksheet = writer.sheets[sheet]
        for colnum in range(worksheet.dim_colmax + 1):
            worksheet.set_column(colnum, colnum, colwidths[sheet][colnum])
    writer.save()

    print('---Long Term Report succesfuly compiled in ' + str(round(time.time() - start, 1)) + ' seconds---')

def TimeChoice(data1, data2, name1, name2, location, districtfile):
    start = time.time()
    print('---Begin Time Choice Report compilation---')

    trip_ok_1 = data1['Trip'][['arrtm', 'trexpfac', 'travdist']].query('travdist > 0 and travdist < 200')
    trip_ok_2 = data2['Trip'][['arrtm', 'trexpfac', 'travdist']].query('travdist > 0 and travdist < 200')
    trip_ok_1 = trip_ok_1.reset_index()
    trip_ok_2 = trip_ok_2.reset_index()
    tour_ok_1 = data1['Tour'][['tardest', 'tlvdest', 'toexpfac', 'tautodist']].query('tautodist > 0 and tautodist < 200')
    tour_ok_2 = data2['Tour'][['tardest', 'tlvdest', 'toexpfac', 'tautodist']].query('tautodist > 0 and tautodist < 200')
    tour_ok_1 = tour_ok_1.reset_index()
    tour_ok_2 = tour_ok_2.reset_index()

    cp1 = time.time()
    print('Preliminary data frames created in ' + str(round(cp1 - start, 1)) + ' seconds')

    #Trip arrival time by hour
    trip_ok_1['hr'] = min_to_hour(trip_ok_1['arrtm'], 0)
    trip_ok_2['hr'] = min_to_hour(trip_ok_2['arrtm'], 0)
    trip_1_time = trip_ok_1[['hr', 'trexpfac']].groupby('hr').sum()['trexpfac']
    trip_2_time = trip_ok_2[['hr', 'trexpfac']].groupby('hr').sum()['trexpfac']
    trip_1_time_share = 100 * trip_1_time / trip_1_time.sum()
    trip_2_time_share = 100 * trip_2_time / trip_2_time.sum()
    trip_time = pd.DataFrame()
    trip_time[name1 + ' (%)'] = trip_1_time_share
    trip_time[name2 + ' (%)'] = trip_2_time_share
    trip_time = get_differences(trip_time, name1 + ' (%)', name2 + ' (%)', 2)
    trip_time = recode_index(trip_time, 'hr', 'Arrival Hour')

    cp2 = time.time()
    print('Trip Apprival Time by Hour data frame created in ' + str(round(cp2 - cp1, 1)) + ' seconds')

    #Tour Primary Destination arrival time by hour
    tour_ok_1['hrapd'] = min_to_hour(tour_ok_1['tardest'], 0)
    tour_ok_2['hrapd'] = min_to_hour(tour_ok_2['tardest'], 0)
    tour_1_time_apd = tour_ok_1[['hrapd', 'toexpfac']].groupby('hrapd').sum()['toexpfac']
    tour_2_time_apd = tour_ok_2[['hrapd', 'toexpfac']].groupby('hrapd').sum()['toexpfac']
    tour_1_time_share_apd = 100 * tour_1_time_apd / tour_1_time_apd.sum()
    tour_2_time_share_apd = 100 * tour_2_time_apd / tour_2_time_apd.sum()
    tour_time_apd = pd.DataFrame()
    tour_time_apd[name1 + ' (%)'] = tour_1_time_share_apd
    tour_time_apd[name2 + ' (%)'] = tour_2_time_share_apd
    tour_time_apd = get_differences(tour_time_apd, name1 + ' (%)', name2 + ' (%)', 2)
    tour_time_apd = recode_index(tour_time_apd, 'hrapd', 'Primary Destination Arrival Hour')

    cp3 = time.time()
    print('Tour Primary Destination Arrival Time by Hour data frame created in ' + str(round(cp3 - cp2, 1)) + ' seconds')

    #Tour Primary Destination Departure time by hour
    tour_ok_1['hrlpd'] = min_to_hour(tour_ok_1['tlvdest'], 0)
    tour_ok_2['hrlpd'] = min_to_hour(tour_ok_2['tlvdest'], 0)
    tour_1_time_lpd = tour_ok_1[['hrlpd', 'toexpfac']].groupby('hrlpd').sum()['toexpfac']
    tour_2_time_lpd = tour_ok_2[['hrlpd', 'toexpfac']].groupby('hrlpd').sum()['toexpfac']
    tour_1_time_share_lpd = 100 * tour_1_time_lpd / tour_1_time_lpd.sum()
    tour_2_time_share_lpd = 100 * tour_2_time_lpd / tour_2_time_lpd.sum()
    tour_time_lpd = pd.DataFrame()
    tour_time_lpd[name1 + ' (%)'] = tour_1_time_share_lpd
    tour_time_lpd[name2 + ' (%)'] = tour_2_time_share_lpd
    tour_time_lpd = get_differences(tour_time_lpd, name1 + ' (%)', name2 + ' (%)', 2)
    tour_time_lpd = recode_index(tour_time_lpd, 'hrlpd', 'Primary Destination Departure Hour')

    cp4 = time.time()
    print('Tour Primary Destination Departure Time by Hour data frame created in ' + str(round(cp4 - cp3, 1)) + ' seconds')

    #Compile the file
    writer = pd.ExcelWriter(location + '/TimeChoiceReport.xlsx', engine = 'xlsxwriter')
    trip_time.to_excel(excel_writer = writer, sheet_name = 'Trip Arrival Times by Hour', na_rep = 'NA')
    tour_time_apd.to_excel(excel_writer = writer, sheet_name = 'Tour PD Arr & Dep Times by Hour', na_rep = 'NA', startrow = 1)
    tour_time_lpd.to_excel(excel_writer = writer, sheet_name = 'Tour PD Arr & Dep Times by Hour', na_rep = 'NA', startrow = 29)
    writer.save()

    colwidths = getmaxwidths(location + '/TimeChoiceReport.xlsx')
    colors = ['#004488', '#00C0C0']

    writer = pd.ExcelWriter(location + '/TimeChoiceReport.xlsx', engine = 'xlsxwriter')
    workbook = writer.book
    merge_format = workbook.add_format({'align': 'center', 'bold': True, 'border': 1})
    trip_time.to_excel(excel_writer = writer, sheet_name = 'Trip Arrival Times by Hour', na_rep = 'NA')
    tour_time_apd.to_excel(excel_writer = writer, sheet_name = 'Tour PD Arr & Dep Times by Hour', na_rep = 'NA', startrow = 1)
    tour_time_lpd.to_excel(excel_writer = writer, sheet_name = 'Tour PD Arr & Dep Times by Hour', na_rep = 'NA', startrow = 29)
    sheet = 'Trip Arrival Times by Hour'
    worksheet = writer.sheets[sheet]
    for colnum in range(worksheet.dim_colmax + 1):
        worksheet.set_column(colnum, colnum, colwidths[sheet][colnum])
    chart = workbook.add_chart({'type': 'column'})
    for colnum in range(1, 3):
        chart.add_series({'name': [sheet, 0, colnum],
                            'categories': [sheet, 2, 0, 25, 0],
                            'values': [sheet, 2, colnum, 25, colnum],
                            'fill': {'color': colors[colnum - 1]}})
    chart.set_title({'name': 'Trip Arrival Time by Hour of Day'})
    chart.set_size({'width': 704, 'height': 520})
    chart.set_x_axis({'name': 'Hour of Day', 'num_font': {'rotation': -60}})
    chart.set_y_axis({'name': 'Percent of Trips'})
    chart.set_legend({'position': 'top'})
    worksheet.insert_chart('G1', chart)
    sheet = 'Tour PD Arr & Dep Times by Hour'
    worksheet = writer.sheets[sheet]
    worksheet.merge_range(0, 0, 0, 4, 'Tour Share by Primary Destination Arrival Hour', merge_format)
    worksheet.merge_range(28, 0, 28, 4, 'Tour Share by Primary Destination Departure Hour', merge_format)
    for colnum in range(worksheet.dim_colmax + 1):
        worksheet.set_column(colnum, colnum, colwidths[sheet][colnum])
    chart = workbook.add_chart({'type': 'column'})
    for colnum in range(1, 3):
        chart.add_series({'name': [sheet, 1, colnum],
                            'categories': [sheet, 3, 0, 26, 0],
                            'values': [sheet, 3, colnum, 26, colnum],
                            'fill': {'color': colors[colnum - 1]}})
    chart.set_title({'name': [sheet, 0, 0]})
    chart.set_size({'width': 640, 'height': 540})
    chart.set_x_axis({'name': 'Hour of Day', 'num_font': {'rotation': -60}})
    chart.set_y_axis({'name': 'Percent of Tours'})
    chart.set_legend({'position': 'top'})
    worksheet.insert_chart('F1', chart)
    chart = workbook.add_chart({'type': 'column'})
    for colnum in range(1, 3):
        chart.add_series({'name': [sheet, 29, colnum],
                            'categories': [sheet, 31, 0, 54, 0],
                            'values': [sheet, 31, colnum, 54, colnum],
                            'fill': {'color': colors[colnum - 1]},})
    chart.set_title({'name': [sheet, 28, 0]})
    chart.set_size({'width': 640, 'height': 540})
    chart.set_x_axis({'name': 'Hour of Day', 'num_font': {'rotation': -60}})
    chart.set_y_axis({'name': 'Percent of Tours'})
    chart.set_legend({'position': 'top'})
    worksheet.insert_chart('F29', chart)
    writer.save()

    print('---Time Choice Report successfully compiled in ' + str(round(time.time() - start, 1)) + ' seconds---')
    
def report_compile(h5_results_file,h5_results_name,
                   h5_comparison_file,h5_comparison_name,
                   guidefile,districtfile,report_output_location):
    print('+-+-+-+Begin summary report file compilation+-+-+-+')
    timerstart=time.time()
    data1 = convert(h5_results_file,guidefile,h5_results_name)
    data2 = convert(h5_comparison_file,guidefile,h5_comparison_name)
    data1=hhmm_to_min(data1)
    data2=hhmm_to_min(data2)
    zone_district = get_districts(districtfile)
    if run_daysim_report == True:
        DaysimReport(data1,data2,h5_results_name,h5_comparison_name,report_output_location,zone_district)
    if run_day_pattern_report == True:
        DayPattern(data1,data2,h5_results_name,h5_comparison_name,report_output_location)
    if run_mode_choice_report == True:
        ModeChoice(data1,data2,h5_results_name,h5_comparison_name,report_output_location)
    if run_dest_choice_report == True:
        DestChoice(data1,data2,h5_results_name,h5_comparison_name,report_output_location,zone_district)
    if run_long_term_report == True:
        LongTerm(data1,data2,h5_results_name,h5_comparison_name,report_output_location,zone_district)
    if run_time_choice_report == True:
        TimeChoice(data1,data2,h5_results_name,h5_comparison_name,report_output_location,zone_district)
    if run_district_summary_report == True:
        WorkFAZSummary(data1,data2,h5_results_name,h5_comparison_name,report_output_location,zone_district)
    totaltime = round(time.time() - timerstart, 1)
    if totaltime < 60:
        print('+-+-+-+Summary report compilation complete in ' + str(totaltime % 60) + ' seconds+-+-+-+')
    elif int(totaltime) / 60 == 1:
        print('+-+-+-+Summary report compilation complete in 1 minute and ' + str(totaltime % 60) + ' seconds+-+-+-+')
    else:
        print('+-+-+-+Summary report compilation complete in ' + str(int(totaltime / 60)) + ' minutes and ' + str(totaltime % 60) + ' seconds+-+-+-+')


def main():
    
    report_compile(h5_results_file,h5_results_name,
                   h5_comparison_file,h5_comparison_name,
                   guidefile,districtfile,report_output_location)

main()