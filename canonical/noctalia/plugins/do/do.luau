--!nonstrict
-- /do: every available cap action. See actions.luau.
local p = require("./actions.luau").provider(nil)
onQuery, onActivate = p.onQuery, p.onActivate
