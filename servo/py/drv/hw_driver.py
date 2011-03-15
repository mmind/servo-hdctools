# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Base class for servo drivers."""
import logging


class HwDriverError(Exception):
  """Exception class for HwDriver."""


class HwDriver(object):
  """Base class for all hardware drivers."""
  def __init__(self, interface, params):
    """Driver constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
          control
      params: dictionary of params needed to perform operations on gpio driver

          params dictionary can have k=v pairs necessary to communicate with the
          underlying hardware.  Notables are:
            width: integer of width of the control in bits.  
                Default: 1
            offset: integer of position of bit(s) with respect to lsb. 
                Default: 0
            map: name string of map dictionary to use for unmapping / remapping
            fmt: function name string to call to format the result.

         Additional param keys will be described in sub-class drivers.

    Attributes:
      _logger: logger object.  May be accessed via sub-class
      _interface: interface object.  May be accessed via sub-class
      _params: parameter dictionary.  May be accessed via sub-class
    """
    self._logger = logging.getLogger("Driver")
    self._logger.debug("")
    self._interface = interface
    self._params = params

  def set(self, logical_value):
    """Set hardware control to a particular value.
    
    TODO(tbroch) logical_value will need float support for DAC's

    Args:
      logical_value: Integer value to write to hardware.
    """
    self._logger.debug("logical_value = %s" % str(logical_value))
    raise NotImplementedError("Should be implemeted in subclass")

  def get(self):
    """Get control value and return it

    Returns:
      logical value (int | float) to caller.
    """
    self._logger.debug("")
    raise NotImplementedError("Should be implemeted in subclass")

  def _create_logical_value(self, hw_value):
    """Create logical value using mask & offset.

    logical_value = (hw_value & mask) >> offset

    In MOST cases, subclass drivers should use this for data coming back from
    get method.

    Args:
      hw_value: value to convert to logical value

    Returns:
      integer in logical representation
    """
    (offset, mask) = self._get_offset_mask()
    if offset is not None:
      fmt_value = (hw_value & mask) >> offset
    else:
      fmt_value = hw_value
    return fmt_value

  def _create_hw_value(self, logical_value):
    """Create hardware value using mask & offset.

    hw_value = (logical_value << offset) & mask 

    In MOST cases, subclass drivers should use this for data going to value
    argument in set method.

    Args:
      logical_value: value to convert to hardware value

    Returns:
      integer in hardware representation

    Raises:
      HwDriverError: when logical_value would assert bits outside the mask
    """
    (offset, mask) = self._get_offset_mask()
    if offset is not None:
      hw_value = (logical_value << offset)
      if hw_value != (hw_value & mask):
        raise HwDriverError("format value asserts bits outside mask")
    else:
      hw_value = logical_value
    return hw_value

  def _get_offset_mask(self):
    """Retrieve offset and mask.

    Subclasses should use to obtain &| create these ints from param dict

    Returns:
      tuple (offset, mask) where:
        offset: integer offset or None if not defined in param dict
        mask: integer mask or None if offset not defined in param dict
      For example if width=2 and offset=4 then mask=0x30

    """
    if 'offset' in self._params:
      offset = int(self._params['offset'])
      if 'width' not in self._params:
        mask = 1 << offset
      else:
        mask = (2 ** int(self._params['width'])) - 1
    else:
      offset = None
      mask = None
    return (offset, mask)
