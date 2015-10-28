# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Python version of Servo hardware debug & control board server."""

import errno
import logging
import optparse
import os
import pkg_resources
import select
import SimpleXMLRPCServer
import socket
import sys
import usb

import ftdi_common
import multiservo
import servo_interfaces
import servo_server
import system_config


VERSION = pkg_resources.require('servo')[0].version

MAX_ISERIAL_STR = 128

# If user does not specify a port to use, try ports in this range. Traverse
# the range from high to low addresses to maintain backwards compatibility
# (the first checked default port is 9999, the range is such that all possible
# port numbers are 4 digits).
DEFAULT_PORT_RANGE = (9990, 9999)

# This text file holds servod configuration parameters. This is especially
# handy for multi servo operation.
#
# The file format is pretty loose:
#  - text starting with # is ignored til the end of the line
#  - empty lines are ignored
#  - configuration lines consist of up to 4 comma separated fields (all
#    but the first field optional):
#        servo-name, serial-number, port-number, board-name
#
#    where
#     . servo-name - a user defined symbolic name, just a reference
#                     to a certain servo board
#     . serial-number - serial number of the servo board this line pertains to
#     . port-number - desired port number for servod for this board, can be
#                     overridden by the command line switch --port or
#                     environment variable setting SERVOD_PORT
#     . board-name - board configuration file to use, can be
#                     overridden by the command line switch --board
#
# Since the same parameters could be defined using different means, there is a
# hierarchy of definitions:
#   command line <- environment definition <- rc config file
DEFAULT_RC_FILE = '/home/%s/.servodrc' % os.getenv('SUDO_USER', '')

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
                    help="port for server to listen on, by default "
                    "will try ports in %d..%d range, could also be "
                    "supplied through environment variable SERVOD_PORT" %
                    DEFAULT_PORT_RANGE)
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
  parser.add_option("-u", "--usbkm232", type=str,
                    help="path to USB-KM232 device which allow for "
                    "sending keyboard commands to DUTs that do not "
                    "have built in keyboards. Used in FAFT tests. "
                    "(Optional), e.g. /dev/ttyUSB0")

  multiservo.add_multiservo_parser_options(parser)
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
            (not serialname or usb_get_iserial(device).endswith(serialname)):
        matched_devices.append(device)
  return matched_devices

def find_servod_match(logger, options, all_servos, servodrc):
  """Find a servo matching one of servodrc lines

  Given a list of servod objects matching discovered servos, display the list
  to the user and check if there is a configuration file line corresponding to
  one of the servos.

  If a line like that exists, and it includes options which are not yet
  defined in the options object - set these options' values. If the option is
  already defined - report that this config line setting is ignored.

  Args:
    logger: a logging instance used by this servod driver
    options: an options object as returned by parse_options
    all_servos: a list of servod objects corresponding to discovered servo
                devices
    servodrc: a dictionary representing the contents of the servodrc file, as
              returned by parse_rc() above (if any)

  Returns:
    a matching servod object, if found, None otherwise

  Raises:
    ServodEror in case required name is not found in the config file
  """

  for servo in all_servos:
    logger.info("Found servo, vid: 0x%04x pid: 0x%04x sid: %s", servo.idVendor,
                servo.idProduct, usb_get_iserial(servo))

  # If user specified servod name in the command line - match it to the serial
  # number.

  if options.name:
    config = servodrc.get(options.name)
    if not config:
      raise ServodError("Name '%s' not in the config file" % options.name)
    options.serialname = config['sn']
  elif options.serialname:
    # Let's try finding config for a serial name
    for config in servodrc.itervalues():
      if config['sn'] == options.serialname:
        break
    else:
      return None

  if not options.serialname:
    # There is nothing to match
    return None

  for servo in all_servos:
    servo_sn = usb_get_iserial(servo)
    if servo_sn != options.serialname:
      continue

    # Match found, some sanity checks/updates before using it
    matching_servo = servo
    rc_port = config['port']
    if rc_port:
      if not options.port:
        options.port = rc_port
      elif options.port != rc_port:
        logger.warning('Ignoring rc configured port %s for servo %s',
                       rc_port, servo_sn)

    rc_board = config['board']
    if rc_board:
      if not options.board:
        options.board = rc_board
      elif options.board != rc_board:
        logger.warning('Ignoring rc configured board name %s for servo %s',
                       rc_board, servo_sn)
    return matching_servo

  raise ServodError("No matching servo found")


def choose_servo(logger, all_servos):
  """
  Let user choose a servo from available list of unique devices.

  Args:
    logger: a logging instance used by this servod driver
    all_servos: a list of servod objects corresponding to discovered servo
                devices

  Returns:
    servo object for the matching (or single) device, otherwise None
  """
  logger.info("")
  for i, servo in enumerate(all_servos):
    logger.info("Press '%d' for servo, vid: 0x%04x pid: 0x%04x sid: %s", i,
                servo.idVendor, servo.idProduct, usb_get_iserial(servo))

  (rlist, _, _) = select.select([sys.stdin], [], [], 10)
  if not rlist:
    logger.warn("Timed out waiting for your choice\n")
    return None

  rsp = rlist[0].readline().strip()
  try:
    rsp = int(rsp)
  except ValueError:
    logger.warn("%s not a valid choice ... ignoring", rsp)
    return None

  if rsp < 0 or rsp >= len(all_servos):
    logger.warn("%s outside of choice range ... ignoring", rsp)
    return None

  logging.info("")
  servo = all_servos[rsp]
  logging.info("Chose %d ... starting servod on servo "
               "vid: 0x%04x pid: 0x%04x sid: %s",
               rsp, servo.idVendor, servo.idProduct, usb_get_iserial(servo))
  logging.info("")
  return servo


def discover_servo(logger, options, servodrc):
  """Find a servo USB device to use

  First, find all servo devices matching command line options, this may result
  in discovering none, one or more devices.

  Then try matching discovered servos and the configuration defined in
  servodrc. A match this will result in reading missing options from servodrc
  file.

  If there is a match - return the matching device.

  If no match found, but there is only one servo connected - return it. If
  there is no match found and multiple servos are connected - report an error
  and return None.

  Args:
    logger: a logging instance used by this servod driver
    options: the options object returned by opt_parse
    servodrc: a dictionary representing the contents of the servodrc file, as
              returned by parse_rc() above (if any)
  Returns:
    servo object for the matching (or single) device, otherwise None
  """

  vendor, product, serialname = (options.vendor, options.product,
                                 options.serialname)
  all_servos = []
  for (vid, pid) in servo_interfaces.SERVO_ID_DEFAULTS:
    if (vendor and vendor != vid) or \
          (product and product != pid):
      continue
    all_servos.extend(usb_find(vid, pid, serialname))

  if not all_servos:
    logger.error("No servos found")
    return None

  # See if there is a matching entry in servodrc
  matching_servo = find_servod_match(logger, options, all_servos, servodrc)

  if matching_servo:
    return matching_servo

  if len(all_servos) == 1:
    return all_servos[0]

  # Let user choose a servo
  matching_servo = choose_servo(logger, all_servos)
  if matching_servo:
    return matching_servo

  logger.error("Use --vendor, --product or --serialname switches to "
               "identify servo uniquely, or create a servodrc file "
               " and use the --name switch")

  return None

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

def get_lot_id(logger, servo):
  """Get lot_id for a given servo.

  Args:
    servo: usb.Device object

  Returns:
    lot_id of the servo device.
  """
  lot_id = None
  iserial = usb_get_iserial(servo)
  logger.debug('iserial = %s', iserial)
  if not iserial:
    logger.warn("Servo device has no iserial value")
  else:
    try:
      (lot_id, _) = iserial.split('-')
    except ValueError:
      logger.warn("Servo device's iserial was unrecognized.")
  return lot_id

def get_auto_configs(logger, board_version):
  """Get xml configs that should be loaded.

  Args:
    board_version: string, board & version

  Returns:
    configs: list of XML config files that should be loaded
  """
  if board_version not in ftdi_common.SERVO_CONFIG_DEFAULTS:
    logger.warning('Unable to determine configs to load for board version = %s',
                 board_version)
    return []
  return ftdi_common.SERVO_CONFIG_DEFAULTS[board_version]

def main_function():
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
  multiservo.get_env_options(logger, options)

  if options.name and options.serialname:
    logger.error("Mutually exclusive '--name' or '--serialname' is allowed")
    sys.exit(-1)

  servo_device = discover_servo(logger, options,
                                multiservo.parse_rc(logger, options.rcfile))
  if not servo_device:
    sys.exit(-1)

  lot_id = get_lot_id(logger, servo_device)
  board_version = get_board_version(lot_id, servo_device.idProduct)
  logger.debug('board_version = %s', board_version)
  all_configs = []
  if not options.noautoconfig:
    all_configs += get_auto_configs(logger, board_version)

  if options.config:
    for config in options.config:
      # quietly ignore duplicate configs for backwards compatibility
      if config not in all_configs:
        all_configs.append(config)

  if not all_configs:
    raise ServodError("No automatic config found,"
                      " and no config specified with -c <file>")

  scfg = system_config.SystemConfig()

  if options.board:
    board_config = "servo_" + options.board + "_overlay.xml"
    if not scfg.find_cfg_file(board_config):
      logger.error("No XML overlay for board %s", options.board)
      sys.exit(-1)

    logger.info("Found XML overlay for board %s", options.board)
    all_configs.append(board_config)

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
                               board=options.board,
                               version=board_version,
                               usbkm232=options.usbkm232)
  servod.hwinit(verbose=True)
  server.register_introspection_functions()
  server.register_multicall_functions()
  server.register_instance(servod)
  logger.info("Listening on %s port %s" % (options.host, servo_port))
  server.serve_forever()

def main():
  """Main function wrapper to catch exceptions properly"""
  try:
    main_function()
  except KeyboardInterrupt:
    sys.exit(0)
  except ServodError as e:
    print "Error: ", e.message
    sys.exit(1)

if __name__ == '__main__':
  main()
