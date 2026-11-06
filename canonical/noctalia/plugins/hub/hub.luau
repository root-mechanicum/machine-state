--!nonstrict
-- The hub panel: recent notifications, each with Chat, and recent
-- conversations, each with Open. Everything comes from cap and goes back to
-- cap as argv elements, never through a shell. Chat names the notification by
-- its id; cap reads its text itself and opens the answer panel on it.

local CAP = "~/src/machine-state/bin/cap"

local notifs, chats, problem, open = nil, nil, nil, false

local function cap(...)
	return { "env", "CAP_CALLER=keypress", noctalia.expandPath(CAP), ... }
end

local render

local function decoded(res)
	local v = res.exitCode == 0 and noctalia.json.decode(res.stdout or "") or nil
	return type(v) == "table" and v or {}
end

local function load()
	noctalia.runAsync(cap("notifications", "--json", "--limit", "12"), function(res)
		notifs = decoded(res)
		if open then render() end
	end, 10000)
	noctalia.runAsync(cap("inbox", "recent", "--json", "--limit", "8"), function(res)
		chats = decoded(res)
		if open then render() end
	end, 10000)
end

-- "16:15" today, "6 Nov 16:15" before.
local function when(iso)
	iso = tostring(iso or "")
	if iso == "" then return "" end
	local day, hm = iso:sub(1, 10), iso:sub(12, 16)
	if day == os.date("%Y-%m-%d") then return hm end
	local y, m, d = day:match("^(%d+)-(%d+)-(%d+)$")
	local months = { "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" }
	return d and (tostring(tonumber(d)) .. " " .. (months[tonumber(m)] or m) .. " " .. hm) or hm
end

local function discuss(id)
	problem = nil
	noctalia.runAsync(cap("act", "agent.discuss", "notification=" .. tostring(id)), function(res)
		if res.exitCode ~= 0 then
			problem = "Could not open it: " .. noctalia.string.trim(res.stdout or res.stderr or "")
			if open then render() end
		end
	end, 15000)
end

local function reopen(name)
	noctalia.runAsync(cap("inbox", "panel", name), function() end, 10000)
end

local function heading(text)
	return ui.label({ text = text, fontSize = 13, fontWeight = "bold", color = "secondary" })
end

local function entry(top, main, button)
	return ui.row({ gap = 10, align = "center", paddingH = 10, paddingV = 6, radius = 10,
		fill = "surface_container/0.40" }, {
		ui.column({ gap = 2, flexGrow = 1 }, {
			ui.label({ text = top, fontSize = 11, color = "on_surface_variant", maxLines = 1, maxWidth = 400 }),
			ui.label({ text = main, maxLines = 2, maxWidth = 400 }),
		}),
		button,
	})
end

render = function()
	local items = { heading("Notifications") }
	if notifs == nil then
		items[#items + 1] = ui.label({ text = "Loading…", color = "on_surface_variant" })
	elseif #notifs == 0 then
		items[#items + 1] = ui.label({ text = "No notifications", color = "on_surface_variant" })
	end
	for _, n in ipairs(notifs or {}) do
		local main = tostring(n.summary or "")
		local body = (tostring(n.body or ""):match("^[^\n]*") or "")
		if body ~= "" then main = main .. " · " .. body end
		items[#items + 1] = entry(tostring(n.app or "?") .. " · " .. when(n.received), main,
			ui.button({ text = "Chat", onClick = function() discuss(n.id) end }))
	end
	items[#items + 1] = heading("Conversations")
	if chats == nil then
		items[#items + 1] = ui.label({ text = "Loading…", color = "on_surface_variant" })
	elseif #chats == 0 then
		items[#items + 1] = ui.label({ text = "No conversations yet", color = "on_surface_variant" })
	end
	for _, c in ipairs(chats or {}) do
		local turns = tonumber(c.turns) or 1
		local top = when(c.when) .. " · " .. tostring(turns) .. (turns == 1 and " turn" or " turns")
			.. (c.unread and " · unread" or "")
		items[#items + 1] = entry(top, tostring(c.title or c.name),
			ui.button({ text = "Open", onClick = function() reopen(c.name) end }))
	end
	local rows = {
		ui.row({ align = "center" }, {
			ui.label({ text = "Hub", fontSize = 16, fontWeight = "bold", flexGrow = 1 }),
			ui.button({ text = "Close", onClick = function() panel.close() end }),
		}),
	}
	if problem then
		rows[#rows + 1] = ui.label({ text = problem, color = "error", maxWidth = 520 })
	end
	rows[#rows + 1] = ui.scroll({ flexGrow = 1, align = "stretch", gap = 8 }, items)
	panel.render(ui.column({ gap = 12, flexGrow = 1, align = "stretch" }, rows))
end

function onOpen(_context)
	open, problem = true, nil
	-- What was there last time, until cap answers.
	render()
	load()
end

function onClose()
	open = false
end
