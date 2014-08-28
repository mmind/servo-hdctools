# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Expects to be run in an environment with sudo and no interactive password
# prompt, such as within the Chromium OS development chroot.

import logging
import os
import serial
import time


class _BaseHandler(object):
    """Base class for keyboard handlers.
    """
    # Power button press delays in seconds.
    #
    # The EC specification says that 8.0 seconds should be enough
    # for the long power press.  However, some platforms need a bit
    # more time.  Empirical testing has found these requirements:
    #   Alex: 8.2 seconds
    #   ZGB:  8.5 seconds
    # The actual value is set to the largest known necessary value.
    #
    # TODO(jrbarnette) Being generous is the right thing to do for
    # existing platforms, but if this code is to be used for
    # qualification of new hardware, we should be less generous.
    LONG_DELAY = 8.5
    SHORT_DELAY = 0.2
    NORMAL_TRANSITION_DELAY = 1.2

    # Maximum number of times to re-read power button on release.
    RELEASE_RETRY_MAX = 5

    # Default minimum time interval between 'press' and 'release'
    # keyboard events.
    SERVO_KEY_PRESS_DELAY = 0.1

    KEY_MATRIX = None


    def __init__(self, servo):
        """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
        # TODO(fdeng): crbug.com/298379
        # We should move servo object out of servo object
        # to minimize the dependencies on the rest of Autotest.
        self._servo = servo
        board = self._servo.get_board()


    def power_long_press(self):
        """Simulate a long power button press."""
        NotImplementedError()


    def power_normal_press(self):
        """Simulate a normal power button press."""
        NotImplementedError()


    def power_short_press(self):
        """Simulate a short power button press."""
        NotImplementedError()


    def power_key(self, secs=''):
        """Simulate a power button press.

        Args:
          secs: Time in seconds to simulate the keypress.
        """
        NotImplementedError()


    def _press_keys(self, key):
        """Simulate button presses.

        Note, key presses will remain on indefinitely. See
            _press_and_release_keys for release procedure.
        """
        NotImplementedError()


    def _press_and_release_keys(self, key, press_secs=''):
        """Simulate button presses and release."""
        NotImplementedError()


    def ctrl_d(self, press_secs=''):
        """Simulate Ctrl-d simultaneous button presses."""
        NotImplementedError()


    def ctrl_u(self, press_secs=''):
        """Simulate Ctrl-u simultaneous button presses."""
        NotImplementedError()


    def ctrl_enter(self, press_secs=''):
        """Simulate Ctrl-enter simultaneous button presses."""
        NotImplementedError()

    def d_key(self, press_secs=''):
        """Simulate Enter key button press."""
        NotImplementedError()


    def ctrl_key(self, press_secs=''):
        """Simulate Enter key button press."""
        NotImplementedError()


    def enter_key(self, press_secs=''):
        """Simulate Enter key button press."""
        NotImplementedError()


    def refresh_key(self, press_secs=''):
        """Simulate Refresh key (F3) button press."""
        NotImplementedError()


    def ctrl_refresh_key(self, press_secs=''):
        """Simulate Ctrl and Refresh (F3) simultaneous press.

        This key combination is an alternative of Space key.
        """
        NotImplementedError()


    def imaginary_key(self, press_secs=''):
        """Simulate imaginary key button press.

        Maps to a key that doesn't physically exist.
        """
        NotImplementedError()


    def custom_recovery_mode(self):
        """Custom key combination to enter recovery mode."""
        NotImplementedError()


class DefaultHandler(_BaseHandler):
    """Default keyboard handler for DUT with internal keyboards.
    """
    KEY_MATRIX = {
            'ctrl_refresh':  ['0', '0', '0', '1'],
            'ctrl_d':        ['0', '1', '0', '0'],
            'd':             ['0', '1', '1', '1'],
            'ctrl_enter':    ['1', '0', '0', '0'],
            'enter':         ['1', '0', '1', '1'],
            'ctrl':          ['1', '1', '0', '0'],
            'refresh':       ['1', '1', '0', '1'],
            'unused':        ['1', '1', '1', '0'],
            'none':          ['1', '1', '1', '1']}

    def __init__(self, servo):
        """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
        super(DefaultHandler, self).__init__(servo)


    def _press_keys(self, key):
        """Simulate button presses.

        Note, key presses will remain on indefinitely. See
            _press_and_release_keys for release procedure.
        """
        (m1_a1_n, m1_a0_n, m2_a1_n, m2_a0_n) = (
                self.KEY_MATRIX['none'])
        (m1_a1, m1_a0, m2_a1, m2_a0) = self.KEY_MATRIX[key]
        self._servo.set_get_all(['kbd_m2_a0:%s' % m2_a0_n,
                          'kbd_m2_a1:%s' % m2_a1_n,
                          'kbd_m1_a0:%s' % m1_a0_n,
                          'kbd_m1_a1:%s' % m1_a1_n,
                          'kbd_en:on',
                          'kbd_m2_a0:%s' % m2_a0,
                          'kbd_m2_a1:%s' % m2_a1,
                          'kbd_m1_a0:%s' % m1_a0,
                          'kbd_m1_a1:%s' % m1_a1])


    def power_key(self, secs=''):
        """Simulate a power button press.

        Args:
          secs: Time in seconds to simulate the keypress.
        """
        if secs is '':
            secs = self.NORMAL_TRANSITION_DELAY

        logging.info("Pressing power button for %.4f secs" % secs)
        self._servo.set_get_all(['pwr_button:press',
                          'sleep:%.4f' % secs,
                          'pwr_button:release'])
        # TODO(tbroch) Different systems have different release times on the
        # power button that this loop addresses.  Longer term we may want to
        # make this delay platform specific.
        retry = 1
        while True:
            value = self._servo.get('pwr_button')
            if value == 'release' or retry > self.RELEASE_RETRY_MAX:
                break
            logging.info('Waiting for pwr_button to release, retry %d.', retry)
            retry += 1
            time.sleep(self.SHORT_DELAY)


    def _press_and_release_keys(self, key, press_secs=''):
        """Simulate button presses and release."""
        if press_secs is '':
            press_secs = self.SERVO_KEY_PRESS_DELAY
        self._press_keys(key)
        time.sleep(press_secs)
        self._servo.set('kbd_en', 'off')

    def power_normal_press(self):
        """Simulate a normal power button press."""
        self.power_key()


    def power_long_press(self):
        """Simulate a long power button press."""
        # After a long power press, the EC may ignore the next power
        # button press (at least on Alex).  To guarantee that this
        # won't happen, we need to allow the EC one second to
        # collect itself.
        self.power_key(self.LONG_DELAY)
        time.sleep(1.0)


    def power_short_press(self):
        """Simulate a short power button press."""
        self.power_key(self.SHORT_DELAY)


    def ctrl_d(self, press_secs=''):
        """Simulate Ctrl-d simultaneous button presses."""
        self._press_and_release_keys('ctrl_d', press_secs)


    def ctrl_enter(self, press_secs=''):
        """Simulate Ctrl-enter simultaneous button presses."""
        self._press_and_release_keys('ctrl_enter', press_secs)


    def d_key(self, press_secs=''):
        """Simulate Enter key button press."""
        self._press_and_release_keys('d', press_secs)
        return True


    def ctrl_key(self, press_secs=''):
        """Simulate Enter key button press."""
        self._press_and_release_keys('ctrl', press_secs)


    def enter_key(self, press_secs=''):
        """Simulate Enter key button press."""
        self._press_and_release_keys('enter', press_secs)


    def refresh_key(self, press_secs=''):
        """Simulate Refresh key (F3) button press."""
        self._press_and_release_keys('refresh', press_secs)


    def ctrl_refresh_key(self, press_secs=''):
        """Simulate Ctrl and Refresh (F3) simultaneous press.

        This key combination is an alternative of Space key.
        """
        self._press_and_release_keys('ctrl_refresh', press_secs)


    def imaginary_key(self, press_secs=''):
        """Simulate imaginary key button press.

        Maps to a key that doesn't physically exist.
        """
        self._press_and_release_keys('unused', press_secs)


    def custom_recovery_mode(self):
        """Custom key combination to enter recovery mode."""
        self._press_keys('rec_mode')
        self.power_normal_press()
        time.sleep(self.SERVO_KEY_PRESS_DELAY)
        self._servo.set('kbd_en', 'off')


class StoutHandler(DefaultHandler):
    """Default keyboard handler for DUT with internal keyboards.

    """

    KEY_MATRIX = {
            'ctrl_d':        ['0', '0', '0', '1'],
            'd':             ['0', '0', '1', '1'],
            'unused':        ['0', '1', '1', '1'],
            'rec_mode':      ['1', '0', '0', '0'],
            'ctrl_enter':    ['1', '0', '0', '1'],
            'enter':         ['1', '0', '1', '1'],
            'ctrl':          ['1', '1', '0', '1'],
            'refresh':       ['1', '1', '1', '0'],
            'ctrl_refresh':  ['1', '1', '1', '1'],
            'none':          ['1', '1', '1', '1']}

    def __init__(self, servo):
        """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
        super(StoutHandler, self).__init__(servo)


class ParrotHandler(DefaultHandler):
    """Default keyboard handler for DUT with internal keyboards.

    """

    KEY_MATRIX = {
            'ctrl_d':        ['0', '0', '1', '0'],
            'd':             ['0', '0', '1', '1'],
            'ctrl_enter':    ['0', '1', '1', '0'],
            'enter':         ['0', '1', '1', '1'],
            'ctrl_refresh':  ['1', '0', '0', '1'],
            'unused':        ['1', '1', '0', '0'],
            'refresh':       ['1', '1', '0', '1'],
            'ctrl':          ['1', '1', '1', '0'],
            'none':          ['1', '1', '1', '1']}

    def __init__(self, servo):
        """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
        super(ParrotHandler, self).__init__(servo)



class USBkm232Handler(_BaseHandler):
    """Keyboard handler for devices without internal keyboard."""

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

    def __init__(self, servo, serial_device):
        """Constructor for usbkm232 class."""
        super(USBkm232Handler, self).__init__(servo)
        if serial_device is None:
            raise Exception("No device specified when "
                            "initializing usbkm232 keyboard handler")
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
          Exception: if response was incorrect or timed out
        """
        count = 0
        rsp = self.serial.read(1)
        while (len(rsp) != 1 or ord(orig_ch) != (~ord(rsp) & 0xff)) \
                and count < self.MAX_RSP_RETRIES:
            rsp = self.serial.read(1)
            print "re-read rsp"
            count += 1

        if count == self.MAX_RSP_RETRIES:
            raise Exception("Failed to get correct response from usbkm232")
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


    # The power key functions are a copy from DefaultHandler.
    # We need to determine if this is the long term
    # code and move to BaseHandler so that its not
    # duplicate.
    def power_key(self, secs=''):
        """Simulate a power button press.

        Args:
          secs: Time in seconds to simulate the keypress.
        """
        if secs is '':
            secs = self.NORMAL_TRANSITION_DELAY

        logging.info("Pressing power button for %.4f secs" % secs)
        self._servo.set_get_all(['pwr_button:press',
                          'sleep:%.4f' % secs,
                          'pwr_button:release'])
        # TODO(tbroch) Different systems have different release times on the
        # power button that this loop addresses.  Longer term we may want to
        # make this delay platform specific.
        retry = 1
        while True:
            value = self._servo.get('pwr_button')
            if value == 'release' or retry > self.RELEASE_RETRY_MAX:
                break
            logging.info('Waiting for pwr_button to release, retry %d.', retry)
            retry += 1
            time.sleep(self.SHORT_DELAY)


    def power_normal_press(self):
        """Simulate a normal power button press."""
        self.power_key()


    def power_long_press(self):
        """Simulate a long power button press."""
        # After a long power press, the EC may ignore the next power
        # button press (at least on Alex).  To guarantee that this
        # won't happen, we need to allow the EC one second to
        # collect itself.
        self.power_key(self.LONG_DELAY)
        time.sleep(1.0)


    def power_short_press(self):
        """Simulate a short power button press."""
        self.power_key(self.SHORT_DELAY)
    # End power key functions.

    def ctrl_d(self, press_secs=''):
        """Press and release ctrl-d sequence."""
        self._write([self._press('<lctrl>'), self._press('d')])


    def ctrl_u(self):
        """Press and release ctrl-u sequence."""
        self._write([self._press('<lctrl>'), self._press('u')])


    def d_key(self, press_secs=''):
        """Simulate Enter key button press."""
        self._write([self._press('d')])


    def enter_key(self, press_secs=''):
        """Press and release enter"""
        self._write([self._press('<enter>')])


    def ctrl_key(self, press_secs=''):
        """Simulate Enter key button press."""
        self._write([self._press('<lctrl>')])

    def crtl_enter(self):
        """Press and release ctrl+enter"""
        self._write([self._press('<lctrl>'), self._press('<enter>')])


    def space_key(self):
        """Press and release space key."""
        self._write([self._press(' ')])


    def refresh_key(self, press_secs=''):
        """Simulate Refresh key (F3) button press."""
        self._write([self._press('<f3>')])


    def ctrl_refresh_key(self, press_secs=''):
        """Simulate Ctrl and Refresh (F3) simultaneous press.
        This key combination is an alternative of Space key.
        """
        self._write([self._press('<lctrl>'), self._press('<f3>')])


    def tab(self):
        """Press and release tab"""
        self._write([self._press('<tab>')])


    def close(self):
        """Close usbkm232 device."""
        self.serial.close()
