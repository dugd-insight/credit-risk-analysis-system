# -*- coding: utf-8 -*-
"""
知识库 v3.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
定义所有风险分析触发的监管/准则/金融风控原则。
每条规则包含：
  - id          唯一编号
  - category    大类
  - subcategory 子类
  - name        规则名称
  - trigger_metric     触发指标名
  - trigger_condition  触发函数 (value → bool)
  - regulation  触发的监管依据
  - standard    适用的会计/风控准则
  - benchmark   行业参考区间（用于报告展示）
  - risk_level  风险等级 CRITICAL/HIGH/MEDIUM/LOW
  - suggestion  授信处置建议

v3.0 新增：
  - 制造业存货异动规则
  - 流动比率低于 1.0 高危规则
  - 所得税率异常低规则（制造业无免税资质）
  - 利润含金量优质规则（正向加分）
"""

KNOWLEDGE_BASE = [

    # ═══════════════════════════════════════════════
    # 偿债能力类
    # ═══════════════════════════════════════════════
    {
        'id': 'SOL-001',
        'category': '偿债能力',
        'subcategory': '短期流动性',
        'name': '流动比率低于安全阈值 1.5',
        'trigger_metric': 'current_ratio',
        'trigger_condition': lambda v: v < 1.5,
        'regulation': '《商业银行贷款风险分类办法》（银保监规〔2023〕2号）第十二条',
        'standard': '企业会计准则第37号-金融工具列报；银行信贷通用要求流动比率≥1.5',
        'benchmark': '优良≥2.0 | 正常1.5-2.0 | 偏低1.0-1.5 | 高危<1.0',
        'risk_level': 'HIGH',
        'suggestion': '流动比率低于1.5，短期偿债压力较大，建议要求追加抵押品或压缩授信期限至12个月以内',
    },
    {
        'id': 'SOL-001B',
        'category': '偿债能力',
        'subcategory': '短期流动性',
        'name': '流动比率低于高危阈值 1.0（极度紧张）',
        'trigger_metric': 'current_ratio',
        'trigger_condition': lambda v: v < 1.0,
        'regulation': '《商业银行法》第三十九条流动性比例规定；《银行业监督管理法》第二十一条',
        'standard': 'Basel III 流动性覆盖率(LCR)≥100%；国内银行授信实践要求',
        'benchmark': '低于1.0意味着流动资产无法完全覆盖流动负债，存在立即偿债风险',
        'risk_level': 'HIGH',
        'suggestion': '流动比率低于1.0，流动资产不足以覆盖流动负债，须审核到期债务还款来源，建议附加流动资金监管账户',
    },
    {
        'id': 'SOL-002',
        'category': '偿债能力',
        'subcategory': '短期流动性',
        'name': '速动比率低于 0.8（存货依赖度高）',
        'trigger_metric': 'quick_ratio',
        'trigger_condition': lambda v: v < 0.8,
        'regulation': 'Basel III 净稳定资金比例(NSFR)≥100%要求',
        'standard': '《企业财务通则》第四章资产管理；速动比率标准参考区间：≥1.0为合格',
        'benchmark': '优良≥1.5 | 正常1.0-1.5 | 偏低0.8-1.0 | 高危<0.8',
        'risk_level': 'HIGH',
        'suggestion': '速动比率低于0.8，剔除存货后流动资产严重不足，需核查存货变现能力，存货不得重复质押',
    },
    {
        'id': 'SOL-003',
        'category': '偿债能力',
        'subcategory': '长期偿债',
        'name': '资产负债率超过 60% 制造业警戒线',
        'trigger_metric': 'debt_ratio',
        'trigger_condition': lambda v: v > 0.60,
        'regulation': '国家统计局《规模以上工业企业财务指标》制造业参考值；《商业银行法》第三十九条',
        'standard': '制造业资产负债率合理区间：50-60%；超60%进入关注区间',
        'benchmark': '优良<50% | 正常50-60% | 警戒60-70% | 高危>70%',
        'risk_level': 'MEDIUM',
        'suggestion': '资产负债率超过60%，建议要求提供固定资产抵押或第三方担保，限制新增负债',
    },
    {
        'id': 'SOL-003B',
        'category': '偿债能力',
        'subcategory': '长期偿债',
        'name': '资产负债率超过 70% 高危线',
        'trigger_metric': 'debt_ratio',
        'trigger_condition': lambda v: v > 0.70,
        'regulation': '《商业银行信贷资产风险分类办法》第六条；银保监〔2023〕2号',
        'standard': 'CBIRC 银行业监管：资产负债率持续超70%列为关注类',
        'benchmark': '超过70%意味着债权人承担绝大部分资产风险，企业净资产缓冲不足',
        'risk_level': 'HIGH',
        'suggestion': '资产负债率超过70%，属于高风险区间，建议要求强担保（足值抵押），并限制授信额度不超过净资产50%',
    },
    {
        'id': 'SOL-004',
        'category': '偿债能力',
        'subcategory': '利息偿付',
        'name': '利息保障倍数不足 2 倍',
        'trigger_metric': 'interest_coverage',
        'trigger_condition': lambda v: v < 2.0,
        'regulation': '《贷款风险分类指引》关注类贷款判定标准',
        'standard': 'IFRS 9 金融工具减值测试；利息保障倍数<2认为偿息能力不足',
        'benchmark': '优良≥5 | 正常3-5 | 偏低2-3 | 高危<2',
        'risk_level': 'HIGH',
        'suggestion': '息税前利润不足以覆盖利息2倍，存在违约风险，建议列为关注类，加强贷后监控',
    },

    # ═══════════════════════════════════════════════
    # 盈利能力类
    # ═══════════════════════════════════════════════
    {
        'id': 'PROF-001',
        'category': '盈利能力',
        'subcategory': '净利润质量',
        'name': '净利率低于 2%（盈利脆弱型）',
        'trigger_metric': 'net_profit_margin',
        'trigger_condition': lambda v: v < 0.02,
        'regulation': '《商业银行信贷资产风险分类办法》第六条',
        'standard': '企业会计准则第30号-财务报表列报；制造业净利率安全底线2%',
        'benchmark': '优良≥5% | 正常2-5% | 偏低1-2% | 高危<1%',
        'risk_level': 'MEDIUM',
        'suggestion': '净利率低于2%，安全边际极低，原材料涨价或需求下滑即可导致亏损，建议缩短贷款期限',
    },
    {
        'id': 'PROF-002',
        'category': '盈利能力',
        'subcategory': '资产回报',
        'name': 'ROE 低于 5%（资本利用效率低）',
        'trigger_metric': 'roe',
        'trigger_condition': lambda v: v < 0.05,
        'regulation': '《商业银行资本管理办法》附件12：信用风险权重法；国资委考核ROE≥6%要求',
        'standard': 'Basel II/III 经济资本配置原则；A股制造业ROE中位数约8-12%',
        'benchmark': '优良≥15% | 正常8-15% | 偏低5-8% | 低效<5%',
        'risk_level': 'MEDIUM',
        'suggestion': 'ROE低于5%，资本利用效率偏低，高杠杆未能带来高回报，需关注资金用途合规性',
    },
    {
        'id': 'PROF-003',
        'category': '盈利能力',
        'subcategory': '毛利润质量',
        'name': '毛利率低于 10%（成本压力过大）',
        'trigger_metric': 'gross_profit_margin',
        'trigger_condition': lambda v: v < 0.10,
        'regulation': '《商业银行信用风险内部评级体系监管指引》',
        'standard': '制造业毛利率合理区间参考：一般制造业≥15%，钢铁/化工类特殊 ≥8%',
        'benchmark': '优良≥25% | 正常15-25% | 偏低10-15% | 高危<10%',
        'risk_level': 'MEDIUM',
        'suggestion': '毛利率低于10%，产品附加值极低，成本控制空间有限，建议关注原材料和能源价格变动风险',
    },

    # ═══════════════════════════════════════════════
    # 现金流类
    # ═══════════════════════════════════════════════
    {
        'id': 'CF-001',
        'category': '现金流',
        'subcategory': '经营活动',
        'name': '经营活动净现金流为负（主业失血）',
        'trigger_metric': 'operating_cashflow',
        'trigger_condition': lambda v: v < 0,
        'regulation': '《商业银行信用风险内部评级体系监管指引》第三十三条',
        'standard': '企业会计准则第31号-现金流量表；经营CF持续为负是最重要的风险信号',
        'benchmark': '经营CF>0 且>净利润为优；CF<0 表示主业无法自我造血',
        'risk_level': 'HIGH',
        'suggestion': '主业造血能力不足，企业依赖融资维持运营，建议要求补充抵押品或拒绝续贷',
    },
    {
        'id': 'CF-002',
        'category': '现金流',
        'subcategory': '利润含金量',
        'name': '利润现金含金量不足 60%',
        'trigger_metric': 'cash_profit_ratio',
        'trigger_condition': lambda v: v < 0.6,
        'regulation': '《企业内部控制应用指引》第10号',
        'standard': '企业会计准则解释第8号；含金量<60%说明利润中应收账款虚增成分大',
        'benchmark': '优良>200% | 正常100-200% | 偏低60-100% | 疑虑<60%',
        'risk_level': 'MEDIUM',
        'suggestion': '每元净利润对应现金流入不足0.6元，关注应收账款质量，防范虚增收入风险',
    },
    {
        'id': 'CF-003',
        'category': '现金流',
        'subcategory': '还款能力',
        'name': '现金比率低于 10%（即期偿债能力弱）',
        'trigger_metric': 'cash_ratio',
        'trigger_condition': lambda v: v < 0.10,
        'regulation': 'Basel III 净稳定资金比例(NSFR)≥100%要求',
        'standard': '《企业财务通则》第十四条；现金比率≥20%为合格',
        'benchmark': '优良≥30% | 正常20-30% | 偏低10-20% | 高危<10%',
        'risk_level': 'HIGH',
        'suggestion': '现金对流动负债覆盖率低于10%，存在即期流动性风险，要求提供近期银行流水核实现金真实性',
    },

    # ═══════════════════════════════════════════════
    # 营运能力类
    # ═══════════════════════════════════════════════
    {
        'id': 'OPS-001',
        'category': '营运能力',
        'subcategory': '存货管理',
        'name': '存货单季增幅超过 50%（异常备货）',
        'trigger_metric': 'inventory_growth',
        'trigger_condition': lambda v: v > 0.50,
        'regulation': '《商业银行押品管理指引》第十七条；单季存货增幅>50%触发银行审查',
        'standard': '企业会计准则第1号-存货减值测试；存货激增需评估跌价风险',
        'benchmark': '存货增幅：正常<30% | 关注30-50% | 审查>50% | 高危>100%',
        'risk_level': 'HIGH',
        'suggestion': '存货单季大幅增长，需要求企业提供：①存货清单及构成；②在手合同证明；③跌价准备计提情况；存货不得重复质押',
    },
    {
        'id': 'OPS-002',
        'category': '营运能力',
        'subcategory': '应收账款',
        'name': '应收账款增速超收入增速 30%（虚收预警）',
        'trigger_metric': 'ar_revenue_growth_gap',
        'trigger_condition': lambda v: v > 0.30,
        'regulation': '《公司法》第一百六十三条关联交易披露；《贷款风险分类指引》',
        'standard': '企业会计准则第22号-ECL模型；应收增速持续超收入增速是虚增收入的典型信号',
        'benchmark': '应收/收入比：稳定<5% | 关注5-10% | 审查>10%且快速增长',
        'risk_level': 'HIGH',
        'suggestion': '应收账款增速超收入增速30%以上，疑似虚增收入，建议核查前五大客户合同及回款记录',
    },

    # ═══════════════════════════════════════════════
    # 税务合规类
    # ═══════════════════════════════════════════════
    {
        'id': 'TAX-001',
        'category': '税务合规',
        'subcategory': '增值税一致性',
        'name': '增值税申报收入与财报收入差异超 15%',
        'trigger_metric': 'vat_revenue_gap',
        'trigger_condition': lambda v: abs(v) > 0.15,
        'regulation': '《税收征收管理法》第三十五条；银行贷前税务核查规范',
        'standard': '《企业所得税法实施条例》第九条；增值税与财报收入正常差异<15%',
        'benchmark': '差异<5%正常 | 5-15%关注 | >15%疑似虚增收入',
        'risk_level': 'HIGH',
        'suggestion': '税务申报与财务报表收入差异超15%，疑似虚增收入，建议要求说明并核查原始发票及合同',
    },
    {
        'id': 'TAX-002',
        'category': '税务合规',
        'subcategory': '所得税有效税率',
        'name': '实际所得税率异常偏低（有效税率<5%）',
        'trigger_metric': 'effective_tax_rate',
        'trigger_condition': lambda v: v < 0.05,
        'regulation': '《企业所得税法》第四条：法定税率25%；高新技术企业15%',
        'standard': '国家税务总局公告2018年第28号；有效税率正常区间15%-25%',
        'benchmark': '法定25%（一般企业）| 优惠15%（高新）| 进一步优惠10%（西部）| 异常<5%',
        'risk_level': 'MEDIUM',
        'suggestion': '实际税率远低于法定税率，需核查是否具备免税资质（高新证书/西部政策备案），防范税收违规风险',
    },

    # ═══════════════════════════════════════════════
    # 财务造假预警类
    # ═══════════════════════════════════════════════
    {
        'id': 'FRAUD-001',
        'category': '财务造假预警',
        'subcategory': 'Beneish模型',
        'name': 'Beneish M-Score 超高危警戒值 -1.78',
        'trigger_metric': 'm_score',
        'trigger_condition': lambda v: v > -1.78,
        'regulation': '《商业银行合规风险管理指引》反欺诈条款；银保监会2022年金融机构尽职调查指引',
        'standard': 'Beneish(1999) M-Score模型：>-1.78造假概率约76%，>-2.22中等风险',
        'benchmark': '<-2.22安全 | -2.22~-1.78中风险 | >-1.78高危造假',
        'risk_level': 'CRITICAL',
        'suggestion': 'M-Score高于-1.78，财务造假概率高，建议立即暂停授信并启动尽职调查，要求提供审计报告',
    },
    {
        'id': 'FRAUD-002',
        'category': '财务造假预警',
        'subcategory': '三表勾稽',
        'name': '前后期财务数据存在重大异常倒挂',
        'trigger_metric': 'cross_period_anomaly',
        'trigger_condition': lambda v: v > 0.2,
        'regulation': '《反洗钱法》第十九条，可疑交易报告规定；FATF 40条建议第20条',
        'standard': '三表勾稽一致性校验：权益增量≠净利润（差异>15%）；期末现金不匹配等',
        'benchmark': '异常度<0.1正常 | 0.1-0.2关注 | >0.2高危',
        'risk_level': 'CRITICAL',
        'suggestion': '跨期数据存在重大异常，建议要求提供经注册会计师审计的报告，并核实会计师意见类型',
    },
    {
        'id': 'FRAUD-003',
        'category': '财务造假预警',
        'subcategory': '收入质量',
        'name': '三表勾稽不一致（现金流-利润背离）',
        'trigger_metric': 'cash_profit_ratio',
        'trigger_condition': lambda v: v < 0.3,
        'regulation': '《公司法》第一百六十三条；证监会《关于上市公司财务报告信息披露》',
        'standard': '企业会计准则第36号-关联方披露；利润含金量持续低于30%是严重预警信号',
        'benchmark': '含金量<30%表明利润与现金流严重背离，极大概率存在虚增利润',
        'risk_level': 'HIGH',
        'suggestion': '利润现金含金量低于30%，利润真实性存疑，建议核查前五大客户应收款，要求提供资金流水',
    },

]


def get_triggered_rules(metric_name: str, metric_value) -> list:
    """根据指标名称和数值，返回触发的知识库规则列表"""
    if metric_value is None:
        return []
    triggered = []
    for rule in KNOWLEDGE_BASE:
        if rule['trigger_metric'] == metric_name:
            try:
                if rule['trigger_condition'](metric_value):
                    triggered.append(rule)
            except Exception:
                pass
    return triggered


def get_rules_by_category(category: str) -> list:
    """获取特定类别的所有规则"""
    return [r for r in KNOWLEDGE_BASE if r['category'] == category]


def get_all_categories() -> list:
    """获取所有类别"""
    seen = []
    for r in KNOWLEDGE_BASE:
        if r['category'] not in seen:
            seen.append(r['category'])
    return seen


# 行业参考标准（用于报告中知识库依据展示）
INDUSTRY_BENCHMARKS = {
    '制造业': {
        '资产负债率': {
            'excellent': '<50%', 'normal': '50-60%', 'warning': '60-70%', 'danger': '>70%',
            'source': '国家统计局规模以上工业企业财务指标均值约55-60%',
        },
        '流动比率': {
            'excellent': '≥2.0', 'normal': '1.5-2.0', 'warning': '1.0-1.5', 'danger': '<1.0',
            'source': '银行信贷普遍要求≥1.5',
        },
        '速动比率': {
            'excellent': '≥1.5', 'normal': '1.0-1.5', 'warning': '0.8-1.0', 'danger': '<0.8',
            'source': '行业通用标准',
        },
        '毛利率': {
            'excellent': '≥25%', 'normal': '15-25%', 'warning': '10-15%', 'danger': '<10%',
            'source': '钢铁/化工类通常8-15%，机械制造20-30%',
        },
        '净利率': {
            'excellent': '≥5%', 'normal': '2-5%', 'warning': '1-2%', 'danger': '<1%',
            'source': 'A股制造业上市公司净利率中位数约3-5%',
        },
        'ROE': {
            'excellent': '≥15%', 'normal': '8-15%', 'warning': '5-8%', 'danger': '<5%',
            'source': 'A股制造业ROE中位数约8-12%，国资委考核央企≥6%',
        },
        '利润含金量': {
            'excellent': '>200%', 'normal': '100-200%', 'warning': '60-100%', 'danger': '<60%',
            'source': '经营现金流/净利润，反映利润真实性',
        },
    },
    '担保/金融服务': {
        '资产负债率': {
            'excellent': '<40%', 'normal': '40-60%', 'warning': '60-75%', 'danger': '>75%',
            'source': '融资性担保公司监管规定，净资本/风险资产≥10%',
        },
    },
}
