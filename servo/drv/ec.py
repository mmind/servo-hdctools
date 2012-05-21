# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=ec.

Provides the following EC controlled function:
  lid_open
  kbd_en
  kbd_m1_a0
  kbd_m1_a1
  kbd_m2_a0
  kbd_m2_a1
  dev_mode (Temporary. See crosbug.com/p/9341)
"""
import fdpexpect
import logging
import os
import pexpect


import drv.hw_driver

# Default setting values
DEFAULT_DICT = {'kbd_en': 0,
                'kbd_m1_a0': 1,
                'kbd_m1_a1': 1,
                'kbd_m2_a0': 1,
                'kbd_m2_a1': 1}

# Key matrix row and column mapped from kbd_m*_a*
KEY_MATRIX = [[[(0,4), (2,4)], [(11,4), None]],
              [[(0,2), (2,2)], [(11,2), None]]]

# The memory address storing lid switch state
LID_STATUS_ADDR = "0x40080730"
LID_STATUS_MASK = 0x1

class ecError(Exception):
  """Exception class for ec."""


class ec(drv.hw_driver.HwDriver):
  """Object to access drv=ec controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read kbd_en would be dispatched to
  call _Get_kbd_en.
  """

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
    super(ec, self).__init__(interface, params)
    self._logger.debug("")
    # A dictionary that stores current setting values
    self._dict = DEFAULT_DICT
    self._pty_path = self._interface.get_pty()

  def _open(self):
    """Open EC console and create pexpect interface."""
    self._fd = os.open(self._pty_path, os.O_RDWR | os.O_NONBLOCK)
    self._child = fdpexpect.fdspawn(self._fd)

  def _close(self):
    """Close EC console."""
    os.close(self._fd)
    self._fd = None
    self._child = None

  def _flush(self):
    """Flush EC console output to prevent previous messages interfering."""
    self._child.sendline("")
    while True:
      try:
        self._child.expect(".", timeout=0.01)
      except pexpect.TIMEOUT:
        break

  def _send(self, cmd):
    """Send command to EC.

    This function always flush EC console before sending, and is used as
    a wrapper function to make sure EC console is always flushed before
    sending commands.

    Args:
      cmd: The command string to send to EC.

    Raises:
      ecError: Raised when writing to EC fails.
    """
    self._flush()
    if self._child.sendline(cmd) != len(cmd) + 1:
      raise ecError("Failed to send command.")

  def _issue_cmd(self, cmd):
    """Send command to EC and do not wait for response.

    Args:
      cmd: The command string to send to EC.
    """
    self._open()
    try:
      self._send(cmd)
      self._logger.debug("Sent cmd: %s" % cmd)
    finally:
      self._close()

  def _issue_cmd_get_results(self, cmd, regex_list):
    """Send command to EC and wait for response.

    This function waits for response message matching a regular
    expressions.

    Args:
      cmd: The command issued.
      regex_list: List of Regular expressions used to match response message.
        Note, list must be ordered.

    Returns:
      List of match objects of response message.

    Raises:
      ecError: If timed out waiting for EC response
    """
    #import pdb; pdb.set_trace()
    result_list = []
    self._open()
    try:
      self._send(cmd)
      self._logger.debug("Sending cmd: %s" % cmd)
      for regex in regex_list:
        self._child.expect(regex, timeout=0.3)
        result = self._child.match
        result_list.append(result)
        self._logger.debug("Result: %s" % str(result.groups()))
    except pexpect.TIMEOUT:
      raise ecError("Timeout waiting for EC response.")
    finally:
      self._close()
    return result_list

  def _Get_dev_sw(self):
    """Retrieve fake developer switch state.

    Returns:
      0: Developer switch is off.
      1: Developer switch is on.
    """
    result = self._issue_cmd_get_results("optget fake_dev_switch",
                                       ["([01]) fake_dev_switch"])[0]
    return int(result.group(1))

  def _Set_dev_sw(self, value):
    """Set fake developer switch state."""
    self._issue_cmd("optset fake_dev_switch %s" % value)

  def _set_key_pressed(self, key_rc, pressed):
    """Press/release a key.

    Args:
      key_rc: Tuple containing row and column of the key.
      pressed: 0=release, 1=press.
    """
    if key_rc is None:
      return
    self._issue_cmd("kbpress %d %d %d" % (key_rc + (pressed,)))

  def _set_both_keys(self, pressed):
    """Press/release both simulated key.

    Args:
      pressed: 0=release, 1=press.
    """
    m1_a0 = self._dict["kbd_m1_a0"]
    m1_a1 = self._dict["kbd_m1_a1"]
    m2_a0 = self._dict["kbd_m2_a0"]
    m2_a1 = self._dict["kbd_m2_a1"]
    self._set_key_pressed(KEY_MATRIX[0][m1_a0][m1_a1], pressed)
    self._set_key_pressed(KEY_MATRIX[1][m2_a0][m2_a1], pressed)

  def _Set_kbd_en(self, value):
    """Enable/disable keypress simulation."""
    self._logger.debug("")
    org_value = self._dict["kbd_en"]
    if org_value == 0 and value == 1:
      self._set_both_keys(pressed=1)
    elif org_value == 1 and value == 0:
      self._set_both_keys(pressed=0)
    self._dict["kbd_en"] = value

  def _Get_kbd_en(self):
    """Retrieve keypress simulation enabled/disabled.

    Returns:
      0: Keyboard emulation is disabled.
      1: Keyboard emulation is enabled.
    """
    return self._dict["kbd_en"]

  def _Set_kbd_mx_ax(self, m, a, value):
    """Implementation of _Set_kbd_m*_a*

    Args:
      m: Selection of kbd_m1 or kbd_m2. Note the value is 0/1, not 1/2.
      a: Selection of a0 and a1.
      value: The new value to set.
    """
    self._logger.debug("")
    org_value = self._dict["kbd_m%d_a%d" % (m+1, a)]
    if self._Get_kbd_en() == 1 and org_value != value:
      org_value = [self._dict["kbd_m%d_a0" % (m+1)],
                   self._dict["kbd_m%d_a1" % (m+1)]]
      new_value = list(org_value)
      new_value[a] = value
      self._set_key_pressed(KEY_MATRIX[m][org_value[0]][org_value[1]], 0)
      self._set_key_pressed(KEY_MATRIX[m][new_value[0]][new_value[1]], 1)
    self._dict["kbd_m%d_a%d" % (m+1, a)] = value

  def _Set_kbd_m1_a0(self, value):
    """Setter of kbd_m1_a0."""
    self._Set_kbd_mx_ax(0, 0, value)

  def _Get_kbd_m1_a0(self):
    """Getter of kbd_m1_a0."""
    return self._dict["kbd_m1_a0"]

  def _Set_kbd_m1_a1(self, value):
    """Setter of kbd_m1_a1."""
    self._Set_kbd_mx_ax(0, 1, value)

  def _Get_kbd_m1_a1(self):
    """Getter of kbd_m1_a1."""
    return self._dict["kbd_m1_a1"]

  def _Set_kbd_m2_a0(self, value):
    """Setter of kbd_m2_a0."""
    self._Set_kbd_mx_ax(1, 0, value)

  def _Get_kbd_m2_a0(self):
    """Getter of kbd_m2_a0."""
    return self._dict["kbd_m2_a0"]

  def _Set_kbd_m2_a1(self, value):
    """Setter of kbd_m2_a1."""
    self._Set_kbd_mx_ax(1, 1, value)

  def _Get_kbd_m2_a1(self):
    """Getter of kbd_m2_a1."""
    return self._dict["kbd_m2_a1"]

  def _Get_lid_open(self):
    """Getter of lid_open.

    Returns:
      0: Lid closed.
      1: Lid opened.
    """
    result = self._issue_cmd_get_results("rw %s" % LID_STATUS_ADDR,
        ["read word %s = 0x.......(.)" % LID_STATUS_ADDR])[0]
    res_code = int(result.group(1), 16)
    return res_code & LID_STATUS_MASK

  def _Set_lid_open(self, value):
    """Setter of lid_open.

    Args:
      value: 0=lid closed, 1=lid opened.
    """
    if value == 0:
      self._issue_cmd("lidclose")
    else:
      self._issue_cmd("lidopen")

  def _Get_cpu_temp(self):
    """Getter of cpu_temp.

    Reads CPU temperature through PECI. Only works when device is powered on.

    Returns:
      CPU temperature in degree C.
    """
    result = self._issue_cmd_get_results("temps",
        ["PECI[ \t]*:[ \t]*[0-9]* K[ \t]*=[ \t]*([0-9]*)[ \t]*C"])[0]
    if result is None:
      raise ecError("Cannot retrieve CPU temperature.")
    return result.group(1)

  def _get_battery_values(self):
    """Retrieve various battery related values.

    Battery command in the EC currently exposes the following information:
       Temperature:            0x0bd9 = 3033 x 0.1K (30 C)
       Manufacturer:           acme
       Device:                 S1
       Chemistry:              plutonium
       Serial number:          0xbeef
       Voltage:                0x1fb7 = 8119 mV
       Desired voltage         0x20d0 = 8400 mV
       Design output voltage   0x1ce8 = 7400 mV
       Current:                0xfbca = -1078 mA(DISCHG)
       Desired current         0x06a4 = 1700 mA
       Battery mode:           0x7c7f
       % of charge:            95 %
       Abs % of charge:        95 %
       Remaining capacity:     8061 mAh
       Full charge capacity:   8515 mAh
       Design capacity:        8500 mAh
       Time to empty:          7h:21
       Time to full:           0h:0

    This method currently returns a subset of above.

    Returns:
      Tuple (millivolts, milliamps) where:
        millivolts: battery voltage in millivolts
        milliamps: battery amps in milliamps
    """
    results = self._issue_cmd_get_results('battery',
                                         ['Voltage:.*= (-*\d+) mV',
                                          'Current:.*= (-*\d+) mA'])
    return (int(results[0].group(1), 0), int(results[1].group(1), 0) * -1)

  def _Get_milliamps(self):
    """Retrieve current measuremnents for the battery."""
    (_, milliamps) = self._get_battery_values()
    return milliamps

  def _Get_millivolts(self):
    """Retrieve voltage measuremnents for the battery."""
    (millivolts, _) = self._get_battery_values()
    return millivolts

  def _Get_milliwatts(self):
    """Retrieve power measuremnents for the battery.
    """
    (millivolts, milliamps) = self._get_battery_values()
    return milliamps * millivolts * 1e-3

  def _get_fan_values(self):
    """Retrieve fan related values.

    'faninfo' command in the EC exposes the following information:
      Fan actual speed: 6694 rpm
          target speed: 6600 rpm
          duty cycle:   41%
          status:       2
          enabled:      yes
          powered:      yes

    This method returns a subset of above.

    Returns:
      List [fan_act_rpm, fan_trg_rpm, fan_duty] where:
        fan_act_rpm: Actual fan RPM.
        fan_trg_rpm: Target fan RPM.
        fan_duty: Current fan duty cycle.
    """
    results = self._issue_cmd_get_results('faninfo',
                                         ['Fan actual speed:[ \t]*(\d+) rpm',
                                          'target speed:[ \t]*(\d+) rpm',
                                          'duty cycle:[ \t]*(\d+)%'])
    return [int(results[0].group(1), 0),
            int(results[1].group(1), 0),
            int(results[2].group(1), 0)]

  def _Get_fan_actual_rpm(self):
    """Retrieve actual fan RPM."""
    return self._get_fan_values()[0]

  def _Get_fan_target_rpm(self):
    """Retrieve target fan RPM."""
    return self._get_fan_values()[1]

  def _Get_fan_duty(self):
    """Retrieve current fan duty cycle."""
    return self._get_fan_values()[2]

  def _Set_fan_target_rpm(self, value):
    """Set target fan RPM.

    This function sets target fan RPM or turns on auto fan control.

    Args:
      value: Non-negative values for target fan RPM. -1 is treated as maximum
        fan speed. -2 is treated as auto fan speed control.
    """
    if value == -2:
      self._issue_cmd("autofan")
    else:
      # "-1" is treated as max fan RPM in EC, so we don't need to handle that
      self._issue_cmd("fanset %d" % value)
