# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common definitions of polld."""


# server address
DEFAULT_PORT = 9998
DEFAULT_HOST = "localhost"

# definition of edge triggers
GPIO_EDGE_RISING = 'gpio_rising'
GPIO_EDGE_FALLING = 'gpio_falling'
GPIO_EDGE_BOTH = 'gpio_both'
GPIO_EDGE_LIST = [GPIO_EDGE_RISING, GPIO_EDGE_FALLING, GPIO_EDGE_BOTH]
