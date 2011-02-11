OS_NAME = $(shell uname -s)
ifeq ($(OS_NAME),Darwin)
CC = gcc -DDARWIN
LD = gcc
LD_LIB = gcc -dynamiclib
LIB_EXT = dylib
else
CC = gcc -fPIC
LD = gcc
LD_LIB = gcc -shared 
LIB_EXT = so
endif

ifeq ($(DEBUG),1)
CC += -g -DDEBUG
else
CC += -O2
endif

PKG_CONFIG_PATH ?= /usr/lib/pkgconfig
LIBFTDI_CFLAGS   := $(shell pkg-config --cflags libftdi)
LIBFTDI_LDFLAGS  := $(shell pkg-config --libs   libftdi)

CFLAGS  = -Wall -Werror -c $(LIBFTDI_CFLAGS)
LDFLAGS = $(LIBFTDI_LDFLAGS)

SERIAL_IP = gpio uart i2c
LIB_OBJS = $(SERIAL_IP:%=libftdi%)
SERIAL_OBJS = $(SERIAL_IP:%=ftdi%.o) ftdi_common.o

TARGETS = miniservod $(SERIAL_IP:%=f%_test) 

all: $(TARGETS)

%.o : %.c %.h ftdi_common.h
	$(CC) $(CFLAGS) -o $@ $<

%_test: %_test.o $(SERIAL_OBJS)
	$(LD) $(LDFLAGS) -o $@ $^

miniservod: miniservod.o $(SERIAL_OBJS)
	$(LD) -lpthread $(LDFLAGS) -o $@ $^

# TODO(tbroch) expand to add shared libraries and install
install:
	@echo "install TBD"

clean:
	rm -f *.o *.$(LIB_EXT) $(TARGETS)
