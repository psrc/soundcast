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
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))

import pandas as pd
import xlautofit
import xlsxwriter
import numpy as np
import xlrd
import time
import summary_functions as scf
from standard_summary_configuration import *
from input_configuration import *
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))



input_file = report_output_location+'/network_summary_detailed.xlsx'
output_file= report_output_location+'/network_summary.xlsx'
net_summary_df = pd.io.excel.read_excel(input_file, sheetname = 'Network Summary')
model_run_name = 'Model Run'
comparison_name = 'Comparison Scenario'
comparison_scenario_file = xlrd.open_workbook('output_templates/NetworkSummaryTemplate.xlsx')
comparison_scenario_sheet = comparison_scenario_file.sheet_by_name('Network')

net_summary = xlsxwriter.Workbook(output_file)


summary_by_tp_4k = net_summary_df.groupby('TP_4k').sum() #Group by 4k time
totals = net_summary_df.sum()


#Create lists to iterate over
variables = ['vmt', 'vht', 'delay']
times = ['am', 'md', 'pm', 'ev', 'ni', 'Total']
facilities = ['Freeways', 'Arterials', 'Connectors', 'Total']
title_rows = {'vmt': 0, 'vht': 14, 'delay': 28} #Says which row to start at for each variable

#Define formatting
#Input Locations
# for testing !!!!!!!!! remove later
global font
global title_format
global header_format
global index_format
global number_format 
global percent_format
global decimal_format
global string_format
global cond_format
global colors

font = 'Times New Roman'
title_format = net_summary.add_format({'bold': True, 'font_name': font, 'font_size': 12})
header_format = net_summary.add_format({'bold': True, 'font_name': font, 'font_size': 11, 'align': 'center',    'bottom': True})
index_format = net_summary.add_format({'bold': True, 'font_name': font, 'font_size': 11, 'align': 'left'})
number_format = net_summary.add_format({'font_name': font, 'num_format': '#,##0', 'align': 'right'})
percent_format = net_summary.add_format({'font_name': font, 'num_format': '0.00%'})
decimal_format = net_summary.add_format({'font_name': font, 'num_format': '0.00'})
string_format = net_summary.add_format({'align': 'left'})
cond_format = net_summary.add_format({'bold': True, 'font_color': '#800000'})
colors = ['#004488', '#00CCCC']






#Define dictionary to map from screenline number to name; this should be a file
screenline_dict = {'Primary': {
                                4: 'Tacoma - East of CBD',
                                14: 'Auburn',
                                15: 'Auburn',
                                22: 'Tukwila',
                                23: 'Renton',
                                29: 'Seattle - South of CBD',
                                30: 'Bellevue/Redmond',
                                32: 'TransLake',
                                35: 'Ship Canal',
                                37: 'Kirkland/Redmond',
                                41: 'Seattle - North',
                                43: 'Lynnwood/Bothell',
                                44: 'Bothell',
                                46: 'Mill Creek'},
                    'Secondary': {
                                    2: 'Parkland',
                                    3: 'Puyallup',
                                    7: 'Tacoma Narrows',
                                    18: 'Maple Valley',
                                    19: 'SeaTac',
                                    20: 'Kent',
                                    54: 'Gig Harbor',
                                    57: 'Kitsap - North',
                                    58: 'Agate Pass',
                                    60: 'Cross-Sound',
                                    66: 'Preston, Issaquah',
                                    71: 'Woodinville'}}

#Create a dictionary to map from screenline names to the observed daily volumes
observed_screenline_volumes = {'Tacoma - East of CBD': 283164,
                                'Auburn': 540866,
                                'Tukwila': 245433,
                                'Renton': 85258,
                                'Seattle - South of CBD': 469433,
                                'Bellevue/Redmond': 362151,
                                'TransLake': 234150,
                                'Ship Canal': 507450,
                                'Kirkland/Redmond': 375697,
                                'Seattle - North': 338825,
                                'Lynnwood/Bothell': 255467,
                                'Bothell': 268625,
                                'Mill Creek': 365342,
                                'Parkland': 275733,
                                'Puyallup': 119401,
                                'Tacoma Narrows': 80000,
                                'Maple Valley': 75982,
                                'SeaTac': 72335,
                                'Kent': 557842 ,
                                'Gig Harbor': 61503,
                                'Kitsap - North': 100890,
                                'Agate Pass': 21000,
                                'Cross-Sound': 17412,
                                'Preston, Issaquah': 91451,
                                'Woodinville': 87944}





#Function to write a table for screenlines
def write_screenline_tables(workbook, worksheet, screenline_type, header_format, index_format, number_format, percent_format, decimal_format, cond_format):
    screenline_df = pd.io.excel.read_excel(input_file, sheetname = 'Screenline Volumes')
    global screenline_dict
    screenline_df['Screenline Name'] = screenline_df['Screenline'].map(screenline_dict[screenline_type]) #Writes primary screenlines first, then secondary
    screenline_df = screenline_df.groupby('Screenline Name').sum()
    screenline_df.loc['Auburn', 'Screenline'] = '14/15'
    screenline_df = screenline_df.dropna()
    screenline_df = screenline_df.reset_index()
    screenline_df['Observed Volume'] = screenline_df['Screenline Name'].map(observed_screenline_volumes)
    screenline_df = screenline_df.set_index('Screenline Name')
    screenline_df['Modeled Volume'] = screenline_df['Volumes']
    del screenline_df['Volumes']
    screenline_df = screenline_df[['Screenline', 'Modeled Volume', 'Observed Volume']]
    screenline_df['Est/Obs'] = (screenline_df['Modeled Volume'] / screenline_df['Observed Volume']).round(2)
    screenline_df = scf.get_differences(screenline_df, 'Modeled Volume', 'Observed Volume', -2)
    if screenline_type == 'Primary':
        start_row = 0
    else:
        start_row = 16
    worksheet.write_string(start_row, 0, screenline_type + ' Screenline', header_format)
    columns = screenline_df.columns.tolist()
    index = screenline_df.index.tolist()
    for colnum in range(len(columns)):
        worksheet.write_string(start_row, colnum + 1, columns[colnum], header_format)
    for rownum in range(len(index)):
        worksheet.write_string(start_row + rownum + 1, 0, index[rownum], index_format)
        for colnum in range(len(columns)):
            if columns[colnum] == 'Screenline' and index[rownum] == 'Auburn':
                worksheet.write_string(start_row + rownum + 1, colnum + 1, screenline_df.loc[index[rownum], columns[colnum]], number_format)
            elif columns[colnum] != 'Est/Obs' and columns[colnum] != '% Difference':
                worksheet.write_number(start_row + rownum + 1, colnum + 1, screenline_df.loc[index[rownum], columns[colnum]], number_format)
            elif columns[colnum] == 'Est/Obs':
                worksheet.write_number(start_row + rownum + 1, colnum + 1, screenline_df.loc[index[rownum], columns[colnum]], decimal_format)
            else:
                try:
                    worksheet.write_number(start_row + rownum + 1, colnum + 1, screenline_df.loc[index[rownum], columns[colnum]] / 100, percent_format)
                except TypeError:
                    worksheet.write_string(start_row + rownum + 1, colnum + 1, 'NA', percent_format)
    number_format_bold = workbook.add_format({'font_name': font, 'num_format': '#,##0', 'align': 'right', 'bold': True})
    percent_format_bold = workbook.add_format({'font_name': font, 'num_format': '0.00%', 'bold': True})
    decimal_format_bold = workbook.add_format({'font_name': font, 'num_format': '0.00', 'bold': True})
    if screenline_type == 'Primary':
        total_row = 14
    else:
        total_row = 29
    worksheet.write_string(total_row, 1, 'Total', index_format)
    worksheet.write_number(total_row, 2, screenline_df['Modeled Volume'].sum(), number_format_bold)
    worksheet.write_number(total_row, 3, screenline_df['Observed Volume'].sum(), number_format_bold)
    worksheet.write_number(total_row, 4, screenline_df['Modeled Volume'].sum() / screenline_df['Observed Volume'].sum(), decimal_format_bold)
    worksheet.write_number(total_row, 5, screenline_df['Modeled Volume'].sum() - screenline_df['Observed Volume'].sum(), number_format_bold)
    worksheet.write_number(total_row, 6, screenline_df['Difference'].sum() / screenline_df['Observed Volume'].sum(), percent_format_bold)

    worksheet.conditional_format('G2:G14', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format})
    worksheet.conditional_format('G2:G14', {'type': 'cell', 'criteria': '<=', 'value': -.5, 'format': cond_format})
    worksheet.conditional_format('G18:G29', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format})
    worksheet.conditional_format('G18:G29', {'type': 'cell', 'criteria': '<=', 'value': -.5, 'format': cond_format})

#Function to create a scatterplot for modeled vs.  observed boardings



    
def write_net_sum_tables(network, variable, tables, format_sheet): #Function to write a table to the file
        start_row = title_rows[variable]
        time_df = tables[variable]['time']
        headers = time_df.columns.tolist()
        if format_sheet:
            network.merge_range(start_row, 0, start_row, 13, variable.upper(), title_format)
        network.write_string(start_row + 1, 0, 'Time Period', header_format)
        for i in range(4):
            network.write_string(start_row + 1, i + 1, headers[i], header_format) #Writes headers
        for i in range(len(times)):
            network.write_string(start_row + 2 + i, 0, times[i].upper(), index_format)
            for j in range(len(headers)):
                if headers[j] != '% Difference':
                    if variable != 'Average Speed':
                        network.write_number(start_row + 2 + i, j + 1, time_df.loc[times[i], headers[j]], number_format) #Writes values and difference
                    else:
                        network.write_number(start_row + 2 + i, j + 1, time_df.loc[times[i], headers[j]], decimal_format)
                else:
                    try:
                        network.write_number(start_row + 2 + i, j + 1, time_df.loc[times[i], headers[j]] / 100, percent_format) #Writes percent difference
                    except TypeError:
                        network.write_string(start_row + 2 + i, j + 1, 'NA', index_format) #If actual value is 0, writes 'NA'
        facility_df = tables[variable]['facility'] #This does the same thing grouped by facility type instead of time of day
        for i in range(len(facilities)):
            network.write_string(start_row + 9 + i, 0, facilities[i], index_format)
            for j in range(len(headers)):
                if headers[j] != '% Difference':
                    if variable != 'Average Speed':
                        network.write_number(start_row + 9 + i, j + 1, facility_df.loc[facilities[i], headers[j]], number_format)
                    else:
                        network.write_number(start_row + 9 + i, j + 1, facility_df.loc[facilities[i], headers[j]], decimal_format)
                else:
                    try:
                        network.write_number(start_row + 9 + i, j + 1, facility_df.loc[facilities[i], headers[j]] / 100, percent_format)
                    except TypeError:
                        network.write_string(start_row + 9 + i, j + 1, 'NA', index_format)
        time_chart = net_summary.add_chart({'type': 'column'})
        facility_chart = net_summary.add_chart({'type': 'column'})
        for colnum in range(1, 3):
            time_chart.add_series({'name': [network.name, start_row + 1, colnum],
                                   'categories': [network.name, start_row + 2, 0, start_row + 6, 0],
                                   'values': [network.name, start_row + 2, colnum, start_row + 6, colnum],
                                   'fill': {'color': colors[colnum - 1]}})
            facility_chart.add_series({'name': [network.name, start_row + 1, colnum],
                                   'categories': [network.name, start_row + 9, 0, start_row + 11, 0],
                                   'values': [network.name, start_row + 9, colnum, start_row + 11, colnum],
                                   'fill': {'color': colors[colnum - 1]}})
        time_chart.set_legend({'position': 'top'})
        facility_chart.set_legend({'position': 'top'})
        time_chart.set_size({'width': 8 * 64, 'height': 6 * 20})
        facility_chart.set_size({'width': 8 * 64, 'height': 6 * 20})
        network.insert_chart(start_row + 1, 6, time_chart)
        network.insert_chart(start_row + 8, 6, facility_chart)




#######################HIGHWAY #################################################################################


def highway_summary(network, net_summary, format_sheet, times, screenlines):

        tables = {}

    
        for variable in variables:
            if variable != 'Average Speed':
                time_df = summary_by_tp_4k[['highway_' + variable, 'arterial_' + variable, 'connectors_' + variable]].transpose().sum() #Add up vmt, vht, and delay for times
                time_df.loc['Total'] = time_df.sum()
                time_df = pd.DataFrame.from_items([(model_run_name, time_df)])
                time_df[comparison_name] = np.nan
                comparison_dict = {}
            
                for i in range(len(times)):
                    if times[i] == 'Total':
                        comparison_dict.update({comparison_scenario_sheet.cell(title_rows[variable] + 2 + i, 0).value: comparison_scenario_sheet.cell(title_rows[variable] + 2 + i, 1).value})
                    else:
                        comparison_dict.update({comparison_scenario_sheet.cell(title_rows[variable] + 2 + i, 0).value.lower(): comparison_scenario_sheet.cell(title_rows[variable] + 2 + i, 1).value}) #Get values to compare to
                for tod in comparison_dict:
                    time_df.loc[tod, comparison_name] = comparison_dict[tod]
                time_df = scf.get_differences(time_df, model_run_name, comparison_name, -2)
            else:
                time_df = tables['vmt']['time'][['Model Run', 'Comparison Scenario']] / tables['vht']['time'][['Model Run', 'Comparison Scenario']]
                time_df = scf.get_differences(time_df, model_run_name, comparison_name, 2)        

            if variable != 'Average Speed':
                facility_df = summary_by_tp_4k.sum()[['highway_' + variable, 'arterial_' + variable, 'connectors_' + variable]] #Do the same thing by facility type
                facility_df['Freeways'] = facility_df['highway_' + variable]
                del facility_df['highway_' + variable]
                facility_df['Arterials'] = facility_df['arterial_' + variable]
                del facility_df['arterial_' + variable]
                facility_df['Connectors'] = facility_df['connectors_' + variable]
                del facility_df['connectors_' + variable]
                facility_df = facility_df.transpose()
                facility_df.loc['Total'] = facility_df.sum()
                facility_df = pd.DataFrame.from_items([(model_run_name, facility_df)])
                comparison_dict = {}
                for i in range(len(facilities)):
                    comparison_dict.update({comparison_scenario_sheet.cell(title_rows[variable] + 9 + i, 0).value: comparison_scenario_sheet.cell(title_rows[variable] + 9 + i, 1).value})
                facility_df[comparison_name] = np.nan

                for tod in comparison_dict:
                    facility_df.loc[tod, comparison_name] = comparison_dict[tod]

                facility_df = scf.get_differences(facility_df, model_run_name, comparison_name, -2)
            else:
                facility_df = tables['vmt']['facility'][['Model Run', 'Comparison Scenario']] / tables['vht']['facility'][['Model Run', 'Comparison Scenario']]
            facility_df = scf.get_differences(facility_df, model_run_name, comparison_name, 2)
           


            tables.update({variable: {'time': time_df, 'facility': facility_df}})
            write_net_sum_tables(network, variable, tables, format_sheet) #Write the tables to the excel file

        network.conditional_format('E3:E13', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format}) #Defines conditional format
        network.conditional_format('E3:E13', {'type': 'cell', 'criteria': '<=', 'value': -.5, 'format': cond_format})
        network.conditional_format('E19:E29', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format})
        network.conditional_format('E19:E29', {'type': 'cell', 'criteria': '<=', 'value': -.5, 'format': cond_format})
        network.conditional_format('E35:E45', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format})
        network.conditional_format('E35:E45', {'type': 'cell', 'criteria': '<=', 'value': -.5, 'format': cond_format})
        network.conditional_format('E51:E61', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format})
        network.conditional_format('E51:E61', {'type': 'cell', 'criteria': '<=', 'value': -.5, 'format': cond_format})

        
        write_screenline_tables(net_summary, screenlines, 'Primary', header_format, index_format, number_format, percent_format, decimal_format, cond_format)
        write_screenline_tables(net_summary, screenlines, 'Secondary', header_format, index_format, number_format, percent_format, decimal_format, cond_format)

        #counts_output = pd.io.excel.read_excel(input_file, sheetname = 'Counts Output')
        #counts_by_tod = pd.DataFrame(columns = ['Counts (' + model_run_name + ')', 'Counts (Observed)'],
        #                         index = ['5 to 6', '6 to 7', '7 to 8', '8 to 9',
        #                                  '9 to 10', '10 to 14', '14 to 15', '15 to 16',
        #                                  '16 to 17', '17 to 18', '18 to 20', '20 to 5'])
        #for tod in counts_by_tod.index:
            
        #    counts_by_tod.loc[tod, 'Counts (Observed)'] = scf.get_counts(counts_output, tod)
        #    # hack to fix double counting of 5 to 6 period in 20 to 5
        #    if tod == '20 to 5':
        #        counts_by_tod.loc[tod, 'Counts (Observed)'] =  counts_by_tod.loc[tod, 'Counts (Observed)'] - counts_by_tod.loc['5 to 6', 'Counts (Observed)']
        #    counts_by_tod.loc[tod, 'Counts (' + model_run_name + ')'] = counts_output['vol' + tod.replace(' ', '')].sum()

        #countstime.write_string(0, 0, 'Time Period', header_format)


        #counts_by_tod = scf.get_differences(counts_by_tod, 'Counts (' + model_run_name + ')', 'Counts (Observed)', -2)

        #columns = counts_by_tod.columns.tolist()
        #times = counts_by_tod.index.tolist()

        #for colnum in range(len(columns)):
        #    countstime.write_string(0, colnum + 1, columns[colnum], header_format)
        #    for rownum in range(len(times)):
        #        countstime.write_string(rownum + 1, 0, times[rownum], index_format)
        #        for colnum in range(len(columns)):
        #            if columns[colnum] <> '% Difference':
        #                countstime.write_number(rownum + 1, colnum + 1, counts_by_tod.loc[times[rownum], columns[colnum]], number_format)
        #            else:
        #                try:
        #                    countstime.write_number(rownum + 1, colnum + 1, counts_by_tod.loc[times[rownum], columns[colnum]] / 100, percent_format)
        #                except TypeError:
        #                    countstime.write_string(rownum + 1, colnum + 1, 'NA', index_format)

        #countstime.conditional_format('E2:E13', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format})
        #countstime.conditional_format('E2:E13', {'type': 'cell', 'criteria': '<=', 'value': -.5, 'format': cond_format})
    
        #counts_time_chart = net_summary.add_chart({'type': 'line'})
        #counts_time_chart.add_series({'name': [countstime.name, 0, 1],
        #             'categories': [countstime.name, 2, 0, 12, 0],
        #             'values': [countstime.name, 2, 1, 12, 1],
        #             'line': {'color': colors[0]}})
        #counts_time_chart.add_series({'name': [countstime.name, 0, 2],
        #             'categories': [countstime.name, 2, 0, 12, 0],
        #             'values': [countstime.name, 2, 2, 12, 2],
        #             'line': {'color': colors[1]}})
        #counts_time_chart.set_legend({'position': 'top'})
        #counts_time_chart.set_x_axis({'name': 'Time of Day', 'name_font': {'size': 18}})
        #counts_time_chart.set_y_axis({'name': 'Number of Vehicles', 'name_font': {'size': 18}, 'major_gridlines': {'visible': False}})
        #counts_time_chart.set_size({'width': 606 + 9 * 64, 'height': 22 * 20})
        #counts_time_chart.set_high_low_lines()

        #countstime.insert_chart('A15', counts_time_chart)

        

        
        #counts_all = pd.io.excel.read_excel(input_file, sheetname = 'Counts Output')
        #counts_all = counts_all.reset_index()
        #counts_all = counts_all.fillna(0)
        #counts_all['Total'] = counts_all['vol5to6'] + counts_all['vol6to7'] + counts_all['vol7to8'] + counts_all['vol8to9'] + counts_all['vol9to10'] + counts_all['vol10to14'] + counts_all['vol14to15'] + counts_all['vol15to16'] + counts_all['vol16to17'] + counts_all['vol17to18'] + counts_all['vol18to20'] + counts_all['vol20to5']
        #r2 = (counts_all[['Vol_Daily', 'Total']].corr() ** 2).loc['Vol_Daily', 'Total']
        #slope = (counts_all[['Vol_Daily', 'Total']].cov()).loc['Vol_Daily', 'Total'] / counts_all['Vol_Daily'].var()
        #intercept = counts_all['Total'].mean() - slope * counts_all['Vol_Daily'].mean()
        #columns = counts_all.columns.tolist()
        #index = counts_all.index.tolist()
        #for colnum in range(len(columns)):
        #    countsall.write(0, colnum, columns[colnum])
        #    for rownum in range(len(index)):
        #        try:
        #            countsall.write(rownum + 1, colnum, counts_all.loc[index[rownum], columns[colnum]])
        #        except TypeError:
        #            countsall.write(rownum + 1, colnum, 'NA')
        
        #counts_chart = net_summary.add_chart({'type': 'scatter'})
        #counts_chart.add_series({'name': 'Total',
        #              'categories': [countsall.name, 2, 38, 297, 38],
        #              'values': [countsall.name, 2, 59, 297, 59],
        #              'marker': {
        #                         'type': 'diamond',
        #                         'border': {'color': colors[0]},
        #                         'fill': {'color': colors[1]}},
        #              'trendline': {
        #                            'type': 'linear'}
        #              })
        #counts_chart.set_size({'width': 11 * 96, 'height': 36 * 20})
        #counts_chart.set_title({'name': 'Modeled vs. Observed Counts\nModeled Counts = ' + str(round(slope, 3)) + u' \u00d7 Observed Counts + ' + str(round(intercept, 3)) + '\n' + u'R\u00b2 = ' + str(round(r2, 3))})
        #counts_chart.set_legend({'position': 'none'})
        #counts_chart.set_x_axis({'name': 'Observed Counts'})
        #counts_chart.set_y_axis({'name': 'Modeled Counts'})
        #countsall.insert_chart('B2', counts_chart)



################################################################################################################
###### MAIN ####################################################################################################
def main():


    for format_sheet in range(2): #runs through the code twice: once without and once with formatting column widths


        if format_sheet == 0:
            network = net_summary.add_worksheet('Network')
            screenlines = net_summary.add_worksheet('Screenlines')
            # this isn't working
            #countstime = net_summary.add_worksheet('CountsTime')
            #countsall = net_summary.add_worksheet('CountsAll')
            


        highway_summary(network, net_summary, format_sheet, times, screenlines)

        if format_sheet == 1:
            colwidths = xlautofit.even_widths_single_index(output_file) 
        

        net_summary.close()

if __name__ == "__main__":
    timer_start = time.time()
    main()
 
