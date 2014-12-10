import pandas as pd

parcels_urbansim = pd.read_csv("inputs\\parcel_buffer\\parcels_urbansim.txt", delim_whitespace=True)

parcels_military = pd.read_csv("inputs\\parcel_buffer\\parcels_military.csv")

all_parcels =parcels_urbansim.merge(parcels_military, how='outer', left_on='PARCELID', right_on="Parcel_ID")

all_parcels.fillna(0, inplace =True)

all_parcels['EMPGOV_P'] = all_parcels['EMPGOV_P'] + all_parcels['Emp']
all_parcels['EMPTOT_P'] = all_parcels['EMPTOT_P'] + all_parcels['Emp']

# if a parcel_id is new in the column Parcel_ID,
# add the parcel as the max parcel id  + 1 currently on the parcels table
# fill the X Y s and the EmpGov_P field

max_id =int(all_parcels['PARCELID'].max())
new_max = max_id + 1
max_index = all_parcels.index.max()


all_parcels.fillna(0, inplace =True)

# add the new imaginary parcels to the dataset
for index, row in all_parcels.iterrows():
    if row['Parcel_ID'] == -1:
        row['PARCELID'] = new_max
        new_max = new_max + 1
        row['EMPGOV_P'] = row['Emp']
        row['EMPTOT_P'] = row['Emp']
        row['XCOORD_P'] = row['x']
        row['YCOORD_P'] = row['y']
        row['TAZ_P'] = row['TAZ']

# get rid of the extra columns from the military parcels
for colname in parcels_military.columns:
    all_parcels = all_parcels.drop(colname, 1)

for colname in all_parcels.columns:
    all_parcels[colname] = all_parcels[colname].astype(int)

all_parcels.to_csv("inputs\parcel_buffer\parcels_urbansim.txt", sep = ' ', index = False)
print 'Parcels successfully updated with military jobs.'