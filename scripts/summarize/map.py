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

def main():

  # Store skims in a dictionary
  skim_dict = {}

  # Get bike and walk skims (for Soundcast, only assigned for time period 5 to 6 am)
  skim_dict = get_nmt_skims(skim_dict, tod_nmt='5to6')

  ##### Process the following for a given time periods
  tod = '8to9'    # AM transit

  # Get transit skims
  my_store_8to9 = h5py.File(main_dir + r'/inputs/' + tod + '.h5', "r+")
  # Total transit time
  skim_dict['transit_time'] = clean_skims(my_store_8to9['Skims']['twtwa'])

  # Get auto travel times for a given time period
  # assume we only want the SOV toll class
  sovs = ['svtl' + str(x) for x in range(1,4)]
  sovs = [sov + 't' for sov in sovs]

  tod = '7to8'
  my_auto_store = h5py.File(main_dir + r'/inputs/' + tod + '.h5', "r+")

  # Get data for each SOV skim
  #sov_time = {}
  for sov in sovs:
      skim_dict[sov] = clean_skims(my_auto_store['Skims'][sov])

  # Load in parcel data
  parcels = pd.read_csv(main_dir + r'/inputs/buffered_parcels.dat', delim_whitespace=True)

  # Aggregate parcels to zones and only import employment columns
  tazjobs = parcels.groupby('taz_p').sum()[['empedu_p','empfoo_p','empgov_p', 'empind_p','empmed_p', 'empmed_p', 'empofc_p', 'empret_p',
                                    'empsvc_p', 'empoth_p', 'emptot_p']]

  # Create an empty dataframe with index for zones 1 through highest TAZ number
  newdf = pd.DataFrame(np.zeros(hightaz), index=range(1,hightaz+1))

  # Join tazjobs data to the empty dataframe so all TAZs have data, even if its equal to zero
  jobs = newdf.join(tazjobs)
  jobs.drop(0, axis=1, inplace=True)
  jobs.fillna(0, axis=1, inplace=True)

  # Travel times under certain time
  # Replace OD pairs with travel time less than 15 with an indicator variable 1, 0 otherwise
  filtered_skims = {}

  for skim_name, skim_data in skim_dict.iteritems():
      # filter trips above travtime threshold and 0-time trips
      filtered_skims[skim_name] = np.where(skim_data > 0, 1, 9999)
      # 0-time trips suggest O-D pairs with zero service or access
      filtered_skims[skim_name] = np.where((skim_data < max_trav_time) & (skim_data > 0), 1, 0)

  np.mean(filtered_skims['transit_time'])

  # Build a dataframe with accessibility by mode
  newdf = pd.DataFrame(index=range(1,hightaz+1))   # plus because range func is 0-based

  for skim_name, skim_value in filtered_skims.iteritems():
      print "exporting skim to dataframe: " + skim_name
      newdf[skim_name] = calc_jobs(filtered_skims, skim_name, jobs)

  # add column for TAZ
  newdf['TAZ'] = newdf.index

  # Create dictionary of dataframes to plot
  d = {"Accessibility to Jobs within %d minutes" % max_trav_time : newdf}

  # Start the dataframe explorer webmap
  dframe_explorer.start(d, 
                        center=[47.614848,-122.3359058],
                        zoom=11,
                        #shape_json=main_dir+'/maps/taz2010.geojson',
                        #shape_json=os.path.join(main_dir, r'/inputs/maps/taz2010.geojson'),
                        shape_json=os.path.join('inputs/', 'taz2010.geojson'),
                        geom_name='TAZ',
                        join_name='TAZ',
                        precision=2, 
                        host='0.0.0.0'
                        )  

if __name__ == "__main__":
  main()
