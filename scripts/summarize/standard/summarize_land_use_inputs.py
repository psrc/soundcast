from input_configuration import *
from standard_summary_configuration import *
import pandas as pd
import h5py
import numpy as np

writer = pd.ExcelWriter(out_lu_summary, engine= 'xlsxwriter')
print 'Summarizing parcels and synthetic population'

# Summarize parcel inputs
parcels = pd.read_csv(parcel_decay_file, sep = ' ')


parcel_totals = parcels.sum().to_frame()
parcel_totals.columns= ['Total']

parcel_describe = parcels.describe()


parcel_totals.to_excel(writer,sheet_name='Parcel Totals')
parcel_describe.to_excel(writer, sheet_name = 'Parcel Describe')

# Summarize synthetic household inputs
households_persons=h5py.File(households_persons_file,'r')
persons = households_persons['Person']
households = households_persons['Household']

hh_col_dict = {}
for col in households.keys():
  if col <> 'incomeconverted':
    my_array = np.asarray(households[col])
    hh_col_dict[col] = my_array
household_df = pd.DataFrame(hh_col_dict)
household_describe = household_df.describe()
household_describe.to_excel(writer, sheet_name = 'Household Describe')

person_col_dict = {}
for col in persons.keys():
  my_array = np.asarray(persons[col])
  person_col_dict[col] = my_array
persons_df = pd.DataFrame(person_col_dict)
person_describe = persons_df.describe()
person_describe.to_excel(writer, sheet_name = 'Person Describe')

writer.save()