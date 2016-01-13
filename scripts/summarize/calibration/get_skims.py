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

import h5py
import pandas as pd
import numpy as np
import sys, os
sys.path.append(os.path.join(os.getcwd(),"scripts"))

def from_dict(skim, file_location, tod, taz_map): #Skim matrix for specified locations from a dictionary mapping TAZ's to place names
    file = file_location + '/' + tod + '.h5'
    skims = h5py.File(file, 'r+')
    skim_df = pd.DataFrame()
    for taz in taz_map:
        skim_df[taz_map[taz]] = np.asarray(skims['Skims'][skim][taz]).astype('float') / 100
    skim_df = skim_df.reset_index()
    skim_df['Origin'] = (skim_df['index'] + 1).map(taz_map)
    del skim_df['index']
    skim_df = skim_df.dropna().set_index('Origin')
    return skim_df

def for_all_tazs(skim, file_location, tod): #Imports entire skim matrix
    file = file_location + '/' + tod + '.h5'
    skims = h5py.File(file, 'r+')
    skim_df = pd.DataFrame()
    for taz in range(len(skims['Skims'][skim])):
        skim_df[taz + 1] = np.asarray(skims['Skims'][skim][taz]).astype('float') / 100
    skim_df['Origin'] = skim_df.index + 1
    skim_df = skim_df.set_index('Origin')
    return skim_df

def from_pairs(skim, file_location, tod, od_pairs): #Get skims for specific origin-destination pairs
    file = file_location + '/' + tod + '.h5'
    skims = h5py.File(file, 'r+')
    skim_df = pd.DataFrame()
    output_df = pd.DataFrame(columns = ['Origin TAZ', 'Destination TAZ', 'Skim'])
    i = 1
    for pair in od_pairs:
        skim_df[pair[1]] = np.asarray(skims['Skims'][skim][pair[1] - 1]).astype('float') / 100
        output_df.loc[i] = [pair[0], pair[1], skim_df.loc[pair[0] - 1, pair[1]]]
        i = i + 1
    return output_df

def recode_tazs(od_pair_df, name_map):
    od_pair_df['Origin'] = od_pair_df['Origin TAZ'].map(name_map)
    od_pair_df['Destination'] = od_pair_df['Destination TAZ'].map(name_map)
    del od_pair_df['Origin TAZ']
    del od_pair_df['Destination TAZ']
    od_pair_df = od_pair_df.set_index(['Origin', 'Destination'])
    return od_pair_df