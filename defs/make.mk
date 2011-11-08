# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file contains definitions that are specific to the invocation
# and usage of Gnu Make.

ifndef VERBOSE
# Be silent unless 'VERBOSE' is set on the make command line.
SILENT	= --silent
endif

export HDCTOOLS_BUILD_DIR	= $(HDCTOOLS_DIR)/build

LIBS		=							\
		$(foreach lib,$(MY_LIBS),-l$(lib))

# mkdir: Creates a directory, and all its parents, if it does not exist.
#
# If '$(MKDIR)' returns an error, it's likely because the directories
# already exist, so ignore the error by using 'true'.  If mkdir failed
# for some other reason, like 'out of space', then the build will fail
# through some other mechanism.
#
mkdir	= [ ! -d $(1) ] &&			\
	    $(MKDIR) -p $(1) || true

# remake: Gnu Make function which will create the build directory,
#         then build the first argument by recursively invoking make.
#         The recursive make is performed in the build directory.
#
#         $(call remake,<label>,<subdirectory>,<target>)
#
#         The argument to this function must be the relative pathname
#         from $(HDCTOOLS_DIR).
#
#         ex: @$(call remake,Building,servo,all)
#                             $(1)    $(2)  $(3)
#
#  REL_DIR:
#
#    Directory relative from the root of the source tree.  REL_DIR is
#    built up using the previous value plus the current target
#    directory.
#
#  HDCTOOLS_SOURCE_DIR:
#
#    The directory containing the sources for the target directory
#    being built.  This is used by Makefiles to access files in the
#    source directory.  It has the same value as VPATH.
#
#  THIS_BUILD_DIR:
#
#    The build directory which is currently being built.  This is the
#    same 'pwd', and the directory in which Make is building.
#
#  The build is performed in the build directory and VPATH is used to
#  allow Make to find the source files in the source directory.
#
remake	=								\
	+($(if $(REL_DIR),						\
		export REL_DIR=$${REL_DIR}/$(2),			\
		export REL_DIR=$(2)) &&					\
	$(call mkdir,$(HDCTOOLS_BUILD_DIR)/$${REL_DIR}) &&		\
	    $(MESSAGE) "$(1) $${REL_DIR}";				\
	    $(MAKE) $(SILENT)						\
		-f $(HDCTOOLS_DIR)/$${REL_DIR}/Makefile			\
		-C $(HDCTOOLS_BUILD_DIR)/$${REL_DIR}			\
		VPATH=$(HDCTOOLS_DIR)/$${REL_DIR}			\
		HDCTOOLS_SOURCE_DIR=$(HDCTOOLS_DIR)/$${REL_DIR}		\
		THIS_BUILD_DIR=$(HDCTOOLS_BUILD_DIR)/$${REL_DIR}	\
		$(3))

