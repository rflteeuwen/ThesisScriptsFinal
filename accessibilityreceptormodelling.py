#ACCESSIBILITY
##Indicator5WasteCollectionModelling=group
##WasteCollectionFromReceptor=name

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
##housescollectionimpact=output vector


#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#VARIABLES
global_mode = 2 #mode1=boolean; mode2=level; mode3=levelnetworkdistance
global_wastebringingfrequency = 2 # number of times waste is brought from house to container per week
global_yearlydistance = 29100.0 # yearly walking distance in meters
global_yearlywaste = 92.0 # kg per inhabitant
global_peoplehouse = 5.0
global_peoplecontainer = 500.0
global_rhoorganicwaste = 400.0 # 400 kg / m3
global_containersize = 4 # 4 m3
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
    if d > maxd:
        return 0.0
    else:
        return (maxd - d) / maxd

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
        
def findAverage(layer, i):
    sumvalue = 0.0
    count = 0.0
    for feature in layer.getFeatures():
        attrs = feature.attributes()
        if attrs[i]:
            sumvalue = sumvalue + attrs[i]
            count = count + 1.0
    return sumvalue/count



#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#RECEPTORBASEDMODELLING

#1. is a container accessible...?
if global_mode < 4:
    
    if global_mode < 3:
        
        print "euclidean"
    
        outputs_QGISFIELDCALCULATOR_1=processing.runalg('qgis:fieldcalculator', containers,'joincat2',2,10.0,3.0,True,'to_string(@row_number)',None)
    
        outputs_QGISDISTANCETONEARESTHUB_1=processing.runalg('qgis:distancetonearesthub', houses,outputs_QGISFIELDCALCULATOR_1['OUTPUT_LAYER'],'joincat2',0,0,housescollectionimpact)
        
    #3. network distance instead of euclidean distance
    elif global_mode == 3:
        
        print "network distance"
        
        #sample points
        sample = 10
        outputs_QGISRANDOMPOINTSINLAYERBOUNDS_1=processing.runalg('qgis:randompointsinlayerbounds', houses,sample,50.0,None)
        
        #all houses to points
        outputs_QGISPOLYGONCENTROIDS_2=processing.runalg('qgis:polygoncentroids', houses,None)
        
        #network distance
        outputs_GRASS7VNETDISTANCE_1=processing.runalg('grass7:v.net.distance', roads,outputs_QGISPOLYGONCENTROIDS_2['OUTPUT_LAYER'],containers,50.0,0,None,None,0,None,None,None,None,None,False,parameterextent,-1.0,0.0001,0,None)
        
        outputs_QGISJOINATTRIBUTESBYLOCATION_1=processing.runalg('qgis:joinattributesbylocation', outputs_QGISPOLYGONCENTROIDS_2['OUTPUT_LAYER'],outputs_GRASS7VNETDISTANCE_1['output'],['touches'],50.0,0,'sum,mean,min,max,median',0,housescollectionimpact)
    
    layer = getLayer(housescollectionimpact)
    iPeople = layer.fieldNameIndex('a_inhabita')
    if global_mode < 3:
        iHubDist = layer.fieldNameIndex('HubDist')
    elif global_mode == 3:
        iHubDist = layer.fieldNameIndex('dist')
    
    layer.dataProvider().addAttributes([QgsField("TotalMass", QVariant.Double), QgsField("fIntensity", QVariant.Double),QgsField("Impact", QVariant.Double)])
    layer.updateFields()
    
    iTotalMass = layer.fieldNameIndex('TotalMass')
    iFIntensity = layer.fieldNameIndex('fIntensity')
    iFImpact= layer.fieldNameIndex('Impact')
    
    layer.startEditing()
    
    maxMass = (global_yearlywaste / 26.0) * 2.0 * findAverage(layer, iPeople)

    for feature in layer.getFeatures():
            
        attrs = feature.attributes()
            
        # intensity factor
        n = attrs[iPeople]
        d = attrs[iHubDist]
        nfloat = float(n)
        #1. is a container accessible?
        if global_mode == 1:
            A = booleanaccessibility(d)
            Afloat = float(A)
        #2. how well is a container accessible...?
        elif global_mode == 2:
            A = accessibility(d)
            Afloat = float(A)
        #3. network distance
        elif global_mode == 3:
            A = accessibility(d)
            Afloat = float(A)
        TotalMass = wastemass(Afloat, nfloat, default_willingness)
        FIntensity = normalise(TotalMass, 0.0, maxMass)
        layer.changeAttributeValue(feature.id(), iTotalMass, TotalMass)
        layer.changeAttributeValue(feature.id(), iFIntensity, FIntensity)
            
        #impact
        Impact = FIntensity
        layer.changeAttributeValue(feature.id(), iFImpact, Impact)
        
    layer.commitChanges()

else:
    
    print "unknown mode"

