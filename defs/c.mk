# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file contains definitions which control the C compiler.
ifndef CC
$(warning CC not defined; assuming gcc.)
CC	= $(GCC)
endif

COPTIONS =					\
	-g					\
	-O2


# # Compiler is too old to support
# #
# #	-Wframe-larger-than=256
# #	-Wlarger-than=4096
# #	-Wsync-nand

# # Enable GC on unused functions and data
# CGC	=					\
# 	-ffunction-sections			\
# 	-fdata-sections

# Also need to link with '-Xlinker --library=pthread'.
PTHREAD	= 					\
	-pthread

# LDGC	=					\
# 	-Xlinker --gc-sections


#  TBD: These need code changes to enable.
#	-Wconversion				\
#	-Wdeclaration-after-statement		\
#	-Wextra					\
#	-Wmissing-noreturn			\
#	-Wsign-conversion			\
#	-Wredundant-decls			\
#	-Wshadow				\
#	-Wswitch-default			\
#	-Wsign-compare				\
#	-Wstrict-overflow			\
#	-Wstrict-overflow=5			\
#	-Wtraditional-conversion		\

CWARN	=					\
	-Waddress				\
	-Waggregate-return			\
	-Wall					\
	-Warray-bounds				\
	-Wbad-function-cast			\
	-Wcast-align				\
	-Wcast-qual				\
	-Wchar-subscripts			\
	-Wclobbered				\
	-Wcomment				\
	-Wdisabled-optimization			\
	-Wempty-body				\
	-Werror					\
	-Wfloat-equal				\
	-Wformat				\
	-Wformat-nonliteral			\
	-Wformat-security			\
	-Wformat-y2k				\
	-Wignored-qualifiers			\
	-Wimplicit				\
	-Winit-self				\
	-Winline				\
	-Wlogical-op				\
	-Wmain					\
	-Wmissing-braces			\
	-Wmissing-declarations			\
	-Wmissing-field-initializers		\
	-Wmissing-format-attribute		\
	-Wmissing-include-dirs			\
	-Wmissing-parameter-type		\
	-Wmissing-prototypes			\
	-Wnested-externs			\
	-Wold-style-declaration			\
	-Wold-style-definition			\
	-Woverlength-strings			\
	-Woverride-init				\
	-Wpacked				\
	-Wparentheses				\
	-Wpointer-arith				\
	-Wpointer-sign				\
	-Wreturn-type				\
	-Wsequence-point			\
	-Wstack-protector			\
	-Wstrict-aliasing			\
	-Wstrict-aliasing=3			\
	-Wstrict-prototypes			\
	-Wswitch				\
	-Wswitch-enum				\
	-Wtrigraphs				\
	-Wtype-limits				\
	-Wundef					\
	-Wuninitialized				\
	-Wunknown-pragmas			\
	-Wunsafe-loop-optimizations		\
	-Wunused-function			\
	-Wunused-label				\
	-Wunused-parameter			\
	-Wunused-value				\
	-Wunused-variable			\
	-Wvariadic-macros			\
	-Wvla					\
	-Wvolatile-register-var			\
	-Wwrite-strings				\
	-pedantic-errors

INCLUDES	=				\
		-I$(HDCTOOLS_DIR)/include	\
		-I$(HDCTOOLS_SOURCE_DIR)

ifeq ($(DEBUG),1)
  CDEBUG	= -DDEBUG
endif


ifeq ($(HDCTOOLS_OS_NAME),Darwin) # Mac
  LD_LIB = -dynamiclib
  LIB_EXT = dylib
  OS_CFLAGS += -DDARWIN
else
  ifeq ($(HDCTOOLS_OS_NAME),Linux)
    LD_LIB = -shared
    LIB_EXT = so
    OS_CFLAGS += -fPIC
  else
    $(error '$(HDCTOOLS_OS_NAME)' is not supported by the hdctools build.)
  endif
endif


CFLAGS 	=					\
	-std=gnu99				\
	-MD					\
	$(COPTIONS)				\
	$(INCLUDES)				\
	$(PTHREAD)				\
	$(CWARN)				\
	$(CGC)					\
	$(LDGC)					\
	$(CDEBUG)				\
	$(OS_CFLAGS)
