# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Script to test key sequence using atmel.

Test procedure
1- start servod as sudo servod --board=panther --usbkm232=atmega
   look for output USBKM232: /dev/pts/9
2- launch script as USBKM232_UART_DEVICE=/dev/pts/9 python kb.py
3- press 1 and 2 to swtich from vt1 to vt2
4- press 1 to goto vt1, login and open a browser (as guest)
5- press 9 to see [A-Z] output to URL bar
6- press 0 to send [ -~]
7- press f to walk through all function key
8- press i to go into interactive mode and start typing
9- ctrl-x to get out of interactive mode
10 ctrl-x to get out of program
"""
import os
import sys
import termios
import time
import tty
from usbkm232 import usbkm232

keymap = {
   0: ['<lctrl>', '@'],  # NUL
   1: ['<lctrl>', 'a'],  # SOH
   2: ['<lctrl>', 'b'],  # STX
   3: ['<lctrl>', 'c'],  # ETX
   4: ['<lctrl>', 'd'],  # EOT
   5: ['<lctrl>', 'e'],  # ENQ
   6: ['<lctrl>', 'f'],  # ACK
   7: ['<lctrl>', 'g'],  # BEL
   8: ['<lctrl>', 'h'],  # BS
   9: ['<tab>'],         # HT
  10: ['<lctrl>', 'j'],  # LF
  11: ['<lctrl>', 'k'],  # VT
  12: ['<lctrl>', 'l'],  # FF
  13: ['<enter>'],       # CR
  14: ['<lctrl>', 'n'],  # SO
  15: ['<lctrl>', 'o'],  # SI
  16: ['<lctrl>', 'p'],  # DLE
  17: ['<lctrl>', 'q'],  # DC1
  18: ['<lctrl>', 'r'],  # DC2
  19: ['<lctrl>', 's'],  # DC3
  20: ['<lctrl>', 't'],  # DC4
  21: ['<lctrl>', 'u'],  # NAK
  22: ['<lctrl>', 'v'],  # SYN
  23: ['<lctrl>', 'w'],  # ETB
  24: ['<lctrl>', 'x'],  # CAN
  25: ['<lctrl>', 'y'],  # EM
  26: ['<lctrl>', 'z'],  # SUB
  27: ['<lctrl>', '['],  # ESC
  28: ['<lctrl>', '\\'], # FS
  29: ['<lctrl>', ']'],  # GS
  30: ['<lctrl>', '^'],  # RS
  31: ['<lctrl>', '_'],  # US
  32: [' '],
  33: ['<lshift>', '1'], # !
  34: ['<lshift>', '\''],# "
  35: ['<lshift>', '3'], # #
  36: ['<lshift>', '4'], # $
  37: ['<lshift>', '5'], # %
  38: ['<lshift>', '7'], # &
  39: ['\''],
  40: ['<lshift>', '9'], # (
  41: ['<lshift>', '0'], # )
  42: ['<lshift>', '8'], # *
  43: ['<lshift>', '='], # +
  44: [','],
  45: ['-'],
  46: ['.'],
  47: ['/'],
  48: ['0'],
  49: ['1'],
  50: ['2'],
  51: ['3'],
  52: ['4'],
  53: ['5'],
  54: ['6'],
  55: ['7'],
  56: ['8'],
  57: ['9'],
  58: ['<lshift>', ';'],
  59: [';'],
  60: ['<lshift>', ','], # <
  61: ['='],
  62: ['<lshift>', '.'], # >
  63: ['<lshift>', '/'], # ?
  64: ['<lshift>', '2'], # @
  65: ['<lshift>', 'a'],
  66: ['<lshift>', 'b'],
  67: ['<lshift>', 'c'],
  68: ['<lshift>', 'd'],
  69: ['<lshift>', 'e'],
  70: ['<lshift>', 'f'],
  71: ['<lshift>', 'g'],
  72: ['<lshift>', 'h'],
  73: ['<lshift>', 'i'],
  74: ['<lshift>', 'j'],
  75: ['<lshift>', 'k'],
  76: ['<lshift>', 'l'],
  77: ['<lshift>', 'm'],
  78: ['<lshift>', 'n'],
  79: ['<lshift>', 'o'],
  80: ['<lshift>', 'p'],
  81: ['<lshift>', 'q'],
  82: ['<lshift>', 'r'],
  83: ['<lshift>', 's'],
  84: ['<lshift>', 't'],
  85: ['<lshift>', 'u'],
  86: ['<lshift>', 'v'],
  87: ['<lshift>', 'w'],
  88: ['<lshift>', 'x'],
  89: ['<lshift>', 'y'],
  90: ['<lshift>', 'x'],
  91: ['['],
  92: ['\\'],
  93: [']'],
  94: ['<lshift>', '6'], # ^
  95: ['<lshift>', '-'], # _
  96: ['`'],
  97: ['a'],
  98: ['b'],
  99: ['c'],
  100: ['d'],
  101: ['e'],
  102: ['f'],
  103: ['g'],
  104: ['h'],
  105: ['i'],
  106: ['j'],
  107: ['k'],
  108: ['l'],
  109: ['m'],
  110: ['n'],
  111: ['o'],
  112: ['p'],
  113: ['q'],
  114: ['r'],
  115: ['s'],
  116: ['t'],
  117: ['u'],
  118: ['v'],
  119: ['w'],
  120: ['x'],
  121: ['y'],
  122: ['z'],
  123: ['<lshift>', '['], # {
  124: ['<lshift>', '\\'],# |
  125: ['<lshift>', ']'], # }
  126: ['<lshift>', '`'], # ~
  127: ['<backspace>'],   # DEL
}


def direct_send_seq(kbd, rlist):
  # rlist contains the actual code from usbkm232.py
  buf = []
  for k in rlist:
    buf.append(kbd._press(k))
  for k in rlist:
    buf.append(kbd._release(k))
  kbd._write(buf)


def menu():
  print """
  \r 1 to VT1
  \r 2 to VT2
  \r 0 to send [ -~]
  \r 9 to send [A-Z]
  \r f send function keys (best in VT2 with browser history)
  \r i for interactive (ctrl-X to exit mode)
  \r ctrl-x to exit program.
  \r
  """


def main():
  """Main method."""
  try:
    kbd = usbkm232(os.environ['USBKM232_UART_DEVICE'])
  except KeyError:
    print "-E- Must set environment variable USBKM232_UART_DEVICE"
    sys.exit(-1)
  menu()
  fd = sys.stdin.fileno()
  old_settings = termios.tcgetattr(fd)
  interactive_mode = False
  try:
    tty.setraw(sys.stdin.fileno())
    while True:
      ch = sys.stdin.read(1)
      print '\rRead %c:%d\r' % (ch, ord(ch))
      if interactive_mode:
        if ord(ch) == 24: # Ctrl-X
          print '\rInteractive mode off:\r'
          interactive_mode = False
          menu()
          continue
        buf = []
        for keycode in keymap[ord(ch)]:
          buf.append(kbd._press(keycode))
        kbd._write(buf)
        continue
      # Menu items
      if ch == 'i':  # interactive mode
        print '\rInteractive mode on (ctrl-x to leave).\r'
        interactive_mode = True
      elif ch == 'm':
        menu()
      elif ch == '1':  # VT1
        direct_send_seq(kbd, ['<lctrl>', '<lalt>', '<f1>'])
      elif ch == '2':  # VT2
        direct_send_seq(kbd, ['<lctrl>', '<lalt>', '<f2>'])
      elif ch == '0':  # send [ -~]
        for k in range(32,127):
          buf = []
          for j in keymap[k]:
             buf.append(kbd._press(j))
          kbd._write(buf)
      elif ch == '9':  # send [A-Z].  Note no capslock in VT1
        kbd._write([kbd._press('<capslock>')])
        for k in range(97,123):  # [a-z]
          buf = []
          for j in keymap[k]:
             buf.append(kbd._press(j))
          kbd._write(buf)
        kbd._write([kbd._press('<capslock>')])
      elif ch == 'f': # Send F1- F12
        for i in range(1,12):
          s = '<f%d>' % i
          print '\rSend %s' % s
          direct_send_seq(kbd, [s])
          time.sleep(1)
      elif ord(ch) == 24: # Ctrl-X
        break
      print '\r'
  finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
  kbd.close()


if __name__ == "__main__":
  main()
