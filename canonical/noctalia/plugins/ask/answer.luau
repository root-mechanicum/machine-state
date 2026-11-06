--!nonstrict
-- An /ask thread as a conversation: the person's questions and the agent's
-- answers in bubbles, and a box at the bottom for a follow-up.
--
-- cap opens this panel with the note as markdown. A thread's starts with one
-- line, "@thread <id> <note>", which cap writes; without it (an old note) the
-- panel shows the answer and no box. In the note, "# question" opens the first
-- turn and a "<!-- you -->" line, written only by cap, opens each later one. A
-- "<!-- from: App -->" line opens a turn someone else wrote, such as the
-- notification a discussion is about; cap has already made its text literal.
-- A follow-up runs `cap act agent.ask prompt=… thread=<id>`, the same agent
-- with the same limits; the answer lands in the note, and the panel rereads it.
-- Everything travels as argv elements, never through a shell.

local CAP = "~/src/machine-state/bin/cap"
-- cap gives the agent 15 minutes; wait a little longer than that.
local TIMEOUT_MS = 960000
local YOU = "<!-- you -->"
-- ui.markdown wraps only at a width it is given; the panel is 620 wide.
local TEXT_WIDTH = 460

-- Markdown that wraps inside its bubble. A question is sized to its length,
-- roughly, so a short one gets a small bubble; an answer takes the full width.
local function wrapped(who, md)
	local width = TEXT_WIDTH
	if who == "you" then
		width = math.max(40, math.min(TEXT_WIDTH, #md * 8))
	end
	return ui.markdown({ text = md, width = width })
end

local text, thread, note = "", nil, nil
local pending, problem, open, rev = nil, nil, false, 0

local function cap(...)
	return { "env", "CAP_CALLER=keypress", noctalia.expandPath(CAP), ... }
end

-- The note as turns: { who = "you" | "agent" | "from", name, text = markdown }.
local function turns(body)
	local out = {}
	local function add(kind, name, chunk)
		chunk = noctalia.string.trim(chunk)
		if kind == "from" then
			if chunk ~= "" then
				out[#out + 1] = { who = "from", name = name, text = chunk }
			end
			return
		end
		local q, rest = chunk:match("^#+ ([^\n]*)\n?(.*)$")
		if q then
			out[#out + 1] = { who = "you", text = q }
			chunk = noctalia.string.trim(rest)
		end
		if chunk ~= "" then
			out[#out + 1] = { who = "agent", text = chunk }
		end
	end
	-- A marker is a whole line; the leading newline lets the first line be one.
	local s = "\n" .. body .. "\n"
	local kind, name, start, pos = "start", nil, 1, 1
	while true do
		local i, j, line = s:find("\n(<!%-%- [^\n]- %-%->)\n", pos)
		if not i then break end
		local from = line:match("^<!%-%- from: (.-) %-%->$")
		if line == YOU or from then
			add(kind, name, s:sub(start, i - 1))
			kind, name, start = from and "from" or "you", from, j + 1
		end
		-- The closing newline may open the next marker.
		pos = j
	end
	add(kind, name, s:sub(start))
	return out
end

-- Questions tinted, answers outlined; both markdown, neither a heading. What
-- someone else wrote is tinted differently and carries its sender's name.
local function bubble(who, content, name)
	local mine = who == "you"
	local style = mine and { paddingH = 12, paddingV = 8, radius = 12, gap = 4, fill = "primary/0.16" }
		or who == "from" and { paddingH = 12, paddingV = 8, radius = 12, gap = 4, fill = "tertiary/0.14" }
		or { paddingH = 12, paddingV = 8, radius = 12, gap = 4,
			border = "outline_variant", borderWidth = 1 }
	local children = { content }
	if who == "from" then
		children = { ui.label({ text = name or "", fontSize = 11, fontWeight = "bold",
			color = "tertiary", maxLines = 1 }), content }
	end
	local box = ui.column(style, children)
	if mine then
		return ui.row({}, { ui.spacer({ flexGrow = 1 }), box })
	end
	return ui.row({}, { box, ui.spacer({ flexGrow = 1 }) })
end

local render

local function reload()
	noctalia.runAsync(cap("inbox", "body", note), function(res)
		if res.exitCode == 0 and (res.stdout or "") ~= "" then
			text = res.stdout
		end
		pending = nil
		rev = rev + 1
		if open then render() end
	end, 10000)
end

local function send(value)
	local question = noctalia.string.trim(value or "")
	if question == "" or pending or not thread then return end
	pending, problem = question, nil
	rev = rev + 1
	render()
	local ok = noctalia.runAsync(cap("act", "agent.ask", "prompt=" .. question, "thread=" .. thread),
		function(res)
			if res.exitCode ~= 0 then
				problem = "No answer: " .. noctalia.string.trim(res.stdout or res.stderr or "")
			end
			reload()
		end, TIMEOUT_MS)
	if not ok then
		pending, problem = nil, "Could not start cap."
		render()
	end
end

render = function()
	local items, title = {}, nil
	for _, t in ipairs(turns(text)) do
		if not title then
			if t.who == "you" then
				title = t.text
			elseif t.who == "from" then
				-- cap escaped the text for markdown; the title is a plain label.
				title = t.name .. ": " .. ((t.text:match("^[^\n]*") or ""):gsub("\\(.)", "%1"))
			end
		end
		items[#items + 1] = bubble(t.who, wrapped(t.who, t.text), t.name)
	end
	if pending then
		items[#items + 1] = bubble("you", wrapped("you", pending))
		items[#items + 1] = bubble("agent", ui.label({ text = "Thinking…", color = "secondary" }))
	end
	if problem then
		items[#items + 1] = ui.label({ text = problem, color = "error" })
	end
	local rows = {
		ui.row({ align = "center" }, {
			-- The first question names the window; the discussion itself has no headings.
			ui.label({ text = title or "Assistant", fontSize = 16, fontWeight = "bold",
				flexGrow = 1, maxLines = 1 }),
			ui.button({ text = "Close", onClick = "closeAnswer" }),
		}),
		ui.scroll({ flexGrow = 1, align = "stretch", gap = 10, stickToBottom = true,
			scrollToBottomRev = rev }, items),
	}
	if thread then
		rows[#rows + 1] = ui.input({
			key = "followup-" .. tostring(rev),
			value = "",
			placeholder = pending and "Waiting for the answer…"
				or (#items == 1 and "Say what you want to know or do" or "Ask a follow-up"),
			focus = true,
			enabled = not pending,
			onSubmit = send,
		})
	end
	panel.render(ui.column({ gap = 12, flexGrow = 1, align = "stretch" }, rows))
end

function onOpen(context)
	open, pending, problem = true, nil, nil
	rev = rev + 1
	local id, name, rest = (context or ""):match("^@thread ([%x%-]+) ([%w%._%-]+%.md)\n(.*)$")
	if id then
		thread, note, text = id, name, rest
	else
		thread, note, text = nil, nil, context or "No answer was supplied."
	end
	render()
end

function onClose()
	open = false
end

function closeAnswer() panel.close() end
