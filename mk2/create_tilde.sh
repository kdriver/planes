fgrep -a proximity output.txt | fgrep tail | sed -E 's/.*(~[A-F,0-9]*).*(icoa:[A-F,0-9]*).*(tail:[A-Z,0-9,-]* ).*/\1,\2,\3/' | sort > tilde.csv
