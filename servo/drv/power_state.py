# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import hw_driver


class PowerStateDriver(hw_driver.HwDriver):
  """Abstract superclass to provide board-specific power operations.

  This driver handles a single control with these settings:
    * 'off' - This must power the DUT off, regardless of its
      current state.
    * 'on' - This powers the DUT on in normal (not recovery) mode.
      The behavior of this setting is undefined if the DUT is not
      currently powered off.
    * 'rec' - Equivalent to 'on', except that the DUT boots in
      recovery mode.
    * 'reset' - Equivalent to 'off' followed by 'on'.
      Additionally, the EC will be reset as by the 'cold_reset'
      signal.

  Actual implementation of the required behaviors is delegated to
  the methods `_power_off()` and `_power_on()`, which must be
  implemented in a subclass.

  """

  _STATE_OFF = 'off'
  _STATE_ON = 'on'
  _STATE_REC_MODE = 'rec'
  _STATE_RESET_CYCLE = 'reset'

  REC_ON = 'on'
  REC_OFF = 'off'

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(PowerStateDriver, self).__init__(interface, params)
    self._reset_hold_time = float(
              self._params.get('reset_hold', 0.5))
    self._reset_recovery_time = float(
              self._params.get('reset_recovery', 5.0))

  def _cold_reset(self):
    """Apply cold reset to the DUT.

    This asserts, then de-asserts the 'cold_reset' signal.  The
    exact affect on the hardware varies depending on the board type.

    """
    self._interface.set('cold_reset', 'on')
    time.sleep(self._reset_hold_time)
    self._interface.set('cold_reset', 'off')
    # After the reset, give the EC the time it needs to
    # re-initialize.
    time.sleep(self._reset_recovery_time)

  def _power_off(self):
    """Power off the DUT.

    The DUT is required to be off at the end of this call,
    regardless of its previous state, provided that there is working
    EC and boot firmware.  There is no requirement for working OS
    software.

    """
    raise NotImplementedError()

  def _power_on(self, rec_mode):
    """Force the DUT to power on.

    Behavior is undefined unless the DUT is already powered off,
    e.g. with a call to `_power_off()`.

    At power on, recovery mode is set as specified by the `rec_mode`
    parameter.

    When booting in recovery mode, the client is responsible for
    inserting USB boot media after this method returns.  This
    method is responsible for any delays required to make the DUT
    ready for media insertion after power on.

    Args:
      rec_mode: Setting of recovery mode to be applied at power on.

    """
    raise NotImplementedError()

  def _reset_cycle(self):
    """Force a power cycle using cold reset.

    After the call, the DUT will be powered on in normal (not
    recovery) mode; the call is guaranteed to work regardless of
    the state of the DUT prior to the call.  This call must use
    cold_reset to guarantee that the EC also restarts.

    """
    self._cold_reset()

  def set(self, statename):
    """Set power state according to `statename`."""
    if statename == self._STATE_OFF:
      self._power_off()
    elif statename == self._STATE_ON:
      self._power_on(self.REC_OFF)
    elif statename == self._STATE_REC_MODE:
      self._power_on(self.REC_ON)
    elif statename == self._STATE_RESET_CYCLE:
      self._reset_cycle()
    else:
      raise ValueError("Invalid power_state setting: '%s'. Try one of "
                       "'%s', '%s', '%s', or '%s'." % (statename,
                           self._STATE_ON, self._STATE_OFF,
                           self._STATE_REC_MODE,
                           self._STATE_RESET_CYCLE))
