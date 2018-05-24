#NOISE
##Indicator1NoiseModelling=group
##NoiseFromSource=name


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
##containersnoiseimpact=output vector
##noisebuffer=output vector


#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#VARIABLES
global_mode = 1#mode1=boolean
global_E = 100.0                                                        #noise level of source
global_L = 70.0                                                        #noise nuisance threshold
global_c = 3.0                                                          #shading by building
global_maxshading = 9.0                                             #maximum shading
global_thr_people_house = 10.0
global_thr_people_container = 1000.0
default_rho = 0.02 #default value                          #building density


#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#FORMULAS
def noisecircle():
    D_building = 10.0**((global_E - global_L)/10.0) * default_rho * global_c
    if D_building > 9.0:
        D_building = 9.0
    r = 10.0**((global_E - global_L - D_building)/10.0)
    return r + 10.0
    
def booleannoise(d, r):
    if d <= r:
        return True
    else:
        return False

def noiselevel(d, rho):
    D_distance = 10.0 * math.log(d, 10.0)
    D_building = d * rho * global_c
    if D_building > 9.0:
        D_building = 9.0
    L_eq = global_E - D_distance - D_building
    return L_eq
    
def todatetime(input):
    output = datetime.strptime(input, '%H:%M:%S').time()
    return output

def calculateLinearValue(t, t_0, t_1):
    if type(t) == int: # if integer (frequency, duration)
        if t_0 < t_1:
            # if slope is positive
            dt = float(t_1 - t_0)
            value = float((t - t_0) * (1 / dt))
            return value
        else:
            return None
    elif isinstance(t, time): # if time(moment)
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
    
def noiseMoment(m):
    thr1 = time(7)
    thr2 = time(19)
    thr3 = time(23)
    if thr1 < m <= thr2: # day
        return 0.5
    elif thr2 < m <= thr3: # evening
        value = calculateLinearValue(m, thr2, thr3)
        return (value / 2) + 0.5
    else: # night
        return 1.0

def noiseDuration(d):
    thr1 = 0
    thr2 = 5
    if d < thr2:
        return calculateLinearValue(d, thr1, thr2)
    else:
        return 1

def noiseFrequency(f):
    thr1 = 0
    thr2 = 14
    if f < thr2:
        return calculateLinearValue(f, thr1, thr2)
    else:
        return 1

def noiseTemporality(m, d, f):
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
    
def findPeopleDensity(layer, i):
    Atotal = 0.0
    Ptotal = 0.0
    for feature in layer.getFeatures():
        attrs = feature.attributes()
        Af = feature.geometry().area()
        Atotal = Atotal + Af
        Pf = attrs[i]
        Ptotal = Ptotal + Pf
    print Atotal
    print Ptotal
    return Ptotal/Atotal
    

#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#SOURCEBASEDMODELLING

#1. how many are affected...?
if global_mode == 1:
    
    r = noisecircle()
    
    outputs_QGISFIELDCALCULATOR_1=processing.runalg('qgis:fieldcalculator', containers,'joincat2',2,10.0,3.0,True,'to_string(@row_number)',None)
    
    # spatially model intensity
    outputs_QGISFIXEDDISTANCEBUFFER_1=processing.runalg('qgis:fixeddistancebuffer', outputs_QGISFIELDCALCULATOR_1['OUTPUT_LAYER'],r,20.0,False,None)
    outputs_QGISPOLYGONCENTROIDS_1=processing.runalg('qgis:polygoncentroids', houses,None)
    
    # spatially model people and assign to containers
    outputs_QGISCONCAVEHULL_1=processing.runalg('qgis:concavehull', outputs_QGISPOLYGONCENTROIDS_1['OUTPUT_LAYER'],0.5,False,True,None)
    
    outputs_QGISCOUNTPOINTSINPOLYGONWEIGHTED_1=processing.runalg('qgis:countpointsinpolygonweighted', outputs_QGISFIXEDDISTANCEBUFFER_1['OUTPUT'],outputs_QGISPOLYGONCENTROIDS_1['OUTPUT_LAYER'],'a_inhabita','nrpeople',noisebuffer)
    
    outputs_QGISJOINATTRIBUTESTABLE_1=processing.runalg('qgis:joinattributestable', outputs_QGISFIELDCALCULATOR_1['OUTPUT_LAYER'],outputs_QGISCOUNTPOINTSINPOLYGONWEIGHTED_1['OUTPUT'],'joincat2','joincat2',containersnoiseimpact)
    
    # determine factors, normalise, aggregate
    layer = getLayer(containersnoiseimpact)
    iPeople = layer.fieldNameIndex('nrpeople')
    
    
    layer.dataProvider().addAttributes([QgsField("Hour", QVariant.Double),QgsField("fMoment", QVariant.Double),QgsField("fDuration", QVariant.Double),QgsField("fFrequency", QVariant.Double),QgsField("fIntensity", QVariant.Double),QgsField("fPeople", QVariant.Double),QgsField("fTemporal", QVariant.Double),QgsField("Impact", QVariant.Double)])
    layer.updateFields()
    
    iHour = layer.fieldNameIndex('Hour')
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
    
    outputs_QGISJOINATTRIBUTESBYLOCATION_1=processing.runalg('qgis:joinattributesbylocation', outputs_QGISCONCAVEHULL_1['OUTPUT'],houses,['intersects'],1,1,'sum',0,None)
    layerdensity = getLayer(outputs_QGISJOINATTRIBUTESBYLOCATION_1['OUTPUT'])
    iPeopleForHouses = layerdensity.fieldNameIndex('suma_Inhab')
    thr_people_container = findPeopleDensity(layerdensity, iPeopleForHouses) * 2.0 * math.pi * r * r
    print thr_people_container

    layer.startEditing()

    for feature in layer.getFeatures():
        
        attrs = feature.attributes()
        
        FIntensity = 1.0
        layer.changeAttributeValue(feature.id(), iFIntensity, FIntensity)
        
        nrpeople = attrs[iPeople]
        FPeople = normalise(nrpeople, 0.0, thr_people_container)
        layer.changeAttributeValue(feature.id(), iFPeople, FPeople)
        
        moment = todatetime(attrs[iMoment])
        hour = moment.hour
        fmoment = noiseMoment(moment)
        duration =  attrs[iDuration]
        fduration = noiseDuration(duration)
        frequency =  attrs[iFrequency]
        ffrequency = noiseFrequency(frequency)
        FTemporal = noiseTemporality(fmoment, fduration, ffrequency)
        layer.changeAttributeValue(feature.id(), iHour, hour)
        layer.changeAttributeValue(feature.id(), iFMoment, fmoment)
        layer.changeAttributeValue(feature.id(), iFDuration, fduration)
        layer.changeAttributeValue(feature.id(), iFFrequency, ffrequency)
        layer.changeAttributeValue(feature.id(), iFTemporal, FTemporal)
        
        Impact = aggregate(FIntensity, 1.0, FPeople, 1.0, FTemporal, 1.0, "fuzzyavg")
        layer.changeAttributeValue(feature.id(), iFImpact, Impact)
        
    layer.commitChanges()
    

#2. how many are affected at which level...?


#3. neighbourhood building density


#4. specific shading


#5. emitted noise variable with speed and load

