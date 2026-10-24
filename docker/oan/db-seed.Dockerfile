# The published farmer db-seed image with the OAN metadata layer. Its files sit
# under zz-oan/, so the seed applies them after the farmer's whole tree.
ARG FARMER_VERSION=1.2.1-rc.192
FROM openg2p/openg2p-farmer-registry-db-seed:${FARMER_VERSION}

COPY oan-extension/src/openg2p_registry_oan_extension/meta_data/ /seed/meta_data/zz-oan/

# Sample people from Master Data (the country pack's samples); see oan-extension/seed/.
COPY --chmod=755 oan-extension/seed/ /oan/
ENTRYPOINT ["/oan/entrypoint.sh"]
