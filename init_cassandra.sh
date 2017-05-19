#!/bin/bash

# @file init_cassandra.sh
#
# Copyright (C) Metaswitch Networks
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


set -e

cqlsh < init_cassandra.cql
bin/python src/metaswitch/homer/data/create_db.py

echo "Finished creating DB."
