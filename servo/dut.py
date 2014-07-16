# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Design Under Test (DUT) specifics."""

# dictionary of alias names for various designs.
DUT_ALIASES = {'daisy_spring': 'spring',
               'rush_ryu': 'ryu'}

def get_board_name(board):
  """Return DUT board name.

  Accounts for any aliases / naming inconsistencies.

  Returns:
    string of DUT board name.
  """
  return (DUT_ALIASES[board] if board in DUT_ALIASES else board)
