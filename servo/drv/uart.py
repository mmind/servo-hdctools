# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=uart.
"""
import logging


import drv.hw_driver


class uartError(Exception):
  """Error class for uart class."""


class uart(drv.hw_driver.HwDriver):
  """Object to access type=uart controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method.  That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read pty attached to the uart device would
  be dispatched to call _Get_pty.
  """

  def _Get_pty(self):
    """Get pty device attached to uart.

    Retuns:
      Path to pty attached to the uart.
    """
    self._logger.debug('')
    return self._interface.get_pty()

  def _check_and_get_line_prop(self, valid_props):
    """Check line property request and return it.

    Args:
      valid_props: dict, valid line properties to configure

    Returns:
      string of line property to get or set

    Raises:
      uartError: if key 'line_prop' not in params dict
      uartError: If unrecognized line_prop requested.
    """
    if 'line_prop' not in self._params:
      raise uartError("line_prop key not defined in params dict")
    line_prop = self._params['line_prop']
    if line_prop not in valid_props:
      raise uartError("Unknown uart line_prop %s requested" % line_prop)
    return line_prop

  def _Get_props(self):
    """Gets the requested uart line property.

    Line property is determined by string value in params['line_prop']

    Returns:
      uart line property requested

    Raises:
      uartError: unable to locate line property in interface dict
    """
    self._logger.debug('')
    prop_dict = self._interface.get_uart_props()
    line_prop = self._check_and_get_line_prop(prop_dict)
    return prop_dict[line_prop]

  def _Set_props(self, value):
    """Sets the requested uart control's line property.

    Line property is determined by string value in params['line_prop']

    Args:
      value: integer, to write to line property

    Raises:
      uartError: unable to locate line property in interface dict
    """
    self._logger.debug('')
    prop_dict = self._interface.get_uart_props()
    line_prop = self._check_and_get_line_prop(prop_dict)
    prop_dict[line_prop] = value
    self._interface.set_uart_props(prop_dict)
