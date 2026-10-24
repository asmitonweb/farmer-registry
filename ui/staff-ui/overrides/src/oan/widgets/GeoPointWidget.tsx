'use client';

import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
    getValueByPath,
    setValueByPath,
    setValues,
    useBaseWidget,
    useWidgetContext,
    type WidgetRootState,
} from '@openg2p/registry-widgets';

type Config = Record<string, any>;

const TILE = 256;
const DEFAULTS = {
    tileUrl: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '© OpenStreetMap contributors',
    center: [9.145, 40.4897] as [number, number],
    zoom: 6,
    pinZoom: 15,
    minZoom: 2,
    maxZoom: 19,
    height: 320,
};

const LABELS: Record<string, string> = {
    oan_map_use_my_location: 'Use my location',
    oan_map_clear: 'Clear pin',
    oan_map_hint: 'Click the map to pin the farm; drag to move, scroll or use + and - to zoom.',
    oan_map_locating: 'Finding your location...',
    oan_map_no_location: 'Your location is not available.',
    oan_map_latitude: 'Latitude',
    oan_map_longitude: 'Longitude',
    oan_map_altitude: 'Altitude (m)',
};

// Web Mercator, in pixels of a world 256 * 2^zoom wide.
const project = (lat: number, lon: number, zoom: number) => {
    const world = TILE * 2 ** zoom;
    const sin = Math.min(Math.max(Math.sin((lat * Math.PI) / 180), -0.9999), 0.9999);
    return { x: ((lon + 180) / 360) * world, y: (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * world };
};

const unproject = (x: number, y: number, zoom: number) => {
    const world = TILE * 2 ** zoom;
    const lon = (x / world) * 360 - 180;
    const lat = (Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / world))) * 180) / Math.PI;
    return { lat, lon: ((((lon + 180) % 360) + 360) % 360) - 180 };
};

const num = (value: unknown): number | null => {
    if (value === null || value === undefined || value === '') return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
};

const round = (value: number, places: number) => Number(value.toFixed(places));

async function elevationAt(urlTemplate: string, lat: number, lon: number): Promise<number | null> {
    try {
        const url = urlTemplate.replace('{lat}', String(lat)).replace('{lon}', String(lon));
        const response = await fetch(url);
        if (!response.ok) return null;
        const body = await response.json();
        return num(Array.isArray(body?.elevation) ? body.elevation[0] : body?.elevation ?? body?.results?.[0]?.elevation);
    } catch {
        return null;
    }
}

/**
 * Pin a place on an OpenStreetMap map and get its latitude, longitude and
 * altitude, as the ODK form's map question does. Click the map to place the
 * pin, drag to pan, scroll or +/- to zoom, or use the device's position. The
 * altitude is the device's when it reports one, otherwise the ground elevation
 * at the pin from "elevationUrl" (when configured). The three values can also
 * be typed.
 *
 * Section metadata:
 *   widget: "oan-geo-point"
 *   widget-data-path: {latitude, longitude, altitude}
 *   widget-data-format: {tileUrl, attribution, center: [lat, lon], zoom, pinZoom,
 *                        maxZoom, height, elevationUrl ("...{lat}...{lon}...")}
 */
export function GeoPointWidget({ config }: { config: Config }) {
    const dispatch = useDispatch();
    const { t, schemaData } = useWidgetContext();
    const values = useSelector((state: WidgetRootState) => state.widget.values);
    const paths = (config['widget-data-path'] ?? {}) as Record<string, string>;
    const format = { ...DEFAULTS, ...(config['widget-data-format'] ?? {}) };
    const base = useBaseWidget({ config: { ...config, 'widget-data-path': paths.latitude } as never });
    const readonly = config['widget-readonly'] === true || !base.isEnabled;

    const label = useCallback(
        (key: string) => {
            const fallback = LABELS[key] ?? key;
            const text = t ? t(key, { defaultValue: fallback }) : fallback;
            return !text || text === key ? fallback : text;
        },
        [t],
    );

    const read = (path?: string) =>
        path ? num(getValueByPath(values, path) ?? getValueByPath(schemaData ?? {}, path)) : null;
    const lat = read(paths.latitude);
    const lon = read(paths.longitude);
    const alt = read(paths.altitude);
    const pinned = lat !== null && lon !== null;

    const box = useRef<HTMLDivElement>(null);
    const [width, setWidth] = useState(600);
    const [view, setView] = useState(() => ({
        center: pinned ? { lat: lat!, lon: lon! } : { lat: format.center[0], lon: format.center[1] },
        zoom: pinned ? format.pinZoom : format.zoom,
    }));
    const [status, setStatus] = useState<string | null>(null);

    // Centre on a stored pin once it arrives (the record loads after mount).
    const centred = useRef(pinned);
    useEffect(() => {
        if (pinned && !centred.current) {
            centred.current = true;
            setView({ center: { lat: lat!, lon: lon! }, zoom: format.pinZoom });
        }
    }, [pinned, lat, lon, format.pinZoom]);

    useEffect(() => {
        const element = box.current;
        if (!element) return;
        const observer = new ResizeObserver(([entry]) => entry && setWidth(entry.contentRect.width));
        observer.observe(element);
        return () => observer.disconnect();
    }, []);

    const height = Number(format.height);
    const clampZoom = (z: number) => Math.min(Math.max(z, Number(format.minZoom)), Number(format.maxZoom));
    const centre = project(view.center.lat, view.center.lon, view.zoom);
    const origin = { x: centre.x - width / 2, y: centre.y - height / 2 };

    const write = useCallback(
        (next: { latitude?: number | null; longitude?: number | null; altitude?: number | null }) => {
            let patch: Record<string, unknown> = {};
            for (const [key, value] of Object.entries(next)) {
                const path = paths[key];
                if (path) patch = setValueByPath(patch, path, value);
            }
            dispatch(setValues(patch as never));
            base.onBlur?.();
        },
        [base, dispatch, paths],
    );

    const pin = useCallback(
        async (point: { lat: number; lon: number }, altitude: number | null = null) => {
            write({ latitude: round(point.lat, 7), longitude: round(point.lon, 7), ...(altitude !== null ? { altitude: round(altitude, 1) } : {}) });
            if (altitude === null && format.elevationUrl) {
                const elevation = await elevationAt(String(format.elevationUrl), point.lat, point.lon);
                if (elevation !== null) write({ altitude: round(elevation, 1) });
            }
        },
        [format.elevationUrl, write],
    );

    // Drag to pan; a press that does not move places the pin.
    const drag = useRef<{ x: number; y: number; origin: typeof origin; moved: boolean } | null>(null);
    const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
        if ((event.target as HTMLElement).closest('button')) return;
        event.currentTarget.setPointerCapture(event.pointerId);
        drag.current = { x: event.clientX, y: event.clientY, origin, moved: false };
    };
    const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
        const start = drag.current;
        if (!start) return;
        const dx = event.clientX - start.x;
        const dy = event.clientY - start.y;
        if (!start.moved && Math.hypot(dx, dy) < 4) return;
        start.moved = true;
        const c = unproject(start.origin.x - dx + width / 2, start.origin.y - dy + height / 2, view.zoom);
        setView((v) => ({ ...v, center: c }));
    };
    const onPointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
        const start = drag.current;
        drag.current = null;
        if (!start || start.moved || readonly) return;
        const rect = event.currentTarget.getBoundingClientRect();
        void pin(unproject(origin.x + event.clientX - rect.left, origin.y + event.clientY - rect.top, view.zoom));
    };

    // Zoom about the cursor. A native listener, so the page does not scroll.
    const zoomAt = useCallback(
        (delta: number, px?: number, py?: number) => {
            setView((v) => {
                const zoom = clampZoom(v.zoom + delta);
                if (zoom === v.zoom) return v;
                const c = project(v.center.lat, v.center.lon, v.zoom);
                const ox = (px ?? width / 2) - width / 2;
                const oy = (py ?? height / 2) - height / 2;
                const anchor = unproject(c.x + ox, c.y + oy, v.zoom);
                const a = project(anchor.lat, anchor.lon, zoom);
                return { zoom, center: unproject(a.x - ox, a.y - oy, zoom) };
            });
        },
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [width, height, format.minZoom, format.maxZoom],
    );
    useEffect(() => {
        const element = box.current;
        if (!element) return;
        const onWheel = (event: WheelEvent) => {
            event.preventDefault();
            const rect = element.getBoundingClientRect();
            zoomAt(event.deltaY < 0 ? 1 : -1, event.clientX - rect.left, event.clientY - rect.top);
        };
        element.addEventListener('wheel', onWheel, { passive: false });
        return () => element.removeEventListener('wheel', onWheel);
    }, [zoomAt]);

    const tiles = useMemo(() => {
        const n = 2 ** view.zoom;
        const list: { key: string; src: string; left: number; top: number }[] = [];
        for (let ty = Math.floor(origin.y / TILE); ty <= Math.floor((origin.y + height) / TILE); ty++) {
            if (ty < 0 || ty >= n) continue;
            for (let tx = Math.floor(origin.x / TILE); tx <= Math.floor((origin.x + width) / TILE); tx++) {
                const wrapped = ((tx % n) + n) % n;
                list.push({
                    key: `${view.zoom}/${tx}/${ty}`,
                    src: String(format.tileUrl).replace('{z}', String(view.zoom)).replace('{x}', String(wrapped)).replace('{y}', String(ty)),
                    left: tx * TILE - origin.x,
                    top: ty * TILE - origin.y,
                });
            }
        }
        return list;
    }, [format.tileUrl, height, origin.x, origin.y, view.zoom, width]);

    const marker = pinned ? project(lat!, lon!, view.zoom) : null;

    const locateDevice = () => {
        if (!navigator.geolocation) {
            setStatus(label('oan_map_no_location'));
            return;
        }
        setStatus(label('oan_map_locating'));
        navigator.geolocation.getCurrentPosition(
            ({ coords }) => {
                setStatus(null);
                setView({ center: { lat: coords.latitude, lon: coords.longitude }, zoom: Number(format.pinZoom) });
                void pin({ lat: coords.latitude, lon: coords.longitude }, coords.altitude ?? null);
            },
            () => setStatus(label('oan_map_no_location')),
            { enableHighAccuracy: true, timeout: 15000 },
        );
    };

    const typed = (key: 'latitude' | 'longitude' | 'altitude', raw: string) => write({ [key]: raw === '' ? null : num(raw) });
    const title = config['widget-label'] ? label(String(config['widget-label'])) : '';

    return (
        <div className="mb-[10px] oan-geo">
            <style>{`
                .oan-geo-title { font-weight: 500; margin-bottom: 6px; color: var(--owt-color-text, #111827); }
                .oan-geo-map {
                    position: relative; overflow: hidden; border-radius: 10px; touch-action: none; user-select: none;
                    border: 1px solid var(--owt-color-border, #d1d5db); background: #e5e3df; cursor: ${readonly ? 'grab' : 'crosshair'};
                }
                .oan-geo-map img.tile { position: absolute; width: ${TILE}px; height: ${TILE}px; pointer-events: none; }
                .oan-geo-pin { position: absolute; width: 26px; height: 26px; margin: -26px 0 0 -13px; pointer-events: none; }
                .oan-geo-zoom { position: absolute; top: 8px; right: 8px; display: flex; flex-direction: column; gap: 4px; }
                .oan-geo-zoom button, .oan-geo-actions button {
                    min-width: 30px; height: 30px; padding: 0 10px; font-size: 14px; cursor: pointer;
                    border-radius: var(--owt-btn-border-radius, 6px); background: var(--owt-btn-secondary-bg, #fff);
                    color: var(--owt-btn-secondary-color, #374151); border: 1px solid var(--owt-btn-secondary-border, #d1d5db);
                }
                .oan-geo-attr { position: absolute; right: 0; bottom: 0; padding: 1px 6px; font-size: 11px; background: rgba(255,255,255,.8); }
                .oan-geo-actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; }
                .oan-geo-fields { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; }
                .oan-geo-fields label { display: flex; flex-direction: column; font-size: 13px; color: var(--owt-color-text-muted, #6b7280); }
                .oan-geo-fields input {
                    height: 30px; width: 150px; padding: 0 8px; border-radius: 10px; font-size: 14px;
                    border: 1px solid var(--owt-color-border, #d1d5db); color: var(--owt-color-text, #111827);
                }
                .oan-geo-hint { font-size: 12px; color: var(--owt-widget-helptext-color, #6b7280); }
            `}</style>
            {title && <div className="oan-geo-title owt-field-label">{title}</div>}
            <div
                ref={box}
                className="oan-geo-map"
                style={{ height }}
                onPointerDown={onPointerDown}
                onPointerMove={onPointerMove}
                onPointerUp={onPointerUp}
                onPointerCancel={() => (drag.current = null)}
            >
                {tiles.map((tile) => (
                    <img key={tile.key} className="tile" src={tile.src} alt="" draggable={false}
                         style={{ left: tile.left, top: tile.top }} />
                ))}
                {marker && (
                    <svg className="oan-geo-pin" viewBox="0 0 24 24" style={{ left: marker.x - origin.x, top: marker.y - origin.y }}>
                        <path d="M12 0C7 0 3 4 3 9c0 7 9 15 9 15s9-8 9-15c0-5-4-9-9-9z" fill="var(--owt-color-primary, #ed7c22)" stroke="#fff" strokeWidth="1.5" />
                        <circle cx="12" cy="9" r="3.2" fill="#fff" />
                    </svg>
                )}
                <div className="oan-geo-zoom">
                    <button type="button" aria-label="Zoom in" onClick={() => zoomAt(1)}>+</button>
                    <button type="button" aria-label="Zoom out" onClick={() => zoomAt(-1)}>-</button>
                </div>
                <div className="oan-geo-attr">{format.attribution}</div>
            </div>
            {!readonly && (
                <div className="oan-geo-actions">
                    <button type="button" onClick={locateDevice}>{label('oan_map_use_my_location')}</button>
                    {pinned && (
                        <button type="button" onClick={() => write({ latitude: null, longitude: null, altitude: null })}>
                            {label('oan_map_clear')}
                        </button>
                    )}
                    <span className="oan-geo-hint">{status ?? label('oan_map_hint')}</span>
                </div>
            )}
            <div className="oan-geo-fields">
                {(['latitude', 'longitude', 'altitude'] as const).map((key) => (
                    <label key={key}>
                        {label(`oan_map_${key}`)}
                        <input type="number" step="any" disabled={readonly}
                               value={(key === 'latitude' ? lat : key === 'longitude' ? lon : alt) ?? ''}
                               onChange={(e) => typed(key, e.target.value)} />
                    </label>
                ))}
            </div>
        </div>
    );
}
