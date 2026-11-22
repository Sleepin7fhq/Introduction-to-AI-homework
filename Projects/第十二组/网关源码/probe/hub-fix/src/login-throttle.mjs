// In-memory per (account, IP) login throttle with exponential backoff.
// State is deliberately not persisted: a gateway restart clears lockouts, which
// is acceptable for a LAN demo gateway and avoids writing client IPs to disk.
// Only counters and timestamps are kept — never the password.

const MAX_FAILURES = 5;                 // failures before locking
const BASE_BACKOFF_MS = 10 * 1000;      // first lockout: 10 s
const MAX_BACKOFF_MS = 15 * 60 * 1000;  // cap at 15 min
const STALE_MS = 60 * 60 * 1000;        // forget entries after 1 h idle

export function createLoginThrottle() {
  const entries = new Map(); // key -> { failures, lockedUntil, lastFailure }
  const now = () => Date.now();
  const key = (username, ip) => `${String(username).toLowerCase()}\u0000${ip}`; // 大小写不敏感，防改大小写绕过退避（审计 P3）

  function prune() {
    const t = now();
    for (const [k, v] of entries) {
      if (t - v.lastFailure > STALE_MS) entries.delete(k);
    }
  }

  return {
    check(username, ip) {
      const entry = entries.get(key(username, ip));
      if (!entry) return { allowed: true, failures: 0 };
      if (entry.lockedUntil > now()) {
        return { allowed: false, retryAfterMs: entry.lockedUntil - now(), failures: entry.failures };
      }
      return { allowed: true, failures: entry.failures };
    },
    recordFailure(username, ip) {
      prune();
      const k = key(username, ip);
      const entry = entries.get(k) || { failures: 0, lockedUntil: 0, lastFailure: now() };
      entry.failures += 1;
      entry.lastFailure = now();
      if (entry.failures >= MAX_FAILURES) {
        const backoff = Math.min(BASE_BACKOFF_MS * Math.pow(2, entry.failures - MAX_FAILURES), MAX_BACKOFF_MS);
        entry.lockedUntil = now() + backoff;
      }
      entries.set(k, entry);
      return { failures: entry.failures, lockedUntil: entry.lockedUntil };
    },
    recordSuccess(username, ip) {
      entries.delete(key(username, ip));
    }
  };
}
