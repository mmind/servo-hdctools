# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Python version of Servo hardware debug & control board server."""
import logging
import optparse
import os
import SimpleXMLRPCServer
import sys

import system_config
import servo_server


# TODO(tbroch) determine version string methodology.
VERSION = "0.0.1"


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
  parser.add_option("", "--port", default=9999, type=int,
                    help="port for server to listen on")
  parser.add_option("-v", "--vendor", default=0x0403, type=int,
                    help="vendor id of ftdi device to interface to")
  parser.add_option("-p", "--product", default=0x6011, type=int,
                    help="USB product id of ftdi device to interface with")
  parser.add_option("-s", "--serialname", default=None, type=str,
                    help="device serialname stored in eeprom")
  parser.add_option("-c", "--config", type=str, action="append",
                    help="system config files (XML) to read")
  # TODO(tbroch) add arg for declaring interfaces
  parser.set_usage(parser.get_usage() + examples)
  return parser.parse_args()

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

  scfg = system_config.SystemConfig()
  if options.config is None:
    raise ServodError("Must supply at least one config file ( -c <file> )")

  for cfg_file in options.config:
    scfg.add_cfg_file(cfg_file)

  logger.debug("\n" + scfg.display_config())

  servod = servo_server.Servod(scfg, vendor=options.vendor,
                               product=options.product,
                               serialname=options.serialname)
  server = SimpleXMLRPCServer.SimpleXMLRPCServer((options.host, options.port))
  server.register_introspection_functions()
  server.register_multicall_functions()
  server.register_instance(servod)
  logger.info("Listening on %s port %s" % (options.host, options.port))
  server.serve_forever()

if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    sys.exit(0)
