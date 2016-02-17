# This is a separate script because it needs to be run with
# a 32-bit python install

import arcpy
import os, sys

outMxd = 'results.mxd'

tempPath = sys.path[0]
wrkspc = os.getcwd()
mapDoc = arcpy.mapping.MapDocument(wrkspc + r'//' + outMxd)

# con = wrkspc + '/connections/arcgis on myserver_6080 (publisher).ags'
con = r'GIS Servers\arcgis on webmap_6080 (publisher)'

# Provide other service details
service = 'newResults6'
sddraft =  wrkspc + "/tempdraf6.sddraft"
sd = wrkspc + '/' + service + ".sd"
summary = 'Test map'
tags = 'Test'

# Create service definition draft
arcpy.mapping.CreateMapSDDraft(map_document=mapDoc, 
                               out_sddraft=sddraft, 
                               service_name=service, 
                               server_type='ARCGIS_SERVER', 
                               connection_file_path=None,
                               copy_data_to_server=True, 
                               folder_name=None, 
                               summary=summary, 
                               tags=tags)

# Analyze the service definition draft
analysis = arcpy.mapping.AnalyzeForSD(sddraft)

# Print errors, warnings, and messages returned from the analysis
print "The following information was returned during analysis of the MXD:"
for key in ('messages', 'warnings', 'errors'):
  print '----' + key.upper() + '---'
  vars = analysis[key]
  for ((message, code), layerlist) in vars.iteritems():
    print '    ', message, ' (CODE %i)' % code
    print '       applies to:',
    for layer in layerlist:
        print layer.name,
    print

# Stage and upload the service if the sddraft analysis did not contain errors
if analysis['errors'] == {}:
    # Execute StageService. This creates the service definition.
    arcpy.StageService_server(sddraft, sd)

    # Execute UploadServiceDefinition. This uploads the service definition and publishes the service.
    arcpy.UploadServiceDefinition_server(sd, con)
    print "Service successfully published"
else: 
    print "Service could not be published because errors were found during analysis."

print arcpy.GetMessages()