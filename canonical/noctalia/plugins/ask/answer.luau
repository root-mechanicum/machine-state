-- The answer is passed as panel context, not interpreted as code or a path.
function onOpen(context)
	local answer = context or "No answer was supplied."
	panel.render(ui.column({ gap = 12, flexGrow = 1 }, {
		ui.row({ align = "center" }, {
			ui.label({ text = "Assistant", fontSize = 18, fontWeight = "bold", flexGrow = 1 }),
			ui.button({ text = "Close", onClick = "closeAnswer" }),
		}),
		ui.scroll({ flexGrow = 1 }, { ui.markdown({ text = answer }) }),
	}))
end

function closeAnswer()
	panel.close()
end
