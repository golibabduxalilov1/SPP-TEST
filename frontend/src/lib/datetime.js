// <input type="datetime-local"> values are naive (no timezone marker) and
// represent the browser's own local wall clock — not necessarily the same
// timezone the backend assumes for naive strings. Converting to a UTC
// instant here removes that ambiguity for every consumer of these values.
export function toApiInstant(localDatetimeValue) {
  if (!localDatetimeValue) return localDatetimeValue;
  const date = new Date(localDatetimeValue);
  if (Number.isNaN(date.getTime())) return localDatetimeValue;
  return date.toISOString();
}
