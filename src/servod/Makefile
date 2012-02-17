# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

BINDIR		= /usr/bin
BIN_DEST	= $(DESTDIR)$(BINDIR)

CFLAGS  	+= $(LIBFTDI_CFLAGS)
LDFLAGS		+= $(LIBFTDI_LDFLAGS)
LIBS		+= $(SERIAL_LIBS) -lpthread

TARGETS		= servod-bin

all: $(TARGETS)

%.o : %.c Makefile
	$(MESSAGE) "Compiling $(notdir $<)"
	$(CC) $(CFLAGS) -c -o $@ $<

servod-bin: servod.o
	$(MESSAGE) "Building $(notdir $@)"
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^	\
		-L$(HDCTOOLS_BUILD_DIR)/lib	\
		-lpthread			\
		$(SERIAL_LIBS)

install:
	$(MESSAGE) "Installing '$(TARGETS)' to $(BIN_DEST)"
	$(MKDIR) -p $(BIN_DEST)
	$(CP) $(TARGETS) "$(BIN_DEST)"

-include *.d
