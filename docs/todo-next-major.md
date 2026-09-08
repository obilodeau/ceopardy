# To do in the next major release

Changes worth making that would break existing games, saved databases or
operator configs. Parked here until a major release makes them cheap.

## Database schema

- Widen `State.name` from `db.String(10)`
  ([model.py](../ceopardy/model.py)). Half the keys in use are already over
  the limit -- `dailydouble-wager` (17), `overlay-question` and
  `container-header` (16), `message-text` (12) -- and only SQLite's habit of
  ignoring `VARCHAR` lengths keeps it working. Any move to a stricter engine
  breaks the host drawers.
- Widening it needs a migration, and the project has no migration tooling; a
  major release is the natural place to add one or to declare old databases
  unsupported.

## Configuration

- Identify the custom message entry with an explicit flag (`custom: true`)
  in `MESSAGES` rather than by matching the title against `"Custom"`. Renaming
  the entry currently loses the edit box. Changing the contract invalidates
  existing operator configs.

## API

- Let custom messages be multiline. `/message/show` renders
  `"<p>{0}</p>".format(text)`, so newlines collapse silently. Doing it properly
  means deciding whether host input is escaped -- today it is not, so a host
  can deliberately type HTML, and escaping takes that away.
