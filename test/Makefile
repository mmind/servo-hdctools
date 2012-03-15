# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

BINDIR		= /usr/bin
BIN_DEST	= $(DESTDIR)$(BINDIR)

CFLAGS  	+= $(LIBFTDI_CFLAGS)
LDLIBS		+= $(LIBFTDI_LDLIBS) -lpthread \
	-L$(HDCTOOLS_BUILD_DIR)/lib $(SERIAL_LIBS)

TESTS_SRC	= $(wildcard $(HDCTOOLS_SOURCE_DIR)/*_test.c)
TARGETS		= $(subst $(HDCTOOLS_SOURCE_DIR)/,,$(TESTS_SRC:.c=))

all: $(TARGETS)

%.o : %.c Makefile
	$(COMPILE.c)

$(TARGETS): %: %.o
	$(LINK.c)

install:
	$(MKDIR) -p $(BIN_DEST)
	$(MESSAGE) "Installing '$(TARGETS)' to $(BIN_DEST)"
	$(CP) -p $(TARGETS) "$(BIN_DEST)"

-include *.d
