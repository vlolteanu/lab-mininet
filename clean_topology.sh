#!/bin/bash

for i in {0..128}
do
    ip link del "t$i-u$i" 2> /dev/null
done

for i in {0..128}
do
    for j in {0..128}
    do
        ip link del "c$i-s$j" 2> /dev/null
        ip link del "s$i-t$j" 2> /dev/null
    done
done
