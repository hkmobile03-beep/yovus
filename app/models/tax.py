"""税务模型 - 增值税、企业所得税、附加税"""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaxType(str, enum.Enum):
    """税种"""
    VAT = "vat"                                 # 增值税
    CORPORATE_INCOME = "corporate_income"       # 企业所得税
    URBAN_MAINTENANCE = "urban_maintenance"     # 城市维护建设税
    EDUCATION_SURCHARGE = "education_surcharge" # 教育费附加
    LOCAL_EDUCATION = "local_education"         # 地方教育附加
    STAMP_DUTY = "stamp_duty"                   # 印花税


class InvoiceType(str, enum.Enum):
    """发票类型"""
    SPECIAL = "special"         # 增值税专用发票（可抵扣）
    GENERAL = "general"         # 增值税普通发票
    ELECTRONIC = "electronic"   # 电子发票


class InvoiceDirection(str, enum.Enum):
    """发票方向"""
    OUTPUT = "output"   # 销项（开出）
    INPUT = "input"     # 进项（收到）


class VATInvoice(Base):
    """增值税发票"""
    __tablename__ = "vat_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_no: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, comment="发票号码"
    )
    invoice_code: Mapped[str | None] = mapped_column(String(20), comment="发票代码")
    invoice_type: Mapped[InvoiceType] = mapped_column(
        Enum(InvoiceType), comment="发票类型"
    )
    direction: Mapped[InvoiceDirection] = mapped_column(
        Enum(InvoiceDirection), comment="进/销项"
    )
    invoice_date: Mapped[date] = mapped_column(Date, comment="开票日期")
    period: Mapped[str] = mapped_column(String(7), comment="所属期间(YYYY-MM)")

    # 交易方信息
    counterparty_name: Mapped[str] = mapped_column(String(200), comment="对方名称")
    counterparty_tax_no: Mapped[str | None] = mapped_column(
        String(30), comment="对方税号"
    )

    # 金额
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), comment="不含税金额"
    )
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), comment="税率")
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), comment="税额"
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), comment="价税合计"
    )

    # 认证/抵扣（进项票）
    is_certified: Mapped[bool] = mapped_column(default=False, comment="是否已认证")
    is_deducted: Mapped[bool] = mapped_column(default=False, comment="是否已抵扣")
    certified_date: Mapped[date | None] = mapped_column(Date, comment="认证日期")

    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class TaxDeclaration(Base):
    """纳税申报表"""
    __tablename__ = "tax_declarations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tax_type: Mapped[TaxType] = mapped_column(Enum(TaxType), comment="税种")
    period: Mapped[str] = mapped_column(String(7), index=True, comment="申报期间(YYYY-MM)")
    declaration_date: Mapped[date | None] = mapped_column(Date, comment="申报日期")

    # 申报状态
    status: Mapped[str] = mapped_column(
        String(20), default="draft", comment="状态(draft/calculated/declared/paid)"
    )

    # 核心金额
    taxable_income: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="应税收入/销售额"
    )
    tax_payable: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="应纳税额"
    )
    tax_deductible: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="可抵扣/减免税额"
    )
    tax_due: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="实际应缴税额"
    )

    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    items: Mapped[list["TaxDeclarationItem"]] = relationship(
        back_populates="declaration"
    )


class TaxDeclarationItem(Base):
    """申报表明细（增值税申报表各栏次）"""
    __tablename__ = "tax_declaration_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    declaration_id: Mapped[int] = mapped_column(
        ForeignKey("tax_declarations.id"), comment="申报表ID"
    )
    item_name: Mapped[str] = mapped_column(String(200), comment="栏次/项目名称")
    item_code: Mapped[str | None] = mapped_column(String(20), comment="栏次编号")

    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="金额"
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), comment="税额"
    )

    remark: Mapped[str | None] = mapped_column(Text, comment="备注")

    declaration: Mapped["TaxDeclaration"] = relationship(back_populates="items")
