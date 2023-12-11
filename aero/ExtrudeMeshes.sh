#!/bin/bash
for level in 0 1 2 3; do
    mpiexec -n 14 python genVolMesh.py --level $level
done
