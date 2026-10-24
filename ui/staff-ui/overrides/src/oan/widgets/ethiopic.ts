// Gregorian <-> Ethiopian (Amete Mihret) calendar by Julian Day Number: the
// same arithmetic as the registry's
// oan-extension/.../register_domain/ethiopian_calendar.py, so the form and the
// server always agree. Ethiopian dates are "YYYY-MM-DD" strings: month 13
// (Pagumen, 5 or 6 days) cannot be a JavaScript or database date.

const EPOCH = 1723856;

export type Ymd = [number, number, number];

export const ETHIOPIC_MONTHS = [
    'Meskerem', 'Tikimt', 'Hidar', 'Tahsas', 'Tir', 'Yekatit',
    'Megabit', 'Miyazia', 'Ginbot', 'Sene', 'Hamle', 'Nehase', 'Pagumen',
];

const div = (a: number, b: number) => Math.floor(a / b);

const gregorianToJdn = ([y, m, d]: Ymd) => {
    const a = div(14 - m, 12);
    const yy = y + 4800 - a;
    const mm = m + 12 * a - 3;
    return d + div(153 * mm + 2, 5) + 365 * yy + div(yy, 4) - div(yy, 100) + div(yy, 400) - 32045;
};

const jdnToGregorian = (jdn: number): Ymd => {
    const a = jdn + 32044;
    const b = div(4 * a + 3, 146097);
    const c = a - div(146097 * b, 4);
    const d = div(4 * c + 3, 1461);
    const e = c - div(1461 * d, 4);
    const m = div(5 * e + 2, 153);
    return [100 * b + d - 4800 + div(m, 10), m + 3 - 12 * div(m, 10), e - div(153 * m + 2, 5) + 1];
};

const ethiopicToJdn = ([y, m, d]: Ymd) => EPOCH + 365 + 365 * (y - 1) + div(y, 4) + 30 * m + d - 31;

const jdnToEthiopic = (jdn: number): Ymd => {
    const r = (((jdn - EPOCH) % 1461) + 1461) % 1461;
    const n = (r % 365) + 365 * div(r, 1460);
    return [4 * div(jdn - EPOCH, 1461) + div(r, 365) - div(r, 1460), div(n, 30) + 1, (n % 30) + 1];
};

export const ethiopicMonthLength = (year: number, month: number) => (month === 13 ? (year % 4 === 3 ? 6 : 5) : 30);

export const isValidEthiopic = ([y, m, d]: Ymd) => y >= 1 && m >= 1 && m <= 13 && d >= 1 && d <= ethiopicMonthLength(y, m);

const pad = (n: number, width = 2) => String(n).padStart(width, '0');
export const formatYmd = ([y, m, d]: Ymd) => `${pad(y, 4)}-${pad(m)}-${pad(d)}`;

export const parseYmd = (value: unknown): Ymd | null => {
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value ?? '').trim());
    return match ? [Number(match[1]), Number(match[2]), Number(match[3])] : null;
};

/** "YYYY-MM-DD" Gregorian -> Ethiopian triple, or null. */
export const toEthiopic = (gregorian: unknown): Ymd | null => {
    const ymd = parseYmd(gregorian);
    return ymd ? jdnToEthiopic(gregorianToJdn(ymd)) : null;
};

/** Ethiopian triple -> "YYYY-MM-DD" Gregorian, or null when it is not a real day. */
export const toGregorian = (ethiopic: Ymd): string | null =>
    isValidEthiopic(ethiopic) ? formatYmd(jdnToGregorian(ethiopicToJdn(ethiopic))) : null;

export const todayGregorian = () => {
    const now = new Date();
    return formatYmd([now.getFullYear(), now.getMonth() + 1, now.getDate()]);
};
