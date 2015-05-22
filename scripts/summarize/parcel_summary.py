# Load buffered parcel data and summarize by Regional Growth Center
import pandas as pd
import numpy as np
import os
from input_configuration import *
import input_configuration # Import as a module to access inputs as a dictionary

print "running parcel summary"

buffered_parcels = 'buffered_parcels.dat'   # Parcel data
parcel_urbcen_map = 'parcels_in_urbcens.csv'    # lookup for parcel to RGC
file_out = 'parcel_summary.xlsx'    # summary output file name

# Load files in pandas
main_dir = os.path.abspath('')
try:
    parcels = pd.read_table(main_dir + "/inputs/" + buffered_parcels, sep=' ')
except:
    print "Missing 'buffered_parcels.dat'"

try:
    map = pd.read_csv(main_dir + "/scripts/summarize/" + parcel_urbcen_map)
except:
    print "Missing 'parcels_in_urbcens.csv'"


# Join the urban center location to the parcels file
parcels = pd.merge(parcels, map, left_on='parcelid', right_on='hhparcel')
print "Loading parcel data to summarize..."

# Summarize parcel fields by urban center
mean_by_urbcen = pd.DataFrame(parcels.groupby('NAME').mean())
min_by_urbcen = pd.DataFrame(parcels.groupby('NAME').min())
max_by_urbcen = pd.DataFrame(parcels.groupby('NAME').max())
std_by_urbcen = pd.DataFrame(parcels.groupby('NAME').std())

# Write results to separate worksheets in an Excel file
excel_writer = pd.ExcelWriter(main_dir + '/outputs/' + file_out)

mean_by_urbcen.to_excel(excel_writer=excel_writer, sheet_name='Mean')
min_by_urbcen.to_excel(excel_writer=excel_writer, sheet_name='Min')
max_by_urbcen.to_excel(excel_writer=excel_writer, sheet_name='Max')
std_by_urbcen.to_excel(excel_writer=excel_writer, sheet_name='Std Dev')
