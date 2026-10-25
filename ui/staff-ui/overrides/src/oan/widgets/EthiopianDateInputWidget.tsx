'use client';

import { useEffect } from 'react';
import { useBaseWidget, useWidgetContext, type BaseWidgetConfig } from '@openg2p/registry-widgets';
import EthiopianDateInput from '@/features/activity/components/EthiopianDateInput';

export const ETHIOPIAN_DATE_VARIANT = 'ethiopian';
export const ETHIOPIAN_DATE_CELL = 'oan-ethiopian-date-input';

type Props = { config: BaseWidgetConfig } & Partial<ReturnType<typeof useBaseWidget>>;

/** Upstream calendar input with the registry's standard field/store contract. */
export function EthiopianDateInputWidget(props: Props) {
    const { config } = props;
    const base = useBaseWidget({ config });
    // WidgetRenderer's callback carries table-row edits back to TableWidget.
    const { value, error, touched, isEnabled, isRequired, isVisible, onChange, onBlur } = { ...base, ...props };
    const { t } = useWidgetContext();
    const label = String(config['widget-label'] ?? '');
    const shownLabel = t ? t(label, { defaultValue: label }) : label;
    const disabled = !isEnabled || !!config['widget-readonly'];
    const showError = touched && error.length > 0;
    const id = String(config['widget-id']);

    useEffect(() => {
        if (config['widget-data-default'] === 'today' && value === undefined) {
            onChange(new Date().toISOString().slice(0, 10));
        }
    }, [config, onChange, value]);

    if (!isVisible) return null;

    return (
        <div className="mb-[10px]">
            <div className="flex flex-col sm:flex-row sm:items-start">
                <label
                    htmlFor={`${id}-day`}
                    className="flex items-baseline min-w-0 max-w-full owt-field-label text-base font-medium md:min-w-[120px] sm:pr-4 sm:pt-1 mb-1 sm:mb-0"
                    style={{ fontFamily: 'Roboto, sans-serif' }}
                    title={shownLabel}
                >
                    <span className="min-w-0 truncate">{shownLabel}</span>
                    {isRequired && <span className="ml-1 shrink-0 owt-field-required" aria-hidden="true">*</span>}
                </label>
                <fieldset
                    disabled={disabled}
                    className="flex-1 min-w-0 m-0 border-0 p-0"
                    aria-label={shownLabel}
                    aria-invalid={showError || (isRequired && !value)}
                    aria-describedby={showError ? `${id}-error` : undefined}
                    onBlur={(event) => {
                        if (!event.currentTarget.contains(event.relatedTarget)) onBlur();
                    }}
                >
                    <EthiopianDateInput
                        id={id}
                        value={typeof value === 'string' && value ? value.slice(0, 10) : undefined}
                        onChange={(next) => onChange(next ?? null)}
                        disabled={disabled}
                    />
                    {showError && <p id={`${id}-error`} className="owt-field-error text-sm mt-1">{error[0]}</p>}
                </fieldset>
            </div>
        </div>
    );
}
