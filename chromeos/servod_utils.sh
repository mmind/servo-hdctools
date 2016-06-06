# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

update_config() {
  local config_file=$1
  local key=$2
  local value=$3

  if [ -z "$value" ]; then
    return
  fi

  # If file exists and key is in the config file, replace it in the file.
  # Otherwise append it to the config file.
  if [ -f $config_file ] && grep -q "^${key}=" "$config_file"; then
    sed -i "/$key/c$key=$value" $config_file
  else
    echo "$key=$value" >> $config_file
  fi
}
