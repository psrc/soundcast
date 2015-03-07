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

import pandas as pd
import numpy as np
import math
import sys
import os
sys.path.append(os.path.join(os.getcwd(),"scripts"))

#Computation functions

def get_total(exp_fac): #Gets the total of a series of expansion factors
    total = exp_fac.sum()
    if total < 1:
        total = exp_fac.count()
    return(total)

def weighted_average(df_in, col, weights, grouper = None): #Computes the weighted average. Grouping by another column returns a series instead of a number
    if grouper == None:
        df_in[col + '_sp'] = df_in[col].multiply(df_in[weights])
        n_out = df_in[col + '_sp'].sum() / df_in[weights].sum()
        return(n_out)
    else:
        df_in[col + '_sp'] = df_in[col].multiply(df_in[weights])
        df_out = df_in.groupby(grouper).sum()
        df_out[col + '_wa'] = df_out[col + '_sp'].divide(df_out[weights])
        return(df_out[col + '_wa'])

def get_differences(df, colname1, colname2, roundto): #Computes the difference and percent difference for two specified columns in a data frame
    df['Difference'] = df[colname1] - df[colname2]
    df['% Difference'] = (df['Difference'] / df[colname2] * 100).astype('float').round(2)
    if type(roundto) == list:
        for i in range(len(df['Difference'])):
            df[colname1][i] = round(df[colname1][i], roundto[i])
            df[colname2][i] = round(df[colname2][i], roundto[i])
            df['Difference'][i] = round(df['Difference'][i], roundto[i])
    else:
        for i in range(len(df['Difference'])):
            df[colname1][i] = round(df[colname1][i], roundto)
            df[colname2][i] = round(df[colname2][i], roundto)
            df['Difference'][i] = round(df['Difference'][i], roundto)
    return(df)

def get_counts(counts_df, input_time): #Function to get counts for a SoundCast time period
    count = 0
    if input_time[1] == ' ':
        min_time = int(input_time[0])
    else:
        min_time = int(input_time[0:2])
    l = len(input_time)
    if input_time[l - 2] == ' ':
        max_time = int(input_time[l - 1])
    else:
        max_time = int(input_time[l - 2: l])
    if max_time > min_time:
        for i in range(min_time, max_time):
            if i < 10:
                count += counts_df['Vol_0' + str(i)].sum()
            else:
                count += counts_df['Vol_' + str(i)].sum()
    else:
        for i in range(min_time, 24):
            if i < 10:
                count += counts_df['Vol_0' + str(i)].sum()
            else:
                count += counts_df['Vol_' + str(i)].sum()
        for i in range(max_time + 1):
            if i < 10:
                count += counts_df['Vol_0' + str(i)].sum()
            else:
                count += counts_df['Vol_' + str(i)].sum()
    return count


#Formatting functions

def recode_index(df, old_name, new_name): #Changes the index label
    df[new_name] = df.index
    df = df.reset_index()
    del df[old_name]
    df = df.set_index(new_name)
    return df

def add_index_name(df, index_name): #Adds a name to the index column
    df[index_name] = df.index
    df = df.set_index(index_name)
    return df

def to_percent(number): #Converts a number to a string that is the number followed by a percent sing
    number = '{:.2%}'.format(number)
    return(number)

def share_compare(df, colname1, colname2): #For a mode share, converts the columns to strings of numbers with percent signs
    df[colname1] = df[colname1].apply(to_percent)
    df[colname2] = df[colname2].apply(to_percent)
    df['Difference'] = df['Difference'].apply(to_percent)


#Functions for importing data to pandas
    
def get_districts(file):
    zone_district = pd.DataFrame.from_csv(file, index_col = None)
    return(zone_district)


#Time manipulation functions

def hhmm_to_min(input): #Function that converts time in an hhmm format to a minutes since the day started format
    minmap = {}
    for i in range(0, 24):
        for j in range(0, 60):
            minmap.update({i * 100 + j: i * 60 + j})
    if input['Trip']['deptm'].max() >= 1440:
        input['Trip']['deptm'] = input['Trip']['deptm'].map(minmap)
    if input['Trip']['arrtm'].max() >= 1440:
        input['Trip']['arrtm'] = input['Trip']['arrtm'].map(minmap)
    if input['Trip']['endacttm'].max() >= 1440:
        input['Trip']['endacttm'] = input['Trip']['endacttm'].map(minmap)
    if input['Tour']['tlvorig'].max() >= 1440:
        input['Tour']['tlvorig'] = input['Tour']['tlvorig'].map(minmap)
    if input['Tour']['tardest'].max() >= 1440:
        input['Tour']['tardest'] = input['Tour']['tardest'].map(minmap)
    if input['Tour']['tlvdest'].max() >= 1440:
        input['Tour']['tlvdest'] = input['Tour']['tlvdest'].map(minmap)
    if input['Tour']['tarorig'].max() >= 1440:
        input['Tour']['tarorig'] = input['Tour']['tarorig'].map(minmap)
    return(input)

def min_to_hour(input, base): #Converts minutes since a certain time of the day to hour of the day
    timemap = {}
    for i in range(0, 24):
        if i + base < 24:
            for j in range(0, 60):
                if i + base < 9:
                    timemap.update({i * 60 + j: '0' + str(i + base) + ' - 0' + str(i + base + 1)})
                elif i + base == 9:
                    timemap.update({i * 60 + j: '0' + str(i + base) + ' - ' + str(i + base + 1)})
                else:
                    timemap.update({i * 60 + j: str(i + base) + ' - ' + str(i + base + 1)})
        else:
            for j in range(0, 60):
                if i + base - 24 < 9:
                    timemap.update({i * 60 + j: '0' + str(i + base - 24) + ' - 0' + str(i + base - 23)})
                elif i + base - 24 == 9:
                    timemap.update({i * 60 + j: '0' + str(i + base - 24) + ' - ' + str(i + base - 23)})
                else:
                    timemap.update({i * 60 + j:str(i + base - 24) + ' - ' + str(i + base - 23)})
    output = input.map(timemap)
    return output