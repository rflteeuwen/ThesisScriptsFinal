##ThesisImpactAggregation=group
##SpatialAggregation=name


#INPUTS VIA PROMPT
##AggregationPolygons=vector polygon

#source based inputs
##ValuesToAggregate=vector point
#source based outputs
##Aggregated=output vector


    

#IMPORTS
from qgis.core import * 
from PyQt4.QtCore import *
import processing
import numpy as np

#AGGREGATION

#STEP1 SPATIAL AGGREGATION
# mean of all impact values within an aggregation area 

#spatially aggregate NOISE
outputs_QGISJOINATTRIBUTESBYLOCATION_NOISESCENARIO1=processing.runalg('qgis:joinattributesbylocation', AggregationPolygons,ValuesToAggregate,['intersects'],0.0,1,'mean,sum',1,Aggregated)




























