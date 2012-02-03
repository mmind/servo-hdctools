#!/usr/bin/env python
# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client to control DUT hardware connected to servo debug board
"""
import collections
import logging
import numpy
import optparse
import sys
import time
import xmlrpclib


# TODO(tbroch) determine version string methodology.
VERSION = "0.0.1"

# used to aide sorting of dict keys
KEY_PREFIX='__'
# dict key for tracking sampling time
TIME_KEY = KEY_PREFIX + 'sample_msecs'

class ServoClient(object):
  """Class to link client to servod via xmlrpc.
  """
  def __init__(self):
    self.logger = logging.getLogger("dut-control")

  def initialize(self, servo_host='', servo_port='', verbose=False):
    """Initialize the client connection.

    Args:
      servo_host: name or IP address of servo server host
      servo_port: TCP port on which servod is listening on
      verbose: enable verbose messaging across xmlrpclib.ServerProxy
    """
    self.logger.debug('initialize')
    self.verbose = verbose
    self.remote = 'http://' + servo_host + ':' + servo_port
    self.server = xmlrpclib.ServerProxy(self.remote, verbose=self.verbose,
                                        allow_none=True)

  def doc_all(self):
    self.logger.debug("")
    return self.server.doc_all()

  def doc(self, name):
    self.logger.debug("")
    return self.server.doc(name)

  def get(self, name):
    self.logger.debug("")
    return self.server.get(name)

  def get_all(self, verbose=False):
    self.logger.debug("")
    return self.server.get_all(verbose)

  def set(self, name, value):
    self.logger.debug("")
    return self.server.set(name, value)


def _parse_args():
  """Parse commandline arguments.

  Note, reads sys.argv directly

  Returns:
    tuple (options, args) as described by optparse.OptionParser.parse_args()
    method
  """
  description = (
    "%prog allows users to set and get various controls on a DUT system via"
    " the servo debug & control board.  This client communicates to the board"
    " via a socket connection to the servo server."
    )
  examples = (
    "\nExamples:\n"
    "   %prog\n\tgets value for all controls\n"
    "   %prog -v\n\tgets value for all controls verbosely\n"
    "   %prog i2c_mux\n\tgets value for 'i2c_mux' control\n"
    "   %prog -r 100 i2c_mux\n\tgets value for 'i2c_mux' control 100 times\n"
    "   %prog -t 2 loc_0x40_mv\n\tgets value for 'loc_0x40_mv' control for 2 "
    "seconds\n"
    "   %prog -v i2c_mux\n\tgets value for 'i2c_mux' control verbosely\n"
    "   %prog i2c_mux:remote_adcs\n\tsets 'i2c_mux' to value 'remote_adcs'\n"
    )
  parser = optparse.OptionParser(version="%prog "+VERSION)
  parser.description = description
  parser.add_option("-s", "--server", help="host where servod is running",
                    default="localhost")
  parser.add_option("-p", "--port", help="port where servod is listening",
                    default="9999")
  parser.add_option("-v", "--verbose", help="show verbose info about controls",
                    action="store_true", default=False)
  parser.add_option("-i", "--info", help="show info about controls",
                    action="store_true", default=False)
  parser.add_option("-r", "--repeat", type=int,
                    help="repeat requested command multiple times", default=1)
  parser.add_option("-t", "--time_in_secs", help="repeat requested command for "
                    + "this many seconds", type='float', default=0.0)
  parser.add_option("-d", "--debug", help="enable debug messages",
                    action="store_true", default=False)

  parser.set_usage(parser.get_usage() + examples)
  return parser.parse_args()

def display_table(table, prefix='@@'):
  """Display a two-dimensional array ( list-of-lists ) as a table.

  The table will be spaced out.
  >>> table = [['aaa', 'bbb'], ['1', '2222']]
  >>> display_table(table)
  @@   aaa   bbb
  @@     1  2222
  >>> display_table(table, prefix='%')
  %   aaa   bbb
  %     1  2222
  >>> table = [['a']]
  >>> display_table(table)
  @@   a
  >>> table = []
  >>> display_table(table)
  >>> table = [[]]
  >>> display_table(table)
  >>> table = [['a'], ['1', '2']]
  >>> display_table(table)
  Traceback (most recent call last):
  ...
  IndexError: list index out of range
  >>> table = [['a', 'b'], ['1']]
  >>> display_table(table)
  Traceback (most recent call last):
  ...
  IndexError: list index out of range
  >>> table = [['aaa', 'bbb', 'c'], ['1', '2222', '0']]
  >>> display_table(table)
  @@   aaa   bbb  c
  @@     1  2222  0

  Args:
    table: A two-dimensional array (list of lists) to show.
    prefix: All lines will be prefixed with this and a space.
  """
  if len(table) == 0 or len(table[0]) == 0:
    return

  max_col_width = []
  for col_idx in xrange(len(table[0])):
    col_item_widths = [len(row[col_idx]) for row in table]
    max_col_width.append(max(col_item_widths))

  for row in table:
    out_str = ''
    for i in xrange(len(row)):
      out_str += row[i].rjust(max_col_width[i] + 2)
    print prefix, out_str

def display_stats(stats):
  """Display various statistics for data captured in a table.
  >>> stats = {}
  >>> stats[TIME_KEY] = [50.0, 25.0, 40.0, 10.0]
  >>> stats['frobnicate'] = [11.5, 9.0]
  >>> stats['foobar'] = [11111.0, 22222.0]
  >>> display_stats(stats)
  @@           NAME  COUNT   AVERAGE   STDDEV       MAX       MIN
  @@   sample_msecs      4     31.25    15.16     50.00     10.00
  @@         foobar      2  16666.50  5555.50  22222.00  11111.00
  @@     frobnicate      2     10.25     1.25     11.50      9.00

  Args:
    stats: A dictionary of stats to show.  Key is name of result and value is a
        list of floating point values to show stats for.  See doctest.
        Any key starting with '__' will be sorted first and have its prefix
        stripped.
  """
  table = [['NAME', 'COUNT', 'AVERAGE', 'STDDEV', 'MAX', 'MIN']]
  for key in sorted(stats.keys()):
    if stats[key]:
      stats_np = numpy.array(stats[key])
      disp_key = key.lstrip(KEY_PREFIX)
      row = [disp_key, str(len(stats_np))]
      row.append("%.2f" % stats_np.mean())
      row.append("%.2f" % stats_np.std())
      row.append("%.2f" % stats_np.max())
      row.append("%.2f" % stats_np.min())
      table.append(row)
  display_table(table)

def timed_loop(time_in_secs):
  start_time = time.time()
  secs_so_far = 0.0
  while secs_so_far <= time_in_secs:
    yield secs_so_far
    secs_so_far = time.time() - start_time

def main():
  (options, args) = _parse_args()
  loglevel = logging.INFO
  if options.debug:
    loglevel = logging.DEBUG
  logging.basicConfig(level=loglevel,
                      format="%(asctime)s - %(name)s - " +
                      "%(levelname)s - %(message)s")
  sclient = ServoClient()
  sclient.initialize(servo_host=options.server,
                     servo_port=options.port)
  if not len(args) and options.info:
    # print all the doc info for the controls
    print sclient.doc_all()
  elif not len(args):
    print sclient.get_all(verbose=options.verbose)

  stats = collections.defaultdict(list)

  if options.time_in_secs > 0:
    iterate_over = timed_loop(options.time_in_secs)
  else:
    iterate_over = xrange(options.repeat)

  for _ in iterate_over:
    sample_start = time.time()
    for argnum, arg in enumerate(args):
      logging.debug("cmd = %s" % arg)
      cmdlist = arg.split(':', 1)
      if len(cmdlist) == 2:
        (cmd_name, cmd_value) = cmdlist
        # its a set
        try:
          rv = sclient.set(cmd_name, cmd_value)
          if options.verbose:
            print "SET %s -> %s :: %s" % (cmd_name, cmd_value,
                                          sclient.doc(cmd_name))
        except xmlrpclib.Fault, e:
          # TODO(tbroch) : more detail of failure.  Note xmlrpclib only
          #                passes one exception above
          logging.error("Problem setting %s :: %s\n\t\tIgnoring %s" %
                        (arg, e, ' '.join(args[argnum + 1:])))
          break
      else:
        (cmd_name,) = cmdlist
        # its a get | doc
        get_fx = "get"
        if options.info:
          get_fx = "doc"
        try:
          rv = eval("sclient.%s(cmd_name)" % (get_fx))
          if options.verbose:
            print "%s %s -> %s" % (get_fx.upper(), cmd_name, rv)
          else:
            print "%s:%s" % (arg, rv)
          if get_fx == 'get':
            try:
              stats[cmd_name].append(float(rv))
            except ValueError, e:
              pass
        except  xmlrpclib.Fault, e:
          logging.error("Problem getting %s %s :: %s\n\t\tIgnoring %s" %
                        (get_fx, arg, e, ' '.join(args[argnum+1:])))
          break
        stats[TIME_KEY].append((time.time() - sample_start) * 1000)

  if (options.repeat != 1) or (options.time_in_secs > 0):
    display_stats(stats);

if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    sys.exit(0)
