# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Terminal Freezer utility"""

from __future__ import print_function

import logging
import os
import re
import signal
import subprocess
import time


def CheckForPIDNamespace():
  """Checks to see if we are running with PID namespaces.

  Raises:
    OSError if we are running within the chroot with PID namespaces.
  """
  with open('/proc/1/cmdline') as f:
    if 'cros_sdk' in f.readline():
      raise OSError('You must run this tool in a chroot that was entered'
                    ' with "cros_sdk --no-ns-pid" (see crbug.com/444931 for'
                    ' details)')


class TerminalFreezer(object):
  """SIGSTOP all processes (and their parents) that have the TTY open."""

  def __init__(self, tty):
    self._tty = tty
    self._logger = logging.getLogger('Terminal Freezer (%s)' % self._tty)
    self._processes = None
    CheckForPIDNamespace()

  def __enter__(self):
    try:
      ret = subprocess.check_output(['lsof', '-FR', self._tty],
                                    stderr=subprocess.STDOUT)
    except subprocess.check_output:
      # Ignore non-zero return codes.
      pass

    self._processes = re.findall(r'^(?:R|p)(\d+)$', ret, re.MULTILINE)

    # Don't kill servod, we need that.
    servod_processes = []
    for p in self._processes:
      with open('/proc/%s/cmdline' % p) as f:
        if 'servod' in f.readline():
          servod_processes.append(p)

    self._logger.debug('servod processes: %r', servod_processes)
    for p in servod_processes:
      self._processes.remove(p)

    # SIGSTOP parents before children.
    try:
      for p in reversed(self._processes):
        self._logger.debug('Sending SIGSTOP to process %s!', p)
        time.sleep(0.02)
        os.kill(int(p), signal.SIGSTOP)
    except OSError:
      self.__exit__(None, None, None)
      raise

  def __exit__(self, _t, _v, _b):
    # ...and wake 'em up again in reverse order.
    for p in self._processes:
      self._logger.debug('Sending SIGCONT to process %s!', p)
      try:
        os.kill(int(p), signal.SIGCONT)
      except OSError as e:
        self._logger.error('Error when trying to unfreeze process %s: %s', p, e)
