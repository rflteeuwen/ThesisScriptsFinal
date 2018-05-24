#CONGESTION
##Indicator3CongestionModelling=group
##CongestionFromReceptor=name

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
##roads=vector line
##roadcongestionimpact=output vector
##roadcongestionimpact2=output vector



#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#VARIABLES
global_mode = 4 #mode1=boolean, mode2=level, mode3and4=spreadingvalues
global_containerarea = 10.0
default_duration = 2.0 # duration in minutes
global_occupancy = 1.4 # 1.4 persons per vehicle
default_speed = 30.0
C_thres = 0.8
global_thr_people_container = 10.0
global_thr_people_segment = 10.0

layerforextent = QgsVectorLayer(roads, 'LayerForExtent', 'ogr')
extent = layerforextent.extent()
xmin = extent.xMinimum()
xmax = extent.xMaximum()
ymin = extent.yMinimum()
ymax = extent.yMaximum()
parameterextent = "%f,%f,%f,%f" %(xmin, xmax, ymin, ymax)



#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#FORMULAS
def congestionlevel(lcar, ltruck, c):
    if c > 0:
        C = (loadcar + 2 * loadtruck) / c
        return C
    else:
        return 0
    
def people(lcar, ltruck, C):
    P = (lcar + ltruck) * global_occupancy * (default_duration / 60.0)
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
    
def findAverage(layer, i1, i2, i3, i4):
    sumvalue = 0.0
    count = 0.0
    for feature in layer.getFeatures():
        attrs = feature.attributes()
        if attrs[i1] and attrs[i3]: #AB direction
            sumvalue = sumvalue + attrs[i1] + attrs[i3]
            count = count + 1.0
        elif attrs[i2] and attrs[i4]: #BA direction
            sumvalue = sumvalue + attrs[i2] + attrs[i4]
            count = count + 1.0
    if count == 0:
        return -1
    else:
        print sumvalue/count
        return sumvalue/count
    



#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#RECEPTORBASEDMODELLING



if global_mode < 5:

    r = global_containerarea
    
    outputs_QGISFIXEDDISTANCEBUFFER_1=processing.runalg('qgis:fixeddistancebuffer', containers,r,20.0,False,None)
    outputs_QGISCLIP_1=processing.runalg('qgis:clip', roads,outputs_QGISFIXEDDISTANCEBUFFER_1['OUTPUT'],None)
    outputs_QGISJOINATTRIBUTESBYLOCATION_1=processing.runalg('qgis:joinattributesbylocation', outputs_QGISCLIP_1['OUTPUT'],outputs_QGISFIXEDDISTANCEBUFFER_1['OUTPUT'],['intersects'],1,0,'max',0,roadcongestionimpact)
    
    # calculate impact values of road segments
    layer = getLayer(roadcongestionimpact)
     
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
    iOSCongestion=layer.fieldNameIndex('OS_congest')
    iOSSpeedAB=layer.fieldNameIndex('SPEEDAB')
    iOSSpeedBA=layer.fieldNameIndex('SPEEDBA')
    iOSLoadABtruck=layer.fieldNameIndex('LOADAB')
    iOSLoadBAtruck=layer.fieldNameIndex('LOADBA')
    iOSLoadABcar=layer.fieldNameIndex('LOADAB_5')
    iOSLoadBAcar=layer.fieldNameIndex('LOADBA_5')
    #RD
    iRDCongestion=layer.fieldNameIndex('RD_congest')
    iRDSpeedAB=layer.fieldNameIndex('SPEEDAB_2')
    iRDSpeedBA=layer.fieldNameIndex('SPEEDBA_2')
    iRDLoadABtruck=layer.fieldNameIndex('LOADAB_2')
    iRDLoadBAtruck=layer.fieldNameIndex('LOADBA_2')
    iRDLoadABcar=layer.fieldNameIndex('LOADAB_6')
    iRDLoadBAcar=layer.fieldNameIndex('LOADBA_6')
    #AS
    iASCongestion=layer.fieldNameIndex('AS_congest')
    iASSpeedAB=layer.fieldNameIndex('SPEEDAB_3')
    iASSpeedBA=layer.fieldNameIndex('SPEEDBA_3')
    iASLoadABtruck=layer.fieldNameIndex('LOADAB_3')
    iASLoadBAtruck=layer.fieldNameIndex('LOADBA_3')
    iASLoadABcar=layer.fieldNameIndex('LOADAB_4')
    iASLoadBAcar=layer.fieldNameIndex('LOADBA_4')
    
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
    
    thr_people_segment_OS = 2.0 * findAverage(layerroads, iOSLoadABtruckroads, iOSLoadBAtruckroads, iOSLoadABcarroads, iOSLoadBAcarroads) * global_occupancy * (default_duration / 60.0)
    thr_people_segment_RD = 2.0 * findAverage(layerroads, iRDLoadABtruckroads, iRDLoadBAtruckroads, iRDLoadABcarroads, iRDLoadBAcarroads) * global_occupancy * (default_duration / 60.0)
    thr_people_segment_AS = 2.0 * findAverage(layerroads, iASLoadABtruckroads, iASLoadBAtruckroads, iASLoadABcarroads, iASLoadBAcarroads) * global_occupancy * (default_duration / 60.0)
    print "people OS RD en AS", thr_people_segment_OS, thr_people_segment_RD, thr_people_segment_AS
    
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
            thr_people_segment = thr_people_segment_OS
            
        elif congestionMoment(moment)[1] == "RD":
            C = attrs[iRDCongestion]
            speed = getSpeed(attrs[iRDSpeedAB], attrs[iRDSpeedBA])
            Ltruck = getLoad(attrs[iRDLoadABtruck], attrs[iRDLoadBAtruck])
            Lcar = getLoad(attrs[iRDLoadABcar], attrs[iRDLoadBAcar])
            thr_people_segment = thr_people_segment_RD
            
        elif congestionMoment(moment)[1] == "AS":
            C = attrs[iASCongestion]
            speed = getSpeed(attrs[iASSpeedAB], attrs[iASSpeedBA])
            Ltruck = getLoad(attrs[iASLoadABtruck], attrs[iASLoadBAtruck])
            Lcar = getLoad(attrs[iASLoadABcar], attrs[iASLoadBAcar])
            thr_people_segment = thr_people_segment_AS
        
        if not C: # if C is NULL
            C = 0.0
    
        # intensity factor
        if global_mode == 1:
            #1. congestion...?
            Intensity = booleancongestion(C)
            FIntensity = float(Intensity)
        elif global_mode == 2:
            #2. which level...?
            Intensity = C
            FIntensity = normalise(Intensity, 0, C_thres)
        elif global_mode == 3:
            #3. boolean, wider spread
            Intensity = booleancongestion(C)
            FIntensity = float(Intensity)
        elif global_mode == 4:
            Intensity = C
            FIntensity = normalise(Intensity, 0, C_thres)
        layer.changeAttributeValue(feature.id(), iFIntensity, FIntensity)
        
        #people factor
        nrpeople = (Ltruck + Lcar) * global_occupancy * (default_duration / 60.0)
        FPeople = normalise(nrpeople, 0.0, thr_people_segment)
        layer.changeAttributeValue(feature.id(), iPeople, nrpeople)
        layer.changeAttributeValue(feature.id(), iFPeople, FPeople)
        
        # impact
        Impact = aggregate(FIntensity, 1.0, FPeople, 1.0, FTemporal, 1.0, "fuzzyavg")
        layer.changeAttributeValue(feature.id(), iFImpact, Impact)
        
    layer.commitChanges()
    
    if global_mode == 4:
            
            r_spread = str(default_speed * (1000.0/60.0) * default_duration)
            
            outputs_QGISEXTRACTBYATTRIBUTE_1=processing.runalg('qgis:extractbyattribute', roadcongestionimpact,'fIntensity',2,C_thres/2,None) # all of half the threshold and higher
            
            outputs_QGISPOLYGONCENTROIDS_2=processing.runalg('qgis:polygoncentroids', outputs_QGISEXTRACTBYATTRIBUTE_1['OUTPUT'],None)
            
            outputs_GRASS7VNETISO_1=processing.runalg('grass7:v.net.iso', roads,outputs_QGISPOLYGONCENTROIDS_2['OUTPUT_LAYER'],50.0,2,'1-100000',r_spread,None,None,None,False,parameterextent,-1.0,0.0001,0,None)

            outputs_QGISJOINATTRIBUTESBYLOCATION_2=processing.runalg('qgis:joinattributesbylocation', outputs_GRASS7VNETISO_1['output'],roadcongestionimpact,['intersects'],1,0,'max',1,None)
            outputs_QGISJOINATTRIBUTESBYLOCATION_2=processing.runalg('qgis:joinattributesbylocation', roads,outputs_QGISJOINATTRIBUTESBYLOCATION_2['OUTPUT'],['intersects'],1,0,'max',1,roadcongestionimpact2)
            
            layer = getLayer(roadcongestionimpact2)
            
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
            iCat=layer.fieldNameIndex('cat')
            #OS
            iOSCongestion=layer.fieldNameIndex('OS_congest')
            iOSSpeedAB=layer.fieldNameIndex('SPEEDAB')
            iOSSpeedBA=layer.fieldNameIndex('SPEEDBA')
            iOSLoadABtruck=layer.fieldNameIndex('LOADAB')
            iOSLoadBAtruck=layer.fieldNameIndex('LOADBA')
            iOSLoadABcar=layer.fieldNameIndex('LOADAB_4')
            iOSLoadBAcar=layer.fieldNameIndex('LOADBA_4')
            #RD
            iRDCongestion=layer.fieldNameIndex('RD_congest')
            iRDSpeedAB=layer.fieldNameIndex('SPEEDAB_2')
            iRDSpeedBA=layer.fieldNameIndex('SPEEDBA_2')
            iRDLoadABtruck=layer.fieldNameIndex('LOADAB_2')
            iRDLoadBAtruck=layer.fieldNameIndex('LOADBA_2')
            iRDLoadABcar=layer.fieldNameIndex('LOADA_5')
            iRDLoadBAcar=layer.fieldNameIndex('LOADB_5')
            #AS
            iASCongestion=layer.fieldNameIndex('AS_congest')
            iASSpeedAB=layer.fieldNameIndex('SPEEDAB_3')
            iASSpeedBA=layer.fieldNameIndex('SPEEDBA_3')
            iASLoadABtruck=layer.fieldNameIndex('LOADAB_3')
            iASLoadBAtruck=layer.fieldNameIndex('LOADBA_3')
            iASLoadABcar=layer.fieldNameIndex('LOADA_6')
            iASLoadBAcar=layer.fieldNameIndex('LOADB_6')
            
            layer.startEditing()
            for feature in layer.getFeatures():
                
                attrs = feature.attributes()
                
                if not attrs[iFImpact]: # if Impact is still NULL and therefore has to be set
                
                    #intensity
                    if attrs[iCat] == 1:
                        FIntensity = 0.5 # half, since half the threshold is used for extraction
                    else:
                        FIntensity = 0.0
                    layer.changeAttributeValue(feature.id(), iFIntensity, FIntensity)
                        
                    #temporality
                    if attrs[iCat] == 1:
                        FTemporal = 1.0
                    else:
                        FTemporal = 0.0
                    #layer.changeAttributeValue(feature.id(), iFMoment, fmoment)
                    #layer.changeAttributeValue(feature.id(), iFDuration, fduration)
                    #layer.changeAttributeValue(feature.id(), iFFrequency, ffrequency)
                    layer.changeAttributeValue(feature.id(), iFTemporal, FTemporal)
                    
                    #people factor
                    Ltruck = (getLoad(attrs[iOSLoadABtruck], attrs[iOSLoadBAtruck]) + getLoad(attrs[iASLoadABtruck], attrs[iASLoadBAtruck])) /2.0
                    Lcar = (getLoad(attrs[iOSLoadABcar], attrs[iOSLoadBAcar]) + getLoad(attrs[iASLoadABcar], attrs[iASLoadBAcar])) / 2.0
                    nrpeople = (Ltruck + Lcar) * global_occupancy * (default_duration / 60.0)
                    FPeople = normalise(nrpeople, 0.0, ((thr_people_segment_OS + thr_people_segment_AS)/2.0))
                    layer.changeAttributeValue(feature.id(), iFPeople, FPeople)
                    
                    # impact
                    Impact = aggregate(FIntensity, 1.0, FPeople, 1.0, FTemporal, 1.0, "nocompensation")
                    layer.changeAttributeValue(feature.id(), iFImpact, Impact)
                
            layer.commitChanges()

else:
    
    print "unknown mode"


