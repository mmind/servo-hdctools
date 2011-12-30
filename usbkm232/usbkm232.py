# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Class to control and interact with USBKM232 USB keyboard emulator."""
import serial
import sys
import time

VERSION = "0.0.1"

class usbkm232Error(Exception):
    """Exception class for usbkm232."""


class usbkm232(object):
    """usbkm232 Class."""
    MAX_RSP_RETRIES = 10
    USB_QUEUE_DEPTH = 6
    CLEAR = '\x38'
    KEYS = {
        #row 1
        '`': 1,
        '1': 2,
        '2': 3,
        '3': 4,
        '4': 5,
        '5': 6,
        '6': 7,
        '7': 8,
        '8': 9,
        '9': 10,
        '0': 11,
        '-': 12,
        '=': 13,
        '<undef1>': 14,
        '<backspace>': 15,
        '<tab>': 16,
        'q': 17,
        'w': 18,
        'e': 19,
        'r': 20,
        't': 21,
        'y': 22,
        'u': 23,
        'i': 24,
        'o': 25,
        'p': 26,
        '[': 27,
        ']': 28,
        '\\': 29,
        # row 2
        '<capslock>': 30,
        'a': 31,
        's': 32,
        'd': 33,
        'f': 34,
        'g': 35,
        'h': 36,
        'j': 37,
        'k': 38,
        'l': 39,
        ';': 40,
        '\'': 41,
        '<undef2>': 42,
        '<enter>': 43,
        # row 3
        '<lshift>': 44,
        '<undef3>': 45,
        'z': 46,
        'x': 47,
        'c': 48,
        'v': 49,
        'b': 50,
        'n': 51,
        'm': 52,
        ',': 53,
        '.': 54,
        '/': 55,
        '[clear]': 56,
        '<rshift>': 57,
        # row 4
        '<lctrl>': 58,
        '<undef5>': 59,
        '<lalt>': 60,
        ' ': 61,
        '<ralt>': 62,
        '<undef6>': 63,
        '<rctrl>': 64,
        '<undef7>': 65,
        '<mouse_left>': 66,
        '<mouse_right>': 67,
        '<mouse_up>': 68,
        '<mouse_down>': 69,
        '<lwin>': 70,
        '<rwin>': 71,
        '<win apl>': 72,
        '<mouse_lbtn_press>': 73,
        '<mouse_rbtn_press>': 74,
        '<insert>': 75,
        '<delete>': 76,
        '<mouse_mbtn_press>': 77,
        '<undef16>': 78,
        '<larrow>': 79,
        '<home>': 80,
        '<end>': 81,
        '<undef23>': 82,
        '<uparrow>': 83,
        '<downarrow>': 84,
        '<pgup>': 85,
        '<pgdown>': 86,
        '<mouse_scr_up>': 87,
        '<mouse_scr_down>': 88,
        '<rarrow>': 89,
        # numpad
        '<numlock>': 90,
        '<num7>': 91,
        '<num4>': 92,
        '<num1>': 93,
        '<undef27>': 94,
        '<num/>': 95,
        '<num8>': 96,
        '<num5>': 97,
        '<num2>': 98,
        '<num0>': 99,
        '<num*>': 100,
        '<num9>': 101,
        '<num6>': 102,
        '<num3>': 103,
        '<num.>': 104,
        '<num->': 105,
        '<num+>': 106,
        '<numenter>': 107,
        '<undef28>': 108,
        '<mouse_slow>': 109,
        # row 0
        '<esc>': 110,
        '<mouse_fast>': 111,
        '<f1>': 112,
        '<f2>': 113,
        '<f3>': 114,
        '<f4>': 115,
        '<f5>': 116,
        '<f6>': 117,
        '<f7>': 118,
        '<f8>': 119,
        '<f9>': 120,
        '<f10>': 121,
        '<f11>': 122,
        '<f12>': 123,
        '<prtscr>': 124,
        '<scrllk>': 125,
        '<pause/brk>': 126,
        }

    def __init__(self, serial_device):
        """Constructor for usbkm232 class."""
        self.serial = serial.Serial(serial_device, 9600, timeout=0.1)
        self.serial.setInterCharTimeout(0.5)
        self.serial.setTimeout(0.5)
        self.serial.setWriteTimeout(0.5)


    def _press(self, press_ch):
        """Encode and return character to press using usbkm232.

        Args:
          press_ch: character to press

        Returns:
          Proper encoding to send to the uart side of the usbkm232 to create the
          desired key press.
        """
        return '%c' % self.KEYS[press_ch]


    def _release(self, release_ch):
        """Encode and return character to release using usbkm232.

        This value is simply the _press_ value + 128

        Args:
          release_ch: character to release

        Returns:
          Proper encoding to send to the uart side of the usbkm232 to create the
          desired key release.
        """
        return '%c' % (self.KEYS[release_ch] | 0x80)


    def _rsp(self, orig_ch):
        """Check response after sending character to usbkm232.

        The response is the one's complement of the value sent.  This method
        blocks until proper response is received.

        Args:
          orig_ch: original character sent.

        Raises:
          usbkm232Error: if response was incorrect or timed out
        """
        count = 0
        rsp = self.serial.read(1)
        while (len(rsp) != 1 or ord(orig_ch) != (~ord(rsp) & 0xff)) \
                and count < self.MAX_RSP_RETRIES:
            rsp = self.serial.read(1)
            print "re-read rsp"
            count += 1

        if count == self.MAX_RSP_RETRIES:
            raise Usbkm232Error("Failed to get correct response from usbkm232")
        print "usbkm232: response [-] = \\0%03o 0x%02x" % (ord(rsp), ord(rsp))



    def _write(self, mylist, check=False, clear=True):
        """Write list of commands to usbkm232.

        Args:
          mylist: list of encoded commands to send to the uart side of the
            usbkm232
          check: boolean determines whether response from usbkm232 should be
            checked.
          clear: boolean determines whether keytroke clear should be sent at end
            of the sequence.
        """
        # TODO(tbroch): USB queue depth is 6 might be more efficient to write
        #               more than just one make/break
        for i, write_ch in enumerate(mylist):
            print "usbkm232: writing  [%d] = \\0%03o 0x%02x" % \
                (i, ord(write_ch), ord(write_ch))
            self.serial.write(write_ch)
            if check:
                self._rsp(write_ch)
            time.sleep(.05)

        if clear:
            print "usbkm232: clearing keystrokes"
            self.serial.write(self.CLEAR)
            if check:
                self._rsp(self.CLEAR)


    def writestr(self, mystr):
        """Write string to usbkm232.

        Args:
          mystr: string to send across the usbkm232
          """
        rlist = []
        for write_ch in mystr:
            rlist.append(self._press(write_ch))
            rlist.append(self._release(write_ch))
        self._write(rlist)


    def ctrl_d(self):
        """Press and release ctrl-d sequence."""
        self._write([self._press('<lctrl>'), self._press('d')])


    def ctrl_u(self):
        """Press and release ctrl-u sequence."""
        self._write([self._press('<lctrl>'), self._press('u')])


    def enter(self):
        """Press and release enter"""
        self._write([self._press('<enter>')])


    def space(self):
        """."""
        self._write([self._press(' ')])


    def close(self):
        """Close usbkm232 device."""
        self.serial.close()


def main():
    """Test method."""
    if len(sys.argv) != 2:
        print "-E- USAGE: %s <device of uart>"
        sys.exit(-1)

    kbd = usbkm232(sys.argv[1])
    try:
        while True:
            user_input = raw_input("Enter string to type: ")
            kbd.writestr(user_input)
    except KeyboardInterrupt:
        kbd.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
