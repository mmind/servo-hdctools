# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Server to support long-polling for values of I/O ports.

Current it only supports Linux GPIO interface.
"""

import logging
import optparse
import os
import SimpleXMLRPCServer
import socket
import SocketServer
import sys

import poll_common
from poll_server import Polld, PolldError


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
    '%prog is a server to minitor I/O ports. '
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
  parser.add_option('', '--host', default=poll_common.DEFAULT_HOST, type=str,
                    help='hostname to start server on')
  parser.add_option('', '--port', default=poll_common.DEFAULT_PORT, type=int,
                    help='port for server to listen on')
  parser.set_usage(parser.get_usage() + examples)
  return parser.parse_args()


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
    raise PolldError(error)

  polld = Polld()
  server.register_introspection_functions()
  server.register_multicall_functions()
  server.register_instance(polld)
  logger.info('Listening on %s port %s' % (options.host, options.port))
  server.serve_forever()


def main():
  """Main function wrapper to catch exceptions properly."""
  try:
    real_main()
  except KeyboardInterrupt:
    sys.exit(0)
  except PolldError as e:
    sys.stderr.write('Error: ' + e.message)
    sys.exit(1)


if __name__ == '__main__':
  main()
