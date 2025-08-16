function durs
    for f in *.flac 
        echo $f && dur $f
    end
end
