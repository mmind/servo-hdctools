# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Common functions for tools and libraries related to FTDI devices.
"""
import ctypes
import ctypes.util
import optparse
import os
import sys

import ftdi_common


def ftdi_locate_lib(lib_name):
  """Locate FTDI related dll path.

  TODO(tbroch) To remove in favor of ctypes.util.find_library(lib_name) once
  release of libraries in chroot is complete.

  Args:
    lib_name : string name of library to find
  """
  paths = []
  paths.append(os.getcwd())
  if 'FTDI_LIBRARY_PATH' in os.environ:
    paths.extend(os.environ['FTDI_LIBRARY_PATH'].split(os.pathsep))
  if 'LD_LIBRARY_PATH' in os.environ:
    paths.extend(os.environ['LD_LIBRARY_PATH'].split(os.pathsep))

  lib_ext = ".so"
  if os.name == "posix" and sys.platform == "darwin":
    lib_ext = ".dylib"

  for path in paths:
    lib_path = os.path.join(path,'lib' + lib_name + lib_ext)
    if os.path.exists(lib_path):
      return os.path.realpath(lib_path)
  # Try the default OS library path
  return 'lib' + lib_name + lib_ext


def load_libs(*args):
  """Load libraries and return dll objects.

  Calls sys.exit if unable to locate the library

  Args:
    args : list of strings names of libraries to load

  Returns:
   List of PyDLL objects
  """
  dll_list = []
  for lib_name in args:
    lib_path = ftdi_locate_lib(lib_name)
    try:
      dll_list.append(ctypes.cdll.LoadLibrary(lib_path))
    except OSError,e:
      print "-E- Unable to find library %s : %s" % (lib_name, e)
      sys.exit(1)
  return dll_list

def parse_common_args(vendor=ftdi_common.DEFAULT_VID,
                      product=ftdi_common.DEFAULT_PID, interface=1,
                      serialname=None):
  """Parse common arguments for tools related to FTDI devices.

  Args:
    vendor    : integer value of USB vendor id of FTDI device
    product   : integer value of USB vendor id of FTDI device
    interface : integer ( 1 - 4 ) of interface on FTDI device
    serialname: string of device serialname/number as defined in FTDI eeprom.

  Returns:
    (values, args) where 'values' is a optparse.Values instance and 'args' is
    the list of arguments left over after parsing options.
  """
  parser = optparse.OptionParser()
  parser.add_option("-d", "--debug", help="enable debug messages",
                    action="store_true", default=False)
  parser.add_option("-v", "--vendor", help="vendor id of ftdi device",
                    default=vendor, type=int)
  parser.add_option("-p", "--product", help="product id of ftdi device",
                    default=product, type=int)
  parser.add_option("-i", "--interface", help="ftdi interface to use",
                    type=int, default=interface)
  parser.add_option("-s", "--serialname", default=None, type=str,
                    help="device serialname stored in eeprom")
  return parser.parse_args()
