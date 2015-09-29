#! /bin/bash

keyspace=$(basename $0|sed -e 's#^\(.*\)[.]sh$#\1#')
. /etc/clearwater/config
if [ ! -z $signaling_namespace ]; then
    if [ $EUID -ne 0 ]; then
        echo "When using multiple networks, schema creation must be run as root"
        exit 2
    fi
    namespace_prefix="ip netns exec $signaling_namespace"
fi

$(dirname $0)/../bin/wait4cassandra ${keyspace}
if [ $? -ne 0 ]; then
    exit 1
fi

if [[ ! -e /var/lib/cassandra/data/${keyspace} ]]; then
    echo "CREATE KEYSPACE homestead_provisioning WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 2};
USE homestead_provisioning;
CREATE TABLE implicit_registration_sets (id uuid PRIMARY KEY, dummy text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE service_profiles (id uuid PRIMARY KEY, irs text, initialfiltercriteria text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE public (public_id text PRIMARY KEY, publicidentity text, service_profile text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE private (private_id text PRIMARY KEY, digest_ha1 text, realm text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | $namespace_prefix cqlsh 
fi

echo "USE homestead_provisioning; DESC TABLE private" | cqlsh | grep plaintext_password > /dev/null
if [ $? != 0 ]; then
  echo "USE homestead_provisioning;
  ALTER TABLE private ADD plaintext_password text;" | $namespace_prefix cqlsh
fi
