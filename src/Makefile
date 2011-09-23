OS_NAME = $(shell uname -s)
CC ?= gcc

PKG_CONFIG ?= pkg-config
LIBFTDI_CFLAGS   := $(shell $(PKG_CONFIG) --cflags libftdi)
LIBFTDI_LDFLAGS  := $(shell $(PKG_CONFIG) --libs   libftdi)

CFLAGS  = -Werror -Wall -c $(LIBFTDI_CFLAGS)
LDFLAGS = $(LIBFTDI_LDFLAGS)

ifeq ($(OS_NAME),Darwin)
LD_LIB = -dynamiclib
LIB_EXT = dylib
CFLAGS += -DDARWIN
else
LD_LIB = -shared 
LIB_EXT = so
CFLAGS += -fPIC
endif

ifeq ($(DEBUG),1)
CFLAGS += -g -DDEBUG
else
CFLAGS += -O2
endif

SERIAL_IP = gpio uart i2c
SERIAL_OBJS = $(SERIAL_IP:%=ftdi%.o) ftdi_common.o
LIBS = $(SERIAL_IP:%=libftdi%.$(LIB_EXT))
TARGETS = miniservod $(SERIAL_IP:%=f%_test) 

all: $(TARGETS) $(LIBS)

%.o : %.c Makefile *.h
	$(CC) $(CFLAGS) -o $@ $<

f%_test: f%_test.o ftdi_common.o ftdi%.o
	$(CC) $(LDFLAGS) -o $@ $^

miniservod: miniservod.o $(SERIAL_OBJS)
	$(CC) -lpthread $(LDFLAGS) -o $@ $^

servod: servod.o $(SERIAL_OBJS)
	$(CC) -lpthread $(LDFLAGS) -o $@ $^

install:
	mkdir -p $(DESTDIR)/usr/bin
	for f in $(TARGETS); \
		do cp $$f $(DESTDIR)/usr/bin/.; \
	done
	mkdir -p $(DESTDIR)/usr/lib
	for f in $(LIBS); \
		do cp $$f $(DESTDIR)/usr/lib/.; \
	done

libftdi%.$(LIB_EXT): ftdi%.o ftdi_common.o
	$(CC) $(LDFLAGS) $(LD_LIB) -o $@ $^

clean:
	rm -f *.o *.$(LIB_EXT) $(TARGETS)
