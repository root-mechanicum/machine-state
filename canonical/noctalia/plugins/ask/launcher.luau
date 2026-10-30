--!nonstrict
-- /ask <question>: one row; Enter hands the question to cap and closes. The
-- answer comes back later as a notification and a note (`cap inbox`).
-- The question travels as one argv element, never through a shell.

local CAP = "~/src/machine-state/bin/cap"

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
	local argv = { "env", "CAP_CALLER=keypress", noctalia.expandPath(CAP), "act", "agent.ask", "prompt=" .. id }
	if not noctalia.runAsync(argv) then
		noctalia.notifyError("Ask", "could not start cap")
	end
end
