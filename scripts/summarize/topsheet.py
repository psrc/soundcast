import xlrd
import xlsxwriter
import xlautofit
import sys
import pandas as pd
import math
import time
from input_configuration import *

def copy_sheet(from_book, from_sheet_name, to_book, to_sheet_name, font, index_width): #Copies data from one sheet to another (does not preserve formatting)
    top_format = to_book.add_format({'bold': True, 'font_name': font, 'bottom': True, 'align': 'center'})
    left_format = to_book.add_format({'bold': True, 'font_name': font, 'align': 'left'})
    general_format = to_book.add_format({'font_name': font, 'align': 'right'})
    from_sheet = from_book.sheet_by_name(from_sheet_name)
    to_sheet = to_book.add_worksheet(to_sheet_name)
    for colnum in range(from_sheet.ncols):
        to_sheet.write(0, colnum, from_sheet.cell(0, colnum).value, top_format)
    for rownum in range(1, from_sheet.nrows):
        for colnum in range(index_width):
            to_sheet.write(rownum, colnum, from_sheet.cell(rownum, colnum).value, left_format)
        for colnum in range(index_width, from_sheet.ncols):
            to_sheet.write(rownum, colnum, from_sheet.cell(rownum, colnum).value, general_format)

timer_start = time.time()

for format_sheet in range(2): #Loop through the code twice, once without and once with formatting

    #Excel files to read in
    daysim_summary = report_output_location + '/DaysimReport.xlsx'
    mode_share_summary = report_output_location + '/ModeChoiceReport.xlsx'
    dest_choice_summary = report_output_location + '/DaysimDestChoiceReport.xlsx'
    network_summary = report_output_location + '/network_summary.xlsx'
    travel_time_summary = report_output_location + '/Travel_Time_Summary.xlsx'
    output_file = report_output_location + '/Topsheet.xlsx' #File to output
    table_font = 'Times New Roman'
    
    if format_sheet:
        colwidths = xlautofit.getmaxwidths(output_file)
    else:
        pass
    colors = ['#004488', '#00C0C0']

    outbook = xlsxwriter.Workbook(output_file) #Output workbook
    number_format = outbook.add_format({'align': 'right', 'num_format': '#,##0', 'font_name': table_font}) #Define formats
    decimal_format = outbook.add_format({'align': 'right', 'num_format': '0.00', 'font_name': table_font})
    decimal_format_bold = outbook.add_format({'align': 'right', 'num_format': '0.00', 'font_name': table_font, 'bold': True})
    decimal_format_3 = outbook.add_format({'align': 'right', 'num_format': '0.000', 'font_name': table_font})
    percent_format = outbook.add_format({'align': 'right', 'num_format': '0.00%', 'font_name': table_font})
    index_format = outbook.add_format({'align': 'left', 'font_name': table_font, 'bold': True})
    header_format = outbook.add_format({'align': 'center', 'font_name': table_font, 'bold': True, 'bottom': True})
    title_format = outbook.add_format({'bold': True, 'font_name': table_font, 'font_size': 14})
    str_num_format = outbook.add_format({'align': 'right'})
    cond_format = outbook.add_format({'bold': True, 'font_color': '#800000'})

    dsbook = xlrd.open_workbook(daysim_summary) #Read in book
    basic_summaries = dsbook.sheet_by_name('Basic Summaries')
    daysim = outbook.add_worksheet('DaySim') #Add worksheet for DaySim summaries
    daysim.write(0, 0, 'Basic Summaries', header_format) #Write chart title
    for colnum in range(1, basic_summaries.ncols):
        daysim.write_string(0, colnum, basic_summaries.cell(0, colnum).value, cell_format = header_format) #Write headers
    for rownum in range(1, 3):
        daysim.write_string(rownum, 0, basic_summaries.cell(rownum, 0).value, cell_format = index_format) #Write index
        for colnum in range(1, 4):
            daysim.write_number(rownum, colnum, basic_summaries.cell(rownum, colnum).value, number_format) #Write values
        daysim.write_number(rownum, 4, basic_summaries.cell(rownum, 4).value / 100, percent_format)
    for rownum in range(3, basic_summaries.nrows):
        daysim.write_string(rownum, 0, basic_summaries.cell(rownum, 0).value, cell_format = index_format)
        for colnum in range(1, 4):
            daysim.write_number(rownum, colnum, basic_summaries.cell(rownum, colnum).value, decimal_format)
        try:
            daysim.write_number(rownum, 4, basic_summaries.cell(rownum, 4).value / 100, percent_format)
        except TypeError:
            daysim.write(rownum, 4, 'NA')

    #Write table for mode share
    daysim.write(11, 0, 'Tour Mode Share', header_format)

    mcbook = xlrd.open_workbook(mode_share_summary)
    mode_share = mcbook.sheet_by_name('Tour Mode Share')

    for colnum in range(1, mode_share.ncols):
        daysim.write_string(11, colnum, mode_share.cell(0, colnum).value, cell_format = header_format)
    for rownum in range(2, mode_share.nrows):
        daysim.write_string(rownum + 10, 0, mode_share.cell(rownum, 0).value, cell_format = index_format)
        for colnum in range(1, 5):
            daysim.write_number(rownum + 10, colnum, mode_share.cell(rownum, colnum).value / 100, percent_format)

    dcbook = xlrd.open_workbook(dest_choice_summary)
    dest_choice = dcbook.sheet_by_name('% Trips by Destination District')

    #Write table for trip destination share
    daysim.write(22, 0, 'Trip Destination Share', header_format)

    for colnum in range(1, dest_choice.ncols):
        daysim.write_string(22, colnum, dest_choice.cell(0, colnum).value, cell_format = header_format)
    for rownum in range(2, dest_choice.nrows):
        daysim.write_string(rownum + 21, 0, dest_choice.cell(rownum, 0).value, cell_format = index_format)
        for colnum in range(1, 5):
            daysim.write_number(rownum + 21, colnum, dest_choice.cell(rownum, colnum).value / 100, percent_format)

    
    else:
        pass

    #Add charts for basic summaries
    basic_summaries_chart = outbook.add_chart({'type': 'column'})
    for colnum in range(1, 3):
        basic_summaries_chart.add_series({'name': [daysim.name, 0, colnum],
                          'categories': [daysim.name, 3, 0, 8, 0],
                          'values': [daysim.name, 3, colnum, 8, colnum],
                          'fill': {'color': colors[colnum - 1]}})
    basic_summaries_chart.set_legend({'position': 'top'})
    basic_summaries_chart.set_size({'width': 6 * 64, 'height': 10 * 21})
    daysim.insert_chart('F1', basic_summaries_chart)

    mode_share_chart = outbook.add_chart({'type': 'column'})
    for colnum in range(1, 3):
        mode_share_chart.add_series({'name': [daysim.name, 11, colnum],
                          'categories': [daysim.name, 12, 0, 19, 0],
                          'values': [daysim.name, 12, colnum, 19, colnum],
                          'fill': {'color': colors[colnum - 1]}})
    mode_share_chart.set_legend({'position': 'top'})
    mode_share_chart.set_size({'width': 6 * 64, 'height': 10 * 21})
    daysim.insert_chart('F12', mode_share_chart)

    destination_share_chart = outbook.add_chart({'type': 'column'})
    for colnum in range(1, 3):
        destination_share_chart.add_series({'name': [daysim.name, 22, colnum],
                          'categories': [daysim.name, 23, 0, 33, 0],
                          'values': [daysim.name, 23, colnum, 33, colnum],
                          'fill': {'color': colors[colnum - 1]}})
    destination_share_chart.set_legend({'position': 'top'})
    destination_share_chart.set_size({'width': 6 * 64, 'height': 10 * 21})
    daysim.insert_chart('F23', destination_share_chart)

    #Add conditional formatting so that a percent difference cell is red and bold if it's greater than 100% or less than -50%
    daysim.conditional_format('E2:E9', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format})
    daysim.conditional_format('E2:E9', {'type': 'cell', 'criteria': '<=', 'value': -.5, 'format': cond_format})
    daysim.conditional_format('E13:E20', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format})
    daysim.conditional_format('E13:E20', {'type': 'cell', 'criteria': '<=', 'value': -.5, 'format': cond_format})
    daysim.conditional_format('E24:E34', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format})
    daysim.conditional_format('E24:E34', {'type': 'cell', 'criteria': '<=', 'value': -.5, 'format': cond_format})

    highway = outbook.add_worksheet('Highway') #Create summaries for the highway network
    counts_all = pd.io.excel.read_excel(network_summary, 'CountsAll')
    counts = pd.DataFrame()
    counts['Modeled'] = counts_all['Total']
    counts['Observed'] = counts_all['Vol_Daily']
    counts = counts.dropna()
    total_modeled = str(round(float(counts['Modeled'].sum() / 1000000), 1)) + ' million'
    total_observed = str(round(float(counts['Observed'].sum() / 1000000), 1)) + ' million'
    r2 = (counts.corr().loc['Modeled', 'Observed'])**2
    rmse = math.sqrt(((counts['Modeled'] - counts['Observed'])**2).mean())
    prmse = rmse / counts['Observed'].mean()
    
    #Write in initial table
    highway.write_string(0, 0, 'Total Observed Volumes', index_format)
    highway.write_string(1, 0, 'Total Modeled Volumes', index_format)
    highway.write_string(2, 0, 'R-squared', index_format)
    highway.write_string(3, 0, '% RMSE', index_format)
    highway.write_string(0, 1, total_modeled, number_format)
    highway.write_string(1, 1, total_observed, number_format)
    highway.write_number(2, 1, r2, decimal_format_3)
    highway.write_number(3, 1, prmse, percent_format)

    #Read in/Write screenline volumes
    network_summary_book = xlrd.open_workbook(network_summary)
    screenline_sheet = network_summary_book.sheet_by_name('Screenlines')
    for rownum in range(screenline_sheet.nrows):
        if rownum in [0, 16]:
            highway.write_string(rownum + 7, 0, screenline_sheet.cell(rownum, 0).value, header_format)
            highway.write_string(rownum + 7, 1, screenline_sheet.cell(rownum, 4).value, header_format)
        elif rownum in [14, 29]:
            highway.write_string(rownum + 7, 0, screenline_sheet.cell(rownum, 1).value, index_format)
            highway.write_number(rownum + 7, 1, screenline_sheet.cell(rownum, 4).value, decimal_format_bold)
        else:
            highway.write_string(rownum + 7, 0, screenline_sheet.cell(rownum, 0).value, index_format)
            try:
                highway.write_number(rownum + 7, 1, screenline_sheet.cell(rownum, 4).value, decimal_format)
                highway.write_number(rownum + 7, 3, screenline_sheet.cell(rownum, 4).value - 1, decimal_format)
            except TypeError:
                highway.write(rownum + 7, 1, screenline_sheet.cell(rownum, 4).value)

    highway.conditional_format('B9:B22', {'type': 'cell', 'criteria': '>=', 'value': 2, 'format': cond_format})
    highway.conditional_format('B9:B22', {'type': 'cell', 'criteria': '<=', 'value': 0.5, 'format': cond_format})
    highway.conditional_format('B25:B37', {'type': 'cell', 'criteria': '>=', 'value': 2, 'format': cond_format})
    highway.conditional_format('B25:B37', {'type': 'cell', 'criteria': '<=', 'value': 0.5, 'format': cond_format})

    #Read in/write transit boardings
    transit = outbook.add_worksheet('Transit')
    transit_summary_sheet = network_summary_book.sheet_by_name('Transit')
    for rownum in range(transit_summary_sheet.nrows):
        for colnum in range(transit_summary_sheet.ncols):
            if rownum in [0, 14]:
                transit.write_string(rownum, colnum, transit_summary_sheet.cell(rownum, colnum).value, title_format)
            elif rownum in [1, 15]:
                transit.write_string(rownum, colnum, transit_summary_sheet.cell(rownum, colnum).value, header_format)
            else:
                if colnum == 0:
                    transit.write_string(rownum, colnum, transit_summary_sheet.cell(rownum, colnum).value, index_format)
                elif colnum ==4:
                    try:
                        transit.write_number(rownum, colnum, transit_summary_sheet.cell(rownum, colnum).value, percent_format)
                    except TypeError:
                        transit.write_string(rownum, colnum, transit_summary_sheet.cell(rownum, colnum).value)
                else:
                    try:
                        transit.write_number(rownum, colnum, transit_summary_sheet.cell(rownum, colnum).value, number_format)
                    except TypeError:
                        transit.write_string(rownum, colnum, transit_summary_sheet.cell(rownum, colnum).value)
    transit.conditional_format('E3:E13', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format})
    transit.conditional_format('E3:E13', {'type': 'cell', 'criteria': '<=', 'value': -0.5, 'format': cond_format})
    transit.conditional_format('E17:E27', {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': cond_format})
    transit.conditional_format('E17:E27', {'type': 'cell', 'criteria': '<=', 'value': -0.5, 'format': cond_format})

    travel_time_book = xlrd.open_workbook(travel_time_summary)

    #Copy sheets from network summary to create charts
    copy_sheet(travel_time_book, 'AM Travel Times', outbook, 'AM Travel Times', table_font, 2)
    copy_sheet(travel_time_book, 'PM Travel Times', outbook, 'PM Travel Times', table_font, 2)
    copy_sheet(network_summary_book, 'CountsAll', outbook, 'CountsAll', table_font, 2)
    copy_sheet(network_summary_book, 'CountsTime', outbook, 'CountsTime', table_font, 1)
    copy_sheet(network_summary_book, 'AMTransitAll', outbook, 'AMTransitAll', table_font, 1)
    copy_sheet(network_summary_book, 'MDTransitAll', outbook, 'MDTransitAll', table_font, 1)

    #Create data frames to calculate slopes, intercepts, and R-squared values for scatterplots and insert charts
    traffic_counts_df = pd.io.excel.read_excel(network_summary, sheetname = 'CountsAll')
    traffic_counts_r2 = (traffic_counts_df[['Vol_Daily', 'Total']].corr()**2).loc['Vol_Daily', 'Total']
    traffic_counts_slope = (traffic_counts_df[['Vol_Daily', 'Total']].cov()).loc['Vol_Daily', 'Total'] / traffic_counts_df['Vol_Daily'].var()
    traffic_counts_intercept = traffic_counts_df['Total'].mean() - traffic_counts_slope * traffic_counts_df['Vol_Daily'].mean()
    #Modeled vs observed traffic counts
    traffic_counts_chart = outbook.add_chart({'type': 'scatter'})
    traffic_counts_chart.add_series({'name': 'Total',
                      'categories': ['CountsAll', 2, 38, 297, 38],
                      'values': ['CountsAll', 2, 59, 297, 59],
                      'marker': {
                                 'type': 'diamond',
                                 'border': {'color': colors[0]},
                                 'fill': {'color': colors[1]}},
                      'trendline': {
                                    'type': 'linear'}
                      })
    traffic_counts_chart.set_size({'width': 7 * 64, 'height': 19 * 20})
    traffic_counts_chart.set_title({'name': 'Modeled vs. Observed Counts\nModeled Counts = ' + str(round(traffic_counts_slope, 3)) + u' \u00d7 Observed Counts + ' + str(round(traffic_counts_intercept, 3)) + '\n' + u'R\u00b2 = ' + str(round(traffic_counts_r2, 3)),
                                    'name_font': {'size': 11}})
    traffic_counts_chart.set_legend({'position': 'none'})
    traffic_counts_chart.set_x_axis({'name': 'Observed Counts'})
    traffic_counts_chart.set_y_axis({'name': 'Modeled Counts'})
    highway.insert_chart('D1', traffic_counts_chart)

    #Primary screenline volumes
    primary_screenline_chart = outbook.add_chart({'type': 'column'})
    primary_screenline_chart.add_series({'name': 'Primary Screenlines',
                                 'categories': ['Highway', 8, 0, 21, 0],
                                 'values': ['Highway', 8, 1, 21, 1],
                                 'fill': {'color': colors[0]}})
    primary_screenline_chart.set_title({'name': 'Estimated Volumes/Observed Volumes\nPrimary Screenlines',
                                        'name_font': {'size': 12}})
    primary_screenline_chart.set_size({'width': 7 * 64, 'height': 18 * 20})
    primary_screenline_chart.set_legend({'position': 'none'})
    primary_screenline_chart.set_x_axis({'num_font': {'rotation': -90, 'bold': True}})
    primary_screenline_chart.set_y_axis({'crossing': 1})
    highway.insert_chart('D20', primary_screenline_chart)

    #Secondary screenline volumes
    secondary_screenline_chart = outbook.add_chart({'type': 'column'})
    secondary_screenline_chart.add_series({'name': 'Primary Screenlines',
                                 'categories': ['Highway', 24, 0, 36, 0],
                                 'values': ['Highway', 24, 1, 36, 1],
                                 'fill': {'color': colors[1]}})
    secondary_screenline_chart.set_title({'name': 'Estimated Volumes/Observed Volumes\nSecondary Screenlines',
                                        'name_font': {'size': 12}})
    secondary_screenline_chart.set_size({'width': 7 * 64, 'height': 18 * 20})
    secondary_screenline_chart.set_legend({'position': 'none'})
    secondary_screenline_chart.set_x_axis({'num_font': {'rotation': -90, 'bold': True}})
    secondary_screenline_chart.set_y_axis({'crossing': 1})
    highway.insert_chart('K20', secondary_screenline_chart)

    #Traffic counts by time of day
    counts_time_chart = outbook.add_chart({'type': 'line'})
    counts_time_chart.add_series({'name': ['CountsTime', 0, 1],
                     'categories': ['CountsTime', 2, 0, 12, 0],
                     'values': ['CountsTime', 2, 1, 12, 1],
                     'line': {'color': colors[0]}})
    counts_time_chart.add_series({'name': ['CountsTime', 0, 2],
                     'categories': ['CountsTime', 2, 0, 12, 0],
                     'values': ['CountsTime', 2, 2, 12, 2],
                     'line': {'color': colors[1]}})
    counts_time_chart.set_legend({'position': 'top'})
    counts_time_chart.set_x_axis({'name': 'Time of Day', 'name_font': {'size': 12}, 'num_font': {'rotation': -75}})
    counts_time_chart.set_y_axis({'name': 'Number of Vehicles', 'name_font': {'size': 12}, 'major_gridlines': {'visible': False}})
    counts_time_chart.set_size({'width': 7 * 64, 'height': 19 * 20})
    counts_time_chart.set_high_low_lines()
    highway.insert_chart('K1', counts_time_chart)

    am_boardings_df = pd.io.excel.read_excel(network_summary, sheetname = 'AMTransitAll')
    am_boardings_n = am_boardings_df['AM Route'].count()
    am_boardings_r2 = (am_boardings_df[['Modeled AM Boardings', 'Observed AM Boardings']].corr()**2).loc['Modeled AM Boardings', 'Observed AM Boardings']
    am_boardings_slope = (am_boardings_df[['Modeled AM Boardings', 'Observed AM Boardings']].cov()).loc['Modeled AM Boardings', 'Observed AM Boardings'] / am_boardings_df['Observed AM Boardings'].var()
    am_boardings_intercept = am_boardings_df['Modeled AM Boardings'].mean() - am_boardings_slope * am_boardings_df['Observed AM Boardings'].mean()

    metro_am_boardings_df = am_boardings_df.query('Code == "MK"')
    metro_am_boardings_n = metro_am_boardings_df['AM Route'].count()
    metro_am_boardings_min = min(metro_am_boardings_df.index.tolist())
    metro_am_boardings_max = max(metro_am_boardings_df.index.tolist())
    metro_am_boardings_r2 = (metro_am_boardings_df[['Modeled AM Boardings', 'Observed AM Boardings']].corr()**2).loc['Modeled AM Boardings', 'Observed AM Boardings']
    metro_am_boardings_slope = (metro_am_boardings_df[['Modeled AM Boardings', 'Observed AM Boardings']].cov()).loc['Modeled AM Boardings', 'Observed AM Boardings'] / metro_am_boardings_df['Observed AM Boardings'].var()
    metro_am_boardings_intercept = metro_am_boardings_df['Modeled AM Boardings'].mean() - metro_am_boardings_slope * metro_am_boardings_df['Observed AM Boardings'].mean()

    #AM Boardings
    am_boardings_chart = outbook.add_chart({'type': 'scatter'})
    am_boardings_chart.add_series({'name': 'Total',
                      'categories': ['AMTransitAll', 2, 3, am_boardings_n + 1, 3],
                      'values': ['AMTransitAll', 2, 2, am_boardings_n + 1, 2],
                      'marker': {
                                 'type': 'diamond',
                                 'border': {'color': colors[0]},
                                 'fill': {'color': colors[1]}},
                      'trendline': {
                                    'type': 'linear'}
                      })
    am_boardings_chart.set_size({'width': 7 * 64, 'height': 14 * 20})
    am_boardings_chart.set_title({'name': 'AM Boardings\nModeled Boardings = ' + str(round(am_boardings_slope, 3)) + u' \u00d7 Observed Boardings + ' + str(round(am_boardings_intercept, 3)) + '\n' + u'R\u00b2 = ' + str(round(am_boardings_r2, 3)),
                                    'name_font': {'size': 11}})
    am_boardings_chart.set_legend({'position': 'none'})
    am_boardings_chart.set_x_axis({'name': 'Observed Boardings'})
    am_boardings_chart.set_y_axis({'name': 'Modeled Boardings'})
    transit.insert_chart('F1', am_boardings_chart)

    #AM Boardings on King County Metro
    metro_am_boardings_chart = outbook.add_chart({'type': 'scatter'})
    metro_am_boardings_chart.add_series({'name': 'Total',
                      'categories': ['AMTransitAll', metro_am_boardings_min + 1, 3, metro_am_boardings_max + 1, 3],
                      'values': ['AMTransitAll', metro_am_boardings_min + 1, 2, metro_am_boardings_max + 1, 2],
                      'marker': {
                                 'type': 'diamond',
                                 'border': {'color': colors[0]},
                                 'fill': {'color': colors[1]}},
                      'trendline': {
                                    'type': 'linear'}
                      })
    metro_am_boardings_chart.set_size({'width': 7 * 64, 'height': 14 * 20})
    metro_am_boardings_chart.set_title({'name': 'King County Metro AM Boardings\nModeled Boardings = ' + str(round(metro_am_boardings_slope, 3)) + u' \u00d7 Observed Boardings + ' + str(round(metro_am_boardings_intercept, 3)) + '\n' + u'R\u00b2 = ' + str(round(metro_am_boardings_r2, 3)),
                                    'name_font': {'size': 11}})
    metro_am_boardings_chart.set_legend({'position': 'none'})
    metro_am_boardings_chart.set_x_axis({'name': 'Observed Boardings'})
    metro_am_boardings_chart.set_y_axis({'name': 'Modeled Boardings'})
    transit.insert_chart('F15', metro_am_boardings_chart)

    #Create charts for travel time summaries
    worksheet = outbook.worksheets()[3]
    worksheet.write(0, 0, 'Origin', header_format)

    am_chart = outbook.add_chart({'type': 'column'})
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

    worksheet = outbook.worksheets()[4]
    worksheet.write(0, 0, 'Origin', header_format)

    pm_chart = outbook.add_chart({'type': 'column'})
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

    #Adjust the column width if it's the second time running through the code
    if format_sheet:
        for sheet in outbook.worksheets():
            for colnum in range(sheet.dim_colmax + 1):
                sheet.set_column(colnum, colnum, colwidths[sheet.name][colnum])
            if sheet.name in ['AM Travel Times', 'PM Travel Times']:
                sheet.set_column(1, 1, 13)
                sheet.set_column(2, 2, 9)
                sheet.freeze_panes(0, 3)

    #Adjust the column width if it's the second time running through the code
    if format_sheet:
        for sheet in outbook.worksheets():
            for colnum in range(sheet.dim_colmax + 1):
                sheet.set_column(colnum, colnum, colwidths[sheet.name][colnum])
            if sheet.name in ['AM Travel Times', 'PM Travel Times']:
                sheet.set_column(1, 1, 13)
                sheet.set_column(2, 2, 9)
                sheet.freeze_panes(0, 3)

    outbook.close()

print('Topsheet created in ' + str(round(time.time() - timer_start, 1)) + ' seconds')