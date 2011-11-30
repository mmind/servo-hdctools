# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

CFLAGS  	+= $(LIBFTDI_CFLAGS) -L $(HDCTOOLS_BUILD_DIR)/lib
LDFLAGS		+= $(LIBFTDI_LDFLAGS)

TESTS_SRC	= $(wildcard $(HDCTOOLS_SOURCE_DIR)/*_test.c)
TARGETS		= $(subst $(HDCTOOLS_SOURCE_DIR)/,,$(TESTS_SRC:.c=))

all: $(TARGETS)

f%_test: f%_test.c
	$(MESSAGE) "Building test $(notdir $@)"
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ -lpthread $(SERIAL_LIBS)

install:

-include *.d
