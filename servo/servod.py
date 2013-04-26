# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Python version of Servo hardware debug & control board server."""
import errno
import logging
import optparse
import os
import SimpleXMLRPCServer
import socket
import sys
import usb

import dut
import ftdi_common
import servo_interfaces
import system_config
import servo_server


# TODO(tbroch) determine version string methodology.
VERSION = "0.0.1"

MAX_ISERIAL_STR = 128

# If user does not specify a port to use, try ports in this range. Traverse
# the range from high to low addresses to maintain backwards compatibility
# (the first checked default port is 9999, the range is such that all possible
# port numbers are 4 digits).
DEFAULT_PORT_RANGE = (9990, 9999)

class ServodError(Exception):
  """Exception class for servod server."""


# TODO(tbroch) merge w/ parse_common_args properly
def _parse_args():
  """Parse commandline arguments.

  Note, reads sys.argv directly

  Returns:
    tuple (options, args) from optparse.parse_args().
  """
  description = (
    "%prog is server to interact with servo debug & control board.  "
    "This server communicates to the board via USB and the client via "
    "xmlrpc library.  Launcher most specify at least one --config <file> "
    "in order for the server to provide any functionality.  In most cases, "
    "multiple configs will be needed to expose complete functionality "
    "between debug & DUT board."
    )
  examples = (
    "\nExamples:\n"
    "   > %prog -b <path>/data/servo.xml\n\tLaunch server on defualt host:port "
    "with configs native to servo\n"
    "   > %prog -b <file> -p 8888\n\tLaunch server listening on "
    "port 8888\n"
    "   > %prog -b <file> -v 0x18d1 -p 0x5001\n\tLaunch targetting usb device "
    "\n\twith vid:pid == 0x18d1:0x5001 (Google/Servo)\n"
    )
  parser = optparse.OptionParser(version="%prog "+VERSION)
  parser.description = description
  parser.add_option("-d", "--debug", action="store_true", default=False,
                    help="enable debug messages")
  parser.add_option("", "--host", default="localhost", type=str,
                    help="hostname to start server on")
  parser.add_option("", "--port", default=None, type=int,
                    help="port for server to listen on, by default " +
                    "will try ports in %d..%d range" % (DEFAULT_PORT_RANGE))
  parser.add_option("-v", "--vendor", default=None, type=int,
                    help="vendor id of ftdi device to interface to")
  parser.add_option("-p", "--product", default=None, type=int,
                    help="USB product id of ftdi device to interface with")
  parser.add_option("-s", "--serialname", default=None, type=str,
                    help="device serialname stored in eeprom")
  parser.add_option("-c", "--config", default=None, type=str, action="append",
                    help="system config files (XML) to read")
  parser.add_option("-b", "--board", default="", type=str, action="store",
                    help="include config file (XML) for given board")
  parser.add_option("--noautoconfig", action="store_true", default=False,
                    help="Disable automatic determination of config files")
  parser.add_option("-i", "--interfaces", type=str, default='',
                    help="ordered space-delimited list of interfaces.  " +
                    "Valid choices are gpio|i2c|uart|gpiouart|dummy")

  parser.set_usage(parser.get_usage() + examples)
  return parser.parse_args()

def usb_get_iserial(device):
  """Get USB device's iSerial string

  Args:
    device: usb.Device object

  Returns:
    iserial: USB devices iSerial string
  """
  device_handle = device.open()
  iserial = None
  try:
    iserial = device_handle.getString(device.iSerialNumber, MAX_ISERIAL_STR)
  except usb.USBError, e:
    # TODO(tbroch) other non-FTDI devices on my host cause following msg
    #   usb.USBError: error sending control message: Broken pipe
    # Need to investigate further
    pass
  except Exception, e:
    raise ServodError("failed to retrieve USB serialname")
  return iserial

def usb_find(vendor, product, serialname):
  """Find USB devices based on vendor, product and serial identifiers.

  Locates all USB devices that match the criteria of the arguments.  In the
  case where input arguments are 'None' that argument is a don't care

  Args:
    vendor: USB vendor id (integer)
    product: USB product id (integer)
    serial: USB serial id (string)

  Returns:
    matched_devices : list of pyusb devices matching input args
  """
  matched_devices = []
  for bus in usb.busses():
    for device in bus.devices:
      if (not vendor or device.idVendor == vendor) and \
            (not product or device.idProduct == product) and \
            (not serialname or usb_get_iserial(device) == serialname):
        matched_devices.append(device)
  return matched_devices

def discover_servo(logger, vendor, product, serialname):
  """Find unique servo USB device.

  Args:
    vendor: USB vendor id (integer)
    product: USB product id (integer)
    serial: USB serial id (string)

  Returns:
    devices: list of usb.Device objects that are servo board(s) or
      empty list if none
  """
  all_servos = []
  for (vid, pid) in servo_interfaces.SERVO_ID_DEFAULTS:
    if (vendor and vendor != vid) or \
          (product and product != pid):
      continue
    all_servos.extend(usb_find(vid, pid, serialname))
  return all_servos

def get_board_version(lot_id, product_id):
  """Get board version string.

  Typically this will be a string of format <boardname>_<version>.
  For example, servo_v2.

  Args:
    lot_id: string, identifying which lot device was fabbed from or None
    product_id: integer, USB product id

  Returns:
    board_version: string, board & version or None if not found
  """
  if lot_id:
    for (board_version, lot_ids) in \
          ftdi_common.SERVO_LOT_ID_DEFAULTS.iteritems():
      if lot_id in lot_ids:
        return board_version

  for (board_version, vids) in \
        ftdi_common.SERVO_PID_DEFAULTS.iteritems():
    if product_id in vids:
      return board_version

  return None

def get_auto_configs(logger, servo):
  """Get xml configs that should be loaded.

  Args:
    servo: usb.Device object

  Returns:
    configs: list of XML config files that should be loaded
  """
  lot_id = None
  iserial = usb_get_iserial(servo)
  if not iserial:
    logger.warn("Servo device has no iserial value")
  else:
    try:
      (lot_id, _) = iserial.split('-')
    except ValueError:
      logger.warn("Servo device's iserial was unrecognized.")

  board_version = get_board_version(lot_id, servo.idProduct)
  logger.debug('iserial = %s board_version = %s', iserial, board_version)
  if board_version not in ftdi_common.SERVO_CONFIG_DEFAULTS:
    logger.warning('Unable to determine configs to load for board version = %s',
                 board_version)
    return []
  return ftdi_common.SERVO_CONFIG_DEFAULTS[board_version]

def main():
  (options, args) = _parse_args()
  loglevel = logging.INFO
  format="%(asctime)s - %(name)s - %(levelname)s"
  if options.debug:
    loglevel = logging.DEBUG
    format += " - %(filename)s:%(lineno)d:%(funcName)s"
  format += " - %(message)s"
  logging.basicConfig(level=loglevel, format=format)

  logger = logging.getLogger(os.path.basename(sys.argv[0]))
  logger.info("Start")

  servo_like_devices = discover_servo(logger, options.vendor, options.product,
                                      options.serialname)
  for device in servo_like_devices:
    logger.info("Found servo, vid: 0x%04x pid: 0x%04x sid: %s", device.idVendor,
                device.idProduct, usb_get_iserial(device))
  if not servo_like_devices:
    logger.error("No servos found")
  if len(servo_like_devices) != 1:
    logger.error("Use --vendor, --product or --serialname switches to "
                 "identify servo uniquely")
    sys.exit(-1)

  servo_device = servo_like_devices[0]

  all_configs = []
  if not options.noautoconfig:
    all_configs += get_auto_configs(logger, servo_device)

  if options.config:
    for config in options.config:
      # quietly ignore duplicate configs for backwards compatibility
      if config not in all_configs:
        all_configs.append(config)

  if not all_configs:
    raise ServodError("No automatic config found,"
                      " and no config specified with -c <file>")

  scfg = system_config.SystemConfig()

  options.board = dut.get_board_name(options.board)

  if options.board:
    board_config = "servo_" + options.board + "_overlay.xml"
    if scfg.find_cfg_file(board_config):
      logger.info("Found XML overlay for board %s", options.board)
      all_configs.append(board_config)
    else:
      logger.warn("No XML overlay for board %s", options.board)

  for cfg_file in all_configs:
    scfg.add_cfg_file(cfg_file)

  logger.debug("\n" + scfg.display_config())

  logger.debug("Servo is vid:0x%04x pid:0x%04x sid:%s" % \
                 (servo_device.idVendor, servo_device.idProduct,
                  usb_get_iserial(servo_device)))

  if options.port:
    start_port = options.port
    end_port = options.port
  else:
    end_port, start_port = DEFAULT_PORT_RANGE
  for servo_port in xrange(start_port, end_port - 1, -1):
    try:
      server = SimpleXMLRPCServer.SimpleXMLRPCServer(
        (options.host, servo_port), logRequests=False)
      break
    except socket.error as e:
      if e.errno == errno.EADDRINUSE:
        continue   # Port taken, see if there is another one next to it.
      logger.fatal("Problem opening Server's socket: %s", e)
      sys.exit(-1)
  else:
    if options.port:
      err_msg = ("Port %d is busy" %  options.port)
    else:
      err_msg = ("Could not find a free port in %d..%d range" %  (
          end_port, start_port))

    logger.fatal(err_msg)
    sys.exit(-1)

  servod = servo_server.Servod(scfg, vendor=servo_device.idVendor,
                               product=servo_device.idProduct,
                               serialname=usb_get_iserial(servo_device),
                               interfaces=options.interfaces.split(),
                               board=options.board)
  servod.hwinit(verbose=True)
  server.register_introspection_functions()
  server.register_multicall_functions()
  server.register_instance(servod)
  logger.info("Listening on %s port %s" % (options.host, servo_port))
  server.serve_forever()

if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    sys.exit(0)
