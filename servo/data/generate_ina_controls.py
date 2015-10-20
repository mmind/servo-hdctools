# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper script to generate system control files for INA219 adcs."""
import imp
import os
import sys
import time

def dump_adcs(adcs, drvname='ina219', interface=2):
  """Dump xml formatted INA219 adcs for servod.

  Args:
    adcs: array of adc elements.  Each array element is a tuple consisting of:
        slv: int representing the i2c slave address plus optional channel if ADC
             (INA3221 only) has multiple channels.  For example,
               "0x40"   : address 0x40 ... no channel
               "0x40:1" : address 0x40, channel 1
        name: string name of the power rail
        sense: float of sense resitor size in ohms
        nom: float of nominal voltage of power rail.
        mux: string name of i2c mux leg these ADC's live on
        is_calib: boolean to determine if calibration is possible for this rail
    drvname: string name of adc driver to enumerate for controlling the adc.
    interface: interface index to handle low-level communication.

  Returns:
    string (large) of xml for the system config of these ADCs to eventually be
    parsed by servod daemon ( servo/system_config.py )
  """
  # Must match REG_IDX.keys() in servo/drv/ina2xx.py
  regs = ['cfg', 'shv', 'busv', 'pwr', 'cur', 'cal']

  if drvname == 'ina231':
    regs.extend(['msken', 'alrt'])
  elif drvname == 'ina3221':
    regs = ['cfg', 'shv', 'busv', 'msken']

  rsp = ""
  for (slv, name, nom, sense, mux, is_calib) in adcs:
    chan = ''
    if drvname == 'ina3221':
      (slv, chan_id) = slv.split(':')
      chan = 'channel="%s"' % chan_id

    rsp += (
      '<control><name>%(name)s_mv</name>\n'
      '<doc>Bus Voltage of %(name)s rail in millivolts on i2c_mux:%(mux)s</doc>\n'
      '<params interface="%(interface)d" drv="%(drvname)s" slv="%(slv)s" %(chan)s'
      ' mux="%(mux)s" rsense="%(sense)s" type="get" subtype="millivolts"'
      ' nom="%(nom)s">\n</params></control>\n'
      '<control><name>%(name)s_shuntmv</name>\n'
      '<doc>Shunt Voltage of %(name)s rail in millivolts on i2c_mux:%(mux)s</doc>\n'
      '<params interface="%(interface)d" drv="%(drvname)s" slv="%(slv)s" %(chan)s'
      ' mux="%(mux)s" rsense="%(sense)s" type="get" subtype="shuntmv"'
      ' nom="%(nom)s">\n</params></control>\n'
      ) % {'name':name, 'drvname':drvname, 'interface':interface, 'slv':slv,
           'mux':mux, 'sense':sense, 'nom':nom, 'chan':chan}

    # in some instances we may not know sense resistor size ( re-work ) or other
    # custom factors may not allow for calibration and those reliable readings
    # on the current and power registers.  This boolean determines which
    # controls should be enumerated based on rails input specification
    if is_calib:
      rsp += (
      '<control><name>%(name)s_ma</name>\n'
      '<doc>Current of %(name)s rail in milliamps on i2c_mux:%(mux)s</doc>\n'
      '<params interface="%(interface)d" drv="%(drvname)s" slv="%(slv)s" %(chan)s'
      'rsense="%(sense)s" type="get" subtype="milliamps">\n'
      '</params></control>\n'
      '<control><name>%(name)s_mw</name>\n'
      '<doc>Power of %(name)s rail in milliwatts on i2c_mux:%(mux)s</doc>\n'
      '<params interface="%(interface)d" drv="%(drvname)s" slv="%(slv)s" %(chan)s'
      ' mux="%(mux)s" rsense="%(sense)s" type="get" subtype="milliwatts">\n'
      '</params></control>\n')  % {'name':name, 'drvname':drvname,
                                   'interface':interface, 'slv':slv,
                                   'mux':mux, 'sense':sense, 'nom':nom, 'chan':chan}

    for reg in regs:
      rsp += (
        '<control><name>%(name)s_%(reg)s_reg</name>\n'
        '<doc>Raw register value of %(reg)s on i2c_mux:%(mux)s</doc>'
        '<params cmd="get" interface="%(interface)d"'
        ' drv="%(drvname)s" slv="%(slv)s" %(chan)s'
        ' subtype="readreg" reg="%(reg)s" mux="%(mux)s"'
        ' fmt="hex">\n</params>') % {'name':name, 'drvname':drvname,
                                     'interface':interface, 'slv':slv,
                                     'mux':mux, 'sense':sense,
                                     'reg':reg, 'chan':chan}
      if reg in ["cfg", "cal"]:
        map_str = ""
        if reg == "cal":
          map_str = ' map="calibrate"'
        rsp += (
          '<params cmd="set" interface="%(interface)d"'
          ' drv="%(drvname)s" slv="%(slv)s" %(chan)s'
          ' subtype="writereg" reg="%(reg)s" mux="%(mux)s"'
          ' fmt="hex"%(map)s>\n</params></control>') % {'drvname':drvname,
                                                 'interface':interface,
                                                 'slv':slv, 'mux':mux,
                                                 'sense':sense,
                                                 'reg':reg,
                                                 'chan':chan,
                                                 'map':map_str}
      else:
        rsp += ('</control>')
  return rsp

def main():
  if len(sys.argv) != 3:
    raise Exception("Missing args.  %s <filename.py> <drvname>" % sys.argv[0])

  module_name = sys.argv[1]
  ina_pkg = imp.load_module(module_name, *imp.find_module(module_name))
  drvname = sys.argv[2]
  drvpath = os.path.join(os.environ['HDCTOOLS_SOURCE_DIR'], '..', 'drv',
                         drvname + '.py')
  if not os.path.isfile(drvpath):
    raise Exception("Unable to locate driver for %s at %s" % (drvname, drvpath))

  drvxml = os.path.join(os.environ['HDCTOOLS_SOURCE_DIR'], '..', 'data',
                        'ina2xx.xml')

  if hasattr(ina_pkg, 'interface'):
    interface = ina_pkg.interface
    if type(interface) != int:
      raise Exception("Invalid interface %r, should be int" % interface)
  else:
    interface = 2  # default I2C interface

  f = open('%s.xml' % module_name, 'w')
  f.write("<?xml version=\"1.0\"?>\n<root>\n")
  f.write("<!-- Autogenerated on "+time.asctime()+"-->\n")
  if os.path.isfile(drvxml):
    f.write("<include><name>ina2xx.xml</name></include>\n")

  try:
    f.write(ina_pkg.inline)
  except AttributeError:
    pass
  except Exception:
    raise

  f.write(dump_adcs(ina_pkg.inas, drvname, interface))
  f.write("</root>")
  f.close()
  rv = os.system("tidy -quiet -mi -xml %s.xml" % module_name)
  if rv:
    print "Error tidying xml output"
    sys.exit(rv)
  # be sure to run 'tidy -mi -xml <file>

if __name__ == "__main__":
  main()
