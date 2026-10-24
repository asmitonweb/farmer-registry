'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useDispatch } from 'react-redux';
import { setValueByPath, setValues, useBaseWidget, useWidgetContext } from '@openg2p/registry-widgets';
import {
    ETHIOPIC_MONTHS,
    ethiopicMonthLength,
    formatYmd,
    toEthiopic,
    toGregorian,
    todayGregorian,
    type Ymd,
} from './ethiopic';

type Config = Record<string, any>;

const LABELS: Record<string, string> = {
    oan_ec: 'EC',
    oan_gc: 'GC',
    oan_ec_day: 'Day',
    oan_ec_month: 'Month',
    oan_ec_year: 'Year',
    oan_ec_clear: 'Clear',
    oan_ec_out_of_range: 'The date must be between {min} and {max}.',
};

const bound = (value: unknown) => (value === 'today' ? todayGregorian() : typeof value === 'string' ? value : null);

/**
 * A date entered and shown in the Ethiopian calendar, with its Gregorian date
 * beside it; either can be typed. The Gregorian date is the one stored (as
 * upstream's date widget stores it), the Ethiopian date is saved with it.
 *
 * Section metadata:
 *   widget: "oan-ethiopic-date"
 *   widget-data-path: {value: "<register>.birth_date", ethiopic: "<register>.birth_date_ec"}
 *   widget-data-options: as upstream's date widget (minDate, maxDate, actions)
 */
export function EthiopicDateWidget({ config }: { config: Config }) {
    const dispatch = useDispatch();
    const { t } = useWidgetContext();
    const paths = (config['widget-data-path'] ?? {}) as Record<string, string>;
    // The base widget tracks the Gregorian value and the widget's conditions.
    const base = useBaseWidget({ config: { ...config, 'widget-data-path': paths.value } as never });
    const gregorian = typeof base.value === 'string' && base.value ? base.value.slice(0, 10) : '';
    const ethiopic = useMemo(() => toEthiopic(gregorian), [gregorian]);

    const label = useCallback(
        (key: string, params?: Record<string, unknown>) => {
            const fallback = LABELS[key] ?? key;
            const text = t ? t(key, { defaultValue: fallback, ...params }) : fallback;
            const shown = !text || text === key ? fallback : text;
            return params ? shown.replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? '')) : shown;
        },
        [t],
    );

    // The Ethiopian date being typed; written once it is a whole, real date.
    const [draft, setDraft] = useState<[string, string, string]>(['', '', '']);
    const [error, setError] = useState<string | null>(null);
    useEffect(() => {
        setDraft(ethiopic ? [String(ethiopic[2]), String(ethiopic[1]), String(ethiopic[0])] : ['', '', '']);
    }, [ethiopic]);

    const options = config['widget-data-options'] ?? {};
    const min = bound(options.minDate);
    const max = bound(options.maxDate);

    const store = useCallback(
        (nextGregorian: string | null) => {
            if (nextGregorian && ((min && nextGregorian < min) || (max && nextGregorian > max))) {
                setError(label('oan_ec_out_of_range', { min: min ?? '', max: max ?? '' }));
                return;
            }
            setError(null);
            const nextEthiopic = nextGregorian ? toEthiopic(nextGregorian) : null;
            let next: Record<string, unknown> = setValueByPath({}, paths.value, nextGregorian);
            if (paths.ethiopic) next = setValueByPath(next, paths.ethiopic, nextEthiopic ? formatYmd(nextEthiopic) : null);
            dispatch(setValues(next as never));
            base.onBlur?.();
        },
        [base, dispatch, label, max, min, paths.ethiopic, paths.value],
    );

    const typeEthiopic = (index: 0 | 1 | 2, value: string) => {
        const next = [...draft] as [string, string, string];
        next[index] = value;
        setDraft(next);
        const [day, month, year] = next.map(Number);
        if (!day || !month || !year || next[2].length !== 4) return;
        const ymd: Ymd = [year, month, Math.min(day, ethiopicMonthLength(year, month))];
        store(toGregorian(ymd));
    };

    const title = config['widget-label'] ? label(String(config['widget-label'])) : '';
    const shownEthiopic = ethiopic ? `${ethiopic[2]} ${ETHIOPIC_MONTHS[ethiopic[1] - 1]} ${ethiopic[0]}` : '';

    if (config['widget-readonly'] === true) {
        return (
            <div className="mb-[10px] flex flex-col sm:flex-row sm:items-start">
                {title && <div className="text-base owt-field-label font-medium md:min-w-[120px] sm:pr-4">{title}:</div>}
                <div className="text-base owt-text font-medium">
                    {gregorian ? `${shownEthiopic} ${label('oan_ec')} (${gregorian} ${label('oan_gc')})` : '-'}
                </div>
            </div>
        );
    }

    const disabled = !base.isEnabled;
    const errors = [error, ...(base.touched ? base.error : [])].filter(Boolean) as string[];
    const days = draft[1] && draft[2].length === 4 ? ethiopicMonthLength(Number(draft[2]), Number(draft[1])) : 30;

    return (
        <div className="mb-[10px] oan-ecdate">
            <style>{`
                .oan-ecdate-row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
                .oan-ecdate select, .oan-ecdate input {
                    height: 30px; padding: 0 8px; border-radius: 10px; font-size: 14px;
                    border: 1px solid var(--owt-color-border, #d1d5db); background: var(--owt-color-bg, #fff);
                    color: var(--owt-color-text, #111827);
                }
                .oan-ecdate select:disabled, .oan-ecdate input:disabled { opacity: 0.6; }
                .oan-ecdate .year { width: 72px; }
                .oan-ecdate .tag { font-size: 12px; font-weight: 600; color: var(--owt-color-text-muted, #6b7280); }
                .oan-ecdate .error { font-size: 12px; color: var(--owt-widget-error-color, #dc2626); margin-top: 4px; }
            `}</style>
            <div className="flex flex-col sm:flex-row sm:items-start">
                {title && (
                    <label className="text-base font-medium owt-field-label md:min-w-[120px] sm:pr-4 sm:pt-1 mb-1 sm:mb-0">
                        {title}
                        {base.isRequired && <span className="owt-field-required"> *</span>}
                    </label>
                )}
                <div className="flex-1 min-w-0">
                    <div className="oan-ecdate-row">
                        <span className="tag">{label('oan_ec')}</span>
                        <select aria-label={label('oan_ec_day')} disabled={disabled} value={draft[0]}
                                onChange={(e) => typeEthiopic(0, e.target.value)}>
                            <option value="">{label('oan_ec_day')}</option>
                            {Array.from({ length: days }, (_, i) => <option key={i} value={i + 1}>{i + 1}</option>)}
                        </select>
                        <select aria-label={label('oan_ec_month')} disabled={disabled} value={draft[1]}
                                onChange={(e) => typeEthiopic(1, e.target.value)}>
                            <option value="">{label('oan_ec_month')}</option>
                            {ETHIOPIC_MONTHS.map((name, i) => <option key={name} value={i + 1}>{name}</option>)}
                        </select>
                        <input className="year" inputMode="numeric" maxLength={4} placeholder={label('oan_ec_year')}
                               aria-label={label('oan_ec_year')} disabled={disabled} value={draft[2]}
                               onChange={(e) => typeEthiopic(2, e.target.value.replace(/\D/g, ''))} />
                        <span className="tag">{label('oan_gc')}</span>
                        <input type="date" disabled={disabled} value={gregorian} min={min ?? undefined} max={max ?? undefined}
                               onChange={(e) => store(e.target.value || null)} />
                        {gregorian && !disabled && (
                            <button type="button" className="tag" onClick={() => store(null)}>{label('oan_ec_clear')}</button>
                        )}
                    </div>
                    {errors.length > 0 && <p className="error" role="alert">{errors[0]}</p>}
                </div>
            </div>
        </div>
    );
}
