##ThesisScenarios=group
##temporalScenarios=name

#IMPORTS
import sys
import csv
import operator
import datetime
from qgis.core import *
import processing
#sys.path.append('C:/Users/rflte/.qgis2/processing/scripts/')
#from containerMoments import containerMoments
#from routeMoments import routeMoments

##inputcontainersshp=vector
##inputrouteshp=vector
##outputcontainerscsv=output file
##outputroutecsv=output file
##generalcsv=output file
##outputcontainersshp=output vector
##outputrouteshp=output vector
# would be nice if code worked without general csv... I think it can with what I know now about reading/editing the attributes table

def calcSecs(length, speed):
    l = float(length) / 1000.0 # length in kilometers
    s = float(speed) # speed in km/h
    if s < 1.0:
        s = 1.0
    t = (l / s) * 60.0 * 60.0 # time in seconds
    return t

    
def getCost(length, speedab, speedba):
    if speedab: 
        return calcSecs(length, speedab)
    elif speedba: 
        return calcSecs(length, speedba)
    else:
        return calcSecs(length, 1.0)
        
        
def shpToCsv(inputshapefile, outputcsv):
    layer=processing.getObject(inputshapefile)
    QgsVectorFileWriter.writeAsVectorFormat(layer,outputcsv, "utf-8", None, "CSV")
    return outputcsv     
        

def temporalities(inf, type, ccol, scol, sth, dur, freq):
    # function takes shapefile, either routes or containers
    # with geometry explicitly added to attribute table
    # converts it to csv, calculates and adds temporalities
    # converts is back to shapefile and returns it
    print "function temporalities started"
    
    #CONVERT SHP TO CSV
    infcsv = shpToCsv(inf, generalcsv)
    
    #OPEN CSV AND PERFORM OPERATIONS
    with open(infcsv,'rb') as f:
        csvreader = csv.reader(f)
        unsortedList = []
        firstline = True
        
        # find sequence value for each line and cast to integer, append it
        for line in csvreader:
            if firstline == True:
                
                # find indexes for variables in input file
                seqnr = line.index(scol)
                costnr = line.index(ccol)
                if type == "route":
                    lennr = line.index("mylength")
                    spabnr = line.index("SPEEDAB_2")
                    spbanr = line.index("SPEEDBA_2")
                elif type == "routecontainers":
                    lennr = line.index("mylength")
                    spabnr = line.index("SPEEDAB_2")
                    spbanr = line.index("SPEEDBA_2")
                    
                # append columns in header
                header = line
                seqname = 'seqint'
                header.append(seqname)
                intseqnr = line.index(seqname)
                momname = 'moment'
                header.append(momname)
                durname = 'duration'
                header.append(durname)
                freqname = 'frequency'
                header.append(freqname)
                firstline = False
                
            elif line[seqnr] != '':
                sequence = int(line[seqnr])
                line.append(sequence)
                unsortedList.append(line)
                
        # sort lines based on integer sequence value
        sortedList = sorted(unsortedList, key=operator.itemgetter(intseqnr), reverse=False)
        
        #CALCULATE TEMPORALITIES
        # if the file is routes
        if type == "route": 
            print "route"
            n = 0
            for line in sortedList:
                if n == 0:
                    # set first in sequence to start time
                    mom = datetime.timedelta(hours=sth)
                    sortedList[n].append(mom)
                    dur = float(sortedList[n][costnr])
                    sortedList[n].append(dur)
                    sortedList[n].append(freq)
                    print "first", n, mom, dur, freq
                    n += 1
                else:
                    print n
                    costsec = getCost(sortedList[n][lennr], sortedList[n][spabnr], sortedList[n][spbanr])
                    mom = mom + datetime.timedelta(seconds=int(costsec))
                    sortedList[n].append(mom)
                    dur = float(sortedList[n][costnr])
                    sortedList[n].append(dur)
                    sortedList[n].append(freq)
                    n += 1    
                        
                with open(outputroutecsv + ".csv", 'wb') as f:
                    csvwriter = csv.writer(f, delimiter=',')
                    csvwriter.writerow([header[seqnr], header[-3], header[-2], header[-1]])
                    for line in sortedList:
                        row = [line[seqnr], line[-3], line[-2], line[-1]]
                        csvwriter.writerow(row) # only writer sequence nr and temporalities
                            
            print "last", n, mom, dur, freq
                

                
        # if the file is containers
        elif type == "container":
            print "container"
            n = 0
            for line in sortedList:
                if n == 0:
                    print n
                    # set first in sequence to start time
                    mom = datetime.timedelta(hours=sth)
                    sortedList[n].append(mom)
                    sortedList[n].append(dur)
                    sortedList[n].append(freq)
                    print "first", n, mom, dur, freq
                    n += 1
                else:
                    print n
                    costsec = (float(sortedList[n-1][costnr]) + float(dur)) # time costs since arriving at previous
                    mom = mom + datetime.timedelta(seconds=int(costsec))
                    sortedList[n].append(mom)
                    sortedList[n].append(dur)
                    sortedList[n].append(freq)
                    n += 1    
                    
                with open(outputcontainerscsv + ".csv", 'wb') as f:
                    csvwriter = csv.writer(f, delimiter=',')
                    csvwriter.writerow([header[seqnr], header[-3], header[-2], header[-1]])
                    for line in sortedList:
                        row = [line[seqnr], line[-3], line[-2], line[-1]]
                        csvwriter.writerow(row) # only writer sequence nr and temporalities
                        
            print "last", n, mom, dur, freq
            
            
            # if the file is routes
        elif type == "routecontainers": 
            print "routecontainers"
            n = 0
            for line in sortedList:
                if n == 0:
                    # set first in sequence to start time
                    mom = datetime.timedelta(hours=sth)
                    sortedList[n].append(mom)
                    dur = float(sortedList[n][costnr])
                    sortedList[n].append(dur)
                    sortedList[n].append(freq)
                    print "first", n, mom, dur, freq
                    n += 1
                else:
                    print n
                    costsec = getCost(sortedList[n][lennr], sortedList[n][spabnr], sortedList[n][spbanr])
                    mom = mom + datetime.timedelta(seconds=int(costsec))
                    sortedList[n].append(mom)
                    dur = float(sortedList[n][costnr])
                    sortedList[n].append(dur)
                    sortedList[n].append(freq)
                    n += 1    
                        
                with open(outputroutecsv + ".csv", 'wb') as f:
                    csvwriter = csv.writer(f, delimiter=',')
                    csvwriter.writerow([header[seqnr], header[-3], header[-2], header[-1]])
                    for line in sortedList:
                        row = [line[seqnr], line[-3], line[-2], line[-1]]
                        csvwriter.writerow(row) # only writer sequence nr and temporalities
                            
            print "last", n, mom, dur, freq
                
            
        # is the file is neither route nor containers
        else:
            print "unknown type of file"
            
            
        shplayer=processing.getObject(inf)
        if type == "route":
            csvlayer=QgsVectorLayer(outputroutecsv+".csv")
            print outputroutecsv
            print csvlayer
            processing.runalg("qgis:joinattributestable",shplayer,csvlayer,"sequence","sequence",outputrouteshp)
        elif type == "container":
            csvlayer=QgsVectorLayer(outputcontainerscsv+".csv")
            print outputcontainerscsv
            print csvlayer
            processing.runalg("qgis:joinattributestable",shplayer,csvlayer,"sequence","sequence",outputcontainersshp)
        if type == "routecontainers":
            csvlayer=QgsVectorLayer(outputroutecsv+".csv")
            print outputroutecsv
            print csvlayer
            processing.runalg("qgis:joinattributestable",shplayer,csvlayer,"sequence","sequence",outputrouteshp)

        if type == "routecontainers":
            print 'assigning temporalities of routes to containers along them'
            outputs_QGISJOINATTRIBUTESBYLOCATION_1=processing.runalg('qgis:joinattributesbylocation', inputcontainersshp,outputrouteshp,['intersects'],500,0,'sum,mean,min,max,median',0,outputcontainersshp)

            # assume container duration of 2 minutes
            layer = QgsVectorLayer(outputcontainersshp, 'outputcontainersshp', 'ogr')
            iDuration = layer.fieldNameIndex('duration')
            layer.startEditing()
            for feature in layer.getFeatures():
                value = 2
                layer.changeAttributeValue(feature.id(), iDuration, value)
        
            layer.commitChanges()
            
            
            

    
    
#GENERATE TEMPORAL SCENARIOS (IE ADD TEMPORALITIES TO SPATIAL SCENARIOS)
def generateTemporalScenario(containershp, routeshp):
    # function takes two shapefiles: containers (points) and routes (lines)
    # which result from generation of spatial scenarios
    # variables concerning temporalities are set
    # and function is called to add temporalities to the shapefiles
    # returns shapefiles with temporalities
    print "function generateTemporalScenarios started"

    #VARIABLES TO SET
    containercostcol = "cost_to_ne" # column with value of cost to next container
    containerseqcol = "sequence" # column with sequence values of containers
    routecostcol = "mycost" # column with cost of road segment itself
    routeseqcol = "sequence" # column with sequence values of route segments
    starthours = 6 # starting time in hours: 9 -> 09:00:00  (hh:mm:ss)
    containerduration = 2 # duration of emptying a container in minutes
    frequency = 4 # days per 2 weeks
        
    #CALCULATION
    #temporalities(inputcontainersshp, "container", containercostcol, containerseqcol, starthours, containerduration, frequency)
    #print "containers with temporalities calculated"
    #temporalities(inputrouteshp, "route", routecostcol, routeseqcol, starthours, containerduration, frequency)
    #print "routes with temporalities calculated"
    temporalities(inputrouteshp, "routecontainers", routecostcol, routeseqcol, starthours, containerduration, frequency)
    print "routes with temporalities calculated, also assigned to containers"

    
generateTemporalScenario(inputcontainersshp, inputrouteshp)





