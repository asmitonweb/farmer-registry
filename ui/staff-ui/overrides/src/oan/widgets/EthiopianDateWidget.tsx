'use client';

import { useSelector } from 'react-redux';
import { getValueByPath, owtFieldInputClass, useWidgetContext, type WidgetRootState } from '@openg2p/registry-widgets';

type Config = Record<string, any>;

// The Ethiopian (Amete Mihret) calendar, by Julian Day Number: the same
// arithmetic as the server's register_domain/ethiopian_calendar.py.
const EPOCH = 1723856;

export const ETHIOPIC_MONTHS = [
    'Meskerem', 'Tikimt', 'Hidar', 'Tahsas', 'Tir', 'Yekatit',
    'Megabit', 'Miyazia', 'Ginbot', 'Sene', 'Hamle', 'Nehase', 'Pagumen',
];

export function gregorianToEthiopic(year: number, month: number, day: number): [number, number, number] {
    const a = Math.floor((14 - month) / 12);
    const y = year + 4800 - a;
    const m = month + 12 * a - 3;
    const jdn = day + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4) - Math.floor(y / 100)
        + Math.floor(y / 400) - 32045;
    const r = (((jdn - EPOCH) % 1461) + 1461) % 1461;
    const n = (r % 365) + 365 * Math.floor(r / 1460);
    return [
        4 * Math.floor((jdn - EPOCH) / 1461) + Math.floor(r / 365) - Math.floor(r / 1460),
        Math.floor(n / 30) + 1,
        (n % 30) + 1,
    ];
}

/** "YYYY-MM-DD" (a date widget's value, or an ISO timestamp) -> its Ethiopic triple. */
export function ethiopicOf(value: unknown): [number, number, number] | null {
    const match = typeof value === 'string' ? /^(\d{4})-(\d{2})-(\d{2})/.exec(value) : null;
    if (!match) return null;
    const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
    const check = new Date(Date.UTC(year, month - 1, day));
    if (check.getUTCMonth() !== month - 1 || check.getUTCDate() !== day) return null;
    return gregorianToEthiopic(year, month, day);
}

/**
 * The Ethiopian calendar date of a Gregorian date on the form, read-only.
 *
 * Dates are entered in the Gregorian calendar with upstream's date widget;
 * this shows the same day in the Ethiopian calendar as it is entered. The
 * stored twin (for example birth_date_ec) is derived by the server on save,
 * so this widget writes nothing.
 *
 * Section metadata:
 *   widget: "oan-ethiopian-date"
 *   widget-data-options: {source: <data path of the Gregorian date>}
 */
export function EthiopianDateWidget({ config }: { config: Config }) {
    const { t, schemaData } = useWidgetContext();
    const values = useSelector((state: WidgetRootState) => state.widget.values);
    const source = String((config['widget-data-options'] ?? {}).source ?? '');
    const typed = source ? getValueByPath(values, source) : undefined;
    const value = typed !== undefined ? typed : getValueByPath(schemaData ?? {}, source);
    const ec = ethiopicOf(value);
    const label = String(config['widget-label'] ?? '');
    const shownLabel = t ? t(label, { defaultValue: label }) : label;
    const text = ec ? `${String(ec[2]).padStart(2, '0')} ${ETHIOPIC_MONTHS[ec[1] - 1]} ${ec[0]}` : '';

    return (
        <div className="mb-[10px]">
            <div className="flex flex-col sm:flex-row sm:items-start">
                <label
                    className="flex items-baseline min-w-0 max-w-full owt-field-label text-base font-medium md:min-w-[120px] sm:pr-4 sm:pt-1 mb-1 sm:mb-0"
                    style={{ fontFamily: 'Roboto, sans-serif' }}
                >
                    <span className="min-w-0 truncate">{shownLabel}</span>
                </label>
                <div className="flex-1 min-w-0">
                    <input
                        type="text"
                        value={text}
                        readOnly
                        disabled
                        aria-readonly
                        title={ec ? `${ec[0]}-${String(ec[1]).padStart(2, '0')}-${String(ec[2]).padStart(2, '0')}` : undefined}
                        className={owtFieldInputClass({
                            disabled: true,
                            className: 'w-full sm:w-[180px] max-w-full h-[30px] px-3 owt-shadow-sm',
                        })}
                        style={{ borderRadius: '10px' }}
                    />
                </div>
            </div>
        </div>
    );
}
