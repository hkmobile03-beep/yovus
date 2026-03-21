"""中国小企业会计准则 - 会计科目表初始化"""

# 电商企业常用会计科目（小企业会计准则）
DEFAULT_CHART_OF_ACCOUNTS = [
    # 资产类
    {"code": "1001", "name": "库存现金", "type": "asset", "direction": "debit"},
    {"code": "1002", "name": "银行存款", "type": "asset", "direction": "debit"},
    {"code": "1012", "name": "其他货币资金", "type": "asset", "direction": "debit"},
    {"code": "101201", "name": "其他货币资金-支付宝", "type": "asset", "direction": "debit"},
    {"code": "101202", "name": "其他货币资金-微信", "type": "asset", "direction": "debit"},
    {"code": "1122", "name": "应收账款", "type": "asset", "direction": "debit"},
    {"code": "112201", "name": "应收账款-天猫", "type": "asset", "direction": "debit"},
    {"code": "112202", "name": "应收账款-京东", "type": "asset", "direction": "debit"},
    {"code": "1221", "name": "其他应收款", "type": "asset", "direction": "debit"},
    {"code": "1405", "name": "库存商品", "type": "asset", "direction": "debit"},
    {"code": "1601", "name": "固定资产", "type": "asset", "direction": "debit"},

    # 负债类
    {"code": "2202", "name": "应付账款", "type": "liability", "direction": "credit"},
    {"code": "2211", "name": "应付职工薪酬", "type": "liability", "direction": "credit"},
    {"code": "2221", "name": "应交税费", "type": "liability", "direction": "credit"},
    {"code": "222101", "name": "应交税费-应交增值税(销项税额)", "type": "liability", "direction": "credit"},
    {"code": "222102", "name": "应交税费-应交增值税(进项税额)", "type": "liability", "direction": "debit"},
    {"code": "222103", "name": "应交税费-未交增值税", "type": "liability", "direction": "credit"},
    {"code": "222110", "name": "应交税费-城市维护建设税", "type": "liability", "direction": "credit"},
    {"code": "222111", "name": "应交税费-教育费附加", "type": "liability", "direction": "credit"},
    {"code": "222112", "name": "应交税费-地方教育附加", "type": "liability", "direction": "credit"},
    {"code": "222120", "name": "应交税费-企业所得税", "type": "liability", "direction": "credit"},
    {"code": "2241", "name": "其他应付款", "type": "liability", "direction": "credit"},
    {"code": "224101", "name": "其他应付款-平台保证金", "type": "liability", "direction": "credit"},

    # 所有者权益类
    {"code": "4001", "name": "实收资本", "type": "equity", "direction": "credit"},
    {"code": "4103", "name": "本年利润", "type": "equity", "direction": "credit"},
    {"code": "4104", "name": "利润分配", "type": "equity", "direction": "credit"},

    # 收入类
    {"code": "6001", "name": "主营业务收入", "type": "revenue", "direction": "credit"},
    {"code": "600101", "name": "主营业务收入-天猫", "type": "revenue", "direction": "credit"},
    {"code": "600102", "name": "主营业务收入-京东", "type": "revenue", "direction": "credit"},
    {"code": "6051", "name": "其他业务收入", "type": "revenue", "direction": "credit"},

    # 成本类
    {"code": "6401", "name": "主营业务成本", "type": "cost", "direction": "debit"},
    {"code": "6402", "name": "其他业务成本", "type": "cost", "direction": "debit"},

    # 费用类
    {"code": "6601", "name": "销售费用", "type": "expense", "direction": "debit"},
    {"code": "660101", "name": "销售费用-平台佣金", "type": "expense", "direction": "debit"},
    {"code": "660102", "name": "销售费用-推广费", "type": "expense", "direction": "debit"},
    {"code": "660103", "name": "销售费用-物流费", "type": "expense", "direction": "debit"},
    {"code": "660104", "name": "销售费用-包装费", "type": "expense", "direction": "debit"},
    {"code": "660105", "name": "销售费用-直通车/钻展", "type": "expense", "direction": "debit"},
    {"code": "660106", "name": "销售费用-京东快车", "type": "expense", "direction": "debit"},
    {"code": "6602", "name": "管理费用", "type": "expense", "direction": "debit"},
    {"code": "660201", "name": "管理费用-办公费", "type": "expense", "direction": "debit"},
    {"code": "660202", "name": "管理费用-折旧费", "type": "expense", "direction": "debit"},
    {"code": "660203", "name": "管理费用-平台技术服务费", "type": "expense", "direction": "debit"},
    {"code": "6603", "name": "财务费用", "type": "expense", "direction": "debit"},
    {"code": "660301", "name": "财务费用-手续费", "type": "expense", "direction": "debit"},
]
