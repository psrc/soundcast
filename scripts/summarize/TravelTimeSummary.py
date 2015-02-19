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

import pandas as pd
import sys
import get_skims
import xlautofit
from input_configuration import *
from summary_functions import get_differences

skim_location = 'inputs'

travel_time_data = pd.io.excel.read_excel(travel_time_file) #Get origin-destination pairs

output_file = report_output_location + '/Travel_Time_Summary.xlsx'

taz_pairs = []
taz_map = {}
for item in travel_time_data.index: #Read in the taz pairs
    i = travel_time_data.loc[item, 'I - Taz']
    j = travel_time_data.loc[item, 'J - Taz']
    dest_name = travel_time_data.loc[item, 'TO']
    if (i, j) not in taz_pairs:
        taz_pairs.append((i, j))
    if j not in taz_map:
        taz_map.update({j: dest_name})

#Read in skims as data frames
am_sov_times = get_skims.recode_tazs(get_skims.from_pairs('svtl2t', skim_location, '7to8', taz_pairs), taz_map)
pm_sov_times = get_skims.recode_tazs(get_skims.from_pairs('svtl2t', skim_location, '17to18', taz_pairs), taz_map)

am_in_vehicle_times = get_skims.recode_tazs(get_skims.from_pairs('ivtwa', skim_location, '7to8', taz_pairs), taz_map)
pm_in_vehicle_times = get_skims.recode_tazs(get_skims.from_pairs('ivtwa', skim_location, '14to15', taz_pairs), taz_map)

am_waiting_times = get_skims.recode_tazs(get_skims.from_pairs('twtwa', skim_location, '7to8', taz_pairs), taz_map)
pm_waiting_times = get_skims.recode_tazs(get_skims.from_pairs('twtwa', skim_location, '14to15', taz_pairs), taz_map)

am_transit_times = am_in_vehicle_times + am_waiting_times
pm_transit_times = pm_in_vehicle_times + pm_waiting_times

am_transit_sov_ratio = am_transit_times / am_sov_times
pm_transit_sov_ratio = pm_transit_times / pm_sov_times

#Create data frames for am and pm
am_times = pd.DataFrame(columns = ['Chart Key', 'Modeled SOV Times', 'Observed SOV Times', 'Difference', '% Difference', 'Modeled Transit Times', 'Modeled Transit/SOV Ratio'])
pm_times = pd.DataFrame(columns = ['Chart Key', 'Modeled SOV Times', 'Observed SOV Times', 'Difference', '% Difference', 'Modeled Transit Times', 'Modeled Transit/SOV Ratio'])

am_times['Modeled SOV Times'] = am_sov_times['Skim']
n = am_times['Modeled SOV Times'].count()
am_times['Modeled Transit Times'] = am_transit_times['Skim']
am_times['Modeled Transit/SOV Ratio'] = am_transit_sov_ratio['Skim']
am_times.loc['Federal Way', 'Seattle']['Observed SOV Times'] = 34 #Observed times are currently hardcoded
am_times.loc['Everett', 'Seattle']['Observed SOV Times'] = 37
am_times.loc['Everett', 'Bellevue']['Observed SOV Times'] = 40
am_times.loc['Tukwila', 'Bellevue']['Observed SOV Times'] = 22
am_times.loc['Auburn', 'Renton']['Observed SOV Times'] = 15
am_times.loc['Bellevue', 'Seattle']['Observed SOV Times'] = 12
am_times.loc['Seattle', 'Bellevue']['Observed SOV Times'] = 13
am_times = get_differences(am_times, 'Modeled SOV Times', 'Observed SOV Times', 0)
am_times['Chart Key'] = [i + 1 for i in range(n)]

pm_times['Modeled SOV Times'] = pm_sov_times['Skim']
n = pm_times['Modeled SOV Times'].count()
pm_times['Modeled Transit Times'] = pm_transit_times['Skim']
pm_times['Modeled Transit/SOV Ratio'] = pm_transit_sov_ratio['Skim']
pm_times.loc['Seattle', 'Federal Way']['Observed SOV Times'] = 27
pm_times.loc['Seattle', 'Everett']['Observed SOV Times'] = 36
pm_times.loc['Bellevue', 'Everett']['Observed SOV Times'] = 33
pm_times.loc['Bellevue', 'Tukwila']['Observed SOV Times'] = 25
pm_times.loc['Renton', 'Auburn']['Observed SOV Times'] = 15
pm_times.loc['Seattle', 'Bellevue']['Observed SOV Times'] = 15
pm_times.loc['Bellevue', 'Seattle']['Observed SOV Times'] = 18
pm_times = get_differences(pm_times, 'Modeled SOV Times', 'Observed SOV Times', 0)
pm_times['Chart Key'] = [i + 1 for i in range(n)]

#Write data frames to Excel
colors = ['#004488', '#00CCCC']
for format in range(2): #Run twice, once without and once with resizing columns
    if format:
        colwidths = xlautofit.getmaxwidths(output_file)
    writer = pd.ExcelWriter(output_file, 'xlsxwriter')
    workbook = writer.book
    header_format = workbook.add_format({'bold': True, 'border': True, 'align': 'center'})
    am_times.to_excel(writer, sheet_name = 'AM Travel Times', float_format = '%.2f', merge_cells = False, na_rep = '-')
    pm_times.to_excel(writer, sheet_name = 'PM Travel Times', float_format = '%.2f', merge_cells = False, na_rep = '-')
    worksheet = writer.sheets['AM Travel Times']
    worksheet.write(0, 0, 'Origin', header_format)

    am_chart = workbook.add_chart({'type': 'column'})
    am_chart.add_series({'name': ['AM Travel Times', 0, 3],
                         'values': ['AM Travel Times', 1, 3, 50, 3],
                         'fill': {'color': colors[0]}})
    am_chart.add_series({'name': ['AM Travel Times', 0, 4],
                         'values': ['AM Travel Times', 1, 4, 50, 4],
                         'fill': {'color': colors[1]}})
    am_chart.add_series({'name': ['AM Travel Times', 0, 7],
                         'values': ['AM Travel Times', 1, 7, 50, 7],
                         'fill': {'color': '#000000'}})
    am_chart.set_title({'name': 'AM Travel Times'})
    am_chart.set_legend({'position': 'top'})
    am_chart.set_y_axis({'name': 'Time (Minutes)'})
    am_chart.set_size({'width': 1080, 'height': 400})
    worksheet.insert_chart('D54', am_chart)

    worksheet = writer.sheets['PM Travel Times']
    worksheet.write(0, 0, 'Origin', header_format)

    pm_chart = workbook.add_chart({'type': 'column'})
    pm_chart.add_series({'name': ['PM Travel Times', 0, 3],
                         'values': ['PM Travel Times', 1, 3, 50, 3],
                         'fill': {'color': colors[0]}})
    pm_chart.add_series({'name': ['PM Travel Times', 0, 4],
                         'values': ['PM Travel Times', 1, 4, 50, 4],
                         'fill': {'color': colors[1]}})
    pm_chart.add_series({'name': ['PM Travel Times', 0, 7],
                         'values': ['PM Travel Times', 1, 7, 50, 7],
                         'fill': {'color': '#000000'}})
    pm_chart.set_title({'name': 'PM Travel Times'})
    pm_chart.set_legend({'position': 'top'})
    pm_chart.set_y_axis({'name': 'Time (Minutes)'})
    pm_chart.set_size({'width': 1080, 'height': 400})
    worksheet.insert_chart('D54', pm_chart)

    if format:
        for sheet in writer.sheets:
            worksheet = writer.sheets[sheet]
            for colnum in range(worksheet.dim_colmax + 1):
                worksheet.set_column(colnum, colnum, colwidths['AM Travel Times'][colnum])
            worksheet.set_column(1, 1, colwidths['AM Travel Times'][0])
            worksheet.set_column(2, 2, 9)
            worksheet.freeze_panes(0, 3)
    writer.save()

print(output_file)

print('Done')