# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

export HDCTOOLS_DIR = $(shell pwd)
include $(HDCTOOLS_DIR)/defs/definitions.mk

SUBDIRS		= src servo/data
SUBDIRS_INSTALL	= $(foreach var,$(SUBDIRS),$(var)-install)

all: 		$(SUBDIRS)
install:	$(SUBDIRS_INSTALL)
clean:
	@rm -rf $(HDCTOOLS_BUILD_DIR)

$(SUBDIRS):
	@$(call remake,Building,$@,all)

$(SUBDIRS_INSTALL):	$(SUBDIRS)
	@$(call remake,Installing,$(subst -install,,$@),install)

.PHONY:	$(SUBDIRS) $(SUBDIRS_INSTALL)
