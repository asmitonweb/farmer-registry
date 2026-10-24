import asyncio
import logging

from .config import Settings

_config = Settings.get_config()

from openg2p_registry_farmer_extension.app import Initializer as FarmerInitializer

# The farmer initializer migrates its mapped classes directly, so the OAN
# columns must be appended to them before any migration runs.
from .register_domain import models as _oan_models  # noqa: F401

_logger = logging.getLogger(_config.logging_default_logger_name)

# OAN registers, in parent-before-child order: (register, history, intake form).
OAN_REGISTERS: list[tuple] = []


class Initializer(FarmerInitializer):
    """The farmer extension's initializer, then OAN's registers."""

    def migrate_database(self, args):
        super().migrate_database(args)

        async def migrate():
            _logger.info("Migrating OAN registers")
            for classes in OAN_REGISTERS:
                for cls in classes:
                    await cls.create_migrate()

        asyncio.run(migrate())
