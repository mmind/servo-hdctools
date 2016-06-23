# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Power state driver for boards with a PD MCU & edge-sensitive warm reset.

Some chipsets' warm reset appear to be edge-sensitive instead of level
sensitive.  This results in a "one-shot warm reset" when using dut-control to
assert the warm reset line.  That is, the application processor (AP) does reset,
but continues to boot despite the fact that the warm reset line is asserted.
For boards with a PD MCU, this causes a problem with the cros_ec_softrec_power
driver.  That driver assumes that the warm reset is level senstive for the
system.  If that driver is used with a edge sensitive system, a race occurs
between the AP booting far enough to tell the PD MCU to jump to its RW image and
the command sent to the EC to reboot but keep the AP off.

See crbug.com/606062#c26 for more information.
"""
import time

import cros_ec_softrec_power


class crosEcPdSoftrecPower(cros_ec_softrec_power.crosEcSoftrecPower):
  """Power state driver for boards that have a PD MCU & one-shot warm reset"""

  _REC_TYPE_REC_ON = cros_ec_softrec_power.crosEcSoftrecPower._REC_TYPE_REC_ON

  def __init__(self, interface, params):
    """Constructor

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(crosEcPdSoftrecPower, self).__init__(interface, params)
    self._boot_to_rec_screen_delay = float(
      self._params.get('boot_to_rec_screen_delay', 5.0))

  def _cold_reset(self):
    """Apply cold reset to the DUT.

    This asserts, then de-asserts the 'cold_reset' signal and the
    'usbpd_reset' signal.  This varies from the generic implementation
    in that the extra 'usbpd_reset' signal must be asserted to reset
    the PD MCU.
    """
    self._interface.set('cold_reset', 'on')
    self._interface.set('usbpd_reset', 'on')

    time.sleep(self._reset_hold_time)

    self._interface.set('usbpd_reset', 'off')
    self._interface.set('cold_reset', 'off')
    # After the reset, give the EC the time it needs to
    # re-initialize.
    time.sleep(self._reset_recovery_time)

  def _power_on_bytype(self, rec_mode, rec_type=_REC_TYPE_REC_ON):
    # In order to reliably enter recovery mode, we must:
    #
    # 0. Hold PD MCU in reset.
    # 1. Assert and deassert cold_reset. (This will reset both the AP and EC.)
    # 2. Reboot the EC and have the EC now hold the AP in reset. (Now, the EC is
    # the only one running and it's in its RO image.  This also clears the
    # EC_IN_RW signal, so that the AP will trust the upcoming recovery mode
    # requests)
    # 3. Release PD MCU reset. (Now, EC and PD MCU are both running in RO code -
    # a requirement to enter recovery mode.)
    #
    # Steps 0-3 will cause EC software sync to fail for the PD MCU, since we
    # held it in reset when the AP booted up in step 1.  This failure will set a
    # recovery reason, but the wrong reason (0x23 / EC software sync - unable to
    # determine active EC image).
    #
    # Therefore, we need to set the _correct_ recovery reason by:
    #
    # 4. Enter recovery mode.  (This will clear the current recovery reason.)
    # 5. Power down the AP.
    # 6. Issue recovery request. (This will set the desired recovery reason.)

    if rec_mode == self.REC_ON:
      self._reboot_to_ro_with_ap_off()
      self._toggle_recovery_boot(rec_type)

    self._power_on_ap()
    if rec_mode == self.REC_ON:
      # Allow time to reach the recovery screen before yielding control.
      time.sleep(self._boot_to_rec_screen_delay)

  def _reboot_to_ro_with_ap_off(self):
    """Reboot the EC and PD MCU to RO and leave the AP off.

    This will cause software sync to fail for the PD MCU and set the recovery
    reason.
    """
    self._interface.set('usbpd_reset', 'on')
    super(crosEcPdSoftrecPower, self)._cold_reset()
    try:
      # Pexpect is minimally greedy, so we can't match the exact reset cause
      # string.  But checking for 'Reset cause' will be enough proof that the EC
      # rebooted.
      self._interface.set('ec_uart_regexp', "['Reset cause:']")
      self._interface.set('ec_uart_cmd', 'reboot ap-off')
    finally:
      self._interface.set('ec_uart_regexp', 'None')

    # Allow enough time for the EC to come up
    time.sleep(self._reset_recovery_time)
    self._interface.set('usbpd_reset', 'off')

  def _toggle_recovery_boot(self, rec_type=_REC_TYPE_REC_ON):
    """Make 2 recovery requests so that the reason is 0x02 ("button pressed")"""
    # Request recovery boot.
    try:
      self._interface.set('ec_uart_regexp', "['Events:']")
      self._interface.set('ec_uart_cmd',
                          self._REC_TYPE_HOSTEVENT_CMD_DICT[rec_type])
      self._power_on_ap()
      # Allow time to reach recovery screen.
      time.sleep(self._boot_to_rec_screen_delay)
      # Power down AP.
      self._power_off()
      #  Repeat our recovery request to the AP.
      self._interface.set('ec_uart_regexp', "['Events:']")
      self._interface.set('ec_uart_cmd',
                          self._REC_TYPE_HOSTEVENT_CMD_DICT[rec_type])
      # Now, when we power up, we should be in recovery mode and our recovery
      # reason should be correct for the recovery button press.
    finally:
      self._interface.set('ec_uart_regexp', 'None')
