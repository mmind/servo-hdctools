# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk
include $(HDCTOOLS_DIR)/defs/utilities.mk

SUBDIRS		= data drv
SUBDIRS_INSTALL	= $(foreach var,$(SUBDIRS),$(var)-install)
PYTHON_SRC	= $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.py))
PYTHON_DST	= $(addprefix $(THIS_BUILD_DIR)/, $(PYTHON_SRC))
LIBFTDI_DEP	= $(THIS_BUILD_DIR)/libftdi_for_servo.py

$(LIBFTDI_DEP):
	$(MESSAGE) "Determine libftdi version using $(PKG_CONFIG)"
	$(PKG_CONFIG) --exists libftdi1 && echo "LIB_NAME = 'ftdi1'" > $@ || \
		echo "LIB_NAME = 'ftdi'" > $@

$(THIS_BUILD_DIR)/%.py: $(HDCTOOLS_SOURCE_DIR)/%.py
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

all: 		$(LIBFTDI_DEP) $(PYTHON_DST) $(SUBDIRS)
install:	$(SUBDIRS_INSTALL)

$(SUBDIRS):
	@$(call remake,Building,$@,all)

$(SUBDIRS_INSTALL):
	@$(call remake,Installing,$(subst -install,,$@),install)

.PHONY:	$(SUBDIRS) $(SUBDIRS_INSTALL)
