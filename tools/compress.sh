#!/usr/bin/env bash
pushd backups
for d in */ ; do
    d="${d%/}"
    [ -L "$d" ] && continue
    date="$(date '+%Y-%m-%d')"
    tar -I 'zstd -T34 -19' --checkpoint=.1024 --totals --totals=SIGUSR1 -c -f "$date $d.tar.zst" "$d"
done
popd
