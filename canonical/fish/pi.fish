# Pi in its own memory-limited scope. On 2026-11-11 a script Pi wrote looped forever and filled
# RAM and swap; systemd-oomd then killed the whole kitty window, Pi included, twice in 30 minutes.
# Inside this scope the kernel kills only the biggest process when the limit is hit (the runaway
# command), OOMPolicy=continue keeps Pi alive, and Pi sees "Killed" (exit 137) as the tool result.
# 8G + 4G swap: Strata resident leaves ~7 GB of RAM, and Pi itself needs a few hundred MB.
# Bypass for one run: `command pi`.
function pi --description 'Pi inside a memory limit (machine-state)'
    systemd-run --user --scope --quiet --collect \
        -p MemoryMax=8G -p MemorySwapMax=4G -p OOMPolicy=continue \
        -- (command -s pi) $argv
end
