"""Domain mapping only; file parsing/queueing remain in registry-platform."""
from openg2p_registry_core.interfaces import G2PPayloadEnricherInterface
from .farmer_file_mapping import row_to_submission


class G2PFarmerFileImportEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data, session):
        return row_to_submission(data)
