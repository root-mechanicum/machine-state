--!nonstrict
-- /do: cap's catalogue as launcher rows. provider(category) narrows it.
--
--   <filter>          rows for matching actions; Enter runs one without args,
--                     or puts its name in the query to take args
--   <action> <args>   one row; bare values fill the declared args in order,
--                     key=value names one. Enter runs it.
--
-- Everything runs as an argv table, never through a shell.

local CAP = "~/src/machine-state/bin/cap"

local function cap()
	return noctalia.expandPath(CAP)
end

local function words(s)
	local out = {}
	for w in s:gmatch("%S+") do
		table.insert(out, w)
	end
	return out
end

local function argNames(a)
	-- JSON objects lose their order in Luau tables; cap lists args in declared
	-- order as `arg_order`, falling back to sorted names.
	if type(a.arg_order) == "table" then
		return a.arg_order
	end
	local names = {}
	for k in a.args or {} do
		table.insert(names, k)
	end
	table.sort(names)
	return names
end

local function invocation(a, rest)
	local argv, given, names, nextPos = { cap(), "act", a.action }, {}, argNames(a), 1
	for _, w in words(rest) do
		local k, v = w:match("^([%w_]+)=(.*)$")
		if not k then
			while names[nextPos] and given[names[nextPos]] do
				nextPos += 1
			end
			k, v = names[nextPos], w
		end
		if not k then
			return nil, "too many values"
		end
		given[k] = true
		table.insert(argv, k .. "=" .. v)
	end
	return argv
end

local function run(argv, label)
	noctalia.runAsync(argv, function(res)
		if res.exitCode ~= 0 then
			local msg = (res.stderr ~= "" and res.stderr or res.stdout):gsub("%s+$", "")
			noctalia.notifyError(label, msg:match("[^\n]*$") or "failed")
		end
	end, 60000)
end

local function rows(catalogue, filter, category)
	local out = {}
	for _, a in catalogue do
		if a.available and (not category or a.category == category) then
			local score = nil
			if filter ~= "" then
				score = noctalia.fuzzyScore(filter, a.label .. " " .. a.action .. " " .. (a.category or ""))
			end
			if filter == "" or score then
				local takesArgs = next(a.args or {}) ~= nil
				table.insert(out, {
					id = takesArgs and "" or noctalia.json.encode({ argv = { cap(), "act", a.action }, label = a.label }),
					query = takesArgs and (a.action .. " ") or nil,
					title = a.label,
					subtitle = a.action .. (takesArgs and ("  ·  " .. table.concat(argNames(a), " ")) or ""),
					glyph = category and "app-window" or "bolt",
					score = score,
				})
			end
		end
	end
	return out
end

local function withArgs(catalogue, text, category)
	local name, rest = text:match("^(%S+)%s+(.*)$")
	if not name then
		name, rest = text, nil
	end
	for _, a in catalogue do
		if a.action == name and a.available and (not category or a.category == category) then
			if rest == nil and next(a.args or {}) == nil then
				return nil
			end
			local argv, err = invocation(a, rest or "")
			if not argv then
				return { { id = "", title = a.label, subtitle = err, glyph = "alert-triangle" } }
			end
			local shown = table.concat(argv, " ", 4)
			return { {
				id = noctalia.json.encode({ argv = argv, label = a.label }),
				title = a.label,
				subtitle = "Enter: " .. a.action .. (shown ~= "" and (" " .. shown) or "")
					.. "  ·  args: " .. table.concat(argNames(a), " "),
				glyph = category and "app-window" or "bolt",
			} }
		end
	end
	return nil
end

local M = {}

function M.provider(category)
	local p = {}

	function p.onQuery(query)
		local text = noctalia.string.trim(query or "")
		noctalia.runAsync({ cap(), "list", "--json" }, function(res)
			local catalogue = res.exitCode == 0 and noctalia.json.decode(res.stdout) or nil
			if type(catalogue) ~= "table" then
				launcher.setResults(query, { { id = "", title = "cap is not answering",
					subtitle = (res.stderr or ""):match("[^\n]*") or "", glyph = "alert-triangle" } })
				return
			end
			launcher.setResults(query, withArgs(catalogue, text, category) or rows(catalogue, text, category))
		end, 10000)
	end

	function p.onActivate(id)
		if id == "" then
			return
		end
		local job = noctalia.json.decode(id)
		if type(job) == "table" and type(job.argv) == "table" then
			table.insert(job.argv, 1, "env")
			table.insert(job.argv, 2, "CAP_CALLER=launcher")
			run(job.argv, job.label or "cap")
		end
	end

	return p
end

return M
