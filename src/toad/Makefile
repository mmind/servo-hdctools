# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

BINDIR		= /usr/bin
BIN_DEST	= $(DESTDIR)$(BINDIR)

ETCDIR		= /etc
ETC_DEST	= $(DESTDIR)$(ETCDIR)
UDEV_DEST	= $(ETC_DEST)/udev/rules.d

ifeq ($(FTDIVERSION),)
  LDLIBS	+= -lusb
endif

CFLAGS  	+= -Wno-cast-qual $(LIBFTDI_CFLAGS)
LDLIBS		+= $(LIBFTDI_LDLIBS)

FTDI_COMMON	= $(HDCTOOLS_BUILD_DIR)/lib/ftdicommon.o

TARGETS		= toad
UDEV_RULE	= $(HDCTOOLS_DIR)/$${REL_DIR}/50-toad.rules

all: $(TARGETS)

%.o : %.c Makefile
	$(COMPILE.c)

toad: toad.o $(FTDI_COMMON)
	$(LINK.c)

install:
	$(MESSAGE) "Installing '$(TARGETS)' to $(BIN_DEST)"
	$(MKDIR) -p $(BIN_DEST)
	$(CP) $(TARGETS) "$(BIN_DEST)"
	$(MESSAGE) "Installing '$(notdir $(UDEV_RULE))' to $(UDEV_DEST)"
	$(MKDIR) -p $(UDEV_DEST)
	$(CP) $(UDEV_RULE) $(UDEV_DEST)

-include *.d
