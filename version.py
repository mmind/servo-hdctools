# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import subprocess


def get_ghash():
  """Get the hash of the latest git commit.

  Returns:
    string of the hash, or 'unknown' if not found.
  """
  try:
    ghash = subprocess.check_output(
        ['git', 'rev-parse', '--short',  '--verify', 'HEAD']).rstrip()
  except:
    # Fall back to the VCSID provided by the packaging system.
    try:
      ghash = os.environ['VCSID'].rsplit('-', 1)[1][:7]
    except:
      ghash = 'unknown'
  return ghash


__version__ = '0.0.1-' + get_ghash()
