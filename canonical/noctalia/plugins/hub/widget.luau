--!nonstrict
-- The hub in the bar: an icon, and for a minute after a notification its app
-- and summary. Click opens the hub panel either way.

local SHOW_S = 60
local fresh = noctalia.state.get("fresh")

local function live()
	return type(fresh) == "table" and (os.time() - (tonumber(fresh.at) or 0)) < SHOW_S
end

local function render()
	local on = live()
	local children = {
		ui.glyph({ name = "message-circle", size = 16, color = on and "primary" or "on_surface" }),
	}
	if on then
		children[2] = ui.label({
			text = tostring(fresh.app or "") .. ": " .. tostring(fresh.summary or ""),
			fontSize = 11, maxLines = 1, maxWidth = 240,
		})
	end
	barWidget.render(ui.row({ gap = 6, align = "center" }, children))
	barWidget.setTooltip(on and "Talk about it, or see recent notifications and conversations"
		or "Notifications and conversations")
end

function update() render() end

function onClick()
	noctalia.togglePanel("machine-state/hub:hub")
end

noctalia.state.watch("fresh", function(v)
	fresh = v
	render()
end)
noctalia.setUpdateInterval(5000)
render()
