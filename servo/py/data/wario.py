#!/usr/bin/env python
# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper script to generate system control files for Wario adcs
"""
import os
import sys
import time

def dump_adcs():
  """Dump xml formatted adcs for wario board for servod.
  """
  regs = ['cfg', 'shv', 'busv', 'pwr', 'cur', 'cal']
  inas = [(0x40, 'ppvar_vbat', 19.5, 0.030),
          (0x41, 'pp5000', 5.0,  0.010),
          (0x42, 'pp3300', 3.3,  0.010),
          (0x43, 'pp1050', 1.05, 0.030),
          (0x44, 'pp1800', 1.8,  0.010),
          (0x45, 'vdd_core', 1.5,  0.010),
          (0x46, 'vdd_cpu', 1.5,  0.010),
          (0x47, 'ppsm2_vout', 4.5,  0.010),
          (0x48, 'pp1800_cpumem', 1.8,  0.010),
          (0x49, 'pp1800_dram', 1.8,  0.100),
          (0x4a, 'ppvar_bl', 19.5, 0.100),
          (0x4b, 'pp3300_lcd', 3.3,  0.100),
          (0x4c, 'pp3300_wwan', 3.3,  0.010),
          (0x4d, 'pp1800_wlan', 1.8,  0.100),
          (0x4e, 'pp3300_wlan', 3.3,  0.100),
          (0x4f, 'pp3300_lvdsd', 3.3,  0.100)]
  rsp = ""
  for (slv, name, nom, sense) in inas:
    slv = hex(slv)
    nom = str(nom)
    sense = str(sense)
    rsp += "<control><name>"+name+"_mv</name>\n"
    rsp += "<doc>Voltage of "+name+" rail in millivolts</doc>\n"
    rsp += "<params interface=\"2\" drv=\"ina219\" slv=\""+slv+"\""
    rsp += " rsense=\""+sense+"\" type=\"get\" subtype=\"millivolts\""
    rsp += " nom=\""+nom+"\">\n</params></control>\n"
    rsp += "<control><name>"+name+"_ma</name>\n"
    rsp += "<doc>Current of "+name+" rail in milliamps</doc>\n"
    rsp += "<params interface=\"2\" drv=\"ina219\" slv=\""+slv+"\""
    rsp += " rsense=\""+sense+"\" type=\"get\" subtype=\"milliamps\">\n"
    rsp += "</params></control>\n"
    rsp += "<control><name>"+name+"_mw</name>\n"
    rsp += "<doc>Power of "+name+" rail in milliwatts</doc>\n"
    rsp += "<params interface=\"2\" drv=\"ina219\" slv=\""+slv+"\""
    rsp += " rsense=\""+sense+"\" type=\"get\" subtype=\"milliwatts\">\n"
    rsp += "</params></control>\n"
    i = 0
    for reg in regs:
      rsp += "<control><name>"+name+"_"+reg+"_reg</name>\n"
      rsp += "<doc>Raw register value of "+reg+"</doc>"
      rsp += "<params interface=\"2\" drv=\"ina219\" slv=\""+slv+"\""
      rsp += " type=\"get\" subtype=\"readreg\" reg=\""+str(i)+"\""
      rsp += " fmt=\"hex\">\n</params></control>"
      i += 1
  return rsp

def main():
  f = open('wario.xml', 'w')
  f.write("<?xml version=\"1.0\"?>\n<root>\n")
  f.write("<!-- Autogenerated on "+time.asctime()+"-->")
  f.write(dump_adcs())
  f.write("</root>")
  f.close()
  rv = os.system("tidy -mi -xml wario.xml")
  if rv:
    print "Error tidying xml output"
    sys.exit(rv)
  # be sure to run 'tidy -mi -xml <file>

if __name__ == "__main__":
  main()
