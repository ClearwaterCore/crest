#!/bin/bash

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

  echo "CREATE KEYSPACE homer WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 2};
    printf "CREATE KEYSPACE ${keyspace} WITH strategy_class = 'SimpleStrategy' AND strategy_options:replication_factor = 2;" > /tmp/$$.cqlsh.in
        CREATE TABLE simservs (user text PRIMARY KEY, value text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | $namespace_prefix cqlsh 
fi
