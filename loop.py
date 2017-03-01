#!/usr/bin/python
# -*- coding: utf-8 -*-
######################################################################
# * $Id: 
# * $Revision:  $
# * $Date:  $
# * Created By: ldo
######################################################################
import argparse as mod_argparse
import math as mod_math
import gpxpy
import gpxpy.gpx
import pyproj    
import shapely
import shapely.ops as ops
from shapely.geometry.polygon import Polygon
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
    # Need to determine overall direction (E->W is positive, W-> E is negative)
    direction=-1
    #direction=1
    # Loop on all available points (WGS 84)
    for track in gpx.tracks:
        print_gpx_part_info(track, indentation='        ')
        for segment in track.segments:
            previous = segment.points[0]
            # first point of track is always considered valid, will be used to determine the total distance projected on the 45 parralell
            firstpoint = segment.points[0]
            for point in segment.points[1:]:
		print ' # Point with lon/lat {0}/{1}'.format(point.longitude,point.latitude)
                # Discard point if going backward
                # Hopefully there won't be any track crossing longitude 0 ( which is the atlantic)

                if ((point.longitude - previous.longitude)*direction > 0) or ((point.longitude - breakpoint_lon)*direction > 0) :
			#track is moving in the wrong direction or in the right direction but still not after the breakpoint
			print 'Point with lon/lat {0}/{1} has been discarded.'.format(point.longitude,point.latitude)
                        # Need to capture longitude from which track start moving in the wrong direction
                        if (wrongdir == False):
			     breakpoint_lon = previous.longitude
                             print 'Wait for the lon to be > {0}'.format(breakpoint_lon)
                        wrongdir=True
                else:
                        wrongdir=False
                	# Check if segment cross the line
                	# if yes, determine intersection point
                	# Build a polygon with 7 points
                	# else
                	# Build a polygon with 5 points
                	poly = Polygon([(previous.longitude,previous.latitude), (point.longitude,point.latitude), 
                                        (point.longitude, 45.0), (previous.longitude, 45.0), (previous.longitude,previous.latitude)])
                	valid=poly.is_valid
	        	if valid:
                    		area = getArea(poly)
                		print valid,area
                		ecart45=ecart45+area
                	else:
				print 'Invalid Polygon ...'
                previous=point
    # Calculate distance from first to last (projected on the 45//)
    lastpoint = point
    distance45 = lastpoint.distance_3d(firstpoint)

    return ecart45,distance45
         
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

def main():
        gpx_file = open('test1.gpx', 'r')
        ecart=0 
        distance=0 
        ecart,distance=gpxTracksTo45(gpx_file)
        print 'ecart total={0} m2'.format(round(ecart,0))
        print 'distance={0} m'.format(round(distance,0))
        score= ecart/distance
        print 'score={0}'.format(round(score,2))
if __name__ == '__main__':
        main()

