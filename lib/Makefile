# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

LIBDIR		= /usr/lib
LIB_DEST	= $(DESTDIR)$(LIBDIR)

CFLAGS  	+= $(LIBFTDI_CFLAGS)
LDLIBS		+= $(LIBFTDI_LDLIBS)

SERIAL_OBJS	= $(SERIAL_IP:%=ftdi%.o)
LIBS		= $(SERIAL_IP:%=libftdi%.$(LIB_EXT))

all:	$(LIBS)

%.o : %.c Makefile
	$(COMPILE.c)

$(LIBS): ftdicommon.o
libftdi%.$(LIB_EXT): ftdi%.o
	$(LINK.c) $(LD_LIB)

install:
	$(MKDIR) -p $(LIB_DEST)
	$(MESSAGE) "Installing '$(LIBS)' to $(LIB_DEST)"
	$(CP) $(LIBS) "$(LIB_DEST)"

-include *.d
# The test object files normally are deleted because they are
# implicitly built (See 'build chain' and/or '.secondary' in the Gnu
# Make manual).  The result of this deletion is that the test programs
# are rebuilt if 'make && make' is executed.  With '.secondary', they
# are not deleted.
.secondary:    $(SERIAL_OBJS)
