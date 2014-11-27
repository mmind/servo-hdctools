# Copyright 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Serial server."""

from __future__ import print_function
import copy
import glob
import logging
import os
import serial

import serial_utils


class SerialServerError(Exception):
  """Exception class for serial server."""
  pass


class SerialServer(object):
  """A server proxy for handling multiple serial connection interfaces."""

  def __init__(self, params_list):
    """Serial server constructor.

    Args:
      params_list: A list of serial connection parameters.
    """
    self._logger = logging.getLogger('SerialServer')
    # Makes connection for all on params_list and stores in a list.
    self._serials = [self._init_serial(**p) for p in params_list]

  def send(self, serial_index, command):
    """Sends a command to serial connection.

    Args:
      serial_index: index of serial connection.
      command: command to send.

    Raises:
      SerialServerError if it is timeout and fails to send the command.
    """
    try:
      serial = self._serials[serial_index]
    except IndexError:
      raise SerialServerError('index %d out of range' % serial_index)

    try:
      logging.debug('Serial index %d send command: %s', serial_index, command)
      self._serials[serial_index].Send(command + '\n')
    except serial.SerialTimeoutException as e:
      raise SerialServerError('Serial index %d send command: %s fail: %s' %
                              (serial_index, command, e))

  def receive(self, serial_index, num_bytes):
    """Receives N byte data from serial connection.

    Args:
      serial_index: index of serial connection.
      num_bytes: number of bytes to receive. 0 means receiving what already in
          the input buffer.

    Returns:
      Received N bytes.

    Raises:
      SerialServerError if it fails to receive N bytes.
    """
    try:
      serial = self._serials[serial_index]
    except IndexError:
      raise SerialServerError('index %d out of range' % serial_index)

    try:
      read_data = self._serials[serial_index].Receive(num_bytes)
      logging.debug('Serial index %d receive: %s', serial_index, read_data)
      return read_data
    except serial.SerialTimeoutException as e:
      raise SerialServerError('Serial index %d receive fail: %s' %
                              (serial_index, e))

  def _init_serial(self, **params):
    """Makes serial connection.

    Args:
      **params: parameters for serial connection.
          required fields:
          - serial_params: A dict of parameters for making a serial
              connection.

          optional fields:
          - port_index: Physical serial port index, e.g. 1-1.

    Returns:
      SerialDevice instance for corresponding parameters.

    Raises:
      SerialServerError if it fails to find connection.
    """
    serial_params = copy.deepcopy(params['serial_params'])
    serial_driver = serial_params.get('driver')

    serial_port_index = params.get('port_index')

    if serial_port_index:
      serial_path = serial_utils.FindTtyByPortIndex(serial_port_index,
                                                    serial_driver)
      if not serial_path:
        raise SerialServerError(
            'No serial device with driver %r detected at port index %s' %
            (serial_driver, serial_port_index))
      serial_params['port'] = serial_path

    elif not serial_params.get('port'):
      serial_path = serial_utils.FindTtyByDriver(serial_driver)
      if not serial_path:
        raise SerialServerError(
            'No serial device with driver %r detected' % serial_driver)
      serial_params['port'] = serial_path

    logging.info('Connect to ' + serial_params['port'])
    try:
      conn = serial_utils.SerialDevice()
      conn.Connect(**serial_params)
      return conn
    except serial.SerialException as e:
      raise SerialServerError('Connect to %s fail: %s' %
                              (serial_params['port'], e))
