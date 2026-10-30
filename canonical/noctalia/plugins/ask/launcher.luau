--!nonstrict
-- /ask <question>: one row; Enter hands the question to cap and closes. The
-- answer comes back later as a notification and a note (`cap inbox`).

local function shellQuote(s)
	return "'" .. s:gsub("'", "'\\''") .. "'"
end

local function capPath()
	local p = noctalia.getConfig("cap_path")
	return noctalia.expandPath((type(p) == "string" and p ~= "") and p or "~/src/machine-state/bin/cap")
end

function onQuery(query)
	local text = noctalia.string.trim(query or "")
	if text == "" then
		launcher.setResults(query, {
			{ id = "", title = "Ask the agent…", subtitle = "Type a question; the answer arrives as a notification", glyph = "sparkles" },
		})
		return
	end
	launcher.setResults(query, {
		{ id = text, title = text, subtitle = "Ask — sees the windows on this workspace", glyph = "sparkles" },
	})
end

function onActivate(id)
	if id == "" then
		return
	end
	-- keypress: a refusal shows as a notification instead of vanishing.
	local cmd = "env CAP_CALLER=keypress " .. shellQuote(capPath()) .. " act agent.ask prompt=" .. shellQuote(id)
	if not noctalia.runAsync(cmd) then
		noctalia.notifyError("Ask", "could not start cap")
	end
end
