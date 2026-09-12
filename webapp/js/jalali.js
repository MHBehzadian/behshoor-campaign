// Gregorian -> Jalali (Shamsi) conversion. Dates stay Gregorian everywhere in
// the API/DB (ISO "YYYY-MM-DD") — this only formats them for display.
const JALALI_MONTHS = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور","مهر","آبان","آذر","دی","بهمن","اسفند"];
const JALALI_WEEKDAYS = ["شنبه","یکشنبه","دوشنبه","سه‌شنبه","چهارشنبه","پنجشنبه","جمعه"];
const PERSIAN_DIGITS = ["۰","۱","۲","۳","۴","۵","۶","۷","۸","۹"];

function toPersianDigits(input) {
  return String(input).replace(/[0-9]/g, (d) => PERSIAN_DIGITS[d]);
}

// Public-domain algorithm (Pournader/Toossi), used by jalaali-js and similar.
function gregorianToJalali(gy, gm, gd) {
  const g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
  let jy = gy <= 1600 ? 0 : 979;
  gy -= gy <= 1600 ? 621 : 1600;
  const gy2 = gm > 2 ? gy + 1 : gy;
  let days =
    365 * gy +
    Math.floor((gy2 + 3) / 4) -
    Math.floor((gy2 + 99) / 100) +
    Math.floor((gy2 + 399) / 400) -
    80 +
    gd +
    g_d_m[gm - 1];
  jy += 33 * Math.floor(days / 12053);
  days %= 12053;
  jy += 4 * Math.floor(days / 1461);
  days %= 1461;
  if (days > 365) {
    jy += Math.floor((days - 1) / 365);
    days = (days - 1) % 365;
  }
  let jm, jd;
  if (days < 186) {
    jm = 1 + Math.floor(days / 31);
    jd = 1 + (days % 31);
  } else {
    jm = 7 + Math.floor((days - 186) / 30);
    jd = 1 + ((days - 186) % 30);
  }
  return [jy, jm, jd];
}

/** "۱۴۰۴/۰۶/۲۰" from a JS Date or "YYYY-MM-DD" string. */
function formatJalaliNumeric(dateLike) {
  const d = dateLike instanceof Date ? dateLike : new Date(dateLike + "T00:00:00");
  const [jy, jm, jd] = gregorianToJalali(d.getFullYear(), d.getMonth() + 1, d.getDate());
  const pad = (n) => String(n).padStart(2, "0");
  return toPersianDigits(`${jy}/${pad(jm)}/${pad(jd)}`);
}

/** "شنبه ۲۰ شهریور ۱۴۰۴" from a JS Date or "YYYY-MM-DD" string. */
function formatJalaliLong(dateLike) {
  const d = dateLike instanceof Date ? dateLike : new Date(dateLike + "T00:00:00");
  const [jy, jm, jd] = gregorianToJalali(d.getFullYear(), d.getMonth() + 1, d.getDate());
  const weekday = JALALI_WEEKDAYS[(d.getDay() + 1) % 7];
  return `${weekday} ${toPersianDigits(jd)} ${JALALI_MONTHS[jm - 1]} ${toPersianDigits(jy)}`;
}

/** "۲۰ شهریور، ۱۴:۰۵" from an ISO timestamp string. */
function formatJalaliDateTime(isoString) {
  const d = new Date(isoString);
  const [jy, jm, jd] = gregorianToJalali(d.getFullYear(), d.getMonth() + 1, d.getDate());
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return toPersianDigits(`${jd} ${JALALI_MONTHS[jm - 1]}، ${hh}:${mm}`);
}
