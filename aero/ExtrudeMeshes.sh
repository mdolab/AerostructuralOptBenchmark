#!/bin/bash
for level in L1 L2 L3; do
    mpiexec -n 8 python genVolMesh.py --level $level
done
