#! /bin/bash

# This script generates the meshes for the structural model
chordSpacing=(5 10 20 40)
spanSpacing=(3 5 10 20)
verticalSpacing=(3 5 10 20)

for order in 2; do # Forget about 3rd and 4th order for now
    for i in ${!chordSpacing[@]}; do
        let "level = 3 - $i"
        fileName="wingbox-L$level-Order$order"
        python generateWingboxMesh.py --name $fileName --nChord ${chordSpacing[$i]} --nSpan ${spanSpacing[$i]} --nVertical ${verticalSpacing[$i]} --order $order
    done
done

rm -f wingbox*.dcel
