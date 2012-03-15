# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

BINDIR		= /usr/bin
BIN_DEST	= $(DESTDIR)$(BINDIR)

CFLAGS  	+= $(LIBFTDI_CFLAGS)
LDLIBS		+= $(LIBFTDI_LDLIBS) -lpthread \
	-L$(HDCTOOLS_BUILD_DIR)/lib $(SERIAL_LIBS)

TARGETS		= miniservod

all: $(TARGETS)

%.o : %.c Makefile
	$(MESSAGE) "Compiling $(notdir $<)"
	$(CC) $(CFLAGS) -c -o $@ $<

miniservod: miniservod.o
	$(MESSAGE) "Building $(notdir $@)"
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ $(LDLIBS)

install:
	$(MESSAGE) "Installing '$(TARGETS)' to $(BIN_DEST)"
	$(MKDIR) -p $(BIN_DEST)
	$(CP) $(TARGETS) "$(BIN_DEST)"

-include *.d
