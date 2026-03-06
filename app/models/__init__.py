# 全モデルをここで import することで SQLAlchemy の relationship が正しく解決される
from app.models.base import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.music_festival import MusicFestival  # noqa: F401
from app.models.source_site import SourceSite  # noqa: F401
from app.models.collection_log import CollectionLog  # noqa: F401
from app.models.notification_setting import NotificationSetting  # noqa: F401
from app.models.notification_log import NotificationLog  # noqa: F401
