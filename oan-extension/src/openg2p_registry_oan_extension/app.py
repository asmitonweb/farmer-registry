import asyncio
import logging

from .config import Settings

_config = Settings.get_config()

from openg2p_fastapi_common.context import dbengine
from openg2p_registry_farmer_extension.app import Initializer as FarmerInitializer

from .controllers import OANIntakeAuthenticationController

# The farmer initializer migrates its mapped classes directly, so the OAN
# columns must be appended to them before any migration runs.
from .register_domain import models as _oan_models
from .register_domain.services import (
    OANIntakeIdentityService,
    install_oan_intake_service,
)

_logger = logging.getLogger(_config.logging_default_logger_name)

# OAN registers, in parent-before-child order: (register, history, intake form).
OAN_REGISTERS: list[tuple] = [
    (_oan_models.G2PRegisterFarmerPhone, _oan_models.G2PRegisterHistoryFarmerPhone, _oan_models.G2PIntakeFormFarmerPhone),
]


class Initializer(FarmerInitializer):
    """The farmer extension's initializer, then OAN's registers."""

    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        OANIntakeIdentityService()
        install_oan_intake_service()

    async def fastapi_app_startup(self, app):
        # The staff/partner API creates its final FastAPI app after the
        # extension initializer. Register the route during lifespan startup so
        # it is attached to that final app, not the temporary initializer app.
        OANIntakeAuthenticationController().post_init()

    def migrate_database(self, args):
        super().migrate_database(args)
        # The farmer migration ran in its own event loop, which is closed now, and
        # the pooled connections belong to it. Drop them without closing them.
        dbengine.get().sync_engine.dispose(close=False)

        async def migrate():
            _logger.info("Migrating OAN registers")
            for classes in OAN_REGISTERS:
                for cls in classes:
                    await cls.create_migrate()

            await _oan_models.OANIntakeIdentityContext.create_migrate()
            await _oan_models.OANIntakeIdentityAttempt.create_migrate()

        asyncio.run(migrate())
