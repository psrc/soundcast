# this is an example script for when people ask for skims in csv
import h5py
import pandas as pd

user_class_auto = "svtl1t"
user_class_transit = "ivtwa"

pk_skims_loc = r"Z:\brice\soundcast\inputs\7to8.h5"
op_skims_loc = r"Z:\brice\soundcast\inputs\10to14.h5"


h5_pk = h5py.File(pk_skims_loc)
h5_op = h5py.File(op_skims_loc)

# travel time skims for transit (peak hours, in-vehicle time only)
transit = h5_pk["Skims"][user_class_transit]
transit_df = pd.DataFrame(transit[:])
transit_df.to_csv(r"C:\Users\SChildress\Documents\data_request\am_transit_ivt_100.csv")
# car (off-peak hours) for 2014
auto = h5_op["Skims"][user_class_transit]
auto_df = pd.DataFrame(auto[:])
auto_df.to_csv(r"C:\Users\SChildress\Documents\data_request\md_auto_ivt_100.csv")
