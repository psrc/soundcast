import os, sys
import pysal as ps
import numpy as np
import pandas as pd
sys.path.append(os.getcwd())

# open nodes file & convert to pandas dataframe
nodes = ps.open('inputs/scenario/networks/shapefiles/junctions.dbf')
d = dict([(col, np.array(nodes.by_col(col))) for col in nodes.header])
df = pd.DataFrame(d)

# only need nodes that are zones
df = df.loc[df['IsZone'] == 1]

# Scen_Node is the taz id column
df = df.sort(columns = 'Scen_Node')

# create an ordinal/index column. Daysim is 1 based. 
df['zone_ordinal'] = [i for i in xrange(1, len(df) + 1)]

# create a cost columnn for park and rides, set to 0 for now
df['Cost'] = 0

# column for non park & rides, internal zones
df['Dest_eligible'] = 0
df.ix[df.Scen_Node <= 3700, 'Dest_eligible'] = 1

# rename some columns for the taz file
df = df.rename(columns={'Scen_Node': 'Zone_id', 'P_RStalls': 'Capacity', 'Processing' : 'External'})

# write out taz file:
df.to_csv('inputs/scenario/landuse/TAZIndex.txt', columns = ['Zone_id', 'zone_ordinal', 'Dest_eligible', 'External'], index = False, sep='\t') 

# rename some columns for the park and ride file
df = df.rename(columns={'Zone_id': 'ZoneID', 'zone_ordinal' : 'NodeID', })

# write out  park and ride file 
p_rDF = df.loc[df['Capacity'] > 0]
p_rDF.to_csv(r'inputs/scenario/landuse/p_r_nodes.csv', columns = ['NodeID', 'ZoneID', 'XCoord', 'YCoord', 'Capacity', 'Cost'], index = False) 
