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
import logging

import pty_driver

KEY_STATE = [0, 1, 1, 1, 1]

# Key matrix row and column mapped from kbd_m*_a*
KEY_MATRIX = [[[(0,4), (11,4)], [(2,4), None]],
              [[(0,2), (11,2)], [(2,2), None]]]

# EC console mask for enabling only command channel
COMMAND_CHANNEL_MASK = 0x1

class ecError(Exception):
  """Exception class for ec."""


class ec(pty_driver.ptyDriver):
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
    # Add locals to the values dictionary.
    self._dict["kbd"] = KEY_STATE

  def _limit_channel(self):
    """
    Save the current console channel setting and limit the output to
    the command channel (only print output from commands issued on console).

    Raises:
      ecError: when failing to retrieve channel settings
    """
    self._issue_cmd("chan save")
    self._issue_cmd("chan %d" % COMMAND_CHANNEL_MASK)

  def _restore_channel(self):
    """Load saved channel setting"""
    # To improve backward compatibility on EC images that do not have save/
    # restore, set channel mask to power-on default before running restore.
    # TODO(shawnn): Remove this line once all test units have new EC image.
    self._issue_cmd("chan 0xffffffff")

    self._issue_cmd("chan restore")

  def _set_key_pressed(self, key_rc, pressed):
    """Press/release a key.

    Args:
      key_rc: Tuple containing row and column of the key.
      pressed: 0=release, 1=press.
    """
    if key_rc is None:
      return
    self._issue_cmd("kbpress %d %d %d" % (key_rc + (pressed,)))

  def _get_mx_ax_index(self, m, a):
    """Get the index of a kbd_mx_ax control.

    Args:
      m: Selection of kbd_m1 or kbd_m2. Note the value is 0/1, not 1/2.
      a: Selection of a0 and a1.
    """
    return m * 2 + a + 1

  def _set_both_keys(self, pressed):
    """Press/release both simulated key.

    Args:
      pressed: 0=release, 1=press.
    """
    m1_a0, m1_a1, m2_a0, m2_a1 = self._dict["kbd"][1:5]
    self._set_key_pressed(KEY_MATRIX[1][m2_a0][m2_a1], pressed)
    self._set_key_pressed(KEY_MATRIX[0][m1_a0][m1_a1], pressed)

  def _Set_kbd_en(self, value):
    """Enable/disable keypress simulation."""
    self._logger.debug("")
    org_value = self._dict["kbd"][0]
    if org_value == 0 and value == 1:
      self._set_both_keys(pressed=1)
    elif org_value == 1 and value == 0:
      self._set_both_keys(pressed=0)
    self._dict["kbd"][0] = value

  def _Get_kbd_en(self):
    """Retrieve keypress simulation enabled/disabled.

    Returns:
      0: Keyboard emulation is disabled.
      1: Keyboard emulation is enabled.
    """
    return self._dict["kbd"][0]

  def _Set_kbd_mx_ax(self, m, a, value):
    """Implementation of _Set_kbd_m*_a*

    Args:
      m: Selection of kbd_m1 or kbd_m2. Note the value is 0/1, not 1/2.
      a: Selection of a0 and a1.
      value: The new value to set.
    """
    self._logger.debug("")
    org_value = self._dict["kbd"][self._get_mx_ax_index(m, a)]
    if self._Get_kbd_en() == 1 and org_value != value:
      org_value = [self._dict["kbd"][self._get_mx_ax_index(m, 0)],
                   self._dict["kbd"][self._get_mx_ax_index(m, 1)]]
      new_value = list(org_value)
      new_value[a] = value
      self._set_key_pressed(KEY_MATRIX[m][org_value[0]][org_value[1]], 0)
      self._set_key_pressed(KEY_MATRIX[m][new_value[0]][new_value[1]], 1)
    self._dict["kbd"][self._get_mx_ax_index(m, a)] = value

  def _Set_kbd_m1_a0(self, value):
    """Setter of kbd_m1_a0."""
    self._Set_kbd_mx_ax(0, 0, value)

  def _Get_kbd_m1_a0(self):
    """Getter of kbd_m1_a0."""
    return self._dict["kbd"][self._get_mx_ax_index(0, 0)]

  def _Set_kbd_m1_a1(self, value):
    """Setter of kbd_m1_a1."""
    self._Set_kbd_mx_ax(0, 1, value)

  def _Get_kbd_m1_a1(self):
    """Getter of kbd_m1_a1."""
    return self._dict["kbd"][self._get_mx_ax_index(0, 1)]

  def _Set_kbd_m2_a0(self, value):
    """Setter of kbd_m2_a0."""
    self._Set_kbd_mx_ax(1, 0, value)

  def _Get_kbd_m2_a0(self):
    """Getter of kbd_m2_a0."""
    return self._dict["kbd"][self._get_mx_ax_index(1, 0)]

  def _Set_kbd_m2_a1(self, value):
    """Setter of kbd_m2_a1."""
    self._Set_kbd_mx_ax(1, 1, value)

  def _Get_kbd_m2_a1(self):
    """Getter of kbd_m2_a1."""
    return self._dict["kbd"][self._get_mx_ax_index(1, 1)]

  def _Get_lid_open(self):
    """Getter of lid_open.

    Returns:
      0: Lid closed.
      1: Lid opened.
    """
    self._limit_channel()
    result = self._issue_cmd_get_results("lidstate",
        ["lid state: (open|closed)"])[0]
    self._restore_channel()

    return 1 if result[1] == "open" else 0

  def _Set_lid_open(self, value):
    """Setter of lid_open.

    Args:
      value: 0=lid closed, 1=lid opened.
    """
    if value == 0:
      self._issue_cmd("lidclose")
    else:
      self._issue_cmd("lidopen")

  def _Get_volume_up(self):
    """Getter of Volup"""
    result = self._issue_cmd_get_results("btnpress volup",
                                         ["Button volup pressed = (\d+)"])[0]
    return int(result[1])

  def _Set_volume_up(self, value):
    """Setter of Volup

    Args:
      value: 1=button pressed, 0=button released
    """
    self._issue_cmd("btnpress volup %d" % int(value))

  def _Get_volume_down(self):
    """Getter of Voldown"""
    result = self._issue_cmd_get_results("btnpress voldown",
                                         ["Button voldown pressed = (\d+)"])[0]
    return int(result[1])

  def _Set_volume_down(self, value):
    """Setter of Voldown

    Args:
      value: 1=button pressed, 0=button released
    """
    self._issue_cmd("btnpress voldown %d" % int(value))

  def _Get_cpu_temp(self):
    """Getter of cpu_temp.

    Reads CPU temperature through PECI. Only works when device is powered on.

    Returns:
      CPU temperature in degree C.
    """
    self._limit_channel()
    result = self._issue_cmd_get_results("temps",
        ["PECI[ \t]*:[ \t]*[0-9]* K[ \t]*=[ \t]*([0-9]*)[ \t]*C"])[0]
    self._restore_channel()
    if result is None:
      raise ecError("Cannot retrieve CPU temperature.")
    return result[1]

  def _get_battery_values(self):
    """Retrieve various battery related values.

    Battery command in the EC currently exposes the following information:
       Temp:      0x0be1 = 304.1 K (31.0 C)
       Manuf:     SUNWODA
       Device:    S1
       Chem:      LION
       Serial:    0x0000
       V:         0x1ef7 = 7927 mV
       V-desired: 0x20d0 = 8400 mV
       V-design:  0x1ce8 = 7400 mV
       I:         0x06a9 = 1705 mA(CHG)
       I-desired: 0x06a4 = 1700 mA
       Mode:      0x7f01
       Charge:    66 %
         Abs:     65 %
       Remaining: 5489 mAh
       Cap-full:  8358 mAh
         Design:  8500 mAh
       Time-full: 2h:47
         Empty:   0h:0

    This method currently returns a subset of above.

    Returns:
      Tuple (millivolts, milliamps) where:
        millivolts: battery voltage in millivolts
        milliamps: battery amps in milliamps
    """
    self._limit_channel()
    results = self._issue_cmd_get_results('battery',
                                         ['V:[\s0-9a-fx]*= (-*\d+) mV',
                                          'I:[\s0-9a-fx]*= (-*\d+) mA'])
    self._restore_channel()
    return (int(results[0][1], 0), int(results[1][1], 0) * -1)

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
    self._limit_channel()
    results = self._issue_cmd_get_results('faninfo',
                                         ['Actual:[ \t]*(\d+) rpm',
                                          'Target:[ \t]*(\d+) rpm',
                                          'Duty:[ \t]*(\d+)%'])
    self._restore_channel()
    return [int(results[0][1], 0),
            int(results[1][1], 0),
            int(results[2][1], 0)]

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
