#!/bin/bash
cd /workspace/hattin-work/review; a=(); for i in "$@"; do a+=(-i $i.jpg); done; ffmpeg -v error -y "${a[@]}" -filter_complex vstack=$# /tmp/sheet.jpg
