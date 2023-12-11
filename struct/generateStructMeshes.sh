#! /bin/bash

# This script generates the meshes for the structural model
chordSpacing=(5 10 20 40)
spanSpacing=(3 5 10 20)
verticalSpacing=(3 5 10 20)

# for order in 2 3 4; do
order=2
for i in ${!chordSpacing[@]}; do
    let "level = 3 - $i"
    fileName="wingbox-L$level-Order$order"
    python generateWingbox.py --name $fileName --nChord ${chordSpacing[$i]} --nSpan ${spanSpacing[$i]} --nVertical ${verticalSpacing[$i]} --order $order
done
# done
