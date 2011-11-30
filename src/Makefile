# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

SUBDIRS		= miniservod servod
SUBDIRS_INSTALL	= $(foreach var,$(SUBDIRS),$(var)-install)

all:		$(SUBDIRS)
install:	$(SUBDIRS_INSTALL)

$(SUBDIRS):
	@$(call remake,Building,$@,all)

# No subdirectory 'install' target needs any dependency on building
# (such as 'all') The explicit dependency on 'all' here ensures that
# the full source tree is built just once.
$(SUBDIRS_INSTALL):	all
	@$(call remake,Installing,$(subst -install,,$@),install)

.PHONY:	$(SUBDIRS) $(SUBDIRS_INSTALL)

-include *.d
