# Copyright 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""RPCServer to support serial connection to Plankton-Raiden of Dolphin."""

from __future__ import print_function
import logging
import optparse
import os
import SimpleXMLRPCServer
import socket
import SocketServer
import subprocess
import sys
import time

import serial_server

# server address
DEFAULT_PORT = 9997
DEFAULT_HOST = 'localhost'

# definition of plankton raiden parameters
PLANKTON_SERIAL_PARAMS = {'driver': 'ftdi_sio',
                          'baudrate': 115200,
                          'bytesize': 8,
                          'parity': 'N',
                          'stopbits': 1,
                          'timeout': 3,
                          'writeTimeout': 3}

PLANKTON_CONN_PORT = ['1-1.3.2',  # left raiden
                      '1-1.2.4',  # right raiden
                     ]

DOLPHIN_PARAMS =[{'serial_params': PLANKTON_SERIAL_PARAMS,
                  'port_index': port} for port in PLANKTON_CONN_PORT]


class ThreadedXMLRPCServer(SocketServer.ThreadingMixIn,
                           SimpleXMLRPCServer.SimpleXMLRPCServer):
  """Threaded SimpleXMLRPCServer."""
  daemon_threads = True
  allow_reuse_address = True


def parse_args():
  """Parses commandline arguments.

  Returns:
    tuple (options, args) from optparse.parse_args().
  """
  description = (
    '%prog is a server for Dolphin serial control. '
    'This server communicates with the client via xmlrpc.'
    )

  examples = (
    '\nExamples:\n'
    '   > %prog -p 8888\n\tLaunch server listening on port 8888\n'
    )

  parser = optparse.OptionParser()
  parser.description = description
  parser.add_option('-d', '--debug', action='store_true', default=False,
                    help='enable debug messages')
  parser.add_option('', '--host', default=DEFAULT_HOST, type=str,
                    help='hostname to start server on')
  parser.add_option('', '--port', default=DEFAULT_PORT, type=int,
                    help='port for server to listen on')
  parser.set_usage(parser.get_usage() + examples)
  return parser.parse_args()


def modprobe_ftdi_driver():
  """Modprobe FTDI driver on Plankton-Raiden manually."""
  subprocess.call(['modprobe', 'ftdi_sio'])
  with open('/sys/bus/usb-serial/drivers/ftdi_sio/new_id', 'w') as f:
    f.write('18d1 500c\n')
  time.sleep(1)  # Wait after modprobe for TTY connection


def real_main():
  (options, args) = parse_args()
  loglevel = logging.INFO
  format='%(asctime)s - %(name)s - %(levelname)s'
  if options.debug:
    loglevel = logging.DEBUG
    format += ' - %(filename)s:%(lineno)d:%(funcName)s'
  format += ' - %(message)s'
  logging.basicConfig(level=loglevel, format=format)

  logger = logging.getLogger(os.path.basename(sys.argv[0]))
  logger.info('Start')

  try:
    server = ThreadedXMLRPCServer((options.host, options.port),
                                  logRequests=options.debug,
                                  allow_none=True)
  except socket.error as e:
    error = "Problem opening Server's socket: %s" % e
    logger.fatal(error)
    raise serial_server.SerialServerError(error)

  modprobe_ftdi_driver()
  dolphin_server = serial_server.SerialServer(DOLPHIN_PARAMS)
  server.register_introspection_functions()
  server.register_multicall_functions()
  server.register_instance(dolphin_server)
  logger.info('Listening on %s port %s' % (options.host, options.port))
  server.serve_forever()


def main():
  """Main function wrapper to catch exceptions properly."""
  try:
    real_main()
  except KeyboardInterrupt:
    sys.exit(0)
  except serial_server.SerialServerError as e:
    sys.stderr.write('Error: ' + e.message)
    sys.exit(1)


if __name__ == '__main__':
  main()
