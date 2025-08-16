function make-playlist
    ls -1 | grep -E '(flac|mp3|wav)'  > "00 - "(pwd | rev | cut -d/ -f1 | rev).m3u
end
