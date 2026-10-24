# OAN extension

The OpenAgriNet layer on the OpenG2P Farmer Registry. It changes nothing
upstream: the package re-exports the farmer extension and adds its own
registers, services and metadata in new files. It is selected at runtime with
`REGISTRY_EXTENSION_MODULE=openg2p_registry_oan_extension`, as the registry
platform's Extensions Contract describes for coexisting extensions.

| Path | Holds |
|---|---|
| `register_domain/fields.py` | the OAN columns on the farmer registers, declared once |
| `register_domain/models/`, `schemas/` | append those columns to the farmer models and schemas |
| `register_domain/services/` | the farmer domain services, each extended with the section widgets' value rules (`widget_rules.py`) |
| `app.py` | the farmer initializer, plus migration of OAN registers |
| `meta_data/` | the `oan_` metadata layer, applied after the farmer's (`/seed/meta_data/zz-oan/`) |
| `seed/` | the db-seed entrypoint: sample people come from Master Data (the country pack's `samples/`) instead of the Kamuntu demo files; `OAN_SAMPLES_FROM_MASTER_DATA=false` keeps the farmer seed's own |
| `tests/` | `uv run --no-project --with pytest pytest oan-extension/tests` |

Images are built FROM the published farmer images (`docker/oan/`). The staff
UI image is upstream's staff UI build, from the commit of the published image,
with `ui/staff-ui/overrides/` copied on top (`docker/oan/staff-ui.Dockerfile`).

## Staff UI widgets

`ui/staff-ui/overrides/src/oan/widgets/` holds OAN's widgets, registered from
the one overridden upstream file, `src/shared/widgets/RegistryWidgetProvider.tsx`
(a single added import).

The farmer photo (`FarmerPhotoWidget.tsx`) takes a photo with the device camera
or from a file, previews it, and scales it down before upload. The widget
package uploads a section's photo into `record_image_document_id` only for
widgets of type `header-section`, so the photo section declares that type with
`"widget-variant": "oan-farmer-photo"`, and the OAN registration renders the
OAN widget for that variant and upstream's header for everything else.

## Metadata layer

Each file runs after the whole farmer seed, in name order:

| File | Does |
|---|---|
| `10_sections.sql` | derives each OAN section from the upstream one plus the OAN widgets, so upstream changes carry over on the next seed; adds the intake photo section |
| `20_layout.sql` | attaches the OAN sections where the upstream ones were, then detaches those by explicit id |
| `30_translations.sql` | adds labels to each language's domain translations; upstream wording wins on a shared key |
| `40_deduplication.sql` | the farmer duplicate check, with the father's name (middle name) added |
| `90_checks.sql` | raises an error in the seed log if anything above did not apply |

Upstream section rows are never changed. Code lists (body condition,
production type, commodities, primary language) come from the country pack in Master Data.

## Validation on the server

Core applies coded-value checks itself (`REGISTRY_CORE_VALIDATE_ATTRIBUTE_VALUES`).
The widgets' `widget-data-validation` rules (pattern, length, range) are applied
by every register's domain service after the farmer checks, read from the same
section metadata (cached for five minutes), so a rule is written once.
Whether a field is required stays with the UI and with the domain code.
