#!/usr/bin/python
# -*- coding: utf-8 -*-
######################################################################
# * $Id: 
# * $Revision:  $
# * $Date:  $
# * Created By: ldo
######################################################################
import gpxpy
import gpxpy.gpx
import pyproj    
import shapely
import shapely.ops as ops
from shapely.geometry.polygon import Polygon
from functools import partial


# Parsing an existing file:
# -------------------------

def gpxTracksTo45(gpx_content):
    gpx = gpxpy.parse(gpx_content)

    # Check if max and min lat and long are available in metadata.
    
    # Determine first and last point (max[lon], Min[Lon])
    
    # Calculate distance from first to last (projected on the 45//)

    # Loop on all available points (WGS 84)
    for track in gpx.tracks:
        for segment in track.segments:
            previous = segment.points[0]
            for point in segment.points[1:]:
                print 'Segment:({0},{1}) --> {3},{4}) / {2} --> {5}'.format(previous.latitude,previous.longitude, previous.elevation,point.latitude, point.longitude, point.elevation)
                # Convert 
                print 'Poly:({0},{1}) --> {2},{3} --> {4},{5} --> {6},{7} --> {8},{9}'.format(previous.longitude,previous.latitude,point.longitude,point.latitude,point.longitude, 45.0, previous.longitude, 45.0,previous.longitude,previous.latitude)
                poly = Polygon([(previous.longitude,previous.latitude), (point.longitude,point.latitude), (point.longitude, 45.0), (previous.longitude, 45.0), (previous.longitude,previous.latitude)])
                valid=poly.is_valid
	        if valid:
                    	area = getArea(poly)
                	print valid,area
                else:
			print 'Invalid Polygon ...'
			poly2 = poly.buffer(0)				
                        poly2.is_valid
                    	area = getArea(poly2)
                previous=point

def getArea(polygon):
# http://gis.stackexchange.com/questions/127607/area-in-km-from-polygon-of-coordinates
# Polygon of point using WGS84 lat/lon coordonates
# lat1, minimum latitude
# lat2, maximum latitude 
    print 'lat1,lat2:{0},{1}'.format(polygon.bounds[1],polygon.bounds[3])
    project= partial(
            pyproj.transform,
            pyproj.Proj(init='epsg:4326'),
            pyproj.Proj(proj='aea')
            )
    #            lat1=polygon.bounds[1],
    #            lat2=polygon.bounds[3]))

    geom_area = ops.transform(project,polygon)

    # Return the area in m^2
    return  geom_area.area 
                
##### MAIN ######
def main():
        gpx_file = open('test1.gpx', 'r')
        gpxTracksTo45(gpx_file)
        
if __name__ == '__main__':
        main()
