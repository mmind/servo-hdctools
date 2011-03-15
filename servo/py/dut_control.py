#!/usr/bin/env python
# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client to control DUT hardware connected to servo debug board
"""
import logging
import optparse
import xmlrpclib


# TODO(tbroch) determine version string methodology.
VERSION = "0.0.1"


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
  parser.add_option("-d", "--debug", help="enable debug messages",
                    action="store_true", default=False)

  parser.set_usage(parser.get_usage() + examples)
  return parser.parse_args()

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
      except  xmlrpclib.Fault, e:
        logging.error("Problem getting %s %s :: %s\n\t\tIgnoring %s" %
                      (get_fx, arg, e, ' '.join(args[argnum+1:])))
        break

if __name__ == "__main__":
  main()
