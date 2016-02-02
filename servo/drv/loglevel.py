# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for servod's loglevel."""

import logging

import servo.ec3po_interface
import hw_driver

DEFAULT_FMT_STRING = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEBUG_FMT_STRING = ('%(asctime)s - %(name)s - %(levelname)s - '
                    '%(filename)s:%(lineno)d:%(funcName)s - %(message)s')
LOGLEVEL_MAP = {
  'critical' : (logging.CRITICAL, DEFAULT_FMT_STRING),
  'error' : (logging.ERROR, DEFAULT_FMT_STRING),
  'warning' : (logging.WARNING, DEFAULT_FMT_STRING),
  'info' : (logging.INFO, DEFAULT_FMT_STRING),
  'debug' : (logging.DEBUG, DEBUG_FMT_STRING)
}
DEFAULT_LOGLEVEL = 'info'


class loglevel(hw_driver.HwDriver):
  """Class to access loglevel controls."""

  def __init__(self, interface, params):
    """Initializes the loglevel driver.

    Args:
      interface: A driver interface object, but is ignored.
      params: A dictionary of parameters, but is ignored.
    """
    self._interface = interface
    self._params = params

  def set(self, new_level):
    """Changes the current loglevel of the root logger.

    Args:
      new_level: A string containing the new desired log level.

    Raises:
      HwDriverError if passed in an invalid logging level name.
    """
    new_level = new_level.lower()
    root_logger = logging.getLogger()

    try:
      level, fmt_string = LOGLEVEL_MAP[new_level]
      # Set servod's logging level.
      root_logger.setLevel(level)

      # Set the appropriate format string for each logging handler.
      for handler in root_logger.handlers:
        handler.formatter = logging.Formatter(fmt=fmt_string)

      # Set EC-3PO's logging level.
      for interface in self._interface._interface_list:
        if type(interface) is servo.ec3po_interface.EC3PO:
          interface._console.oobm_queue.put('loglevel ' + str(level))

    except KeyError:
      raise hw_driver.HwDriverError('Unknown logging level. '
                                    '(known: critical, error, warning,'
                                    ' info, or debug)')

  def get(self):
    """Gets the current loglevel of the root logger."""
    cur_level =  logging.getLogger().level

    if cur_level == logging.CRITICAL:
      return 'critical'
    elif cur_level == logging.ERROR:
      return 'error'
    elif cur_level == logging.WARNING:
      return 'warning'
    elif cur_level == logging.INFO:
      return 'info'
    elif cur_level == logging.DEBUG:
      return 'debug'
    else:
      return cur_level
