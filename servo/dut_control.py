#!/usr/bin/env python
# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client to control DUT hardware connected to servo debug board
"""
import collections
import logging
import optparse
import sys
import time

import numpy

import client

# TODO(tbroch) determine version string methodology.
VERSION = "0.0.1"

# used to aid sorting of dict keys
KEY_PREFIX = '__'
STATS_PREFIX = '@@'
GNUPLOT_PREFIX = '##'
# dict key for tracking sampling time
TIME_KEY = KEY_PREFIX + 'sample_msecs'


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
    "\tif the exact control name is not found, "
    "a list of similar controls is printed\n"
    "   %prog -r 100 i2c_mux\n\tgets value for 'i2c_mux' control 100 times\n"
    "   %prog -t 2 loc_0x40_mv\n\tgets value for 'loc_0x40_mv' control for 2 "
    "seconds\n"
    "   %prog -y -t 2 loc_0x40_mv\n\tgets value for 'loc_0x40_mv' control for "
    "2 seconds and prepends time in seconds to results\n"
    "   %prog -g -y -t 2 loc_0x40_mv loc_0x41_mv\n"
    "\tgets value for 'loc_0x4[0|1]_mv' control for 2 seconds with gnuplot "
    "style"
    "   %prog -z 100 -t 2 loc_0x40_mv\n\tgets value for 'loc_0x40_mv' control "
    "for 2 seconds sampling every 100ms\n"
    "   %prog -v i2c_mux\n\tgets value for 'i2c_mux' control verbosely\n"
    "   %prog i2c_mux:remote_adcs\n\tsets 'i2c_mux' to value 'remote_adcs'\n"
    )
  parser = optparse.OptionParser(version="%prog "+VERSION)
  parser.description = description
  parser.add_option("-s", "--server", help="host where servod is running",
                    default=client.DEFAULT_HOST)
  parser.add_option("-p", "--port", help="port where servod is listening",
                    default=str(client.DEFAULT_PORT))
  parser.add_option("-v", "--verbose", help="show verbose info about controls",
                    action="store_true", default=False)
  parser.add_option("-i", "--info", help="show info about controls",
                    action="store_true", default=False)
  parser.add_option("-r", "--repeat", type=int,
                    help="repeat requested command multiple times", default=1)
  parser.add_option("-t", "--time_in_secs", help="repeat requested command for "
                    + "this many seconds", type='float', default=0.0)
  parser.add_option("-z", "--sleep_msecs", help="sleep for this many " +
                    "milliseconds between queries", type='float', default=0.0)
  parser.add_option("-y", "--print_time", help="print time in seconds with " +
                    "queries to stdout", action="store_true", default=False)
  parser.add_option("-g", "--gnuplot", help="gnuplot style to stdout.  Implies "
                    "print_time", action="store_true", default=False)
  parser.add_option("--hwinit", help="Initialize controls to their POR/safe "
                    "state", action="store_true", default=False)

  parser.add_option("-d", "--debug", help="enable debug messages",
                    action="store_true", default=False)

  parser.set_usage(parser.get_usage() + examples)
  return parser.parse_args()


def display_table(table, prefix):
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


def display_stats(stats, prefix=STATS_PREFIX):
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
    prefix: All lines will be prefixed with this and a space.
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
  display_table(table, prefix)


def timed_loop(time_in_secs):
  """Pause for time_in_secs."""
  start_time = time.time()
  secs_so_far = 0.0
  while secs_so_far <= time_in_secs:
    yield secs_so_far
    secs_so_far = time.time() - start_time


def _print_gnuplot_header(control_args):
  """Prints gnuplot header.

  Args:
    control_args: list of controls to get or set

  Note, calls sys.exit()
  """
  hdr = []
  # Don't put setting of controls into gnuplot output
  hdr.extend(arg for arg in control_args if ':' not in arg)
  if not hdr:
    logging.critical("Can't use --gnuplot without supplying controls to read "
                     "on command line")
    sys.exit(-1)
  print GNUPLOT_PREFIX + ' seconds ' + ' seconds '.join(hdr)


def do_iteration(requests, options, sclient, stats):
  """Perform one iteration across the controls.

  Args:
    requests: list of strings to make requests to servo about
      Example = ['dev_mode', 'dev_mode:on', 'dev_mode']
    options: optparse object options
    sclient: ServoRequest object
    stats: dict of key=control name, value=control value for stats calcs

  Returns:
    out_str: results string from iteration based on formats in options
  """
  out_list = []
  time_str = ''
  sample_start = time.time()
  for request_str in requests:
    logging.debug("cmd = %s", request_str)
    control = request_str
    if options.info:
      if ':' in request_str:
        logging.warn("Ignoring %s, can't perform set with --info", request_str)
        continue
      request_type = 'doc'
      result = sclient.doc(control)
    elif ':' in request_str:
      request_type = 'set'
      (control, value) = request_str.split(':', 1)
      result = sclient.set(control, value)
    else:
      request_type = 'get'
      result = sclient.get(control)
      try:
        stats[control].append(float(result))
      except ValueError:
        pass

    if options.print_time:
      time_str = "%.4f " % (time.time() - _start_time)

    if options.verbose:
      out_list.append("%s%s %s -> %s" % (time_str, request_type.upper(),
                                         control, result))
    elif request_type is not 'set':
      if options.gnuplot:
        out_list.append("%s%s" % (time_str, result))
      else:
        out_list.append("%s%s:%s" % (time_str, control, result))

  # format of gnuplot is <seconds_val1> <val1> <seconds_val2> <val2> ... such
  # that plotting can then be done with time on x-axis, value on y-axis.  For
  # example, this
  # command would plot two values across time
  #   plot   "file.out" using 1:2 with linespoint
  #   replot "file.out" using 3:4 with linespoint
  if options.gnuplot:
    out_str = " ".join(out_list)
  else:
    out_str = "\n".join(out_list)

  iter_time_msecs = (time.time() - sample_start) * 1000
  stats[TIME_KEY].append(iter_time_msecs)
  if options.sleep_msecs:
    if iter_time_msecs < options.sleep_msecs:
      time.sleep((options.sleep_msecs - iter_time_msecs) / 1000)
  return out_str


def iterate(controls, options, sclient):
  """Perform iterations on various controls.

  Args:
    controls: list of controls to iterate over
    options: optparse object options
    sclient: ServoRequest object
  """
  if options.gnuplot:
    options.print_time = True
    _print_gnuplot_header(controls)

  stats = collections.defaultdict(list)
  if options.time_in_secs > 0:
    iterate_over = timed_loop(options.time_in_secs)
  else:
    iterate_over = xrange(options.repeat)

  for _ in iterate_over:
    iter_output = do_iteration(controls, options, sclient, stats)
    if iter_output: # Avoid printing empty lines
        print iter_output

  if (options.repeat != 1) or (options.time_in_secs > 0):
    prefix = STATS_PREFIX
    if options.gnuplot:
      prefix = GNUPLOT_PREFIX
    display_stats(stats, prefix=prefix)


def real_main():
  (options, args) = _parse_args()
  loglevel = logging.INFO
  if options.debug:
    loglevel = logging.DEBUG
  logging.basicConfig(level=loglevel,
                      format="%(asctime)s - %(name)s - " +
                      "%(levelname)s - %(message)s")
  if options.verbose and options.gnuplot:
    logging.critical("Can't use --verbose with --gnuplot")
    sys.exit(-1)

  if options.info and options.hwinit:
    logging.critical("Can't use --hwinit with --info")
    sys.exit(-1)

  sclient = client.ServoClient(host=options.server, port=options.port,
                               verbose=options.verbose)
  global _start_time
  _start_time = time.time()

  # Perform 1st in order to allow user to then override below
  if options.hwinit:
    sclient.hwinit()
    # all done, don't read all controls
    if not len(args):
      return

  if not len(args) and options.info:
    # print all the doc info for the controls
    print sclient.doc_all()
  elif not len(args):
    print sclient.get_all()
  else:
    if not ':' in ' '.join(args):
        # Sort args only if none of them sets values - otherwise the order is
        # important.
        args = sorted(args)
    iterate(args, options, sclient)


def main():
  try:
    real_main()
  except KeyboardInterrupt:
    sys.exit(0)
  except client.ServoClientError as e:
    sys.stderr.write(e.error_message + '\n')
    sys.exit(1)

# global start time for script
_start_time = 0
if __name__ == '__main__':
  main()
