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
import h5py
import numpy as np
import pandas as pd
from scripts.summarize import dframe_explorer
import socket

# Parameters
hightaz = 3700    # Max TAZ for mapping

# Threshold travel time for accessibility calculation
max_trav_time = 30

main_dir = os.path.abspath('')

def clean_skims(skim, max_zone=3700, divide_by=100):
  '''
  Remove trips outside standard zone areas (e.g., park-and-ride and external zones)
  '''
  skim = skim[0:max_zone,0:max_zone]

  # values stored as integers for Soundcast, divide by 100 for true value
  skim = skim[:].astype('float')/divide_by

  return skim

def calc_jobs(filtered_skims, skim_name, jobs):
  '''
  Sum total jobs accessible within max travel time for origins
  "filtered_skims" input is binary OD skim matrix with 1 for skimmed travel time under a threshold,
  "jobs" is an array of total jobs in each TAZ
  '''
  totjobs = {}
  for i in range(len(filtered_skims[skim_name][0]+1)):    
      totjobs[i+1] = sum(filtered_skims[skim_name][i,:] * jobs['emptot_p']) # +1 to get zone ID
  # Write to dataframe
  df = pd.DataFrame(data=totjobs.values(), index=totjobs.keys(), columns=[skim_name])
  
  return df

def get_nmt_skims(skim_dict, tod_nmt):
  ''' 
  Extract matrix data for nonmotorized (walk and bike) trips.
  '''
  nmt_store = h5py.File(main_dir + r'/inputs/' + tod_nmt + '.h5', "r+") 
  # Get travel time skims for bike and walk
  skim_dict['biket'] = clean_skims(nmt_store['Skims']['biket'])
  skim_dict['walkt'] = clean_skims(nmt_store['Skims']['walkt'])

  return skim_dict

def get_transit_skims(skim_dict, tod_transit):
  # Get AM transit skims (for 8 to 9 AM)
  my_store_8to9 = h5py.File(main_dir + r'/inputs/8to9.h5', "r+")
  # Extract total transit time (twtwa)
  skim_dict['transit_time'] = clean_skims(my_store_8to9['Skims']['twtwa'])

  return skim_dict

def get_auto_skims(skim_dict, tod_auto):
  # Get auto travel times for a given time period
  # assume we only want the SOV toll class
  sovs = ['svtl' + str(x) for x in range(1,4)]
  sovs = [sov + 't' for sov in sovs]

  #tod_auto = '7to8'
  my_auto_store = h5py.File(main_dir + r'/inputs/' + tod_auto + '.h5', "r+")

  # Get data for each SOV skim
  #sov_time = {}
  for sov in sovs:
      skim_dict[sov] = clean_skims(my_auto_store['Skims'][sov])

  return skim_dict

def accessibility_calc(parcels):
  '''
  Accessibility is measured as the total number of jobs accessible within a max travel time, by a given mode and time period.
  The metric is computed first by creating a binary OD table with 1's for trips under a threshold, 0 otherwise.
  The OD binary matrix is multiplied by total jobs in each zone, and summed for each origin. 
  '''

  # Store skims in a dictionary
  skim_dict = {}

  # Access auto, transit, and nonmotorized (bike and walk) skim results in common format
  skim_dict = get_auto_skims(skim_dict, tod_auto='7to8')
  skim_dict = get_nmt_skims(skim_dict, tod_nmt='5to6')
  skim_dict = get_transit_skims(skim_dict, tod_transit='8to9')
  
  # Aggregate parcels to zones and only import employment columns from parcels
  tazjobs = parcels.groupby('taz_p').sum()[['empedu_p','empfoo_p','empgov_p', 'empind_p',
                                            'empmed_p', 'empmed_p', 'empofc_p', 'empret_p',
                                            'empsvc_p', 'empoth_p', 'emptot_p']]

  # Create an empty dataframe with index for zones 1 through highest TAZ number (offset by 1 because pandas is 0-based and zones begin at 1)
  empty_zone_df = pd.DataFrame(np.zeros(hightaz), index=range(1,hightaz+1))

  # Join tazjobs data to the empty dataframe so all TAZs have data, even if its equal to zero
  jobs = empty_zone_df.join(tazjobs)
  jobs.drop(0, axis=1, inplace=True)    # Drop the empty  placeholder column 0 from empty_zone_df
  jobs.fillna(0, axis=1, inplace=True)    # Replace any NaN values with 0

  # Create OD binary matrix with travel time less than max_trav_time = 1, 0 otherwise, store results in new dict
  filtered_skims = {}

  for skim_name, skim_data in skim_dict.iteritems():
      # filter trips above travtime threshold and 0-time trips
      filtered_skims[skim_name] = np.where(skim_data > 0, 1, 9999)
      # 0-time trips suggest O-D pairs with zero service or access
      filtered_skims[skim_name] = np.where((skim_data < max_trav_time) & (skim_data > 0), 1, 0)

  # np.mean(filtered_skims['transit_time'])

  # Build a dataframe with accessibility by mode
  accessiblity_df = pd.DataFrame(index=range(1,hightaz+1))   # plus 1 because range function is 0-based

  for skim_name, skim_value in filtered_skims.iteritems():
      print "Calculating accessibility for: " + skim_name
      accessiblity_df[skim_name] = calc_jobs(filtered_skims, skim_name, jobs)

  # add column for TAZ
  accessiblity_df['TAZ'] = accessiblity_df.index

  # Create legible columns for the dataframe results
  df_name_dict = {'svtl1t': 'SOV - Low Income',
                  'svtl2t': 'SOV - Med Income',
                  'svtl3t': 'SOV - High Income',
                  'transit_time': 'Transit',
                  'walkt': 'Walk',
                  'biket': 'Bike'}

  accessiblity_df.rename(columns=df_name_dict, inplace=True)

  return accessiblity_df

def main():

  # Read parcel data
  parcels = pd.read_csv(main_dir + r'/inputs/buffered_parcels.dat', delim_whitespace=True)
  access_df = accessibility_calc(parcels)

  # Rename parcel's TAZ column to match geo data
  parcels['TAZ'] = parcels['taz_p']

  # Load household-level results from daysim outputs
  daysim = h5py.File(main_dir + r'/outputs/daysim_outputs.h5', "r+")
  hh_df = pd.DataFrame(data={ 'TAZ' : daysim['Household']['zone_id'][:], 
                                  'Household Income': daysim['Household']['hhincome'][:],
                                  'Household Vehicles': daysim['Household']['hhvehs'][:],
                                  'Household Size': daysim['Household']['hhsize'][:]})

  # Create dictionary of dataframes to plot on map
  d = {"Accessibility to Jobs within %d minutes" % max_trav_time : access_df,
       "Land Use": parcels,
       "Households": hh_df}

  # Start the dataframe explorer webmap
  dframe_explorer.start(d, 
                        center=[47.614848,-122.3359058],
                        zoom=11,
                        shape_json=os.path.join('inputs/', 'taz2010.geojson'),
                        geom_name='TAZ',
                        join_name='TAZ',
                        precision=1, 
                        host=socket.gethostbyname(socket.gethostname())    # hosted on machine running the script
                        )  

if __name__ == "__main__":
  main()
