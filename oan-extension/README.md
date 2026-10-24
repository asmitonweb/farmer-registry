# OAN extension

The OpenAgriNet layer on the OpenG2P Farmer Registry. It changes nothing
upstream: the package re-exports the farmer extension and adds its own
registers, services and metadata in new files. It is selected at runtime with
`REGISTRY_EXTENSION_MODULE=openg2p_registry_oan_extension`, as the registry
platform's Extensions Contract describes for coexisting extensions.

| Path | Holds |
|---|---|
| `register_domain/fields.py` | the OAN columns on the farmer registers, declared once |
| `register_domain/models/`, `schemas/` | append those columns to the farmer models and schemas; OAN's own register, FarmerPhone (`registers.py`) |
| `register_domain/derived.py` | the values derived rather than typed (land totals in hectares, location names, Ethiopian calendar dates, phone numbers, the farmer's search text), with no framework imports |
| `register_domain/ethiopian_calendar.py` | Gregorian and Ethiopian calendar conversion |
| `register_domain/services/` | the farmer domain services, each extended with the derived values (`derivations.py`) and the section widgets' value rules (`widget_rules.py`); the FarmerPhone service |
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

## Farmer attributes

Following OpenG2P's review of the previous registry:

- Identifiers are attributes of the farmer, not a table or a section: the Fayda
  FIN is upstream's `foundational_id`, beside `rid`, `odk_farmer_id` and
  `pula_id`, all asked in personal identification. A household member's ODK
  Member ID is `odk_member_id`.
- Location stays on the farmer tab.
- The farmer's `search_text` holds only what a user types to find a farmer: its
  ids and its names in each language (`derived.FARMER_SEARCH_FIELDS`).
- Dates are stored Gregorian. The birth date is entered with the Ethiopian
  calendar widget, and each date has an Ethiopian calendar twin (`*_ec`).
- The household link on the intake form stays upstream's until OpenG2P's
  design for it is agreed. The household-head question is on the register only.

Derived and never typed: the land totals and land ownership, a land's area in
hectares and whether its certificate is on file, the region to kebele names,
the `*_ec` dates, the farmer's phone list (from the phone rows), the household
head's name, and the enumerator details. The enumerator name and date come from
the submission. The position comes from the enumerator's device, if the browser
allows it. They are shown on the read-only Enumerator tab.

## Staff UI widget types

Besides the farmer photo, `ui/staff-ui/overrides/src/oan/widgets/` registers:

| Widget | Does |
|---|---|
| `oan-ethiopic-date` | a date entered in the Ethiopian calendar or the Gregorian one; saves both (`widget-data-path: {value, ethiopic}`) |
| `oan-geo-point` | an OpenStreetMap map to pin a place, as ODK's map question does; saves latitude, longitude and altitude (device altitude, or the ground elevation at the pin from `elevationUrl`) |
| `oan-enumerator-position` | renders nothing; records the device's position once, if allowed |

The map needs its tile and elevation hosts in the staff UI's CSP (`CSP_SRC_IMG`,
`CSP_SRC_CONNECT`). The elevation lookup sends the pin's coordinates to that
service; leave `elevationUrl` out of the section to keep them in.

## Metadata layer

Each file runs after the whole farmer seed, in name order:

| File | Does |
|---|---|
| `05_registers.sql` | the FarmerPhone register, and the location names in the farmer list |
| `10_sections.sql` | derives each OAN section from the upstream one plus the OAN widgets, so upstream changes carry over on the next seed; adds the intake photo section |
| `15_sections.sql` | sections with no upstream counterpart: phones, land totals, enumerator, and the location with the map |
| `20_layout.sql` | attaches the OAN sections where the upstream ones were, then detaches those by explicit id |
| `30_translations.sql` | adds labels to each language's domain translations; upstream wording wins on a shared key |
| `40_deduplication.sql` | the farmer duplicate check, with the father's name (middle name) added |
| `90_checks.sql` | raises an error in the seed log if anything above did not apply |

Upstream section rows are never changed. Code lists (body condition,
production type, commodities, languages) come from the country pack in Master Data;
short fixed lists (phone type) are static options in the section.

## Validation on the server

Core applies coded-value checks itself (`REGISTRY_CORE_VALIDATE_ATTRIBUTE_VALUES`).
The widgets' `widget-data-validation` rules (pattern, length, range) are applied
by every register's domain service after the farmer checks, read from the same
section metadata (cached for five minutes), so a rule is written once.
Whether a field is required stays with the UI and with the domain code.
