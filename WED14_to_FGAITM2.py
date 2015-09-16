#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  WED14_to_FGAITM2.py
#  
#  Copyright 2015 Vadym Kukhtin <valleo@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

'''
Convert WED-1.4 Ramps and AI TaxiRoute to FG AI TrafficManagerII groundnet
Run this script in directory with earth.wed.xml
Groundnet will be written in newGroundNet.xml
'''

import xml.etree.ElementTree as ET
import os
from xml.dom.minidom import parseString

def latNS (coord):
    deg = int (coord)
    if coord < 0 : line = "S" + str (deg)
    else: line = "N" + str (deg)

    min = coord - deg
    line = line + " " + str ("%.3f" % (60 * min))
    return line

def lonEW (coord):
    deg = int (coord)
    if coord < 0 : line = "W" + str (deg)
    else: line = "E" + str (deg)

    min = coord - deg
    line = line + " " + str ("%.3f" % (60 * min))
    return line

def main():
    #Open
    filexml = ET.parse  ("earth.wed.xml")
    objects = filexml.getroot().find("objects")
    
    #Collect
    TaxiRouteNode = []
    for obj in objects.findall("*[@class='WED_TaxiRouteNode']"):
        point = obj.find ("point")
        TaxiRouteNode.append ({'id': obj.get ("id"), \
                              'lat': latNS (eval(point.get("latitude"))), \
                              'lon': lonEW (eval(point.get("longitude")))})
    
    TaxiRoute = []
    for obj in objects.findall("*[@class='WED_TaxiRoute']"):
        beg, en = obj.find ("sources").findall ("source")
        TaxiRoute.append ({'begin':beg.attrib["id"], \
                             'end':en.attrib["id"], \
                            'name':obj.find("hierarchy").attrib["name"], \
                          'oneway':obj.find("taxi_route").attrib["oneway"] \
                          })
        
    RampPosition = []
    for obj in objects.findall("*[@class='WED_RampPosition']"):
        RampPosition.append({ \
                 'id': obj.attrib['id'], \
               'name': obj.find("hierarchy").get("name"), \
                'lat': latNS (eval(obj.find("point").get("latitude"))), \
                'lon': lonEW (eval(obj.find("point").get("longitude"))), \
            'heading': obj.find("point").get("heading"), \
               'type': obj.find("ramp_start").get("type") 
                            })
    
    #Make XML
    groundnet = ET.Element("groundnet")
    
    parkingList = ET.SubElement (groundnet, "parkingList")
    for ramp in RampPosition:
        Parking = ET.SubElement(parkingList, "Parking")
        Parking.set ("index", ramp['id'] )
        Parking.set ("name", ramp['name'])
        Parking.set ("lat", ramp['lat'])
        Parking.set ("lon", ramp['lon'])
        Parking.set ("heading", ramp['heading'])
        #dummy below
        Parking.set ("type", "gate")
        Parking.set ("number", "")
        Parking.set ("radius", "40")
        Parking.set ("airlineCodes", "")
    
    TaxiNodes = ET.SubElement (groundnet, "TaxiNodes")
    for point in TaxiRouteNode:
        node = ET.SubElement(TaxiNodes, "node")
        node.set ("index", point['id'])
        node.set ("lat", point['lat'])
        node.set ("lon", point['lon'])
        node.set ("isOnRunway", "0")
        node.set ("holdPointType", "none")
    
    TaxiWaySegments = ET.SubElement (groundnet, "TaxiWaySegments")
    for route in TaxiRoute:
        arc = ET.SubElement (TaxiWaySegments, "arc")
        arc.set ("begin", route['begin'])
        arc.set ("end", route['end'])
        arc.set ("isPushBackRoute", "0")
        arc.set ("name", route['name'])
    
        #reverse arc
        if route['oneway'] <> "1":
            arc = ET.SubElement (TaxiWaySegments, "arc")
            arc.set ("begin", route['end'])
            arc.set ("end", route['begin'])
            arc.set ("isPushBackRoute", "0")
            arc.set ("name", route['name'])
    
    #Save
    basedir = os.getcwd()
    file_groundnet = open (os.path.join (basedir,  "newGroundNet.xml"), "w")
    ps = parseString (ET.tostring (groundnet))
    file_groundnet.writelines (ps.toprettyxml(indent=" "))
    file_groundnet.close()
    
    return 0

if __name__ == '__main__':
    main()

