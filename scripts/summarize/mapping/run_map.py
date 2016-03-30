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
import socket
import dframe_explorer
from map_configuration import *

# set working directory to soundcast root 
os.chdir('../../..')
main_dir = os.getcwd()

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

def transit_mode_share(trip_hh):
  # Calculate transit mode shares by home TAZ
  non_transit_modes = [1,2,3,4,5,8,9]
  # Replace non-transit modes with 0 and transit modes with 1
  trip_hh['Transit Share'] = trip_hh['Mode'].replace([1,2,3,4,5,8,9],np.zeros(len(non_transit_modes)))
  trip_hh['Transit Share'] = trip_hh['Transit Share'].replace(6,1)

  # Get transit share by income
  trip_hh_inc = { "low_inc": trip_hh.query('Household_Income < 25000'),
                  "med_inc": trip_hh.query('25000 < Household_Income < 75000'),
                  "high_inc": trip_hh.query('Household_Income > 75000')}

  my_dict = {}
  for df_name, df in trip_hh_inc.iteritems():
    # Compute percent of trips by transit for households in each zone
    transit_share_df = df.groupby('TAZ').sum()/df.groupby('TAZ').count()
    # Add the result to an empty df with all zones
    empty_zone_df = pd.DataFrame(np.zeros(hightaz), index=range(1,hightaz+1))
    transit_share = empty_zone_df.join(transit_share_df)
    transit_share.drop(0, axis=1, inplace=True)    # Drop the empty  placeholder column 0 from empty_zone_df
    transit_share.fillna(0, axis=1, inplace=True)    # Replace any NaN values with 0
    transit_share['TAZ'] = transit_share.index
    
    # Store the df with transit share for each income class in a dictionary 
    transit_share[df_name] = transit_share['Transit Share']
    my_dict[df_name] = transit_share

  # Combine all dfs from the dictionary into a single dataframe
  transit_share = pd.concat(objs=[my_dict['low_inc']['low_inc'],my_dict['med_inc']['med_inc'],my_dict['high_inc']['high_inc']],axis=1)
  transit_share['TAZ'] = transit_share.index

  return transit_share

def main():

  print "Processing data before loading map"

  # Read parcel data
  #parcels = pd.read_csv(main_dir + r'/inputs/buffered_parcels.dat', delim_whitespace=True)
  #access_df = accessibility_calc(parcels)

  # Rename parcel's TAZ column to match geo data
  #parcels['TAZ'] = parcels['taz_p']

  # Load daysim results
  daysim_main = h5py.File(main_dir + r'/outputs/daysim_outputs.h5', "r+")
  daysim_alt = h5py.File(map_daysim_alt, 'r+')

  trip_main = pd.DataFrame(data={ 'Household ID': daysim_main['Trip']['hhno'][:],
                            'Travel Time': daysim_main['Trip']['travtime'][:],
                            'Travel Cost': daysim_main['Trip']['travcost'][:],
                            'Travel Distance': daysim_main['Trip']['travdist'][:],
                            'Mode': daysim_main['Trip']['mode'][:],
                            'Purpose': daysim_main['Trip']['dpurp'][:]})

  trip_alt = pd.DataFrame(data={ 'Household ID': daysim_alt['Trip']['hhno'][:],
                            'Travel Time': daysim_alt['Trip']['travtime'][:],
                            'Travel Cost': daysim_alt['Trip']['travcost'][:],
                            'Travel Distance': daysim_alt['Trip']['travdist'][:],
                            'Mode': daysim_alt['Trip']['mode'][:],
                            'Purpose': daysim_alt['Trip']['dpurp'][:]})

  hh_main = pd.DataFrame(data={ 'TAZ' : daysim_main['Household']['hhtaz'][:], 
                              'Household_Income': daysim_main['Household']['hhincome'][:],
                              'Household Vehicles': daysim_main['Household']['hhvehs'][:],
                              'Household Size': daysim_main['Household']['hhsize'][:],
                              'Household ID': daysim_main['Household']['hhno'][:]})

  hh_alt = pd.DataFrame(data={ 'TAZ' : daysim_alt['Household']['hhtaz'][:], 
                              'Household_Income': daysim_alt['Household']['hhincome'][:],
                              'Household Vehicles': daysim_alt['Household']['hhvehs'][:],
                              'Household Size': daysim_alt['Household']['hhsize'][:],
                              'Household ID': daysim_alt['Household']['hhno'][:]})

  pers_main = pd.DataFrame(data={'Household ID': daysim_main['Person']['hhno'][:],
                                 'Age': daysim_main['Person']['pagey'][:],
                                 'Gender': daysim_main['Person']['pgend'][:]})
  pers_alt = pd.DataFrame(data={'Household ID': daysim_alt['Person']['hhno'][:],
                                 'Age': daysim_alt['Person']['pagey'][:],
                                 'Gender': daysim_alt['Person']['pgend'][:]})

  trip_hh_main = pd.merge(trip_main, hh_main[['TAZ', 'Household ID', 'Household_Income']], on='Household ID')
  trip_hh_main = pd.merge(trip_hh_main, pers_main, on='Household ID')

  trip_hh_alt = pd.merge(trip_alt, hh_alt[['TAZ', 'Household ID', 'Household_Income']], on='Household ID')
  trip_hh_alt = pd.merge(trip_hh_alt, pers_alt, on='Household ID')

  # Transit share by income class
  #transit_share = transit_mode_share(trip_hh)

  # Create dictionary of dataframes to plot on map
  d = {'main': trip_hh_main,
       'alternative': trip_hh_alt
       # "Accessibility to Jobs within %d minutes" % max_trav_time : access_df,
       # "Land Use": parcels,
       # "Households": hh_df,
       # "Trips": trip_hh,
       # "Transit Mode Share": transit_share
       }

  # Start the dataframe explorer webmap
  dframe_explorer.start(d, 
                        center=[47.614848,-122.3359058],
                        zoom=11,
                        shape_json=os.path.join('inputs/', 'taz2010.geojson'),
                        geom_name='TAZ',
                        join_name='TAZ',
                        precision=3, 
                        host=socket.gethostbyname(socket.gethostname())    # hosted on machine running the script
                        )  

if __name__ == "__main__":
  main()
