"""电商平台数据解析"""

from app.services.platform.base import BasePlatformParser
from app.services.platform.jd import JDParser
from app.services.platform.tmall import TmallParser

__all__ = ["BasePlatformParser", "TmallParser", "JDParser"]
