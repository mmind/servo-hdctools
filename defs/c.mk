# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file contains definitions which control the C compiler.
ifndef CC
$(warning CC not defined; assuming gcc.)
CC	= $(GCC)
endif

# COPTIONS =					\
# 	-g					\
# 	-O2					\
# 	-funit-at-a-time

# # Compiler is too old to support
# #
# #	-Wframe-larger-than=256
# #	-Wlarger-than=4096
# #	-Wsync-nand

# # Enable GC on unused functions and data
# CGC	=					\
# 	-ffunction-sections			\
# 	-fdata-sections

# # Also need to link with '-Xlinker --library=pthread'.
# PTHREAD	= 					\
# 	-pthread

# LDGC	=					\
# 	-Xlinker --gc-sections

# CWARN	=					\
# 	-Waddress				\
# 	-Waggregate-return			\
# 	-Wall					\
# 	-Warray-bounds				\
# 	-Wbad-function-cast			\
# 	-Wcast-align				\
# 	-Wcast-qual				\
# 	-Wchar-subscripts			\
# 	-Wclobbered				\
# 	-Wcomment				\
# 	-Wconversion				\
# 	-Wdeclaration-after-statement		\
# 	-Wdisabled-optimization			\
# 	-Wempty-body				\
# 	-Werror					\
# 	-Wextra					\
# 	-Wfloat-equal				\
# 	-Wformat				\
# 	-Wformat-nonliteral			\
# 	-Wformat-security			\
# 	-Wformat-y2k				\
# 	-Wignored-qualifiers			\
# 	-Wimplicit				\
# 	-Winit-self				\
# 	-Winline				\
# 	-Wlogical-op				\
# 	-Wmain					\
# 	-Wmissing-braces			\
# 	-Wmissing-declarations			\
# 	-Wmissing-field-initializers		\
# 	-Wmissing-format-attribute		\
# 	-Wmissing-include-dirs			\
# 	-Wmissing-noreturn			\
# 	-Wmissing-parameter-type		\
# 	-Wmissing-prototypes			\
# 	-Wnested-externs			\
# 	-Wold-style-declaration			\
# 	-Wold-style-definition			\
# 	-Woverlength-strings			\
# 	-Woverride-init				\
# 	-Wpacked				\
# 	-Wparentheses				\
# 	-Wpointer-arith				\
# 	-Wpointer-sign				\
# 	-Wredundant-decls			\
# 	-Wreturn-type				\
# 	-Wsequence-point			\
# 	-Wshadow				\
# 	-Wsign-compare				\
# 	-Wsign-conversion			\
# 	-Wstack-protector			\
# 	-Wstrict-aliasing			\
# 	-Wstrict-aliasing=3			\
# 	-Wstrict-overflow			\
# 	-Wstrict-overflow=5			\
# 	-Wstrict-prototypes			\
# 	-Wswitch				\
# 	-Wswitch-default			\
# 	-Wswitch-enum				\
# 	-Wtraditional-conversion		\
# 	-Wtrigraphs				\
# 	-Wtype-limits				\
# 	-Wundef					\
# 	-Wuninitialized				\
# 	-Wunknown-pragmas			\
# 	-Wunsafe-loop-optimizations		\
# 	-Wunused-function			\
# 	-Wunused-label				\
# 	-Wunused-parameter			\
# 	-Wunused-value				\
# 	-Wunused-variable			\
# 	-Wvariadic-macros			\
# 	-Wvla					\
# 	-Wvolatile-register-var			\
# 	-Wwrite-strings				\
# 	-pedantic-errors

INCLUDES	=				\
		-I$(HDCTOOLS_DIR)/include	\
		-I$(HDCTOOLS_SOURCE_DIR)

ifeq ($(DEBUG),1)
  CDEBUG	= -DDEBUG
endif

CFLAGS 	=					\
	-MD					\
	-g					\
	-O2					\
	-Wall					\
	-Werror					\
	$(CDEBUG)

ifeq ($(HDCTOOLS_OS_NAME),Darwin) # Mac
  LD_LIB = -dynamiclib
  LIB_EXT = dylib
  CFLAGS += -DDARWIN
else
  ifeq ($(HDCTOOLS_OS_NAME),Linux)
    LD_LIB = -shared
    LIB_EXT = so
    CFLAGS += -fPIC
  else
    $(error '$(HDCTOOLS_OS_NAME)' is not supported.)
  endif
endif


# CFLAGS	=					\
# 	-std=gnu99				\
# 	-MD \
# 	$(INCLUDES)				\
# 	$(PTHREADS)				\
# 	$(CWARN) $(COPTIONS) $(CGC) $(LDGC)
