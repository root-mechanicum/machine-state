--!nonstrict
-- Notices new notifications. Every few seconds it stats Noctalia's history file,
-- which is cheap; only when the file changed does it ask cap for the newest
-- entry. A new one is published as `fresh` for the bar widget. What is already
-- there at start is not new, and cap's own answers have their own popup.

local CAP = "~/src/machine-state/bin/cap"
local HISTORY = "~/.local/state/noctalia/notification_history.json"

local stamp, seen, busy = nil, nil, false

local function newest()
	busy = true
	noctalia.runAsync({ noctalia.expandPath(CAP), "notifications", "--json", "--limit", "1" }, function(res)
		busy = false
		local list = res.exitCode == 0 and noctalia.json.decode(res.stdout or "") or nil
		local n = type(list) == "table" and list[1] or nil
		if type(n) ~= "table" or n.id == seen then return end
		local first = seen == nil
		seen = n.id
		if first or n.app == "cap" then return end
		noctalia.state.set("fresh", { id = n.id, app = n.app, summary = n.summary, at = os.time() })
	end, 10000)
end

function update()
	if busy then return end
	busy = true
	noctalia.runAsync({ "stat", "-c", "%.9Y %s", noctalia.expandPath(HISTORY) }, function(res)
		busy = false
		local now = res.exitCode == 0 and noctalia.string.trim(res.stdout or "") or nil
		if now and now ~= stamp then
			stamp = now
			newest()
		end
	end, 5000)
end

noctalia.setUpdateInterval(3000)
update()
