# OAN extension

The OpenAgriNet layer on the OpenG2P Farmer Registry. It changes nothing
upstream: the package re-exports the farmer extension and adds its own
registers, services and metadata in new files. It is selected at runtime with
`REGISTRY_EXTENSION_MODULE=openg2p_registry_oan_extension`, as the registry
platform's Extensions Contract describes for coexisting extensions.

| Path | Holds |
|---|---|
| `register_domain/` | OAN registers and overlay services. Each `__init__` re-exports the farmer one first |
| `app.py` | the farmer initializer, plus migration of OAN registers |
| `meta_data/` | the `oan_` metadata layer, applied after the farmer's (`/seed/meta_data/zz-oan/`) |

Images are built FROM the published farmer images (`docker/oan/`).
