const DIGITS_AFTER_998 = 9;

// Strips everything but digits, drops a leading "998" (with or without "+")
// so the user can type "998901234567" or "901234567" and get the same result.
function extractLocalDigits(raw) {
  let digits = (raw || "").replace(/\D/g, "");
  if (digits.startsWith("998")) digits = digits.slice(3);
  return digits.slice(0, DIGITS_AFTER_998);
}

// Formats as the user types: "+998 90 123 45 67"
export function formatUzPhone(raw) {
  const digits = extractLocalDigits(raw);
  if (!digits) return "+998 ";
  const parts = [digits.slice(0, 2), digits.slice(2, 5), digits.slice(5, 7), digits.slice(7, 9)].filter(Boolean);
  return `+998 ${parts.join(" ")}`;
}

// Normalizes to the canonical "+998901234567" shape the backend expects.
export function normalizeUzPhone(formatted) {
  return `+998${extractLocalDigits(formatted)}`;
}

export function isValidUzPhone(formatted) {
  return extractLocalDigits(formatted).length === DIGITS_AFTER_998;
}
