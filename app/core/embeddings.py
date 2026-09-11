"""Central embedding settings.

Import `EMBEDDING_DIMENSION` from this module only. Do not duplicate the
integer in models, migrations, or services.
"""

from app.core.config import get_settings

EMBEDDING_DIMENSION = get_settings().embedding_dimension
