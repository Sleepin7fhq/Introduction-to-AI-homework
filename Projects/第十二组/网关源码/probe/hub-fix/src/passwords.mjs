import crypto from "node:crypto";

const SCRYPT = { N: 16384, r: 8, p: 1, keylen: 64 };

// Async scrypt so a login / password hash never blocks the event loop.
// crypto.scrypt's callback form is wrapped rather than util.promisify to keep
// the (password, salt, keylen, options) signature unambiguous.
function scryptAsync(password, salt, keylen, options) {
  return new Promise((resolve, reject) => {
    crypto.scrypt(password, salt, keylen, options, (error, key) => error ? reject(error) : resolve(key));
  });
}

export function generatePassword(length = 10) {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";
  const bytes = crypto.randomBytes(length);
  return Array.from(bytes, b => alphabet[b % alphabet.length]).join("");
}

export async function hashPassword(password, salt = crypto.randomBytes(16).toString("hex")) {
  const hash = (await scryptAsync(password, salt, SCRYPT.keylen, SCRYPT)).toString("hex");
  return { salt, hash };
}

export async function verifyPassword(password, salt, expectedHash) {
  if (!password || !salt || !expectedHash) return false;
  const actual = await scryptAsync(password, salt, Buffer.from(expectedHash, "hex").length, SCRYPT);
  return crypto.timingSafeEqual(actual, Buffer.from(expectedHash, "hex"));
}
