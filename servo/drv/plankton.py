# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=plankton.

Provides the following functionis:
  usbc_role
  usbc_mux
  usbc_polarity
"""
import collections
import logging

import pty_driver
import re

USBC_STATE = [None, None, None]

class planktonError(Exception):
  """Exception class for plankton."""


class plankton(pty_driver.ptyDriver):
  """Object to access drv=plankton controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read usbc_role would be dispatched to
  call _Get_usbc_role.
  """

  IO_EXPANDER_BUS = 1
  IO_EXPANDER_ADDR = 0x40
  IO_EXPANDER_WIDTH = 8

  STATE_ID_ROLE = 0
  STATE_ID_MUX = 1
  STATE_ID_POLARITY = 2

  USBC_ROLE_SINK = 0
  USBC_ROLE_5V_SRC = 1
  USBC_ROLE_12V_SRC = 2
  USBC_ROLE_20V_SRC = 3
  USBC_ROLE_ACTION = ["dev", "5v", "12v", "20v"]

  USBC_MUX_USB = 0
  USBC_MUX_DP = 1
  USBC_MUX_ACTION = ["usb", "dp"]

  USBC_POLARITY_0 = 0
  USBC_POLARITY_1 = 1
  USBC_POLARITY_ACTION = ["pol0", "pol1"]

  INA_SENSE = "ina 0"
  INA_SENSE_DICT = collections.OrderedDict([
      ("configuration", r"Configuration: ([0-9a-f]+)"),
      ("shunt_voltage_mv", r"Shunt voltage: [0-9a-f]+ => (-?\d+) uV"),
      ("voltage_mv", r"Bus voltage  : [0-9a-f]+ => (-?\d+) mV"),
      ("power_mw", r"Power        : [0-9a-f]+ => (-?\d+) mW"),
      ("current_ma", r"Current      : [0-9a-f]+ => (-?\d+) mA"),
      ("calibration", r"Calibration  : ([0-9a-f]+)"),
      ("mask_enable", r"Mask/Enable  : ([0-9a-f]+)"),
      ("alert_limit", r"Alert limit  : ([0-9a-f]+)")])

  PD_STATE = "pd 0 state"

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
        control
      params: dictionary of params needed to perform operations on
        devices. The only params used now is 'subtype', which is used
        by get/set method of base class to decide how to dispatch
        request.
    """
    super(plankton, self).__init__(interface, params)
    self._logger.debug("")
    self._state = USBC_STATE

  def _set_usbc_action(self, action):
    self._issue_cmd("usbc %s" % action)

  def _Set_usbc_role(self, value):
    if self._state[self.STATE_ID_ROLE] != value:
      self._set_usbc_action(self.USBC_ROLE_ACTION[value])
      self._state[self.STATE_ID_ROLE] = value

  def _Get_usbc_role(self):
    if self._state[self.STATE_ID_ROLE] is None:
      raise planktonError("usbc_role not initialized")
    return self._state[self.STATE_ID_ROLE]

  def _Set_usbc_mux(self, value):
    if self._state[self.STATE_ID_MUX] != value:
      self._set_usbc_action(self.USBC_MUX_ACTION[value])
      self._state[self.STATE_ID_MUX] = value

  def _Get_usbc_mux(self):
    if self._state[self.STATE_ID_MUX] is None:
      raise planktonError("usbc_mux not initialized")
    return self._state[self.STATE_ID_MUX]

  def _Set_usbc_polarity(self, value):
    if self._state[self.STATE_ID_POLARITY] != value:
      self._set_usbc_action(self.USBC_POLARITY_ACTION[value])
      self._state[self.STATE_ID_POLARITY] = value

  def _Get_usbc_polarity(self):
    if self._state[self.STATE_ID_POLARITY] is None:
      raise planktonError("usbc_polarity not initialized")
    return self._state[self.STATE_ID_POLARITY]

  def _get_ina(self):
    matches = self._issue_cmd_get_results(
        self.INA_SENSE, self.INA_SENSE_DICT.values())
    return dict(zip(self.INA_SENSE_DICT.keys(),
                    zip(*matches)[1]))

  def _Get_vbus_current(self):
    return self._get_ina()["current_ma"]

  def _Get_vbus_voltage(self):
    return self._get_ina()["voltage_mv"]

  def _Get_vbus_power(self):
    return self._get_ina()["power_mw"]

  def _get_pd_state(self):
    m = self._issue_cmd_get_results(self.PD_STATE, ['(Port.*) - (Role:.*)\r'])
    # Parse the response to get each value
    enable = re.search('CC\d,\s+([\w]+)', m[0][0])
    role = re.search('Role:\s+([\w]+-[\w]+)', m[0][0])
    state = re.search('State:\s+([\w]+_[\w]+)', m[0][0])
    flags = re.search('Flags:\s+([\w]+)', m[0][0])
    polarity = re.search('(CC\d)', m[0][0])
    # Fill the dict fields
    state_result = {}
    state_result["enable"] = enable.group(1)
    state_result["polarity"] = polarity.group(1)
    state_result["role"] = role.group(1)
    state_result["state"] = state.group(1)
    state_result["flags"] = flags.group(1)

    return state_result

  def _Get_pd_enable(self):
    return 1 if self._get_pd_state()["enable"] == "Ena" else 0

  def _Get_pd_role(self):
    return self._get_pd_state()["role"]

  def _Get_pd_polarity(self):
    return self._get_pd_state()["polarity"]

  def _Get_pd_flags(self):
    return self._get_pd_state()["flags"]

  def _Get_pd_state(self):
    return self._get_pd_state()["state"]

  def _i2c_write(self, bus, addr, offset, value):
    self._issue_cmd("i2cxfer w %d 0x%x 0x%x 0x%x" % (bus, addr, offset, value))

  def _i2c_read(self, bus, addr, offset):
    match = self._issue_cmd_get_results(
        "i2cxfer r %d 0x%x 0x%x" % (bus, addr, offset),
        [r"\S+ \[(\d+)\]"])[0]

    if not match:
      raise planktonError("Failed to read from I2C")

    return int(match[1])

  def _get_io_expander_input(self):
    return self._i2c_read(self.IO_EXPANDER_BUS, self.IO_EXPANDER_ADDR, 0)

  def _get_io_expander_output(self):
    return self._i2c_read(self.IO_EXPANDER_BUS, self.IO_EXPANDER_ADDR, 1)

  def _set_io_expander_output(self, value):
    return self._i2c_write(self.IO_EXPANDER_BUS, self.IO_EXPANDER_ADDR, 1,
                           value)

  def _get_io_expander_mask(self):
    return self._i2c_read(self.IO_EXPANDER_BUS, self.IO_EXPANDER_ADDR, 3)

  def _set_io_expander_mask(self, value):
    return self._i2c_write(self.IO_EXPANDER_BUS, self.IO_EXPANDER_ADDR, 3,
                           value)

  def _Get_io_expander_input(self):
    return self._get_io_expander_input()

  def _Get_io_expander_output(self):
    return self._get_io_expander_output()

  def _Get_io_expander_mask(self):
    return self._get_io_expander_mask()

  def _get_gpio_offset(self):
    """Gets offset from parameters.

    Returns:
      GPIO offset, in range(IO_EXPANDER_WIDTH).

    Raises:
      planktonError: when offset not in params dict, or out of range.
    """
    try:
      offset = int(self._params['offset'])
    except (KeyError, ValueError) as e:
      raise planktonError(e)

    if offset not in range(self.IO_EXPANDER_WIDTH):
      raise planktonError("GPIO offset out of range")

    return offset

  def _Get_expander_gpio(self):
    """Gets value for Plankton IO expander driver.

    Returns:
      integer value from GPIO. 0 or 1.
    """
    return (self._get_io_expander_input() >> self._get_gpio_offset()) & 1

  def _Set_expander_gpio(self, bit):
    """Sets value for Plankton IO expander driver.

    Args:
      bit: new GPIO level. Any non-zero will be treated as singular '1'.
    """
    offset = self._get_gpio_offset()
    bit = 1 if int(bit) else 0
    self._logger.debug("Set gpio[%d]: %d" % (offset, bit))
    if bit == (self._get_io_expander_input() >> offset) & 1:
      return

    # Set or clear output value
    output_value = self._get_io_expander_output()
    new_value = output_value & ~(1 << offset) | (bit << offset)
    if new_value != output_value:
      self._set_io_expander_output(new_value)

    # Switch to output mode
    input_mask = self._get_io_expander_mask()
    new_mask = input_mask & ~(1 << offset)
    if new_mask != input_mask:
      self._set_io_expander_mask(new_mask)
