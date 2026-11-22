// Pure state transitions for the administrator's workspace sharing picker.
// Kept free of DOM access so the selection rules can be tested directly in Node.
// granted is now a { name: role } map; role is "chat" (协作) or "viewer" (只读).

export function createShareState(users, owner, granted = {}) {
  const candidates = (Array.isArray(users) ? users : [])
    .filter(user => user && typeof user.name === "string" && user.name && user.name !== owner)
    .map(user => ({ name: user.name, displayName: user.displayName || user.name }));
  const known = new Set(candidates.map(user => user.name));
  const grantedMap = {};
  if (Array.isArray(granted)) {
    for (const name of granted) if (typeof name === "string" && known.has(name)) grantedMap[name] = "chat";
  } else if (granted && typeof granted === "object") {
    for (const [name, role] of Object.entries(granted))
      if (known.has(name)) grantedMap[name] = role === "viewer" ? "viewer" : "chat";
  }
  return {
    candidates,
    granted: grantedMap,
    available: candidates.filter(user => !Object.hasOwn(grantedMap, user.name)).map(user => user.name)
  };
}

export function moveShareMembers(state, direction, names) {
  const grant = direction === "grant";
  const source = new Set(grant ? state.available : Object.keys(state.granted));
  const moving = new Set((Array.isArray(names) ? names : []).filter(name => source.has(name)));
  if (!moving.size) return state;
  const granted = { ...state.granted };
  if (grant) { for (const name of moving) granted[name] = "chat"; }
  else { for (const name of moving) delete granted[name]; }
  return {
    candidates: state.candidates,
    granted,
    available: state.candidates.filter(user => !Object.hasOwn(granted, user.name)).map(user => user.name)
  };
}

export function setShareRole(state, name, role) {
  if (!Object.hasOwn(state.granted, name)) return state;
  if (role !== "viewer" && role !== "chat") return state;
  return { ...state, granted: { ...state.granted, [name]: role } };
}
