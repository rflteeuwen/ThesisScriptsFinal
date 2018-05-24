#ACCESSIBILITY
##Indicator5WasteCollectionModelling=group
##WasteCollectionFromSource=name

#IMPORTS
from qgis.core import *
from PyQt4.QtCore import *
import processing
import math

#set extent parameters for GRASS
layerforextent = QgsVectorLayer(roads, 'LayerForExtent', 'ogr')
extent = layerforextent.extent()
xmin = extent.xMinimum()
xmax = extent.xMaximum()
ymin = extent.yMinimum()
ymax = extent.yMaximum()
parameterextent = "%f,%f,%f,%f" %(xmin, xmax, ymin, ymax)

#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#INPUT AND OUTPUT
##houses=vector polygon
##containers=vector point
##roads=vector line
##containerscollectionimpact=output vector
##collectionbuffer=output vector
##intermediate=output vector


#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#VARIABLES
global_mode = 1#mode1=boolean; mode3=networkboolean
global_wastebringingfrequency = 2 # number of times waste is brought from house to container per week
global_yearlydistance = 29100.0 # yearly walking distance in meters
global_yearlywaste = 92.0 # kg per inhabitant
global_peoplehouse = 5.0
global_peoplecontainer = 500.0
global_rhoorganicwaste = 400.0 # 400 kg / m3
global_containersize = 4 # 5 m31
global_fullnessrate = 1 # fill up container up to 100%
default_willingness = 0.3
default_minimumwillingness = 0.1
default_maximumwillingness = 0.5


#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#FORMULAS
def maxdistance():
    maxd = global_yearlydistance / (52.0 * 2.0 * global_wastebringingfrequency)
    return maxd + 10.0

def accessibility(d):
    maxd = maxdistance()
    A = (maxd - d) / maxd
    return A

def wastemass(A, n, f):
    M = A * global_yearlywaste/26.0 * n * f
    return M
    
def booleanaccessibility(d):
    if d <= maxdistance():
        return True
    else:
        return False

def getLayer(mylayer):
    return QgsVectorLayer(mylayer, 'mylayer', 'ogr')
    
def normalise(value, lower, upper):
    if value > upper:
        return 1.0
    elif value < lower:
        return 0.0
    else:
        return ((float(value) - float(lower))/(float(upper) - float(lower)))
    
def aggregate(I, wI, T, wT, P, wP, compensationmode):
    if compensationmode == "nocompensation":
        return I**wI * T**wT * P**wP
    elif compensationmode == "fullcompensation":
        return (I * wI + T * wT + P * wP) / (wI + wT + wP)
    else:
        print "unknown mode"
        return -1




#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#SOURCEBASEDMODELLING

#1. how many have access...?
if global_mode < 4:
#if global_mode == 9:
    
    r = maxdistance()
    
    outputs_QGISFIELDCALCULATOR_1=processing.runalg('qgis:fieldcalculator', containers,'joincat2',2,10.0,3.0,True,'to_string(@row_number)',None)
    
    if global_mode == 1:
    
        # spatially model intensity
        outputs_QGISFIXEDDISTANCEBUFFER_1=processing.runalg('qgis:fixeddistancebuffer', outputs_QGISFIELDCALCULATOR_1['OUTPUT_LAYER'],r,20.0,False,collectionbuffer)
        outputs_QGISPOLYGONCENTROIDS_1=processing.runalg('qgis:polygoncentroids', houses,None)
        
        # spatially model people and assign to containers
        outputs_QGISCOUNTPOINTSINPOLYGONWEIGHTED_1=processing.runalg('qgis:countpointsinpolygonweighted', outputs_QGISFIXEDDISTANCEBUFFER_1['OUTPUT'],outputs_QGISPOLYGONCENTROIDS_1['OUTPUT_LAYER'],'a_inhabita','nrpeople',None)
        outputs_QGISJOINATTRIBUTESTABLE_1=processing.runalg('qgis:joinattributestable', outputs_QGISFIELDCALCULATOR_1['OUTPUT_LAYER'],outputs_QGISCOUNTPOINTSINPOLYGONWEIGHTED_1['OUTPUT'],'joincat2','joincat2',containerscollectionimpact)
        
    elif global_mode == 3:
        
        # connect containers to roads
        outputs_GRASS7VNETCONNECT_1=processing.runalg('grass7:v.net.connect', roads,containers,50.0,False,parameterextent,-1.0,0.0001,0,None)
        outputs_GRASS7VNETISO_1=processing.runalg('grass7:v.net.iso', outputs_GRASS7VNETCONNECT_1['output'],containers,50.0,2,'1-100000','140,280',None,None,None,False,parameterextent,-1.0,0.0001,0,None) # r as a number, not a parameter, change if possible
        outputs_QGISEXTRACTBYATTRIBUTE_1=processing.runalg('qgis:extractbyattribute', outputs_GRASS7VNETISO_1['output'],'cat',0,'1',None)
        outputs_SAGACONVERTLINESTOPOINTS_1=processing.runalg('saga:convertlinestopoints', outputs_QGISEXTRACTBYATTRIBUTE_1['OUTPUT'],True,1.0,intermediate)
        outputs_QGISCONCAVEHULL_1=processing.runalg('qgis:concavehull', outputs_SAGACONVERTLINESTOPOINTS_1['POINTS'],0.1,True,True,None)
        outputs_QGISFIXEDDISTANCEBUFFER_1=processing.runalg('qgis:fixeddistancebuffer', outputs_QGISCONCAVEHULL_1['OUTPUT'],10.0,20.0,False,collectionbuffer)
        
        
        outputs_QGISJOINATTRIBUTESBYLOCATION_1=processing.runalg('qgis:joinattributesbylocation', outputs_QGISFIXEDDISTANCEBUFFER_1['OUTPUT'],houses,['intersects'],0.0,1,'sum',0,None)
        outputs_QGISPOLYGONCENTROIDS_1=processing.runalg('qgis:polygoncentroids', outputs_QGISJOINATTRIBUTESBYLOCATION_1['OUTPUT'],None)
        outputs_QGISJOINATTRIBUTESBYLOCATION_2=processing.runalg('qgis:joinattributesbylocation', containers,outputs_QGISPOLYGONCENTROIDS_1['OUTPUT_LAYER'],['equals'],50.0,0,'sum,mean,min,max,median',0,containerscollectionimpact)      

    layer = getLayer(containerscollectionimpact)
    
    layer.dataProvider().addAttributes([QgsField("TotalMass", QVariant.Double), QgsField("fIntensity", QVariant.Double),QgsField("Impact", QVariant.Double)])
    layer.updateFields()
    
    iTotalMass = layer.fieldNameIndex('TotalMass')
    iFIntensity = layer.fieldNameIndex('fIntensity')
    iFrequency = layer.fieldNameIndex('frequency')
    iFImpact= layer.fieldNameIndex('Impact')
    if global_mode == 1:
        iPeople = layer.fieldNameIndex('nrpeople')
    if global_mode == 3:
        iPeople = layer.fieldNameIndex('suma_Inhab')
    
    layer.startEditing()
    
    maxMass = global_rhoorganicwaste * global_containersize * global_fullnessrate

    for feature in layer.getFeatures():
            
        attrs = feature.attributes()
            
        # intensity factor
        n = attrs[iPeople]
        f = attrs[iFrequency]
        nfloat = float(n)
        ffloat = float(f)
        #1. is a container accessible?
        #2. how well is a container accessible...?
        A = 1.0
        TotalMass = wastemass(A, nfloat, default_willingness)
        maxMassFreq = maxMass * ffloat
        FIntensity = normalise(TotalMass, 0.0, maxMassFreq)
        layer.changeAttributeValue(feature.id(), iTotalMass, TotalMass)
        layer.changeAttributeValue(feature.id(), iFIntensity, FIntensity)
            
        #impact
        Impact = FIntensity
        layer.changeAttributeValue(feature.id(), iFImpact, Impact)
        
    layer.commitChanges()

#2. how many have access at what level...?


#3. network distance instead of euclidean distance


#4. willingness variable with density

