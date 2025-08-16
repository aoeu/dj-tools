function dur
    ffprobe $argv[1] 2>&1 | grep Duration | cut -d, -f1
end
