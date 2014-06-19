#!/usr/bin/env python
# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Client to test polld."""

import logging
import optparse
import sys
import xmlrpclib

import poll_common


__all__ = ['PollClientError', 'PollClient']


class PollClientError(Exception):
  """Exception class for poll_client."""
  pass


class PollClient(object):
  """Class to interface with polld via XMLRPC."""
  def __init__(self, host, tcp_port, verbose=False):
    """Constructor.

    Args:
      host: Name or IP address of servo server host.
      tcp_port: TCP port on which servod is listening on.
      verbose: Enables verbose messaging across xmlrpclib.ServerProxy.
    """
    remote = 'http://%s:%s' % (host, tcp_port)
    # TODO(jchuang): Keep alive in transport layer.
    self._server = xmlrpclib.ServerProxy(remote, verbose=verbose)

  def poll_gpio(self, gpio_port, edge):
    """Long-polls a GPIO port.

    Args:
      gpio_port: GPIO port
      edge: value in GPIO_EDGE_LIST[]

    Raises:
      PollClientError: If error occurs when polling the GPIO port.
    """
    try:
      self._server.poll_gpio(gpio_port, edge)
    except Exception as e:
      raise PollClientError('Problem to poll GPIO %s %s %s' %
                            (str(gpio_port), edge, e))


def parse_args():
  """Parses commandline arguments.

  Returns:
    tuple (options, args) from optparse.parse_args().
  """
  usage = (
    'usage: %prog [options] <io_1:port_1> <io_2:port_2> ...\n'
    '\t- io_<n> is either gpio_falling, gpio_rising, or gpio_both.\n'
    '\t- port_<n> is the GPIO port.\n'
    )

  description = (
    '%prog is command-line tool to test polld. '
    )

  examples = (
    '\nExamples:\n'
    '   > %prog gpio_falling:7\n'
    '\tLong polls GPIO port 7 when edge falling is triggered.\n'
    )

  parser = optparse.OptionParser(usage=usage)
  parser.description = description
  parser.add_option('-d', '--debug', action='store_true', default=False,
                    help='enable debug messages')
  parser.add_option('', '--host', default=poll_common.DEFAULT_HOST,
                    type=str, help='hostname of server')
  parser.add_option('', '--port', default=poll_common.DEFAULT_PORT,
                    type=int, help='port that server is listening on')
  parser.add_option('-r', '--repeat', type=int,
                    help='repeat requested command multiple times', default=1)

  parser.set_usage(parser.get_usage() + examples)
  return parser.parse_args()


def iterate(io_ports, options, pclient):
  """Perform iterations on various IO ports.

  Args:
    io_ports: list of IO ports
    options: optparse object options
    pclient: PollClient object
  """
  logger = logging.getLogger()

  for _ in xrange(options.repeat):
    for io_port in io_ports:
      io, port = io_port.split(':')
      if io not in poll_common.GPIO_EDGE_LIST:
        raise PollClientError('invalid I/O %s' % io)
      if not port.isdigit():
        raise PollClientError('invalid port %s' % port)
      pclient.poll_gpio(int(port), io)
      logger.info('poll_gpio %s succeeds', io_port)


def real_main():
  (options, io_ports) = parse_args()
  if options.debug:
    loglevel = logging.DEBUG
  else:
    loglevel = logging.INFO
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  logging.basicConfig(level=loglevel, format=format)
  pclient = PollClient(host=options.host, tcp_port=options.port,
                      verbose=options.debug)
  iterate(io_ports, options, pclient)


def main():
  try:
    real_main()
  except KeyboardInterrupt:
    sys.exit(0)
  except PollClientError as e:
    sys.stderr.write(e.message + '\n')
    sys.exit(1)


if __name__ == '__main__':
  main()
