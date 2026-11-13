-- A cap-validated summary card. Its fixed actions never come from the model.
local CAP = "~/src/machine-state/bin/cap"
local card, problem, busy = nil, nil, false

local function render()
	local original = type(card.original) == "table" and card.original or {}
	local rows = {
		ui.label({ text = card.source or "Notification", color = "secondary", maxLines = 1 }),
		ui.label({ text = card.title or "Summary", fontSize = 16, fontWeight = "bold", maxLines = 3 }),
		ui.scroll({ flexGrow = 1, align = "stretch" }, {
			ui.label({ text = card.summary or "", maxWidth = 500 }),
			ui.label({ text = "Original notification", color = "secondary", maxLines = 1 }),
			ui.label({ text = tostring(original.summary or ""), fontWeight = "bold", maxWidth = 500 }),
			ui.label({ text = tostring(original.body or ""), maxWidth = 500 }),
		}),
	}
	if problem then rows[#rows + 1] = ui.label({ text = problem, color = "error", maxWidth = 500 }) end
	rows[#rows + 1] = ui.row({ gap = 8 }, {
		ui.button({ text = "Discuss", enabled = not busy, onClick = function()
			if busy then return end
			busy = true
			noctalia.runAsync({ "env", "CAP_CALLER=keypress", noctalia.expandPath(CAP),
				"act", "agent.discuss", "notification=" .. tostring(card.notification),
				"card=" .. tostring(card.id) }, function(res)
				busy = false
				if res.exitCode ~= 0 then
					problem = "Could not open discussion: " .. noctalia.string.trim(res.stdout or res.stderr or "")
					render()
				else
					panel.close()
				end
			end, 15000)
		end }),
		ui.button({ text = "Close", onClick = function() panel.close() end }),
	})
	panel.render(ui.column({ gap = 12, flexGrow = 1, align = "stretch" }, rows))
end

function onOpen(context)
	local v = noctalia.json.decode(context or "")
	card = type(v) == "table" and v or {}
	problem = card.type ~= "summary_card" and "Invalid presentation." or nil
	busy = problem ~= nil
	render()
end
