#!/usr/bin/python
# -*- coding: utf-8 -*-
######################################################################
# * $Id: 
# * $Revision:  $
# * $Date:  $
# * Created By: ldo
# Script to build a report(json) from a track (gpx) for the very unique
# "45 challenge". It includes amongst other things:
# - delimiting the area in between the track and the 45 parrallel
# - a score calculation using the distance and the elevation gain
######################################################################
import argparse as mod_argparse
import math as mod_math
import sys, getopt
import gpxpy
import gpxpy.gpx
import pyproj    
import json
import datetime,time
import shapely
import shapely.ops as ops
from shapely.geometry.polygon import Polygon
from shapely.geometry import Point,LineString,MultiPolygon,mapping,shape
from functools import partial


######################################################################
# Parsing an existing file:
######################################################################

def gpxTracksTo45(gpx_content):
    gpx = gpxpy.parse(gpx_content)
    ecart45=0
    distance45=0
    breakpoint_lon=0
    wrongdir=False
    area=0
    temparea=0

    now = datetime.datetime.today().strftime('%Y-%m-%d %hh:%mm')

    # Process the total uphill/downhill elevation for the given track
    uphill, downhill = gpx.get_uphill_downhill()

    # initialize  a geo json dictionary to store result of the processing
    gjson_dict={}
    gjson_dict["type"]= "FeatureCollection"
    feat_list = []

    # Initialize a list to store all valid points to build a polygon for the area
    pointlist = []
    # Initialize a list to buffer point before calculating intermediate area
    templist = []

    # Need to determine overall direction (E->W is positive, W-> E is negative)
    # overall direction is determine by first and last point, regardless of the 
    # max or min longitude.
    # First determin first and last
    # Loop on all available points (WGS 84)
    for track in gpx.tracks:
        for segment in track.segments:
            previous = segment.points[0]
            firstpoint = segment.points[0]
            for point in segment.points[1:]:
                 lastpoint = point
    # End looping on points in the tracks

    if (lastpoint.longitude-firstpoint.longitude) < 0:
	print 'Direction is East to West'
       	direction=1
    else: 
    	print 'Direction is West to East'
       	direction=-1

    # Loop on all available points (WGS 84)
    for track in gpx.tracks:
        print_gpx_part_info(track, indentation='        ')
        for segment in track.segments:
            previous = segment.points[0]
            # first point of track is always considered valid, will be used to 
            # determine the total distance projected on the 45 parralell
            firstpoint = segment.points[0]
            lastpoint = segment.points[0]

            # First point projected on the 45th line (will be used to build the line)
            pointzero = Point(firstpoint.longitude,45.0)
            pointlist.append(pointzero)
            pointlist.append(Point(firstpoint.longitude,firstpoint.latitude))
            templist.append(pointzero)
            templist.append(Point(firstpoint.longitude,firstpoint.latitude))

            for point in segment.points[1:]:
                # Discard point if going backward
                # Hopefully there won't be any track crossing lon 0 (which is the atlantic)

                if ((point.longitude - previous.longitude)*direction > 0) or ((point.longitude - breakpoint_lon)*direction > 0):
			# track is moving in the wrong direction 
			# or in the right dir but still not passed the breakpoint
                        # Need to capture 1st point from which track start
			# moving in the wrong direction
                        if (wrongdir == False):
			                 breakpoint_lon = previous.longitude
                        wrongdir=True
                else:
                        wrongdir=False
                        # Check if segment is crossing the 45// ?
                        if ((lastpoint.latitude<45.0 and point.latitude >= 45.0) or (lastpoint.latitude>45.0 and point.latitude <= 45.0)):
                              print 'Crossing detected before long/lat: {:.6f}/{:.6f}'.format(point.longitude,point.latitude)
                              # Set aside a polygon without intersection and calculate area
                              # first build a Point for the intersect on the 45
                              # use Thales ...
                              intersectlon=point.longitude-((point.longitude-lastpoint.longitude)*((45.0-point.latitude)/(lastpoint.latitude-point.latitude)))
                              print 'Crossing detected at longitude: {:.6f}'.format(intersectlon)
                              intersectpoint = Point(intersectlon,45.0)
                              templist.append(intersectpoint)
                              pointlist.append(Point(point.longitude,point.latitude))
    
                              # Build a polygon from the temporary list of points
                              temppoly=Polygon([[p.x, p.y] for p in templist])
                              temparea = getArea(temppoly)
                              print 'Temp area to add: {:.0f} m2'.format(temparea)
                              area = area + temparea
                              # reset templist
                              templist = []
                              templist.append(intersectpoint)
                              
                        # save current point in lastpoint
                        lastpoint = point
                        pointlist.append(Point(point.longitude,point.latitude))
                        templist.append(Point(point.longitude,point.latitude))
                previous=point

    # End looping on points in the track
     
    # Calculate distance from first to last (projected on the 45//)
    # Projection of the track on the 45//

    # Build a Point for the last point projected onthe 45
    thelastpoint = Point(lastpoint.longitude,45.0)
    pointlist.append(thelastpoint)
    templist.append(thelastpoint)
    # Build the latest polygon 
    temppoly=Polygon([[p.x, p.y] for p in templist])
    temparea = getArea(temppoly)
    print '(Last)Temp area to add: {:.0f} m2'.format(temparea)
    area = area + temparea
    
    #Build a polygon from the list of points
    newpoly=Polygon([[p.x, p.y] for p in pointlist])

    lastpoint.latitude=45.0
    firstpoint.latitude=45.0

    if firstpoint.time is None:
        starttime='no datetime<b>found within the track'
    else:
        starttime=firstpoint.time.strftime("%d %b %Y %H:%M")
    if lastpoint.time is None:
        endtime='no datetime<b>found within the track'
    else:
        endtime=lastpoint.time.strftime("%d %b %Y %H:%M")

    distance45 = lastpoint.distance_3d(firstpoint)
    ecart45 = getArea(newpoly)
    area_km2 = area / 1000000 
    # There is bonus for uphill gain
    score= ecart45/(distance45+(uphill*10))

    print 'ecart total={0} m2'.format(round(ecart45,0))
    print 'area total={0} m2'.format(round(area,0))
    print 'area total={0} km2'.format(round(area_km2,0))
    print 'distance={0:.0f} m'.format(round(distance45,0))
    print 'cumulative elevation gain={0} m'.format(round(uphill,0))
    print 'score={0}'.format(round(score,1))

    # Add two markers for start and end of the projected distance
    type_dict = {}
    pt_dict = {}
    prop_dict = {}
    type_dict["type"]= "Feature"
    pt_dict["type"]="Point"
    type_dict["geometry"]=mapping(thelastpoint)
    prop_dict["name"]= 'end'
    prop_dict["popup"]=endtime
    type_dict["properties"]=prop_dict
    feat_list.append(type_dict)

    type_dict = {}
    pt_dict = {}
    prop_dict = {}
    type_dict["type"]= "Feature"
    pt_dict["type"]="Point"
    type_dict["geometry"]=mapping(pointzero)
    prop_dict["name"]= 'start'
    prop_dict["popup"]=starttime
    type_dict["properties"]=prop_dict
    feat_list.append(type_dict)
 
    # Add a line in between the two markers
    type_dict = {}
    pt_dict = {}
    prop_dict = {}
    type_dict["type"]= "Feature"
    pt_dict["type"]="LineString"
    type_dict["geometry"]=mapping(LineString([pointzero,thelastpoint]))
    prop_dict["name"]= 'projection'
    prop_dict["popup"]= 'distance={0:.0f} m'.format(round(distance45,0))
    type_dict["properties"]=prop_dict
    feat_list.append(type_dict)

    # Add a polygon to delimit the area between track and the 45th line
    type_dict = {}
    pt_dict = {}
    prop_dict = {}
    type_dict["type"]= "Feature"
    pt_dict["type"]="Polygon"
    gjson_dict["features"] = feat_list
    type_dict["geometry"]=mapping(Polygon(newpoly))
    prop_dict["name"]= 'area'
    prop_dict["popup"]='<b>score={0:.0f} points</b><hr>surface={1:.0f} m2<br>distance={2:.0f} m<br>denivel&eacute;e={3:.0f} m<br><br><i>calculated on:</i>'.format(round(score,0), round(ecart45,0),round(distance45,0),round(uphill,0))
    type_dict["properties"]=prop_dict
    feat_list.append(type_dict)

    return gjson_dict
         
######################################################################
#
######################################################################
def getArea(polygon):
# http://gis.stackexchange.com/questions/127607/area-in-km-from-polygon-of-coordinates
# Polygon of point using WGS84 lat/lon coordonates
    project= partial(
            pyproj.transform,
            pyproj.Proj(init='epsg:4326'),
            pyproj.Proj(proj='aea')
            )

    geom_area = ops.transform(project,polygon)

    # Return the area in m^2
    return  geom_area.area 

######################################################################
#
######################################################################
def format_time(time_s):
    if not time_s:
        return 'n/a'
    else:
        minutes = mod_math.floor(time_s / 60.)
        hours = mod_math.floor(minutes / 60.)
    return '%s:%s:%s' % (str(int(hours)).zfill(2), str(int(minutes % 60)).zfill(2), str(int(time_s % 60)).zfill(2))

######################################################################
#
######################################################################
def print_gpx_part_info(gpx_part, indentation='    '):
    """
    gpx_part may be a track or segment.
    """
    length_2d = gpx_part.length_2d()
    length_3d = gpx_part.length_3d()
    print('{}Length 2D: {:.3f}km'.format(indentation, length_2d / 1000.))
    print('{}Length 3D: {:.3f}km'.format(indentation, length_3d / 1000.))

    moving_time, stopped_time, moving_distance, stopped_distance, max_speed = gpx_part.get_moving_data()
    print('%sMoving time: %s' % (indentation, format_time(moving_time)))
    print('%sStopped time: %s' % (indentation, format_time(stopped_time)))
    #print('%sStopped distance: %sm' % stopped_distance)
    print('{}Max speed: {:.2f}m/s = {:.2f}km/h'.format(indentation, max_speed if max_speed else 0, max_speed * 60. ** 2 / 1000. if max_speed else 0))

    uphill, downhill = gpx_part.get_uphill_downhill()
    print('{}Total uphill: {:.2f}m'.format(indentation, uphill))
    print('{}Total downhill: {:.2f}m'.format(indentation, downhill))

    start_time, end_time = gpx_part.get_time_bounds()
    print('%sStarted: %s' % (indentation, start_time))
    print('%sEnded: %s' % (indentation, end_time))

    points_no = len(list(gpx_part.walk(only_points=True)))
    print('%sPoints: %s' % (indentation, points_no))

    if points_no > 0:
        distances = []
        previous_point = None
        for point in gpx_part.walk(only_points=True):
            if previous_point:
                distance = point.distance_2d(previous_point)
                distances.append(distance)
            previous_point = point
        print('{}Avg distance between points: {:.2f}m'.format(indentation, sum(distances) / len(list(gpx_part.walk()))))

##### MAIN ######
def make_parser():
    parser = mod_argparse.ArgumentParser(usage='%(prog)s [-s] [file ...]',
    description='Command line utility to extract basic statistics from gpx file(s)')
    return parser

def main(argv):
	inputfile = ''
	outputfile = ''
	try:
	   opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
	except getopt.GetoptError:
   		print 'loop.py -i <inputfile> -o <outputfile>'
   		sys.exit(2)
	for opt, arg in opts:
          if opt == '-h':
      		print 'loop.py -i <inputfile> -o <outputfile>'
                sys.exit()
          elif opt in ("-i", "--ifile"):
      		inputfile = arg
          elif opt in ("-o", "--ofile"):
                outputfile = arg
        if outputfile=='':
            outputfile='out.json'

        gpx_file = open(inputfile, 'r')
        ecart=0 
        distance=0 
        geojson=gpxTracksTo45(gpx_file)
        # Dump serializaed geo json dictionnary
        with open(outputfile, 'w') as outfile:
             json.dump(geojson, outfile, sort_keys = True, indent = 4,
		   ensure_ascii=False)
 
if __name__ == '__main__':
        main(sys.argv[1:])

