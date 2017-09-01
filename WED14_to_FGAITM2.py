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
# -- build KDtree for static models
from scipy.spatial import KDTree
import numpy
import math

'''
Convert WED-1.4 Ramps and AI TaxiRoute to FG AI TrafficManagerII groundnet
Run this script in directory with earth.wed.xml
Groundnet will be written to files ICAO.groundnet.xml
'''

import xml.etree.ElementTree as ET
import os
from xml.dom.minidom import parseString
import logging

def calc_distance(node1, node2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """    
    dlon = math.radians(node2[1]) - math.radians(node1[1])
    dlat = math.radians(node2[0]) - math.radians(node1[0])
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(node1[0])) * math.cos(math.radians(node2[0])) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    # 6367 km is the radius of the Earth
    km = 6367 * c
#     print km
    return km

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
    parser.add_argument("-c", "--connect-parking", dest="connect_parking", action="store_true",
                        help="connect parking positions (WED)", required=False)
    parser.add_argument("-n", "--nesting", dest="nesting", action="store_true",
                        help="enable deep nesting support (WED)", default=False, required=False)
    
    args = parser.parse_args()

    #Open
    filexml = ET.parse  (args.filename)
    objects = filexml.getroot().find("objects")
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    if args.connect_parking:
        logging.info("Unconnected parkings will be connected to nearest node")
    
    #Iterate over airports
    for airport in objects.findall("*[@class='WED_Airport']"):
        airport_id = airport.get("id")
        airport_name = airport.find("hierarchy").get("name")
        airport_icao = airport.find("airport").get("icao")
        logging.info("Processing %s (%s)" %( airport_name, airport_icao))
        groups = []
        for grp in objects.findall("*[@class='WED_Group']"):
            if grp.get("parent_id") != airport_id:
                 continue
            groups.append( grp.get("id"))
        
        #Collect
        TaxiRouteNode = []
        for obj in objects.findall("*[@class='WED_TaxiRouteNode']"):
            if obj.get("parent_id") != airport_id and not obj.get("parent_id") in groups:
                continue
            point = obj.find ("point")
            TaxiRouteNode.append ({'id': obj.get ("id"), \
                                  'lat_deg': eval(point.get("latitude")), \
                                  'lon_deg': eval(point.get("longitude")), \
                                  'lat': latNS (eval(point.get("latitude"))), \
                                  'lon': lonEW (eval(point.get("longitude")))})
        #Count runways
        num_runways = 0
        for obj in objects.findall("*[@class='WED_Runway']"):
            if obj.get("parent_id") != airport_id and not obj.get("parent_id") in groups:
                continue
            num_runways += 1
            
        
        TaxiRoute = []
        RunWays = []
        RunWayEnds = {}
        for obj in objects.findall("*[@class='WED_TaxiRoute']"):
            if obj.get("parent_id") != airport_id and not obj.get("parent_id") in groups:
                continue
            beg, en = obj.find ("sources").findall ("source")
            runway_name = obj.find("taxi_route").attrib["runway"]
            if runway_name and not runway_name == "None":
        #Find the runways (could be nicer if Python would support more XPath)
        #We want to ignore them since flightgear doesn't want them
                RunWays.append({'name':runway_name,\
                                'begin':beg.attrib["id"], \
                                'end':en.attrib["id"], \
                                })
                #TODO Check for doubles (Warning since we want single element runways)
                RunWayEnds[beg.attrib["id"]] = runway_name 
                RunWayEnds[en.attrib["id"]] = runway_name                 
            else:
                TaxiRoute.append ({'begin':beg.attrib["id"], \
                                   'end':en.attrib["id"], \
                                   'name':obj.find("hierarchy").attrib["name"], \
                                   'oneway':obj.find("taxi_route").attrib["oneway"], \
                                   'isPushBackRoute':'0' \
                                  })
            
            
        RampPosition = []
        for obj in objects.findall("*[@class='WED_RampPosition']"):
            if obj.get("parent_id") != airport_id and not obj.get("parent_id") in groups:
                continue
            RampPosition.append({ \
                     'id': obj.attrib['id'], \
                   'name': obj.find("hierarchy").get("name"), \
                'lat_deg': eval(obj.find("point").get("latitude")), \
                'lon_deg': eval(obj.find("point").get("longitude")), \
                    'lat': latNS (eval(obj.find("point").get("latitude"))), \
                    'lon': lonEW (eval(obj.find("point").get("longitude"))), \
                'heading': obj.find("point").get("heading"), \
                   'type': obj.find("ramp_start").get("type"), \
                   'type': obj.find("ramp_start").get("ramp_op_type") 
                                })
        
        
        
        #Make XML
        groundnet = ET.Element("groundnet")
        groundnet.append(ET.Comment("Groundnet for %s (%s)" % (airport_name,airport_icao)))

#         transformed_list = [ [x['id'], x['lat_deg'], x['lon_deg']] for x in TaxiRouteNode]
        transformed_list = [[x['lat_deg'], x['lon_deg']] for x in TaxiRouteNode]
        if len(transformed_list) == 0:
            logging.info('No routepoints for nearest search')
            tree = None
        else:
            tree = KDTree(transformed_list, leafsize=3)        
        
        parkingList = ET.SubElement (groundnet, "parkingList")
        for ramp in RampPosition:
            Parking = ET.SubElement(parkingList, "Parking")
            Parking.set ("index", ramp['id'] )
            Parking.set ("name", ramp['name'])
            Parking.set ("lat", ramp['lat'])
            Parking.set ("lon", ramp['lon'])
            Parking.set ("heading", ramp['heading'])
            #dummy below
            print "Ramptype : " + ramp['type']
            if ramp['type'] == "Gate":
                Parking.set ("type", "gate")
            elif ramp['type'] == "Misc":
                Parking.set ("type", "gate")
            else: 
                Parking.set ("type", "tie-down")
            Parking.set ("number", "")
            #TODO calc by type
            Parking.set ("radius", "40")
            Parking.set ("airlineCodes", "")     
            
            if not tree is None:
#                 print [ramp['lat_deg'], ramp['lon_deg']]
                nearest = tree.query_ball_point( [ramp['lat_deg'], ramp['lon_deg']], 0.01)
                dist = [(calc_distance( [ramp['lat_deg'], ramp['lon_deg']], tree.data[x]), tree.data[x], TaxiRouteNode[x]) for x in nearest]
#                 print tree.data[dist[0]]
                dist = sorted(dist, key=lambda point: point[0])
                if dist[0][0]>0.5:
                    logging.warn("Long distance route for %s (%d3)", ramp['name'], dist[0][0] )
                nearest_node = dist[0][2]
                route = {'begin': nearest_node['id'], 'end': ramp['id'], 'name': ramp['name'], 'oneway': '0', 'isPushBackRoute':'1'}
                TaxiRoute.append(route)
                logging.debug("Added route for ramp %s", ramp['name'])
#                 print dist[0][2]
            #TODO        
        
        TaxiNodes = ET.SubElement (groundnet, "TaxiNodes")

        for point in TaxiRouteNode:
            node = ET.SubElement(TaxiNodes, "node")
            node.set ("index", point['id'])
            node.set ("lat", point['lat'])
            node.set ("lon", point['lon'])
            if point['id'] in RunWayEnds:                
                node.set ("isOnRunway", "1")
            else:
                node.set ("isOnRunway", "0")
            node.set ("holdPointType", "none")
            
        
        #Start building the flightgear groundnet
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
                arc.set ("isPushBackRoute", route['isPushBackRoute'])
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

