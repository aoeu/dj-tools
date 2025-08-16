function hz
    ffprobe $argv[1] 2>&1 | grep -i hz -B4
end
