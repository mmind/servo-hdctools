# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

LIBDIR		= /usr/lib
LIB_DEST	= $(DESTDIR)$(LIBDIR)

CFLAGS  	+= $(LIBFTDI_CFLAGS)
LDFLAGS		+= $(LIBFTDI_LDFLAGS)
LIBS		+= $(SERIAL_LIBS) -lpthread

TARGETS		= servod

all: $(TARGETS)

%.o : %.c Makefile
	$(MESSAGE) "Compiling $(notdir $<)"
	$(CC) $(CFLAGS) -c -o $@ $<

servod: servod.o
	$(MESSAGE) "Building $(notdir $@)"
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^	\
		-L$(HDCTOOLS_BUILD_DIR)/lib	\
		-lpthread			\
		$(SERIAL_LIBS)

install:
	$(MESSAGE) "Installing '$(TARGETS)' to $(LIB_DEST)"
	$(MKDIR) -p $(LIB_DEST)
	$(CP) $(TARGETS) "$(LIB_DEST)"

-include *.d
