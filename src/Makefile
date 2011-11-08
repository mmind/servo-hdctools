# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

BINDIR		= /usr/bin
LIBDIR		= /usr/lib
BIN_DEST	= $(DESTDIR)$(BINDIR)
LIB_DEST	= $(DESTDIR)$(LIBDIR)

LIBFTDI_CFLAGS	:= $(shell $(PKG_CONFIG) --cflags libftdi)
LIBFTDI_LDFLAGS	:= $(shell $(PKG_CONFIG) --libs   libftdi)
CFLAGS  	+= $(LIBFTDI_CFLAGS)
LDFLAGS		+= $(LIBFTDI_LDFLAGS)

SERIAL_IP	= gpio uart i2c
SERIAL_OBJS	= $(SERIAL_IP:%=ftdi%.o) ftdi_common.o
LIBS		= $(SERIAL_IP:%=libftdi%.$(LIB_EXT))
TESTS		= $(SERIAL_IP:%=f%_test)
TARGETS		= miniservod servod $(TESTS)

all: $(TARGETS) $(LIBS)

%.o : %.c Makefile
	$(MESSAGE) "Compiling $(notdir $<)"
	$(CC) $(CFLAGS) -c -o $@ $<

f%_test: f%_test.o ftdi_common.o ftdi%.o
	$(MESSAGE) "Building test $(notdir $@)"
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ -lpthread

miniservod: miniservod.o $(SERIAL_OBJS)
	$(MESSAGE) "Building $(notdir $@)"
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ -lpthread

servod: servod.o $(SERIAL_OBJS)
	$(MESSAGE) "Building $(notdir $@)"
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ -lpthread

libftdi%.$(LIB_EXT): ftdi%.o ftdi_common.o
	$(MESSAGE) "Building library $(notdir $@)"
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ $(LD_LIB)

install:
	$(MESSAGE) "Installing '$(TARGETS)' to $(BIN_DEST)"
	$(MKDIR) -p $(BIN_DEST)
	$(CP) $(TARGETS) "$(BIN_DEST)"
	$(MKDIR) -p $(LIB_DEST)
	$(MESSAGE) "Installing '$(LIBS)' to $(LIB_DEST)"
	$(CP) $(LIBS) "$(LIB_DEST)"

-include *.d

# The test object files normally are deleted because they are
# implicitly built (See 'build chain' and/or '.secondary' in the Gnu
# Make manual).  The result of this deletion is that the test programs
# are rebuilt if 'make && make' is executed.  With '.secondary', they
# are not deleted.
.secondary:	$(TESTS:%=%.o)
