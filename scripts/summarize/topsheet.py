import pandas as pd
import numpy as np
import os
import xlsxwriter

# Load transit agency operator by transit line
operator = pd.read_csv('inputs/route_id.csv')[["id","Code"]]

# Define model time periods for AM period
transit_am = ['6to7', '7to8', '8to9']

# Set source for model boarding estimates
model_board = 'outputs/am_transit.csv'

# Set source for network summary, by TOD
network_summary_loc = 'outputs/network_summary.csv'

# Set source for VMT bu user class
uc_vmt_loc = 'outputs/uc_vmt.csv'

# Define a dictionary to order TODs by logical order
tod_list = ['am', 'md', 'pm', 'ev', 'ni']

def process_transit_boardings():
    boards_and_counts = []
    # Import modelled hourly boardings for AM periods
    board_merge = pd.merge(operator[["id","Code"]],
                       pd.read_csv(model_board)[[tod + '_board' for tod in transit_am] + ["id"]],
                       on = "id")
    # Sum all AM periods by transit line
    board_merge['sum'] = board_merge[[tod + '_board' for tod in transit_am]].sum(axis=1)
    
    # Group line boardings by transit operator
    sum_board = board_merge["sum"].groupby(board_merge['Code']).sum().reset_index()
    return sum_board

def process_observed_boardings(sum_board):
    # Import observed AM boardings by transit operator
    transit_counts = pd.read_csv('inputs/transit_counts.csv')
    sum_counts = transit_counts[["Description","Code","AM Observed", "MD Observed"]].groupby('Code').sum().reset_index()
    
    #Rename column header
    sum_board.rename(columns={'Code' : 'Code', 0 : 'AM Modeled'}, inplace=True)
    board_and_counts = [sum_board, sum_counts]
    return board_and_counts

def process_merged_boardings(sum_board, sum_counts):
    # merge counts and estimates
    merged_am = pd.merge(sum_board, sum_counts, on="Code")
    # find differences between observed and modelled
    merged_am["Difference"] = merged_am["AM Modeled"] - merged_am["AM Observed"]
    merged_am["% Difference"] = merged_am["Difference"]/merged_am["AM Modeled"]
    return merged_am

def transit_summary():
    sum_boards = process_transit_boardings()
    boards_and_counts = process_observed_boardings(sum_boards)
    transit_summary = process_merged_boardings(boards_and_counts[0], boards_and_counts[1])
    return transit_summary #remove this later, just testing

def import_network_summary(network_summary_loc):
    network_summary = pd.read_csv(network_summary_loc)
    return network_summary

def tod_summary(network_summary, tod_list):
    # sum for all facility types and group by TOD
    network_summary["VMT"] = network_summary["arterial_vmt"] + network_summary["connectors_vmt"] + network_summary["highway_vmt"]
    network_summary["VHT"] = network_summary["arterial_vht"] + network_summary["connectors_vht"] + network_summary["highway_vht"]
    network_summary["Delay"] = network_summary["arterial_delay"] + network_summary["connectors_delay"] + network_summary["highway_delay"]
    tod_summary = network_summary[["TP_4k","VMT","VHT","Delay"]].groupby("TP_4k").sum().reset_index()
    tod_list_df = pd.DataFrame(tod_list)       #create dataframe of TOD list
    tod_list_df["order"] = tod_list_df.index   #add order of TOD periods
    tod_list_df.columns = ["TP_4k","order"]    #Change column headers
    tod_summary = pd.merge(tod_summary, tod_list_df,on="TP_4k").sort(["order"])
    tod_summary.columns = ["TOD", "VMT", "VHT", "Delay", "order"]
    return tod_summary

def facility_summary(network_summary):
    facility_type = ['arterial', 'connectors', 'highway']
    data_type = ['vmt', 'vht', 'delay']
    facility_columns = []
    x = 0; y = 0
    for type in facility_type:
        for data in data_type:
            facility_columns.append(facility_type[x] + '_' + data_type[y])
            y += 1
        y = 0; x += 1
    facility_summary = network_summary[facility_columns].sum()
    
    # Group data by facility type
    # Create column for data type
    grouped_facility = pd.DataFrame(facility_summary)
    grouped_facility["data_type"] = "NaN"
    grouped_facility["Facility Type"] = "NaN"
    for s in xrange(len(facility_summary)):
        grouped_facility["data_type"][s] = facility_summary.index[s].split("_")[-1]
        grouped_facility["Facility Type"][s] = facility_summary.index[s].split("_")[0]

    #Create a new table 
    reordered_facility = pd.DataFrame(index=facility_type)
    reordered_facility["Facility Type"] = "NaN"
    reordered_facility["VMT"] = "NaN"
    reordered_facility["VHT"] = "NaN"
    reordered_facility["Delay"] = "NaN"
    z = 0
    for facility in facility_type:
        reordered_facility.loc[facility, "Facility Type"] = facility
        reordered_facility.loc[facility, "VMT"] = grouped_facility.loc[facility + "_vmt"][0]
        reordered_facility.loc[facility, "VHT"] = grouped_facility.loc[facility + "_vht"][0]
        reordered_facility.loc[facility, "Delay"] = grouped_facility.loc[facility + "_delay"][0]
    return reordered_facility
 

def vmt_mode_tod(uc_vmt_loc):
    uc_vmt = pd.read_csv(uc_vmt_loc)
    print "finished vmt by mode and tod"
    return uc_vmt

def trips_mode_tod():
    print "finished trops by mode by tod"


def write_transit_table(worksheet,data,title_format,header_format,cell_format):
    header = list(data.columns.values)                              # Get table header list
    standard_col_width = 12                                         # Set standard column width
    worksheet.merge_range("A1:F1","Transit Boarding",title_format)  # Write table title
    # initialize row and column counts
    row = 1
    col = 0
    # print header
    for i in xrange(0,len(header)):
        worksheet.write(row,col,data.columns.values[i],header_format)
        col += 1
    # reset column and row numbers
    col = 0
    row = 2
    for index in data.index.values:                               #cycle through rows after cycling through columns
        for column_name in header:
            worksheet.write(row,col,data[column_name][index],cell_format)
            worksheet.set_column(col, col, standard_col_width)
            col += 1      # iterate through each column
        col = 0           # reset column number to 1 to align rows
        row += 1          # iterate through each row of data
    return row

def write_tod_summary(worksheet,data,title_format,header_format,cell_format,start_row):
    # Add buffer space
    start_row += 2
    #title = "Transit Boarding"
    #title_row = "A" + str(start_row + 2) + ":F" + str(start_row + 2)
    header = list(data.columns.values)                              # Get table header list
    standard_col_width = 12                                         # Set standard column width
    #worksheet.merge_range(title_row,title,title_format)  # Write table title
    # initialize row and column counts
    row = start_row
    col = 1
    # print header
    for i in xrange(0,len(header)-1):
        worksheet.write(row,col,data.columns.values[i],header_format)
        col += 1
    # reset column and row numbers
    col = 1
    row = start_row + 1
    for index in data.index.values:                               #cycle through rows after cycling through columns
        for column_name in header[:-1]:
            worksheet.write(row,col,data[column_name][index],cell_format)
            worksheet.set_column(col, col, standard_col_width)
            col += 1      # iterate through each column
        col = 1           # reset column number to 1 to align rows
        row += 1          # iterate through each row of data
    return row

def write_facility_summary(worksheet,data,title_format,header_format,cell_format,start_row):
    # Add buffer space
    start_row += 2
    header = list(data.columns.values)                              # Get table header list
    standard_col_width = 12                                         # Set standard column width
    #worksheet.merge_range(title_row,title,title_format)  # Write table title
    # initialize row and column counts
    row = start_row
    col = 1
    # print header
    for i in xrange(0,len(header)):
        worksheet.write(row,col,data.columns.values[i],header_format)
        col += 1
    # reset column and row numbers
    col = 1
    row = row + 1
    for index in data.index.values:                               #cycle through rows after cycling through columns
        for column_name in header[:]:
            worksheet.write(row,col,data[column_name][index],cell_format)
            worksheet.set_column(col, col, standard_col_width)
            col += 1      # iterate through each column
        col = 1           # reset column number to 0 to align rows
        row += 1          # iterate through each row of data


# Move this to a function later ###
workbook = xlsxwriter.Workbook('topsheet.xlsx')
worksheet1 = workbook.add_worksheet()

cell_format = workbook.add_format({
        'align':'center',
        'num_format': '#,##0'})
title_format = workbook.add_format({
        'bold': 1,
        'align': 'center'})
header_format = workbook.add_format({
        'align': 'center',
        'italic': True})

# Process summary data
transit_summary = transit_summary() 

# Write out results to excel
start_row = write_transit_table(worksheet1,transit_summary,title_format,header_format,cell_format)

network_summary = import_network_summary(network_summary_loc)
tod_summary = tod_summary(network_summary, tod_list)

start_row = write_tod_summary(worksheet1,tod_summary,title_format,header_format,cell_format, start_row)

# Report facility-based results
facility_summary = facility_summary(network_summary)
write_facility_summary = write_facility_summary(worksheet1, facility_summary,title_format,header_format,cell_format, start_row)

# Report VMT by mode and by TOD
vmt_mode_tod = vmt_mode_tod(uc_vmt_loc)
workbook.close()


print "script ended"