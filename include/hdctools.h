/* Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */
#if !defined(_HDCTOOLS_H_)
#define _HDCTOOLS_H_
#include <assert.h>

/* assert_on_compile: Produce compile-time error if '_expr'
 *                    is not constant & true.
 */
#define assert_on_compile(_expr)                                        \
    do {                                                                \
        enum { assert_on_compile_enum = ((_expr) ? 1 : -1) };           \
        typedef char assert_on_compile_type[assert_on_compile_enum];    \
    } while (0)
#endif

/* ARRAY_LENGTH: Produces number of elements in an array.
 *
 * NOTE: Do not use this with declared pointer types, only array
 *       types.
 */
#define ARRAY_LENGTH(_arr) (sizeof(_arr) / sizeof(_arr[0]))

/* PARSE_NUMBER: Use strtoul() to parse a number from text.
 *
 * __text: 'nptr' argument to strtoul()
 * __ptr : 'endptr' parameter to strtoul().
 * __dest: Location where parsed value should be stored.
 *
 *  NOTE: '0' is always used as the 'base' argument of strtoul().
 *
 *        If the parsed 'unsigned long' value does not fit in the
 *        destination, an assertion will fire.
 */
#define PARSE_NUMBER(__text, __ptr, __dest)                     \
    do {                                                        \
        unsigned long __temp = strtoul(__text, __ptr, 0);       \
        __dest = (typeof(__dest))__temp;                        \
        /* Ensure represenation didn't chagne */                \
        assert((typeof(__temp))__dest == __temp);               \
    } while (0)

#define NIBBLE(_v) (unsigned char)((_v) & 0xf)
#define MAKE_BYTE(_hi, _lo) (unsigned char)((NIBBLE(_hi) << 4) | NIBBLE(_lo))
