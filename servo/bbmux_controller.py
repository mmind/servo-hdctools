# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import re

SIGNALS_RE = '^signals'
MUX_ROOT = '/sys/kernel/debug/omap_mux'


def use_omapmux():
  """Whether or not to utilize the Kernel OMAPMUX Controls.

  If the omap mux controls exists utilize them, otherwise assume the
  device-tree has been properly configured.

  Returns:
    True is the device-tree path exists and is not populated. False otherwise.
  """
  return os.path.exists(MUX_ROOT)


class BBmuxController(object):
  """Provides omap mux controls to interfaces that require them.

    Class Variables:
      _pin_name_map : Map of signal name to pin name.
      _pin_mode_map : Map of signal name to the correct mode to select it.
  """


  # These values are the same regardless of instance so once we have generated
  # them once, share it amongst the different instances.
  _pin_mode_map = {}
  _pin_name_map = {}

  def __init__(self):
    self._logger = logging.getLogger('BBmuxController')
    self._logger.debug('')
    if not BBmuxController._pin_name_map:
      self._init_pin_maps()

  def _init_pin_maps(self):
    """Create a map pairing pins to the correct mux control file.

    This function goes through each mux file in the omap_mux folder.
    Each file has a signals line listing the signals this mux controls.

    For example:
      signals: sig1 | sig2 | sig3 | mmc2_dat6 | NA | NA | NA | gpio0_26

    The end result is two maps that for a given signal name we can determine
    which mux file it belongs to and what is the value to select it.
    """
    # TODO (sbasi/tbroch) crbug.com/241623 - default these gpios on boot.
    for mux_file in os.listdir(MUX_ROOT):
      mux_file_path = os.path.join(MUX_ROOT, mux_file)
      if os.path.isdir(mux_file_path):
        # Skip any folders in the mux directory.
        continue
      with open(mux_file_path, 'r') as f:
        for line in f:
          # Check if this is the signals line.
          if re.match(SIGNALS_RE, line):
            # The line starts with 'signals:' which is not a field. So start
            # counting from -1.
            control_num = -1
            for field in line.split():
              if field is not '|':
                BBmuxController._pin_mode_map[field] = control_num
                BBmuxController._pin_name_map[field] = mux_file
                self._logger.debug('Pin %s in in file %s with mode %s', field,
                                   self._pin_name_map[field],
                                   self._pin_mode_map[field])
                control_num += 1

  def set_muxfile(self, mux, mode_val, sel_val):
    """Allow direct access to the muxfiles.

    Useful if a mux is incorrectly labelled.

    Args:
      mux : Mux we want to set.
      mode_val : Mode we want to assign to this i/o. Should be a 3-bit hex
                 number.
                 Bit 2: 1=Input 0=Output
                 Bit 1: 1=Pull Up 0=Pull Down
                 Bit 0: 1=Pull Enabled 0=Pull Disabled.
      sel_val : Signal we want to choose. Should be a 3-bit hex number.
    """
    mode = mode_val * 16 + sel_val
    mux = os.path.join(MUX_ROOT, mux)
    with open(mux, 'w') as mux_file:
      # We want to set the Pin Mux to the correct setting + mode.
      self._logger.debug('Writing 0x%02x to %s', mode, mux)
      mux_file.write('0x%02x' % mode)

  def set_pin_mode(self, pin_name, mode_val):
    """Select/setup a pin to be used by the Beaglebone.

    Args:
      pin_name : Pin we want to select.
      mode_val : Mode we want to assign to this i/o. Should be a 3-bit hex
                 number.
                 Bit 2: 1=Input 0=Output
                 Bit 1: 1=Pull Up 0=Pull Down
                 Bit 0: 1=Pull Enabled 0=Pull Disabled.
    """
    mux_name = BBmuxController._pin_name_map[pin_name]
    sel_val = BBmuxController._pin_mode_map[pin_name]
    self.set_muxfile(mux_name, mode_val, sel_val)