# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inas = [
        # TODO(nsanders): Come up with a way to support multiple voltages.
        (0x40, 'ppdut5', 5.0, 0.01, 'rem', True), # A0: GND, A1: GND
       ]
interface = 3
