# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
OS_NAME = $(shell uname -s)
CC ?= gcc

PKG_CONFIG ?= pkg-config
LIBFTDI_CFLAGS   := $(shell $(PKG_CONFIG) --cflags libftdi)
LIBFTDI_LDFLAGS  := $(shell $(PKG_CONFIG) --libs   libftdi)

ifeq ($(DEBUG),1)
CFLAGS += -g -DDEBUG
else
CFLAGS ?= -O2
endif

CFLAGS  += -Werror -Wall $(LIBFTDI_CFLAGS)
LDFLAGS += $(LIBFTDI_LDFLAGS)

ifeq ($(OS_NAME),Darwin)
LD_LIB = -dynamiclib
LIB_EXT = dylib
CFLAGS += -DDARWIN
else
LD_LIB = -shared 
LIB_EXT = so
CFLAGS += -fPIC
endif

SERIAL_IP = gpio uart i2c
SERIAL_OBJS = $(SERIAL_IP:%=ftdi%.o) ftdi_common.o
LIBS = $(SERIAL_IP:%=libftdi%.$(LIB_EXT))
TARGETS = miniservod $(SERIAL_IP:%=f%_test)

all: $(TARGETS) $(LIBS)

%.o : %.c Makefile *.h
	$(CC) $(CFLAGS) $(CPPFLAGS) -c -o $@ $<

f%_test: f%_test.o ftdi_common.o ftdi%.o
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ -lpthread

miniservod: miniservod.o $(SERIAL_OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ -lpthread

servod: servod.o $(SERIAL_OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ -lpthread

BINDIR = /usr/bin
LIBDIR = /usr/lib
install:
	mkdir -p $(DESTDIR)$(BINDIR)
	for f in $(TARGETS); \
		do cp $$f $(DESTDIR)$(BINDIR)/.; \
	done
	mkdir -p $(DESTDIR)$(LIBDIR)
	for f in $(LIBS); \
		do cp $$f $(DESTDIR)$(LIBDIR)/.; \
	done

libftdi%.$(LIB_EXT): ftdi%.o ftdi_common.o
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ $(LD_LIB)
