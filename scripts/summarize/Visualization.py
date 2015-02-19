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

import sys
import os.path
sys.path.append("C:\\Program Files (x86)\\ArcGIS\\Desktop10.2\\bin")
sys.path.append("C:\\Program Files (x86)\\ArcGIS\\Desktop10.2\\arcpy")
sys.path.append("C:\\Program Files (x86)\\ArcGIS\\Desktop10.2\\AcrToolbox\\Scripts")

import arcpy
from arcpy import env
import subprocess

'''
def run():
    run_R ='"C:/Program Files/R/R-3.0.2/bin/R.exe" --max-mem-size=50000M CMD Sweave --pdf ' + "D:/Visualization/test.r"
    run_R ='"C:/Program Files/R/R-3.0.2/bin/R.exe" --max-mem-size=50000M CMD' + "D:/Visualization/test.r"

    returncode = subprocess.call(run_R)
    
run()
'''


RunPath = "."
env.workspace = RunPath
env.qualifiedFieldNames = False


def MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable):
    ####Before all the steps, check whether the outputdataset and outputlayer exists or not
    if arcpy.Exists(outputdataset):
        arcpy.Delete_management(outputdataset)
    if arcpy.Exists(outputlayer):
        arcpy.Delete_management(outputlayer)
    #Add Join on "District.shp", then export data
    try:
        layer = lyrname
        inputdataset = "shpInputs/Taz.shp"
        InField = "TAZ"
        JoinField = "TAZ"
        arcpy.MakeFeatureLayer_management(inputdataset, layer)
        arcpy.AddJoin_management(layer, InField, JoinTable, JoinField)
        arcpy.CopyFeatures_management(layer, outputdataset)
        arcpy.Delete_management(layer)
    except Exception, e:
        print "Fail in AddJoin!"
        print e
        return
    #Add Field, Calculate Field, Delete Unnecessary Fields
    #try:
    #    #Add Field
    #    FieldName = "NScaled"
    #    FieldType = "Float"
    #    arcpy.AddField_management(outputdataset, FieldName, FieldType)
    #    #Calculate Field
    #    Expression = "!" + ClassifyField + "!"
    #    arcpy.CalculateField_management(outputdataset, FieldName, Expression, "PYTHON_9.3")
    #    #Delete Unnecessary Fields
    #    DropField = ["NoName", "TAZ_1"]
    #    arcpy.DeleteField_management(outputdataset, DropField)
    #except Exception, e:
    #    print "Fail in Add, Calculate, or Delete Field!"
    #    print e
    #    return

    #output the layer as a map
    try:
        arcpy.MakeFeatureLayer_management(outputdataset, layer)
        arcpy.SaveToLayerFile_management(layer, outputlayer)
        arcpy.Delete_management(layer)
    except Exception, e:
        print "Fail in SaveToLayerFile!"
        print e
        return
    #change the symbology, using quantile classification methods to visualize the result
    #apply symbology from another layer
    try:
        arcpy.ApplySymbologyFromLayer_management(outputlayer, SymbologyLayer)
        
    except Exception, e:
        print "Fail in ApplySymbologyFromLayer!"
        print e
        return

layers = []
titles = []
inputdir = "shpInputs/"
outputdir = "shpOutputs/"

data = "VMTPerPerson_hhtaz"
lyrname = "VMT Per Person(miles)"
ClassifyField = "VMTPPS"
SymbologyLayer = inputdir + "VMTSymbology.lyr"
outputdataset = outputdir + data + ".shp"
outputlayer = outputdir + data + ".lyr"
JoinTable = RunPath + "/tables/" + data + ".csv"
MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable)
layers.append(outputlayer)
titles.append("Average VMT Per Capita By Residence")

data = "VMTPerPerson_pwtaz"
lyrname = "VMT Per Person(miles)"
ClassifyField = "VMTPPS"
SymbologyLayer = inputdir + "VMTSymbology2.lyr"
outputdataset = outputdir + data + ".shp"
outputlayer = outputdir + data + ".lyr"
JoinTable = RunPath + "/tables/" + data + ".csv"
MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable)
layers.append(outputlayer)
titles.append("Average VMT Per Capita By Work")


data = "work_commute_dist_by_hhtaz"
lyrname = "Work Commute Distance(miles)"
ClassifyField = "CDIST"
SymbologyLayer = inputdir + "work_commute_distance_Symbology.lyr"
outputdataset = outputdir + data + ".shp"
outputlayer = outputdir + data + ".lyr"
JoinTable = RunPath + "/tables/" + data + ".csv"
MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable)
titles.append("Work Commute Distance By Residence")
layers.append(outputlayer)

data = "work_commute_dist_by_pwtaz"
lyrname = "Work Commute Distance(miles)"
ClassifyField = "CDIST"
SymbologyLayer = inputdir + "work_commute_distance_Symbology.lyr"
outputdataset = outputdir + data + ".shp"
outputlayer = outputdir + data + ".lyr"
JoinTable = RunPath + "/tables/" + data + ".csv"
MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable)
titles.append("Work Commute Distance By Work")
layers.append(outputlayer)

data = "school_commute_dist_by_hhtaz"
lyrname = "School Commute Distance(miles)"
ClassifyField = "CDIST"
SymbologyLayer = inputdir + "school_commute_distance_Symbology.lyr"
outputdataset = outputdir + data + ".shp"
outputlayer = outputdir + data + ".lyr"
JoinTable = RunPath + "/tables/" + data + ".csv"
MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable)
titles.append("School Commute Distance By Residence")
layers.append(outputlayer)

data = "school_commute_dist_by_pstaz"
lyrname = "School Commute Distance(miles)"
ClassifyField = "CDIST"
SymbologyLayer = inputdir + "school_commute_distance_Symbology.lyr"
outputdataset = outputdir + data + ".shp"
outputlayer = outputdir + data + ".lyr"
JoinTable = RunPath + "/tables/" + data + ".csv"
MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable)
titles.append("School Commute Distance By School")
layers.append(outputlayer)

data = "home_Based_Tour_modeShare_taz"
lyrname = "SOV Mode Share"
ClassifyField = "SOV"
SymbologyLayer = inputdir + "SOV_modeshare_Symbology.lyr"
outputdataset = outputdir + "home_Based_SOV_modeShare_taz.shp"
outputlayer = outputdir + "home_Based_SOV_modeShare_taz.lyr"
JoinTable = RunPath + "/tables/" + data + ".csv"
MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable)
titles.append("Home-Based SOV Mode Share By Residence")
layers.append(outputlayer)


lyrname = "HOV Mode Share"
ClassifyField = "HOV"
SymbologyLayer = inputdir + "HOV_modeshare_Symbology.lyr"
outputdataset = outputdir + "home_Based_HOV_modeShare_taz.shp"
outputlayer = outputdir + "home_Based_HOV_modeShare_taz.lyr"
MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable)
titles.append("Home-Based HOV Mode Share By Residence")
layers.append(outputlayer)


lyrname = "Transit Mode Share"
ClassifyField = "transit"
SymbologyLayer = inputdir + "transit_modeshare_Symbology.lyr"
outputdataset = outputdir + "home_Based_transit_modeShare_taz.shp"
outputlayer = outputdir + "home_Based_transit_modeShare_taz.lyr"
MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable)
titles.append("Home-Based Transit Mode Share By Residence")
layers.append(outputlayer)


lyrname = "Walk Mode Share"
ClassifyField = "walk"
SymbologyLayer = inputdir + "walk_modeshare_Symbology.lyr"
outputdataset = outputdir + "home_Based_walk_modeShare_taz.shp"
outputlayer = outputdir + "home_Based_walk_modeShare_taz.lyr"
MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable)
titles.append("Home-Based Walk Mode Share By Residence")
layers.append(outputlayer)

lyrname = "Bike Mode Share"
ClassifyField = "bike"
SymbologyLayer = inputdir + "bike_modeshare_Symbology.lyr"
outputdataset = outputdir + "home_Based_bike_modeShare_taz.shp"
outputlayer = outputdir + "home_Based_bike_modeShare_taz.lyr"
MakeTazMaps(data, lyrname, outputdataset, outputlayer, JoinTable)
titles.append("Home-Based Bike Mode Share By Residence")
layers.append(outputlayer)




mxd = arcpy.mapping.MapDocument(RunPath + "/Map_PugetSound.mxd")
df = arcpy.mapping.ListDataFrames(mxd)[0]
pdfPath = RunPath + "/maps/PugetSound.pdf"
if os.path.isfile(pdfPath):
        os.remove(pdfPath)
pdfDoc = arcpy.mapping.PDFDocumentCreate(pdfPath)

for i in range(0,len(layers)):
    addLayer = arcpy.mapping.Layer(RunPath + "/" + layers[i])
    waterLayer = arcpy.mapping.ListLayers(mxd, "", df)[0]
    arcpy.mapping.InsertLayer(df,waterLayer,addLayer,"AFTER")
    #arcpy.mapping.AddLayer(df, addLayer, "AUTO_ARRANGE")
    outputpdf = RunPath + "/maps/" + str(i) + ".pdf"
    if os.path.isfile(outputpdf):
        os.remove(outputpdf)
    #check if file exists
    arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")[0].text = titles[i]
    arcpy.mapping.ExportToPDF(mxd, outputpdf)
    pdfDoc.appendPages(outputpdf)
    arcpy.mapping.RemoveLayer(df, arcpy.mapping.ListLayers(mxd,"",df)[1])
pdfDoc.saveAndClose()

for i in range(0,len(layers)):
    outputpdf = RunPath + "/maps/" + str(i) + ".pdf"
    if os.path.isfile(outputpdf):
        os.remove(outputpdf)



mxd = arcpy.mapping.MapDocument(RunPath + "/Map_Part.mxd")
df = arcpy.mapping.ListDataFrames(mxd)[0]
pdfPath = RunPath + "/maps/Part.pdf"
if os.path.isfile(pdfPath):
        os.remove(pdfPath)
pdfDoc = arcpy.mapping.PDFDocumentCreate(pdfPath)

for i in range(0,len(layers)):
    addLayer = arcpy.mapping.Layer(RunPath + "/" + layers[i])
    waterLayer = arcpy.mapping.ListLayers(mxd, "", df)[0]
    arcpy.mapping.InsertLayer(df,waterLayer,addLayer,"AFTER")
    #arcpy.mapping.AddLayer(df, addLayer, "AUTO_ARRANGE")
    outputpdf = RunPath + "/maps/" + str(i) + "_part.pdf"
    if os.path.isfile(outputpdf):
        os.remove(outputpdf)
    #check if file exists
    arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")[0].text = titles[i]
    arcpy.mapping.ExportToPDF(mxd, outputpdf)
    pdfDoc.appendPages(outputpdf)
    arcpy.mapping.RemoveLayer(df, arcpy.mapping.ListLayers(mxd,"",df)[1])
pdfDoc.saveAndClose()

for i in range(0,len(layers)):
    outputpdf = RunPath + "/maps/" + str(i) + "_part.pdf"
    if os.path.isfile(outputpdf):
        os.remove(outputpdf)


mxd = arcpy.mapping.MapDocument(RunPath + "/Map_Seattle.mxd")
df = arcpy.mapping.ListDataFrames(mxd)[0]
pdfPath = RunPath + "/maps/Seattle.pdf"
if os.path.isfile(pdfPath):
        os.remove(pdfPath)
pdfDoc = arcpy.mapping.PDFDocumentCreate(pdfPath)

for i in range(0,len(layers)):
    addLayer = arcpy.mapping.Layer(RunPath + "/" + layers[i])
    waterLayer = arcpy.mapping.ListLayers(mxd, "", df)[0]
    arcpy.mapping.InsertLayer(df,waterLayer,addLayer,"AFTER")
    #arcpy.mapping.AddLayer(df, addLayer, "AUTO_ARRANGE")
    outputpdf = RunPath + "/maps/" + str(i) + "_Seattle.pdf"
    if os.path.isfile(outputpdf):
        os.remove(outputpdf)
    #check if file exists
    arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT")[0].text = titles[i]
    arcpy.mapping.ExportToPDF(mxd, outputpdf)
    pdfDoc.appendPages(outputpdf)
    arcpy.mapping.RemoveLayer(df, arcpy.mapping.ListLayers(mxd,"",df)[1])
pdfDoc.saveAndClose()

for i in range(0,len(layers)):
    outputpdf = RunPath + "/maps/" + str(i) + "_Seattle.pdf"
    if os.path.isfile(outputpdf):
        os.remove(outputpdf)






















