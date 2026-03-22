"""应用配置"""

from decimal import Decimal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库
    database_url: str = "sqlite+aiosqlite:///./yovus_finance.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # 安全
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24小时

    # 应用
    app_env: str = "development"
    app_debug: bool = True

    # 税务配置 - 一般纳税人
    default_vat_rate: Decimal = Decimal("0.13")  # 增值税基本税率13%
    vat_rate_9: Decimal = Decimal("0.09")  # 9%税率
    vat_rate_6: Decimal = Decimal("0.06")  # 6%税率（服务类）
    corporate_income_tax_rate: Decimal = Decimal("0.25")  # 企业所得税25%
    urban_maintenance_tax_rate: Decimal = Decimal("0.07")  # 城市维护建设税7%
    education_surcharge_rate: Decimal = Decimal("0.03")  # 教育费附加3%
    local_education_surcharge_rate: Decimal = Decimal("0.02")  # 地方教育附加2%

    # 电商平台佣金费率 (默认值，可按类目覆盖)
    tmall_commission_rate: Decimal = Decimal("0.05")  # 天猫佣金5%
    jd_commission_rate: Decimal = Decimal("0.08")  # 京东佣金8%

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
