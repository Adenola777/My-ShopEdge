/** Dates and money as the admin pages show them, in Europe/London like every figure. */

const DATE_TIME = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/London", day: "numeric", month: "short", year: "numeric",
  hour: "2-digit", minute: "2-digit",
});
const DATE = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/London", day: "numeric", month: "short", year: "numeric",
});

/** @param {string | null | undefined} iso */
export function when(iso) {
  return iso ? DATE_TIME.format(new Date(iso)) : "";
}

/** @param {string | null | undefined} iso */
export function day(iso) {
  return iso ? DATE.format(new Date(iso)) : "";
}

/** Integer minor units to pounds, without floating point arithmetic on the amount.
 * @param {number} minor */
export function pounds(minor) {
  const sign = minor < 0 ? "-" : "";
  const abs = Math.abs(minor);
  const whole = Math.floor(abs / 100).toLocaleString("en-GB");
  return `${sign}£${whole}.${String(abs % 100).padStart(2, "0")}`;
}
