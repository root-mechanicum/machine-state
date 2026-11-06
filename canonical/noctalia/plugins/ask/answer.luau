--!nonstrict
-- The answer to an /ask, and a box for a follow-up in the same thread.
--
-- cap opens this panel with the answer as markdown. A thread's answer starts
-- with one line, "@thread <id> <note>", which cap writes; without it (an old
-- note) the panel only shows the answer. A follow-up runs
-- `cap act agent.ask prompt=… thread=<id>`, the same agent with the same
-- limits; the answer lands in the note, and the panel shows the note again.
-- Everything travels as argv elements, never through a shell.

local CAP = "~/src/machine-state/bin/cap"
-- cap gives the agent 15 minutes; wait a little longer than that.
local TIMEOUT_MS = 960000

local text, thread, note = "", nil, nil
local draft, busy, problem, open, rev = "", false, nil, false, 0

local function cap(...)
	return { "env", "CAP_CALLER=keypress", noctalia.expandPath(CAP), ... }
end

local render

local function reload()
	noctalia.runAsync(cap("inbox", "body", note), function(res)
		if res.exitCode == 0 and (res.stdout or "") ~= "" then
			text = res.stdout
		end
		busy = false
		if open then render() end
	end, 10000)
end

local function send(value)
	local question = noctalia.string.trim(value or "")
	if question == "" or busy or not thread then return end
	busy, problem, draft = true, nil, ""
	rev = rev + 1
	-- Shown at once; the note's own copy replaces it when the answer is in.
	text = text .. "\n\n## " .. question
	render()
	local ok = noctalia.runAsync(cap("act", "agent.ask", "prompt=" .. question, "thread=" .. thread),
		function(res)
			if res.exitCode ~= 0 then
				problem = "No answer: " .. noctalia.string.trim(res.stdout or res.stderr or "")
			end
			reload()
		end, TIMEOUT_MS)
	if not ok then
		busy, problem = false, "could not start cap"
		render()
	end
end

render = function()
	local rows = {
		ui.row({ align = "center" }, {
			ui.label({ text = "Assistant", fontSize = 18, fontWeight = "bold", flexGrow = 1 }),
			ui.button({ text = "Close", onClick = "closeAnswer" }),
		}),
		ui.scroll({ flexGrow = 1, stickToBottom = true, scrollToBottomRev = rev },
			{ ui.markdown({ text = text }) }),
	}
	if thread then
		if busy or problem then
			rows[#rows + 1] = ui.label({ text = busy and "Thinking… (the answer also goes to the note)" or problem })
		end
		rows[#rows + 1] = ui.input({
			key = "followup-" .. tostring(rev),
			value = draft,
			placeholder = "Ask a follow-up",
			flexGrow = 1,
			focus = true,
			enabled = not busy,
			onChange = function(v) draft = v or "" end,
			onSubmit = send,
		})
	end
	panel.render(ui.column({ gap = 12, flexGrow = 1 }, rows))
end

function onOpen(context)
	open, busy, problem, draft = true, false, nil, ""
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
