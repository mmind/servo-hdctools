# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

include $(HDCTOOLS_DIR)/defs/definitions.mk
INAS=wario servo_loc

# TODO(tbroch) should probably be added to setup.py if possible
all:
	for name in $(INAS); do \
		python "$(HDCTOOLS_SOURCE_DIR)/ina219.py" $$name; \
	done

install:
	echo "Done by ${PWD}/../../setup.py"
