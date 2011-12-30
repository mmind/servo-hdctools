# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Convenience script to press key sequence using usbkm232."""
import os
import sys

from usbkm232 import usbkm232


def main():
    """Main method."""
    try:
        kbd = usbkm232(os.environ['USBKM232_UART_DEVICE'])
    except KeyError:
        print "-E- Must set environment variable USBKM232_UART_DEVICE"
        sys.exit(-1)
    count = 1
    if len(sys.argv) > 1:
        count = int(sys.argv[1])

    for _ in xrange(0, count):
        kbd.space()
    kbd.close()


if __name__ == "__main__":
    main()
