# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""GPIO polling."""

import atexit
import logging
import os
import select
import socket
import threading

import poll_common


# Ref: https://www.kernel.org/doc/Documentation/gpio/sysfs.txt
_GPIO_ROOT = '/sys/class/gpio'
_EXPORT_FILE =  os.path.join(_GPIO_ROOT, 'export')
_UNEXPORT_FILE = os.path.join(_GPIO_ROOT, 'unexport')
_GPIO_PIN_PATTERN = os.path.join(_GPIO_ROOT, 'gpio%d')


class PollGpioError(Exception):
  """Exception class for PollGpio."""
  pass


class PollGpio(object):
  """Monitors the status of one GPIO input.

  Do not create PollGpio object directly. Use factory method
  PollGpio.get_instance() to get a PollGpio object to use. Otherwise, it'd be
  problematic when two PollGpio objects controlling the same port.
  """
  # Mapping from GPIO port to (object, edge).
  _instances = dict()
  # Lock around _instances.
  _instance_lock = threading.Lock()

  # Mapping values for /sys/class/gpio/gpioN/edge.
  _EDGE_VALUES = {
      poll_common.GPIO_EDGE_RISING: 'rising',
      poll_common.GPIO_EDGE_FALLING: 'falling',
      poll_common.GPIO_EDGE_BOTH: 'both'
      }

  @classmethod
  def get_instance(cls, port, edge):
    """Constructs or returns an existing PollGpio object.

    Args:
      port: GPIO port
      edge: value in GPIO_EDGE_LIST[]

    Returns:
      PollGpio object for the port.

    Raises:
      PollGpioError: Invalid Operation.
    """
    with cls._instance_lock:
      if port not in cls._instances:
        cls._instances[port] = (PollGpio(port, edge), edge)
      elif cls._instances[port][1] != edge:
        # It's possible to support different edge types for one GPIO by setting
        # edge='both' in sysfs. But it's impractical in real-world use case
        # because hardware design should already demand one specific edge type.
        raise PollGpioError('The gpio %d was assigned different edge' % port)
      return cls._instances[port][0]

  def __init__(self, port, edge):
    """Constructor.

    Args:
      port: GPIO port
      edge: value in GPIO_EDGE_LIST[]

    Attributes:
      _port: Same as argument 'port'.
      _edge: Same as argument 'edge'.
      _logger: Logger.
      _thread: GPIO-polling thread.
      _wait_cond: Conditional variable to notify all client threads waiting for
                  GPIO edge.
      _stop_sockets: Socket pair to interrupt poll() call in polling thread.

    Raises:
      PollGpioError
    """
    try:
      self._port = port
      self._edge = edge

      self._logger = logging.getLogger('PollGpio')
      self._thread = None
      self._wait_cond = threading.Condition()
      self._stop_sockets = socket.socketpair()

      self._export_sysfs()
      self._start_thread()
      atexit.register(self._cleanup)  # must release system resource
    except Exception as e:
      raise PollGpioError('Fail to __init__ GPIO %d: %s' % (self._port, e))

  def _cleanup(self):
    """Stops the monitor thread and unexport the sysfs interface."""
    try:
      self._logger.debug('')
      self._stop_thread()
      self._unexport_sysfs()
    except Exception as e:
      logging.error('Fail to clean up GPIO %d: %s', self._port, e)

  def _start_thread(self):
    """Starts polling thread."""
    self._thread = threading.Thread(target=self._polling_loop)
    self._thread.daemon = True
    self._thread.start()

  def _stop_thread(self):
    """Stops polling thread."""
    self._stop_sockets[0].send('.')
    self._thread.join(timeout=1.0)
    if self._thread.is_alive():
      self._logger.warning('fail to stop thread of GPIO %d' % self._port)

  def _get_sysfs_path(self):
    return _GPIO_PIN_PATTERN % self._port

  def _export_sysfs(self):
    """Exports GPIO sysfs interface."""
    self._logger.debug('export GPIO port %d %s', self._port, self._edge)
    if not os.path.exists(self._get_sysfs_path()):
      with open(_EXPORT_FILE, 'w') as f:
        f.write(str(self._port))
    with open(os.path.join(self._get_sysfs_path(), 'edge'), 'w') as f:
      f.write(self._EDGE_VALUES[self._edge])

  def _unexport_sysfs(self):
    """Unexports GPIO sysfs interface."""
    self._logger.debug('unexport GPIO port %d', self._port)
    with open(_UNEXPORT_FILE, 'w') as f:
      f.write(str(self._port))

  def _read_value(self):
    """Updates the GPIO value from sysfs."""
    with open(os.path.join(self._get_sysfs_path(), 'value'), 'r') as f:
      return int(f.read().strip())

  def _polling_loop(self):
    """Main loop of polling thread."""
    with open(os.path.join(self._get_sysfs_path(), 'value'), 'r') as f:
      poll = select.poll()
      poll.register(f, select.POLLPRI | select.POLLERR)
      poll.register(self._stop_sockets[1], select.POLLIN | select.POLLERR)
      stop_flag = False
      while not stop_flag:
        # After edge is triggered, re-read from head of 'gpio[N]/value'.
        # Or poll() will return immediately next time.
        f.seek(0)
        f.read()
        self._logger.debug('poll()-ing on gpio %d', self._port)
        ret = poll.poll()
        self._logger.debug('poll() on gpio %d returns %s', self._port, ret)
        for fd, _ in ret:
          if fd == f.fileno():
            self._wait_cond.acquire()
            self._wait_cond.notifyAll()
            self._wait_cond.release()
          if fd == self._stop_sockets[1].fileno():
            if len(self._stop_sockets[1].recv(1)) > 0:
              self._logger.debug('stopping thread')
              stop_flag = True

  def poll(self):
    """Waits for a GPIO port being edge triggered.

    Raises:
      PollGpioError
    """
    try:
      self._logger.debug('client starts waiting')
      self._wait_cond.acquire()
      self._wait_cond.wait()
      self._wait_cond.release()
      self._logger.debug('client finishes waiting')
    except Exception as e:
      raise PollGpioError('Fail to poll GPIO %d: %s' % (self._port, e))
