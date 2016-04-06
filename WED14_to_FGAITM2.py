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
import argparse

'''
Convert WED-1.4 Ramps and AI TaxiRoute to FG AI TrafficManagerII groundnet
Run this script in directory with earth.wed.xml
Groundnet will be written to files ICAO.groundnet.xml
'''

import xml.etree.ElementTree as ET
import os
from xml.dom.minidom import parseString
import logging

def latNS (coord):
    deg = int (coord)
    if coord < 0 :
        line = "S" + str (-deg) + " " + str ("%.3f" % (-60 * (coord - deg)))
    else:
        line = "N" + str (deg) + " " + str ("%.3f" % (60 * (coord - deg)))

    return line

def lonEW (coord):
    deg = int (coord)
    if coord < 0 :
        line = "W" + str (-deg) + " " + str ("%.3f" % (-60 * (coord - deg)))
    else:
        line = "E" + str (deg) + " " + str ("%.3f" % (60 * (coord - deg)))

    return line

def main():
    
    parser = argparse.ArgumentParser(description="wed2fg reads a Worldeditor (WED) file and generates flightgear groundnets ")
    parser.add_argument("-f", "--file", dest="filename",
                        help="read filename", default="earth.wed.xml", required=False)
    parser.add_argument("-o", "--output_dir", dest="output_dir",
                        help="use output directory", default=".", required=False)
    parser.add_argument("-s", "--subdirs", dest="subdirs", action="store_true",
                        help="generate subdirectories", required=False)
    
    args = parser.parse_args()

    #Open
    filexml = ET.parse  (args.filename)
    objects = filexml.getroot().find("objects")
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    
    #Iterate over airports
    for airport in objects.findall("*[@class='WED_Airport']"):
        airport_id = airport.get("id")
        airport_name = airport.find("hierarchy").get("name")
        airport_icao = airport.find("airport").get("icao")
        logging.info("Processing %s (%s)" %( airport_name, airport_icao))
        
        #Collect
        TaxiRouteNode = []
        for obj in objects.findall("*[@class='WED_TaxiRouteNode']"):
            if obj.get("parent_id") != airport_id:
                continue
            point = obj.find ("point")
            TaxiRouteNode.append ({'id': obj.get ("id"), \
                                  'lat': latNS (eval(point.get("latitude"))), \
                                  'lon': lonEW (eval(point.get("longitude")))})
        
        TaxiRoute = []
        for obj in objects.findall("*[@class='WED_TaxiRoute']"):
            if obj.get("parent_id") != airport_id:
                continue
            beg, en = obj.find ("sources").findall ("source")
            TaxiRoute.append ({'begin':beg.attrib["id"], \
                                 'end':en.attrib["id"], \
                                'name':obj.find("hierarchy").attrib["name"], \
                              'oneway':obj.find("taxi_route").attrib["oneway"] \
                              })
            
        RampPosition = []
        for obj in objects.findall("*[@class='WED_RampPosition']"):
            if obj.get("parent_id") != airport_id:
                continue
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
        groundnet.append(ET.Comment("Groundnet for %s (%s)" % (airport_name,airport_icao)))
        
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
        basedir = os.path.abspath(args.output_dir)
        if args.subdirs:
            if not os.path.exists(os.path.join (basedir, airport_icao[0], airport_icao[1], airport_icao[2])):
                os.makedirs(os.path.join (basedir, airport_icao[0], airport_icao[1], airport_icao[2]))
            file_groundnet = open (os.path.join (basedir, airport_icao[0], airport_icao[1], airport_icao[2],  airport_icao + ".groundnet.xml"), "w")
        else:
            file_groundnet = open (os.path.join (basedir,  airport_icao + ".groundnet.xml"), "w")
        ps = parseString (ET.tostring (groundnet))
        file_groundnet.writelines (ps.toprettyxml(indent="  "))
        file_groundnet.flush()
        file_groundnet.close()
    
    return 0

if __name__ == '__main__':
    main()

