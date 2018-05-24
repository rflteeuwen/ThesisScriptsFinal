#CO2
##Indicator4CO2Modelling=group
##CO2FromSource=name

#IMPORTS
from qgis.core import *
from PyQt4.QtCore import *
import processing
import math
import datetime
from datetime import datetime, time, timedelta, date

#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#INPUT AND OUTPUT
##route=vector line
##roads=vector line
##routeco2impact=output vector


#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#VARIABLES
# assuming 5 tonne lorry using diesel
global_mode = 3 #mode1=defaultspeedload; mode2=variablespeeddefaultload; mode3=variablespeedload
default_weightladen = 50.0
default_speed = 50.0
default_totalmassthreshold = 3.0


#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#FORMULAS
def fuelconsumption(weightladen):
    C = 0.001167 * weightladen + 0.15797
    return C
    
def speedfactor(speed):
    if speed >= 80:
        Fs = 1.0
    elif speed <= 50:
        Fs = 0.97
    else:
        Fs = 0.94
    return Fs

def co2mass(d, C, Fs):
    M = d * C * Fs * 2.63
    return M
    
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
        
def calculateLinearValue(t, t_0, t_1):
    if type(t) == int: # if integer (frequency, duration)
        if t == t_0:
            return 0.0
        elif t == t_1:
            return 1.0
        elif t_0 < t_1:
            # if slope is positive
            dt = float(t_1 - t_0)
            value = float((t - t_0) * (1 / dt))
            return value
        else:
            print "wrong "
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
        try: 
            if t == t_0:
                return 0.0
            elif t == t_1:
                return 1.0
            elif t_0 < t_1:
                # if slope is positive
                dt = float(t_1 - t_0)
                value = float((t - t_0) * (1 / dt))
                return value
            else:
                print "wrong"
                return None
        except:
            print "unknown type calculateLinearValue()"



#   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   -   - 
#SOURCEBASEDMODELLING



if global_mode < 4:
    
    # calculate length of segment
    outputs_QGISFIELDCALCULATOR_1=processing.runalg('qgis:fieldcalculator', route,'mylength',0,10.0,3.0,True,'$length',None)
    
    #include road data
    outputs_QGISJOINATTRIBUTESBYLOCATION_1=processing.runalg('qgis:joinattributesbylocation', outputs_QGISFIELDCALCULATOR_1['OUTPUT_LAYER'],roads,['intersects'],1,0,'sum,mean,min,max,median',0,routeco2impact)

    layer = getLayer(routeco2impact)
    
    layer.dataProvider().addAttributes([QgsField("TotalMass", QVariant.Double),QgsField("PerKmMass", QVariant.Double),QgsField("fIntensity", QVariant.Double),QgsField("Impact", QVariant.Double)])
    layer.updateFields()
    
    iTotalMass = layer.fieldNameIndex('TotalMass')
    iPerKmMass = layer.fieldNameIndex('PerKmMass')
    iFIntensity = layer.fieldNameIndex('fIntensity')
    iSequence = layer.fieldNameIndex('sequence')
    iFrequency = layer.fieldNameIndex('frequency')
    iFImpact = layer.fieldNameIndex('Impact')
    iLength = layer.fieldNameIndex('mylength')
    ISpeedAB = layer.fieldNameIndex('SPEEDAB_2')
    ISpeedBA = layer.fieldNameIndex('SPEEDBA_2')
    
    first = layer.minimumValue(iSequence)
    print 'first is ', first, type(first)
    last = layer.maximumValue(iSequence)
    print 'last is ', last, type(last)

    layer.startEditing()

    for feature in layer.getFeatures():
        
        attrs = feature.attributes()
        
        if attrs[ISpeedAB]:
            speed = attrs[ISpeedAB]
        elif attrs[ISpeedBA]:
            speed = attrs[ISpeedBA]
        else:
            speed = default_speed
        
        if speed == 0.0:
            speed = default_speed
        
        
        if global_mode == 1:
            #1.how much CO2 is emitted using defaults
            l = attrs[iLength]/1000.0
            fc = fuelconsumption(default_weightladen)
            sf = speedfactor(default_speed)
            f = float(attrs[iFrequency])
            TotalMass = l * fc * sf * 2.63 * f
        elif global_mode == 2:
            #2. use variable speed factor
            l = attrs[iLength]/1000.0
            fc = fuelconsumption(default_weightladen)
            sf = speedfactor(speed)
            f = float(attrs[iFrequency])
            TotalMass = l * fc * sf * 2.63 * f
        elif global_mode == 3:
            #3. use increasing load along route
            t = attrs[iSequence]
            fSequence = calculateLinearValue(t, first, last)
            load = fSequence * 100.0
            fc = fuelconsumption(load) 
            
            l = attrs[iLength]/1000.0
            sf = speedfactor(speed)
            f = float(attrs[iFrequency])
            TotalMass = l * fc * sf * 2.63 * f
        
        layer.changeAttributeValue(feature.id(), iTotalMass, TotalMass)
        layer.changeAttributeValue(feature.id(), iPerKmMass, TotalMass/l)
        
        Intensity = TotalMass/(attrs[iLength]/1000.0)
        FIntensity = normalise(Intensity, 0.0, default_totalmassthreshold) # check threshold
        layer.changeAttributeValue(feature.id(), iFIntensity, FIntensity)
        
        Impact = FIntensity
        layer.changeAttributeValue(feature.id(), iFImpact, Impact)
        
    layer.commitChanges()
    
else:
    
    print "unknown mode"





