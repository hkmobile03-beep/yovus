import { useState, useRef, useEffect } from 'react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const QUICK_PROMPTS = [
  { label: '利润分析', prompt: '请分析本月各平台的利润情况，哪个平台表现最好？' },
  { label: '税务风险', prompt: '请检查当前的税务申报数据，是否存在风险点？' },
  { label: '对账差异', prompt: '请分析最近的对账差异，主要原因是什么？' },
  { label: '营收趋势', prompt: '请分析近6个月的营收趋势，并给出预测。' },
  { label: 'SKU 建议', prompt: '请分析各SKU的利润率，给出产品组合优化建议。' },
  { label: '费用优化', prompt: '请分析平台费用结构，有哪些降本空间？' },
]

const DEMO_RESPONSES: Record<string, string> = {
  '请分析本月各平台的利润情况，哪个平台表现最好？': `## 本月各平台利润分析

### 核心发现

| 平台 | 营收 | 利润 | ROI |
|------|------|------|-----|
| 天猫 | ¥160,200 | ¥133,790 | 506.6% |
| 京东自营 | ¥106,800 | ¥88,984 | 499.5% |
| 淘宝 | ¥53,400 | ¥40,594 | 317.0% |
| 京东POP | ¥35,600 | ¥28,328 | 389.5% |

### 分析结论

**天猫表现最优**，ROI达到506.6%，主要得益于：
- 佣金率相对较低（5%）
- 推广费用投入产出比高
- 客单价较高

### 建议

1. **加大天猫投入**：ROI最高，可适当增加推广预算
2. **优化淘宝推广**：推广费用占比偏高（15%），建议精细化投放
3. **关注京东POP**：利润绝对值较低，考虑是否值得持续投入`,

  '请检查当前的税务申报数据，是否存在风险点？': `## 税务风险检查报告

### 风险等级：中等

#### 发现以下风险点：

**1. 进项发票缺失 [高风险]**
- 直通车推广费 ¥86,420 中有1笔未取得发票
- 物流费用 ¥45,320 中有2笔未取得发票
- **影响**：不可抵扣进项税约 ¥7,800

**2. 双基准收入差异 [中风险]**
- 订单口径收入与确认收入存在跨月差异
- 差异金额约 ¥45,000
- **建议**：准备差异说明备查

**3. 成本进项抵扣率 [低风险]**
- 当前统一按13%计算进项抵扣
- 部分供应商可能适用6%或9%税率
- **建议**：核实各供应商适用税率

### 行动建议
1. 尽快催收缺失的发票
2. 准备收入差异的书面说明
3. 梳理供应商发票税率清单`,

  '请分析最近的对账差异，主要原因是什么？': `## 对账差异分析

### 总体情况
- 3月差异：14笔，金额 ¥-1,256.80
- 2月差异：5笔，金额 ¥-432.50
- 平均匹配率：99.1%

### 差异原因分类

| 原因 | 笔数 | 金额 | 占比 |
|------|------|------|------|
| 佣金计算差异 | 8 | ¥-856.30 | 50.7% |
| 跨月结算时间差 | 5 | ¥-312.00 | 18.5% |
| 运费补差未同步 | 4 | ¥-420.50 | 24.9% |
| 其他 | 2 | ¥-100.50 | 5.9% |

### 根因分析
1. **佣金差异**：平台活动期间佣金费率调整未及时同步到系统
2. **跨月结算**：月底最后1-2天的订单，平台次月才出结算单
3. **运费补差**：平台补贴运费差额未在订单中体现

### 改进建议
1. 建立佣金费率变更的自动同步机制
2. 对账时增加T+2的时间窗口容差
3. 单独追踪运费补差科目`,
}

export default function AIAnalysis() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  async function sendMessage(text: string) {
    if (!text.trim()) return
    const userMsg: Message = { role: 'user', content: text.trim(), timestamp: new Date() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // Try API first, fallback to demo
    let response = ''
    try {
      const result = await fetch('/api/v1/ai/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text.trim(), context_type: 'general' }),
      })
      if (result.ok) {
        const data = await result.json()
        response = data.analysis || data.message || '分析完成'
      } else {
        throw new Error('API unavailable')
      }
    } catch {
      // Demo mode - use preset responses or generic
      response = DEMO_RESPONSES[text.trim()] ||
        `## 分析结果\n\n基于当前数据分析：\n\n您的问题「${text.trim()}」涉及的核心指标如下：\n\n- 本月总营收：¥356,000\n- 毛利率：34.7%\n- 净利率：25.1%\n\n> 连接后端 AI 服务后，将提供更深入的个性化分析。\n\n### 建议\n1. 定期回顾关键指标变动\n2. 关注异常波动的数据\n3. 对比同期历史数据`
    }

    // Simulate typing delay
    await new Promise(r => setTimeout(r, 800))
    setMessages(prev => [...prev, { role: 'assistant', content: response, timestamp: new Date() }])
    setLoading(false)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="mb-6">
        <h2 className="font-serif text-lg font-semibold text-ink">AI 分析</h2>
        <p className="text-sm text-ink-muted mt-1">智能财务分析助手</p>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col bg-white rounded-lg border border-border-light overflow-hidden">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-12 h-12 rounded-full bg-paper-warm flex items-center justify-center mb-4">
                <span className="font-serif text-xl text-ink-muted">智</span>
              </div>
              <h3 className="text-sm text-ink-light mb-1">AI 财务分析助手</h3>
              <p className="text-xs text-ink-muted mb-8 max-w-md">
                基于您的电商财务数据，提供利润分析、税务风险检查、对账差异分析等智能洞察
              </p>

              {/* Quick prompts */}
              <div className="grid grid-cols-3 gap-2 max-w-lg">
                {QUICK_PROMPTS.map(qp => (
                  <button
                    key={qp.label}
                    onClick={() => sendMessage(qp.prompt)}
                    className="px-3 py-2 text-xs text-ink-light bg-paper-warm rounded-lg border border-border-light hover:border-border hover:bg-paper-dark transition-colors text-left"
                  >
                    <span className="block font-normal mb-0.5">{qp.label}</span>
                    <span className="text-ink-muted line-clamp-2">{qp.prompt}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] ${
                msg.role === 'user'
                  ? 'bg-indigo text-white rounded-2xl rounded-br-md px-4 py-2.5'
                  : 'bg-paper-warm rounded-2xl rounded-bl-md px-5 py-4'
              }`}>
                {msg.role === 'assistant' ? (
                  <div className="text-sm leading-relaxed prose prose-sm max-w-none
                    [&_h2]:text-base [&_h2]:font-normal [&_h2]:mt-2 [&_h2]:mb-2 [&_h2]:text-ink
                    [&_h3]:text-sm [&_h3]:font-normal [&_h3]:mt-3 [&_h3]:mb-1 [&_h3]:text-ink-light
                    [&_table]:text-xs [&_table]:my-2 [&_th]:px-2 [&_th]:py-1 [&_th]:border-b [&_th]:border-border [&_th]:text-left [&_th]:font-normal
                    [&_td]:px-2 [&_td]:py-1 [&_td]:border-b [&_td]:border-border-light
                    [&_ul]:my-1 [&_li]:my-0.5 [&_li]:text-ink-light
                    [&_strong]:font-normal [&_strong]:text-ink
                    [&_blockquote]:border-l-2 [&_blockquote]:border-gold [&_blockquote]:pl-3 [&_blockquote]:text-ink-muted [&_blockquote]:italic
                    [&_ol]:my-1
                  "
                    dangerouslySetInnerHTML={{ __html: formatMarkdown(msg.content) }}
                  />
                ) : (
                  <p className="text-sm">{msg.content}</p>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-paper-warm rounded-2xl rounded-bl-md px-5 py-4">
                <div className="flex gap-1.5">
                  <span className="w-1.5 h-1.5 bg-ink-muted rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 bg-ink-muted rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 bg-ink-muted rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="border-t border-border-light px-4 py-3">
          <div className="flex items-end gap-3">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入您的分析问题..."
              rows={1}
              className="flex-1 resize-none text-sm bg-paper-warm rounded-lg px-4 py-2.5 focus:outline-none focus:ring-1 focus:ring-border placeholder:text-ink-muted/50"
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || loading}
              className="px-4 py-2.5 bg-ink text-paper rounded-lg text-sm disabled:opacity-30 hover:bg-ink-light transition-colors"
            >
              发送
            </button>
          </div>
          <p className="text-xs text-ink-muted mt-2 px-1">
            按 Enter 发送，Shift+Enter 换行
          </p>
        </div>
      </div>
    </div>
  )
}

// Simple markdown to HTML converter
function formatMarkdown(text: string): string {
  return text
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\|(.+)\|/g, (match) => {
      const cells = match.split('|').filter(c => c.trim())
      if (cells.every(c => /^[-\s]+$/.test(c))) return ''
      const tag = match.includes('---') ? 'th' : 'td'
      return '<tr>' + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>'
    })
    .replace(/(<tr>.*<\/tr>)/s, '<table>$1</table>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>')
}
