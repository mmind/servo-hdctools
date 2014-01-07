# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Common code for multiservo operation support"""

import os

if os.getuid():
  DEFAULT_RC_FILE = '/home/%s/.servodrc' % os.getenv('USER', '')
else:
  DEFAULT_RC_FILE = '/home/%s/.servodrc' % os.getenv('SUDO_USER', '')


def add_multiservo_parser_options(parser):
  """Add common options descriptors to the parser object

  Both servod and dut-control accept command line options for configuring
  multiservo operation. This function configures the command line parser
  object to accept those options.
  """
  parser.add_option("--rcfile", type=str,
                    default=DEFAULT_RC_FILE,
                    help="servo description file for multi-servo operation,"
                    " %s is used by default." % DEFAULT_RC_FILE)
  parser.add_option("-n", "--name", type=str,
                    help="symbolic name of the servo board, "
                    "used as a config shortcut, could also be supplied "
                    "through environment variable SERVOD_NAME")


def parse_rc(logger, rc_file):
  """Parse servodrc configuration file

  The format of the configuration file is described above in comments to
  DEFAULT_RC_FILE. I the file is not found or is mis-formatted, a warning is
  printed but the program tries to continue.

  Args:
    logger: a logging instance used by this servod driver
    rc_file: a string, name of the file storing the configuration

  Returns:
    a dictionary, where keys are symbolic servo names, and values are
    dictionaries representing servo parameters read from the config file,
    keyed by strings 'sn' (for serial number), 'port', and 'board'.
  """

  rcd = {}  # Dictionary representing the rc file contents.
  if os.path.isfile(rc_file):
    for rc_line in open(rc_file, 'r').readlines():
      line = rc_line.split('#')[0].strip()
      if not line:
        continue
      elts = [x.strip() for x in line.split(',')]
      name = elts[0]
      if not name or len(elts) < 2 or [x for x in elts if ' ' in x]:
        logger.info('ignoring rc line "%s"', rc_line.rstrip())
        continue
      rcd[name] = {
        'sn': elts[1],
        'port': None,
        'board': None
        }
      if (len(elts) > 2):
        rcd[name]['port'] = int(elts[2])
        if len(elts) > 3:
          rcd[name]['board'] = elts[3]
          if len(elts) > 4:
            logger.info("discarding %s for for %s", ' '.join(elts[4:]), name)
  return rcd


def get_env_options(logger, options):
  """Look for non-defined options in the environment

  SERVOD_PORT and SERVOD_NAME environment variables can be used if --port
  and --name command line switches are not set. Set the options values as
  necessary.

  Args:
    logger: a logging instance used by this servod driver
    options: the options object returned by opt_parse
  """
  if not options.port:
    env_port = os.getenv('SERVOD_PORT')
    if env_port:
      try:
        options.port = int(env_port)
      except ValueError:
        logger.warning('Ignoring environment port definition "%s"', env_port)
  if not options.name:
    options.name = os.getenv('SERVOD_NAME')
