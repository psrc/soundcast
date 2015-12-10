# Calculate average "upslope" (total elevation gain divided by length traversed) on a network
# Should be used as a post-process on an emme-formatted network file
# outputs emme attribute files that are required by the bike model

# This is full of hard-codes, but it's important code I don't want to lose so it's checked in!

import arcpy
import pandas as pd
from arcpy.sa import *
import arcinfo

arcpy.CheckOutExtension("Spatial")

def split_edges(in_fc, spatial_reference, fields=["SHAPE@",'PSRCEdgeID'], segment_len=10):
    '''Loop through each edge and split it into points
       Edges are split in lengths defined by segment_len (default is 10 feet)
       Returns tuple of edge ID and tuple of point X and Y coordinates.'''
    point_results = []
    counter = 0    # process takes a while, so we print a counter for monitoring
    with arcpy.da.SearchCursor(in_fc, fields, spatial_reference=spatial_reference) as cursor:
        # loop through each edge  
        for row in cursor:
            print "processing edge: " + str(counter)
            # create points along each edge, 
            # iterator defined desired segment length
            split_count = int(row[0].length/segment_len) 
            for i in range(split_count):
                point = row[0].positionAlongLine(i*segment_len)
                point_data = (str(row[1]), (point.firstPoint.X, point.firstPoint.Y))
                point_results.append(point_data)
            counter += 1
    return point_results

def create_points_fc(point_results, out_path, out_name, spatial_reference):
    print 'writing points data to feature class'
    # make a new empty feature class to load the point_results results
    # delete if it exists
    try:
        arcpy.CreateFeatureclass_management(out_path=out_path, out_name=out_name, 
                                            geometry_type='POINT', template='',
                                            spatial_reference=spatial_reference)
    except:
        print "couldn't create feature class, may already exist"
    # Add a column to the new feature class so we can add the EdgeID data
    arcpy.AddField_management(out_name, "PSRCEdgeID", "LONG", field_length = 50)

    # Add the point_results data to the new feature class
    cursor = arcpy.da.InsertCursor(r'D:\slope\slope921.gdb' + out_name, ('PSRCEdgeID', 'SHAPE@XY'))
    # Add a row for each point that we created
    for row in point_results:
        cursor.insertRow(row)
    del cursor

def join_elev_data(in_point_features, in_raster, out_point_features):
    ''' Add elevation data to point feature class
        The current raster is at 30ft intervals (i.e., 30x30' squares of elevation variation). 
        Elevation should be in feet for this raster.
        May be updating this data at some point.'''
    ExtractValuesToPoints(in_point_features, 
                            in_raster, 
                            out_point_features)

def process_elev_data(points_fc_with_elev, edges_fc):
    # Load in points feature class with new elevation field
    print "Loading feature class data to NumPy, may take a while to process" 
    elevation_shp = arcpy.da.FeatureClassToNumPyArray(points_fc_with_elev,
                                                        ('RASTERVALU','PSRCEdgeID'))

    # Load results into a dataframe for quicker calcs
    df = pd.DataFrame(elevation_shp)

    # We also need edge length, so we have to load in the edges feature class ClassName(object):
    edges = arcpy.da.FeatureClassToNumPyArray(edges_fc, ('PSRCEdgeID', 'NewINode', 'NewJNode', 'ActiveLink', 'FacilityTy', 'Fullname', 'Direction', 'Shape_Length'))
    edges_df = pd.DataFrame(edges)

    # Merge the two dfs
    df = df.merge(edges_df)

    # Get the length
    df['edgeID']= df['PSRCEdgeID']
    length = df.groupby('PSRCEdgeID').min()[['Shape_Length','edgeID']]

    # Get a list of all unique Edge IDs
    edges = df.groupby('PSRCEdgeID').mean().index

    # Calculate upslope for all edges
    # Loop through all edges
    counter = 0
    upslope_ij = {}
    upslope_ji = {}
    for edge in edges: # Replace [1] with edges when ready to loop over everything
        print counter
        edge_df = df.query("PSRCEdgeID == " + str(edge))
        # Extract the elevation data to numPy because it's faster to loop over
        elev_data = edge_df['RASTERVALU'].values
        # Loop through each point in each edge
        upslope_ij[edge] = 0
        upslope_ji[edge] = 0
        for point in xrange(len(elev_data)-1):  # stop short of the list because we only want to compare the 2nd to last to last
            elev_diff = elev_data[point+1] - elev_data[point]
            if elev_diff > 0:
                upslope_ij[edge] += elev_diff
            elif elev_diff < 0:
                upslope_ji[edge] += abs(elev_diff)      # since we know it will be "negative" for the JI direction when calculated
                                                        # in references to the IJ direction
        counter +=1

    # Import dictionary to a series and attach upslope back on the original dataframe
    upslope_ij_s = pd.Series(upslope_ij, name='elev_gain_ij')
    upslope_ji_s = pd.Series(upslope_ji, name='elev_gain_ji')
    upslope_ij_s.index.name='edgeID'
    upslope_ij_s = upslope_ij_s.reset_index()
    upslope_ji_s.index.name='edgeID'
    upslope_ji_s = upslope_ji_s.reset_index()

    # Combine series to a dataframe
    newdf = upslope_ij_s.merge(upslope_ji_s)

    # add in edge length to df
    newdf = newdf.merge(length)

    # Calcualte the average upslope 
    # Calcualte the average upslope 
    newdf['avg_upslope_ij'] = newdf['elev_gain_ij']/newdf['Shape_Length']
    newdf['avg_upslope_ji'] = newdf['elev_gain_ji']/newdf['Shape_Length']

    # Join other attributes to the df
    newdf = newdf.merge(edges_df, left_on='edgeID', right_on='PSRCEdgeID')

    # Write results to csv
    newdf.to_csv('slope_output.csv')

def write_emme_attr():
    ''' Write network attributes for elevation gain and bike attributes for use in Emme '''

    # Read in bicycle attribute table
    bike_attr = r'D:\slope\slope921.gdb\tblBikeAttributes'

    # Note that we can't have null fields- need to update the gdb to ensure this
    bike_np = arcpy.da.TableToNumPyArray(bike_attr, ('PSRCEdgeID', 'IJBikeFacil', 'JIBikeFacil'))
    bike_df = pd.DataFrame(bike_np)

    # Load in elevation data from edges dataframe results
    edge_df = pd.read_csv('slope_output.csv')

    # Merge the bike data with the elevation data based on edge ID 
    total_merge = edge_df.merge(bike_df)

def main(run_split_edges, run_process_elev_data, run_join_elev_data):

    # Work within a file gdb
    arcpy.env.workspace = r'D:\slope\slope921.gdb'

    # Edges shapefile
    # in_fc = r"D:\slope\test.gdb\edges_0"
    in_fc = r"D:\slope\slope921.gdb\edges_0"
    output_fc = r'\edges_0_test6'

    sr = arcpy.Describe(in_fc).spatialReference
    
    # Split edges into tuple of points and create a feature class of results
    if run_split_edges:
        point_results= split_edges(in_fc, spatial_reference=sr, fields=["SHAPE@",'PSRCEdgeID'], 
                                    segment_len=10, )

        create_points_fc(point_results=point_results, out_path=r'D:\slope\slope921.gdb',
                         out_name=output_fc, spatial_reference=sr)

    if run_join_elev_data:
        print 'joining large number of points to elevation data'
        print 'process will take several minutes'
        join_elev_data( in_point_features=output_fc, 
                        in_raster='PSRC30ft11', 
                        out_point_features='edges_0_with_elev9')

    if run_process_elev_data:
        process_elev_data(points_fc_with_elev=r"D:\slope\slope921.gdb\edges_0_with_elev9", 
            edges_fc=r"D:\slope\slope921.gdb\edges_0")


if __name__ == "__main__":
    main(run_split_edges=False,
         run_join_elev_data=True,
         run_process_elev_data=True)

