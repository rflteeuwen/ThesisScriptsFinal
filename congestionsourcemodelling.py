#CONGESTION
##Indicator3CongestionModelling=group
##CongestionFromSource=name

#IMPORTS
from qgis.core import *
from PyQt4.QtCore import *
import processing
import math
import datetime
from datetime import datetime, time, timedelta, date

#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#INPUT AND OUTPUT
##containers=vector point
##route=vector line
##roads=vector line
##containercongestionimpact=output vector


#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#VARIABLES
global_mode = 2 #mode1=boolean, mode2=level
global_containerarea = 10.0
default_duration = 2.0 # duration in minutes
global_occupancy = 1.4 # 1.4 persons per vehicle
default_speed = 30.0
C_thres = 0.8
global_thr_people_container = 10.0
global_thr_people_segment = 10.0



#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#FORMULAS
def congestionlevel(lcar, ltruck, c):
    C = (loadcar + 2 * loadtruck) / c
    return C
    
def people(lcar, ltruck, C):
    P = (lcar + ltruck) * global_occupancy * (default_duration / 60)
    return P
    
def booleancongestion(C):
    if C >= C_thres:
        return True
    else:
        return False
        
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
        
def congestionMoment(m):
    thr1 = time(7)
    thr2 = time(9)
    thr3 = time(16)
    thr4 = time(18)
    if thr1 < m <= thr2:
        return [1, "OS"]
    elif thr3 < m <= thr4:
        return [1, "AS"]
    else:
        return [0, "RD"]
    
def congestionDuration(d):
    thr1 = 0.0
    thr2 = 1.0
    if d < thr2:
        return calculateLinearValue(d, thr1, thr2)
    else:
        return 1
    
def congestionFrequency(f):
    thr1 = 0
    thr2 = 14
    if f < thr2:
        return calculateLinearValue(f, thr1, thr2)
    else:
        return 1

def congestionTemporality(m, d, f):
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
        
def getSpeed(SpeedAB, SpeedBA):
    if SpeedAB:
        speed = SpeedAB
    elif SpeedBA:
        speed = SpeedBA
    else:
        speed = default_speed
    return speed
    
def getLoad(LoadAB, LoadBA):
    if LoadAB:
        load = LoadAB
    elif LoadBA:
        load = LoadBA
    else:
        load = 1.0
    return load
    
def findLoadDensity(layer, i1, i2, i3, i4):
    count = 0.0
    Ptotal = 0.0
    for feature in layer.getFeatures():
        attrs = feature.attributes()
        if attrs[i1]:
            Pf = attrs[i1] + attrs[i3]
        elif attrs[i2]:
            Pf = attrs[i2] + attrs[i4]
        Ptotal = Ptotal + Pf
        count = count + 1.0
    if count == 0.0:
        print "error"
        return -1
    return Ptotal / count # average number of people per m





#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#SOURCEBASEDMODELLING

if global_mode < 3:
    
    outputs_QGISFIELDCALCULATOR_1=processing.runalg('qgis:fieldcalculator', containers,'joincat2',2,10.0,3.0,True,'to_string(@row_number)',None)
    
    outputs_QGISFIXEDDISTANCEBUFFER_1=processing.runalg('qgis:fixeddistancebuffer', outputs_QGISFIELDCALCULATOR_1['OUTPUT_LAYER'],global_containerarea,20.0,False,None)
    
    # find max congestion level and max load within buffer
    outputs_QGISJOINATTRIBUTESBYLOCATION_1=processing.runalg('qgis:joinattributesbylocation', outputs_QGISFIXEDDISTANCEBUFFER_1['OUTPUT'],roads,['intersects'],1,1,'max',0,None)
    
    # assign these levels to container
    outputs_QGISJOINATTRIBUTESTABLE_1=processing.runalg('qgis:joinattributestable', outputs_QGISFIELDCALCULATOR_1['OUTPUT_LAYER'],outputs_QGISJOINATTRIBUTESBYLOCATION_1['OUTPUT'],'joincat2','joincat2',containercongestionimpact)
    
    # calculate impact values of container
    layer = getLayer(containercongestionimpact)
     
    layer.dataProvider().addAttributes([QgsField("nrpeople", QVariant.Double),QgsField("Hour", QVariant.Double),QgsField("fMoment", QVariant.Double),QgsField("fDuration", QVariant.Double),QgsField("fFrequency", QVariant.Double),QgsField("fIntensity", QVariant.Double),QgsField("fPeople", QVariant.Double),QgsField("fTemporal", QVariant.Double),QgsField("Impact", QVariant.Double)])
    layer.updateFields()
    
    iHour = layer.fieldNameIndex('Hour')
    iPeople = layer.fieldNameIndex('nrpeople')
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
    #OS
    iOSCongestion=layer.fieldNameIndex('maxOS_cong')
    iOSSpeedAB=layer.fieldNameIndex('maxSPEEDAB')
    iOSSpeedBA=layer.fieldNameIndex('maxSPEEDBA')
    iOSLoadABtruck=layer.fieldNameIndex('maxLOADAB')
    iOSLoadBAtruck=layer.fieldNameIndex('maxLOADBA')
    iOSLoadABcar=layer.fieldNameIndex('maxLOADA_3')
    iOSLoadBAcar=layer.fieldNameIndex('maxLOADB_3')
    #RD
    iRDCongestion=layer.fieldNameIndex('maxRD_cong')
    iRDSpeedAB=layer.fieldNameIndex('maxSPEED_4')
    iRDSpeedBA=layer.fieldNameIndex('maxSPEED_6')
    iRDLoadABtruck=layer.fieldNameIndex('maxLOADAB_')
    iRDLoadBAtruck=layer.fieldNameIndex('maxLOADBA_')
    iRDLoadABcar=layer.fieldNameIndex('maxLOADA_4')
    iRDLoadBAcar=layer.fieldNameIndex('maxLOADB_4')
    #AS
    iASCongestion=layer.fieldNameIndex('maxAS_cong')
    iASSpeedAB=layer.fieldNameIndex('maxSPEED_9')
    iASSpeedBA=layer.fieldNameIndex('maxSPEED_13')
    iASLoadABtruck=layer.fieldNameIndex('maxLOADA_1')
    iASLoadBAtruck=layer.fieldNameIndex('maxLOADB_1')
    iASLoadABcar=layer.fieldNameIndex('maxLOADA_2')
    iASLoadBAcar=layer.fieldNameIndex('maxLOADB_2')
    
    layerroads = getLayer(roads)
    iOSLoadABtruckroads=layerroads.fieldNameIndex('LOADAB')
    iOSLoadBAtruckroads=layerroads.fieldNameIndex('LOADBA')
    iOSLoadABcarroads=layerroads.fieldNameIndex('LOADAB_5')
    iOSLoadBAcarroads=layerroads.fieldNameIndex('LOADBA_5')
    iRDLoadABtruckroads=layerroads.fieldNameIndex('LOADAB_2')
    iRDLoadBAtruckroads=layerroads.fieldNameIndex('LOADBA_2')
    iRDLoadABcarroads=layerroads.fieldNameIndex('LOADAB_6')
    iRDLoadBAcarroads=layerroads.fieldNameIndex('LOADBA_6')
    iASLoadABtruckroads=layerroads.fieldNameIndex('LOADAB_3')
    iASLoadBAtruckroads=layerroads.fieldNameIndex('LOADBA_3')
    iASLoadABcarroads=layerroads.fieldNameIndex('LOADAB_4')
    iASLoadBAcarroads=layerroads.fieldNameIndex('LOADBA_4')
    
    thr_people_container_OS = 2.0 * findLoadDensity(layerroads, iOSLoadABtruckroads, iOSLoadBAtruckroads, iOSLoadABcarroads, iOSLoadBAcarroads) * global_occupancy * (default_duration / 60.0)
    thr_people_container_RD = 2.0 * findLoadDensity(layerroads, iRDLoadABtruckroads, iRDLoadBAtruckroads, iRDLoadABcarroads, iRDLoadBAcarroads) * global_occupancy * (default_duration / 60.0)
    thr_people_container_AS = 2.0 * findLoadDensity(layerroads, iASLoadABtruckroads, iASLoadBAtruckroads, iASLoadABcarroads, iASLoadBAcarroads) * global_occupancy * (default_duration / 60.0)

    layer.startEditing()
    for feature in layer.getFeatures():
        
        attrs = feature.attributes()
        
        #temporality factor
        moment = todatetime(attrs[iMoment])
        hour = moment.hour
        fmoment = congestionMoment(moment)[0]
        duration =  attrs[iDuration]
        fduration = congestionDuration(duration)
        frequency =  attrs[iFrequency]
        ffrequency = congestionFrequency(frequency)
        FTemporal = congestionTemporality(fmoment, fduration, ffrequency)
        layer.changeAttributeValue(feature.id(), iHour, hour)
        layer.changeAttributeValue(feature.id(), iFMoment, fmoment)
        layer.changeAttributeValue(feature.id(), iFDuration, fduration)
        layer.changeAttributeValue(feature.id(), iFFrequency, ffrequency)
        layer.changeAttributeValue(feature.id(), iFTemporal, FTemporal)
        
        if congestionMoment(moment)[1] == "OS":
            C = attrs[iOSCongestion]
            speed = getSpeed(attrs[iOSSpeedAB], attrs[iOSSpeedBA])
            Ltruck = getLoad(attrs[iOSLoadABtruck], attrs[iOSLoadBAtruck])
            Lcar = getLoad(attrs[iOSLoadABcar], attrs[iOSLoadBAcar])
            thr_people_container = thr_people_container_OS
            
        elif congestionMoment(moment)[1] == "RD":
            C = attrs[iRDCongestion]
            speed = getSpeed(attrs[iRDSpeedAB], attrs[iRDSpeedBA])
            Ltruck = getLoad(attrs[iRDLoadABtruck], attrs[iRDLoadBAtruck])
            Lcar = getLoad(attrs[iRDLoadABcar], attrs[iRDLoadBAcar])
            thr_people_container = thr_people_container_RD
            
        elif congestionMoment(moment)[1] == "AS":
            C = attrs[iASCongestion]
            speed = getSpeed(attrs[iASSpeedAB], attrs[iASSpeedBA])
            Ltruck = getLoad(attrs[iASLoadABtruck], attrs[iASLoadBAtruck])
            Lcar = getLoad(attrs[iASLoadABcar], attrs[iASLoadBAcar])
            thr_people_container = thr_people_container_AS
        
        if not C: # if C is NULL
            C = 0.0
    
        # intensity factor
        if global_mode == 1:
            #1. how many are affected...?
            Intensity = booleancongestion(C)
            FIntensity = float(Intensity)
        elif global_mode == 2:
            #2. how many are affected at which level...?
            Intensity = C
            FIntensity = normalise(Intensity, 0, C_thres)
        layer.changeAttributeValue(feature.id(), iFIntensity, FIntensity)
        
        #people factor
        nrpeople = (Ltruck + Lcar) * global_occupancy * (default_duration / 60.0)
        FPeople = normalise(nrpeople, 0.0, thr_people_container)
        layer.changeAttributeValue(feature.id(), iPeople, nrpeople)
        layer.changeAttributeValue(feature.id(), iFPeople, FPeople)
        
        # impact
        Impact = aggregate(FIntensity, 1.0, FPeople, 1.0, FTemporal, 1.0, "fuzzyavg")
        layer.changeAttributeValue(feature.id(), iFImpact, Impact)
        
    layer.commitChanges()









