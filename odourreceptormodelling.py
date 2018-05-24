#ODOUR
##Indicator2OdourModelling=group
##OdourFromReceptor=name

#IMPORTS
from qgis.core import *
from PyQt4.QtCore import *
import processing
import math
import datetime
from datetime import datetime, time, timedelta, date



#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#INPUT AND OUTPUT
##houses=vector polygon
##containers=vector point
##housesodourimpact=output vector


#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#VARIABLES
global_mode = 3 #mode1=boolean; mode3=level
global_C = 59.0 # OUe/s/m2 emitted odour of fresh waste
global_Cthres = 0.5
global_surface = 4.0 # m2 of emitting surfaceFormat
global_thr_people_house = 5.0
global_thr_people_container = 50.0

global_Vaverage = 48.2 # weighted average
global_Fnorth = 0.123 # wind direction frequency
global_Unorth = 36.0 # wind direction speed
global_Feast = 0.173 # wind direction frequency
global_Ueast = 36.0 # wind direction speed
global_Fsouth = 0.293 # wind direction frequency
global_Usouth = 51.0 # wind direction speed
global_Fwest = 0.411 # wind direction frequency
global_Uwest = 55.0 # wind direction speed




#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#FORMULAS
def odourcircle(Udirection):
    E = global_C * global_surface
    r = (E / (global_Cthres * math.pi * Udirection * 0.04422 ))**0.64255
    return r + 10.0
    
def booleanodour(d, r):
    if d <= r:
        return True
    else:
        return False

def odourlevel(d, Udirection):
    E = global_C * global_surface
    C = E / (math.pi * 0.04422 * d**1.5563 * Udirection )
    if C > E:
        return E
    else:
        return C
        
def todatetime(input):
    output = datetime.strptime(input, '%H:%M:%S').time()
    return output

def calculateLinearValue(t, t_0, t_1):
    if type(t) == int: # if integer (frequency)
        if t_0 < t_1:
            # if slope is positive
            dt = float(t_1 - t_0)
            value = float((t - t_0) * (1 / dt))
            return value
        else:
            return None
    elif isinstance(t, time): # if time(moment, duration)
        if t_0 < t_1:
            # if slope is positive
            dts = (datetime.combine(date.min, t_1) - datetime.combine(date.min, t_0)).total_seconds()
            t_0s = (t_0.hour * 60 + t_0.minute) * 60 + t_0.second
            ts = (t.hour * 60 + t.minute) * 60 + t.second
            value = (ts - t_0s) * (1 / dts)
            return value
        else:
            return None
    else:
        return None
        
def odourMoment(m):
    thr1 = time(12)
    thr2 = time(16)
    thr3 = time(22)
    if m <= thr1:
        return 0.5
    elif thr1 < m <= thr2:
        value = calculateLinearValue(m, thr1, thr2)
        return (value / 2) + 0.5
    elif thr2 < m <= thr3:
        return 1
    else:
        return 0.5
        
def odourDuration(d):
    thr1 = 10
    thr2 = 60
    thr3 = 480
    if d <= thr1:
        return 0
    elif thr1 < d <= thr2:
        value = calculateLinearValue(d, thr1, thr2)
        return value/2
    elif thr2 < d <= thr3:
        value = calculateLinearValue(d, thr2, thr3)
        return 0.5 + value/2
    else:
        return 1
    
def odourFrequency(f):
    thr1 = 0
    thr2 = 14
    if f < thr2:
        return calculateLinearValue(f, thr1, thr2)
    else:
        return 1

def odourTemporality(m, d, f):
    return (m * d * f) # no compensation allowed

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
    elif compensationmode == "fuzzymax":
        return bool(I) * bool(T) * bool(P) * max([I, T, P])
    elif compensationmode == "fuzzyavg":
        return bool(I) * bool(T) * bool(P) * (I * wI + T * wT + P * wP) / (wI + wT + wP)
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



#1. is noise present at ...?
#3. what is the odour level at...?
if global_mode == 1 or global_mode == 3 :

    r = odourcircle(global_Vaverage)
    
    outputs_QGISFIELDCALCULATOR_1=processing.runalg('qgis:fieldcalculator', containers,'joincat2',2,10.0,3.0,True,'to_string(@row_number)',None)
    
    # distance for Intensity Factor
    outputs_QGISDISTANCETONEARESTHUB_1=processing.runalg('qgis:distancetonearesthub', houses,outputs_QGISFIELDCALCULATOR_1['OUTPUT_LAYER'],'joincat2',0,0,None)
    
    # container joincat = house HubName to assign temporalities of closest container to house
    outputs_QGISJOINATTRIBUTESTABLE_1=processing.runalg('qgis:joinattributestable', outputs_QGISDISTANCETONEARESTHUB_1['OUTPUT'],outputs_QGISFIELDCALCULATOR_1['OUTPUT_LAYER'],'HubName','joincat2',None)
    
    # count number of containers in proximity for duration
    outputs_QGISFIXEDDISTANCEBUFFER_1=processing.runalg('qgis:fixeddistancebuffer', outputs_QGISJOINATTRIBUTESTABLE_1['OUTPUT_LAYER'],r,20.0,False,None)
    outputs_QGISCOUNTPOINTSINPOLYGON_1=processing.runalg('qgis:countpointsinpolygon', outputs_QGISFIXEDDISTANCEBUFFER_1['OUTPUT'],containers,'count_Cont',None)
    outputs_QGISJOINATTRIBUTESTABLE_2=processing.runalg('qgis:joinattributestable', outputs_QGISJOINATTRIBUTESTABLE_1['OUTPUT_LAYER'],outputs_QGISCOUNTPOINTSINPOLYGON_1['OUTPUT'],'a_cat','a_cat',housesodourimpact)
    
    # determine factors, normalise, aggregate
    layer = getLayer(housesodourimpact)
    iPeople = layer.fieldNameIndex('a_inhabita')
    iHubDist = layer.fieldNameIndex('HubDist')
    
    layer.dataProvider().addAttributes([QgsField("Hour", QVariant.Double),QgsField("fMoment", QVariant.Double),QgsField("fDuration", QVariant.Double),QgsField("fFrequency", QVariant.Double),QgsField("fIntensity", QVariant.Double),QgsField("fPeople", QVariant.Double),QgsField("fTemporal", QVariant.Double),QgsField("Impact", QVariant.Double)])
    layer.updateFields()
    
    iHour = layer.fieldNameIndex('Hour')
    iCountContainer = layer.fieldNameIndex('count_Cont')
    iFMoment = layer.fieldNameIndex('fMoment')
    iFDuration = layer.fieldNameIndex('fDuration')
    iFFrequency = layer.fieldNameIndex('fFrequency')
    iFIntensity = layer.fieldNameIndex('fIntensity')
    iFPeople = layer.fieldNameIndex('fPeople')
    iFTemporal = layer.fieldNameIndex('fTemporal')
    iFImpact= layer.fieldNameIndex('Impact')
    iMoment= layer.fieldNameIndex('moment')
    iDuration= layer.fieldNameIndex('duration')
    iFrequency= layer.fieldNameIndex('frequency')
    
    thr_people_house = 2.0 * findAverage(layer, iPeople)

    layer.startEditing()
    for feature in layer.getFeatures():
        
        attrs = feature.attributes()
    
        # intensity factor
        d = attrs[iHubDist]
        if global_mode == 1:
            Intensity = booleanodour(d, r)
            FIntensity = float(Intensity)
        elif global_mode == 3:
            Intensity = odourlevel(d, global_Vaverage)
            FIntensity = normalise(Intensity, global_Cthres, global_C)
        layer.changeAttributeValue(feature.id(), iFIntensity, FIntensity)
        
        #people factor
        nrpeople = attrs[iPeople]
        FPeople = normalise(nrpeople, 0.0, thr_people_house)
        layer.changeAttributeValue(feature.id(), iFPeople, FPeople)
        
        #temporal factor SHOULD BE EVALUATED AND CHANGED!!!
        moment = todatetime(attrs[iMoment])
        hour = moment.hour
        fmoment = odourMoment(moment)
        duration =  attrs[iDuration]
        newduration =  float(attrs[iDuration]) * attrs[iCountContainer]
        fduration = odourDuration(duration)
        frequency =  attrs[iFrequency]
        ffrequency = odourFrequency(frequency)
        FTemporal = odourTemporality(fmoment, fduration, ffrequency)
        layer.changeAttributeValue(feature.id(), iHour, hour)
        layer.changeAttributeValue(feature.id(), iFMoment, fmoment)
        layer.changeAttributeValue(feature.id(), iDuration, newduration)
        layer.changeAttributeValue(feature.id(), iFDuration, fduration)
        layer.changeAttributeValue(feature.id(), iFFrequency, ffrequency)
        layer.changeAttributeValue(feature.id(), iFTemporal, FTemporal)
        
        # impact
        Impact = aggregate(FIntensity, 1.0, FPeople, 1.0, FTemporal, 1.0, "fuzzyavg")
        layer.changeAttributeValue(feature.id(), iFImpact, Impact)
        
    layer.commitChanges()



#2. is odour present at... in direction...?
if global_mode == 2:
    
    print "direction"



#4. emitted odour variable with frequency of collection
if global_mode == 4:
    
    print "variable emission"
    
else:
    
    print "unknown mode"


