from input_configuration import *
from standard_summary_configuration import *
import pandas as pd


parcels = pd.read_csv(parcel_decay_file, sep = ' ')


parcel_totals = parcels.sum().to_frame()
parcel_totals.columns= ['Total']

parcel_describe = parcels.describe()

writer = pd.ExcelWriter(out_lu_summary, engine= 'xlsxwriter')
parcel_totals.to_excel(writer,sheet_name='Totals')
parcel_describe.to_excel(writer, sheet_name = 'Describe')

writer.save()