##ThesisScenarios=group
##spatialScenarios=name

#make sure that a grass mapset is opened! and that all necessary layers are switched on

#INPUTS VIA PROMPT
##roads=vector
##containers=vector
#OUTPUTS VIA PROMPT
##containersinsequence=output vector
##routeinsequence=output vector


#IMPORTS
from qgis.core import * 
import processing

#set extent parameters for GRASS
layerforextent = QgsVectorLayer(roads, 'LayerForExtent', 'ogr')
extent = layerforextent.extent()
xmin = extent.xMinimum()
xmax = extent.xMaximum()
ymin = extent.yMinimum()
ymax = extent.yMaximum()
parameterextent = "%f,%f,%f,%f" %(xmin, xmax, ymin, ymax)

# define category for containers to join them later on
outputs_QGISFIELDCALCULATOR_2=processing.runalg('qgis:fieldcalculator', containers,'joincat',2,10.0,3.0,True,'to_string(@row_number)',None)
print 1

#calculate length of road segments
outputs_QGISFIELDCALCULATOR_6=processing.runalg('qgis:fieldcalculator', roads,'roadlength',0,10.0,3.0,True,'$length',None)
print 2

# calculate costs based on speed and length
outputs_QGISADVANCEDPYTHONFIELDCALCULATOR_1=processing.runalg('qgis:advancedpythonfieldcalculator', outputs_QGISFIELDCALCULATOR_6['OUTPUT_LAYER'],'roadcost',1,10.0,3.0,'def calcSeconds(length, speed):\n	if speed == 0.0:\n		speed = 1.0\n	return ((length / 1000.0)/ speed) * 60.0 * 60.0\n\ndef getCost(length, speedab, speedba):\n	if speedab: \n		return calcSeconds(length, speedab)\n	elif speedba: \n		return calcSeconds(length, speedba)\n	else:\n		return calcSeconds(length, 1.0)','value = getCost(<roadlength>, <SPEEDAB_2>, <SPEEDBA_2>)',None)
print 3

# run grass salesman algorithm to calculate fastest route along all containers
outputs_GRASSSALESMAN_1=processing.runalg('grass7:v.net.salesman', outputs_QGISADVANCEDPYTHONFIELDCALCULATOR_1['OUTPUT_LAYER'],outputs_QGISFIELDCALCULATOR_2['OUTPUT_LAYER'],50.0,2,'1-10000','roadcost',None,False,parameterextent,-1.0,0.0001,0,None,None)
print 4

#join salesman outcome (table with containers in sequence) with containers based on join category defined earlier
outputs_QGISJOINATTRIBUTESTABLE_1=processing.runalg('qgis:joinattributestable', outputs_QGISFIELDCALCULATOR_2['OUTPUT_LAYER'],outputs_GRASSSALESMAN_1['sequence'],'joincat','category',containersinsequence)
print 5

# join salesman routes with roads with costs attribute
outputs_QGISJOINATTRIBUTESBYLOCATION_1=processing.runalg('qgis:joinattributesbylocation', outputs_GRASSSALESMAN_1['output'],outputs_QGISADVANCEDPYTHONFIELDCALCULATOR_1['OUTPUT_LAYER'],['intersects'],0.1,0,'sum,mean,min,max,median',0,None)
print 6

# calculate sequence of route segments based on row numbers resulting from grass salesman
outputs_QGISFIELDCALCULATOR_4=processing.runalg('qgis:fieldcalculator', outputs_QGISJOINATTRIBUTESBYLOCATION_1['OUTPUT'],'sequence',1,10.0,3.0,True,'@row_number',None)
print 7

# calculate length of all segments in routes
outputs_QGISFIELDCALCULATOR_5=processing.runalg('qgis:fieldcalculator', outputs_QGISFIELDCALCULATOR_4['OUTPUT_LAYER'],'mylength',0,10.0,3.0,True,'$length',None)
print 8

# calculate costs based on speed and length
outputs_QGISADVANCEDPYTHONFIELDCALCULATOR_2=processing.runalg('qgis:advancedpythonfieldcalculator', outputs_QGISFIELDCALCULATOR_5['OUTPUT_LAYER'],'mycost',1,10.0,3.0,'def calcSeconds(length, speed):\n	if speed == 0.0:\n		speed = 1\n	return ((length / 1000.0) / speed) * 60.0 * 60.0\n\ndef getCost(length, speedab, speedba):\n	if speedab: \n		return calcSeconds(length, speedab)\n	elif speedba: \n		return calcSeconds(length, speedba)\n	else:\n		return calcSeconds(length, 1.0)','value = getCost(<mylength>, <SPEEDAB_2>, <SPEEDBA_2>)',routeinsequence)
print 9, "done"


