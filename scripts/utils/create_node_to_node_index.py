import pandas as pd
import h5py
import numpy as np

# This file creates node to node index file and node to node distance file from DTAlite output. 


# create index
node_to_node = pd.read_csv(r'R:\SoundCast\all_streets_2014\DaysimDataTools\2_Parcel_Buffering\2_DTALite\output_shortest_path.txt')
node_to_node['record_number'] = node_to_node.index + 1
min = pd.DataFrame(node_to_node.groupby(['from_node_id'])['record_number'].min())
max = pd.DataFrame(node_to_node.groupby(['from_node_id'])['record_number'].max())
min = min.merge(max, how='left', left_index = True, right_index = True)
min.reset_index(level = 0, inplace = True)
min = min.rename(columns = {'record_number_x' : 'first_rec', 'record_number_y' : 'last_rec'}) 
min.to_csv(r'R:\SoundCast\all_streets_2014\final_node_node_distance_files_2014\node_index_2014.txt', index = False, sep = ' ')

# export node distance to h5
node_to_node.distance = node_to_node.distance * 5280
h5file = h5py.File(r'R:\SoundCast\all_streets_2014\final_node_node_distance_files_2014\node_to_node_distance.h5', "w")
h5file.create_dataset('node', data=node_to_node['to_node_id'].astype('int32'), compression='gzip')
h5file.create_dataset('distance', data=node_to_node['distance'].astype('int16'), compression='gzip')
h5file.close()


