'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  getValueByPath,
  setValueByPath,
  setValues,
  useWidgetContext,
  type BaseWidgetConfig,
  type WidgetRootState,
} from '@openg2p/registry-widgets';

type Paths = {
  contextId?: string;
  evidenceReference?: string;
  submissionId?: string;
  first_name?: string;
  middle_name?: string;
  last_name?: string;
  birth_date?: string;
  gender?: string;
  foundational_id?: string;
  first_name_amh?: string;
  middle_name_amh?: string;
  last_name_amh?: string;
};

type AuthConfig = {
  service: string;
  providerId: string;
  providerName?: string;
  registerId: string;
  formId: string;
  startEndpoint: string;
  statusEndpoint: string;
  resetEndpoint: string;
  mockVerifyEndpoint?: string;
  mode?: 'oidc' | 'mock';
  mockPageUrl?: string;
  callbackOrigin: string;
};

type Props = { config: BaseWidgetConfig; schemaData?: Record<string, unknown> };

const unwrap = (value: any) => value?.response_body?.response_payload ?? value?.response_payload ?? value;

export function IntakeIdentityWidget({ config, schemaData }: Props) {
  const { dataSourceRequestHandler, hostContext, t } = useWidgetContext();
  const dispatch = useDispatch();
  const values = useSelector((state: WidgetRootState) => state.widget.values) as Record<string, unknown>;
  const paths = (config['widget-data-path'] ?? {}) as Paths;
  const auth = (config['widget-auth-config'] ?? {}) as AuthConfig;
  const popupRef = useRef<Window | null>(null);
  const [status, setStatus] = useState('MANUAL');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mockMode = auth.mode === 'mock';

  const read = useCallback(
    (path?: string) => {
      if (!path) return undefined;
      return getValueByPath(values, path) ?? getValueByPath(schemaData ?? {}, path);
    },
    [schemaData, values],
  );

  const contextId = read(paths.contextId) as string | undefined;
  const submissionId = read(paths.submissionId) as string | undefined;

  const write = useCallback(
    (path: string | undefined, value: unknown) => {
      if (!path) return;
      dispatch(setValues(setValueByPath({ ...values }, path, value)));
    },
    [dispatch, values],
  );

  const applyMappedValues = useCallback((mappedValues: Record<string, unknown>) => {
    let nextValues = { ...values };
    for (const [field, value] of Object.entries(mappedValues)) {
      const path = paths[field as keyof Paths];
      if (path) nextValues = setValueByPath(nextValues, path, value);
    }
    dispatch(setValues(nextValues));
  }, [dispatch, paths, values]);

  const refreshStatus = useCallback(async () => {
    if (!contextId || !dataSourceRequestHandler) return;
    try {
      const response = await dataSourceRequestHandler(auth.service, auth.statusEndpoint, 'POST', { context_id: contextId });
      const payload = unwrap(response);
      setStatus(String(payload?.status ?? 'MANUAL'));
      if (payload?.mapped_values && typeof payload.mapped_values === 'object') {
        applyMappedValues(payload.mapped_values);
      }
    } catch {
      setStatus('MANUAL');
    }
  }, [applyMappedValues, auth.service, auth.statusEndpoint, contextId, dataSourceRequestHandler]);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (!popupRef.current || event.source !== popupRef.current) return;
      if (event.origin !== auth.callbackOrigin) return;
      if (event.data?.type !== 'oan:intake-auth:complete') return;
      if (!event.data.contextId) return;
      write(paths.contextId, event.data.contextId);
      popupRef.current = null;
      void refreshStatus();
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [auth.callbackOrigin, paths.contextId, refreshStatus, write]);

  const start = async () => {
    if (!dataSourceRequestHandler) return;
    setBusy(true);
    setError(null);
    if (mockMode) {
      const faydaId = String(read(paths.foundational_id) ?? '').trim();
      if (!/^\d{12}$/.test(faydaId)) {
        setError('Paste a 12-digit Fayda ID first.');
        setBusy(false);
        return;
      }
      try {
        const response = await dataSourceRequestHandler(
          auth.service,
          auth.mockVerifyEndpoint ?? 'intake-auth/mock-verify',
          'POST',
          {
          register_id: auth.registerId || hostContext?.form_register_id,
          form_id: auth.formId || hostContext?.form_id,
            provider_id: auth.providerId,
            fayda_id: faydaId,
            submission_id: submissionId ?? null,
          },
        );
        const payload = unwrap(response);
        if (!payload?.context_id || payload.status !== 'VERIFIED') throw new Error('Mock verification failed.');
        write(paths.contextId, payload.context_id);
        applyMappedValues(payload.mapped_values ?? {});
        setStatus('VERIFIED');
      } catch (cause) {
        setStatus('FAILED');
        setError(cause instanceof Error ? cause.message : 'Could not complete mock verification.');
      } finally {
        setBusy(false);
      }
      return;
    }
    const popup = window.open('about:blank', `${config['widget-id']}-intake-auth`, 'popup=yes,width=1024,height=800');
    if (!popup) {
      setError(t?.('idAuth.popupBlocked') ?? 'Popup blocked. Please allow popups and try again.');
      setBusy(false);
      return;
    }
    popupRef.current = popup;
    try {
      const response = await dataSourceRequestHandler(auth.service, auth.startEndpoint, 'POST', {
        register_id: auth.registerId || hostContext?.form_register_id,
        form_id: auth.formId || hostContext?.form_id,
        provider_id: auth.providerId,
        submission_id: submissionId ?? null,
      });
      const payload = unwrap(response);
      if (!payload?.authorization_url || !payload?.context_id) throw new Error('No authorization URL returned.');
      write(paths.contextId, payload.context_id);
      popup.location.href = payload.authorization_url;
    } catch (cause) {
      popup.close();
      popupRef.current = null;
      setError(cause instanceof Error ? cause.message : 'Could not start identity verification.');
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    if (!contextId || !dataSourceRequestHandler) return;
    setBusy(true);
    try {
      await dataSourceRequestHandler(auth.service, auth.resetEndpoint, 'POST', { context_id: contextId });
      setStatus('RESET');
      let nextValues = { ...values };
      if (paths.contextId) nextValues = setValueByPath(nextValues, paths.contextId, null);
      if (paths.evidenceReference) nextValues = setValueByPath(nextValues, paths.evidenceReference, null);
      dispatch(setValues(nextValues));
    } finally {
      setBusy(false);
    }
  };

  const label = useMemo(() => {
    if (status === 'VERIFIED') return 'Verified';
    if (status === 'EXPIRED') return 'Expired';
    if (status === 'RESET') return 'Manual fallback';
    if (status === 'FAILED') return 'Verification failed';
    return 'Not verified';
  }, [status]);

  return (
    <div style={{ display: 'grid', gap: 8, padding: 12, border: '1px solid var(--owt-color-border-light)', borderRadius: 8 }}>
      <strong>{config['widget-label'] ?? 'Identity verification'}</strong>
      <span aria-live="polite">{label}</span>
      {mockMode ? (
        <>
          <label htmlFor={`${config['widget-id']}-fayda-id`}>Paste Fayda ID (FIN)</label>
          <input
            id={`${config['widget-id']}-fayda-id`}
            inputMode="numeric"
            maxLength={12}
            value={String(read(paths.foundational_id) ?? '')}
            onChange={(event) => write(paths.foundational_id, event.target.value.replace(/\D/g, '').slice(0, 12))}
            placeholder="100000000001"
          />
          <a href={auth.mockPageUrl ?? '/mock-fayda.html'} target="_blank" rel="noreferrer">
            Open mock Fayda IDs
          </a>
        </>
      ) : null}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button type="button" onClick={() => void start()} disabled={busy}>
          {busy ? 'Working…' : mockMode ? 'Complete mock verification' : 'Verify identity'}
        </button>
        {contextId ? <button type="button" onClick={() => void reset()} disabled={busy}>Use manual fallback</button> : null}
      </div>
      {error ? <span role="alert" style={{ color: 'var(--owt-color-danger)' }}>{error}</span> : null}
      <small>Test identity verification</small>
    </div>
  );
}
