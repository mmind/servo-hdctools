# Copyright 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

INITDIR		= /etc/init
INIT_DEST	= $(DESTDIR)$(INITDIR)

SERVOD_CONF		= servod.conf
START_SERVOD_CONF	= start_servod.conf
UPSTART_SRC		= $(HDCTOOLS_SOURCE_DIR)/$(SERVOD_CONF)
UPSTART_DST		= $(THIS_BUILD_DIR)/$(SERVOD_CONF)
UPSTART_START_SRC	= $(HDCTOOLS_SOURCE_DIR)/$(START_SERVOD_CONF)
UPSTART_START_DST	= $(THIS_BUILD_DIR)/$(START_SERVOD_CONF)

SHAREDIR	= /usr/share/cros
SHARE_DEST	= $(DESTDIR)$(SHAREDIR)
SERVOD_UTILS	= servod_utils.sh
UTIL_SRC	= $(HDCTOOLS_SOURCE_DIR)/$(SERVOD_UTILS)
UTIL_DST	= $(THIS_BUILD_DIR)/$(SERVOD_UTILS)

$(UPSTART_DST): $(UPSTART_SRC)
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

$(UPSTART_START_DST): $(UPSTART_START_SRC)
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

$(UTIL_DST): $(UTIL_SRC)
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

all:		$(UPSTART_DST) $(UPSTART_START_DST) $(UTIL_DST)

install:
	$(MKDIR) -p $(INIT_DEST)
	$(foreach CONF_FILE,$(SERVOD_CONF) $(START_SERVOD_CONF), \
		$(MESSAGE) "Installing '$(CONF_FILE)' to $(INIT_DEST)"; \
		$(CP) $(CONF_FILE) "$(INIT_DEST)"; \
		chmod a+r "$(INIT_DEST)/$(CONF_FILE)";)

	$(MKDIR) -p $(SHARE_DEST)
	$(MESSAGE) "Installing '$(SERVOD_UTILS)' to $(SHARE_DEST)"
	$(CP) $(SERVOD_UTILS) "$(SHARE_DEST)"
	chmod a+r "$(SHARE_DEST)/$(SERVOD_UTILS)"
