function renderContent(text) {
  const blocks = text.split(/```([\s\S]*?)```/g)
  return blocks.map((block, idx) => {
    if (idx % 2 === 1) {
      return (
        <pre key={idx} className="mt-2 mb-1 bg-slate-900/70 border border-border rounded-lg p-2 overflow-auto text-xs text-slate-100">
          <code>{block}</code>
        </pre>
      )
    }
    return (
      <p key={idx} className="whitespace-pre-wrap text-sm leading-6 m-0">
        {block}
      </p>
    )
  })
}

export default function ChatPanel({
  messages,
  chatInput,
  setChatInput,
  onSend,
  onQuickAction,
  isTyping,
  chatScrollRef
}) {
  const quickActions = ['Hint', 'Explain Code', 'Optimize', 'Find Bug']

  return (
    <section className="panel-shell h-full flex flex-col overflow-hidden">
      <div className="border-b border-border px-3 py-2 flex gap-2 flex-wrap">
        {quickActions.map((label) => (
          <button
            key={label}
            onClick={() => onQuickAction(label)}
            className="text-xs px-2 py-1 rounded-lg border border-border bg-slate-700/50 hover:bg-slate-600/80 transition"
          >
            {label}
          </button>
        ))}
      </div>

      <div ref={chatScrollRef} className="flex-1 overflow-auto scrollbar-thin p-3 space-y-3">
        {messages.length === 0 ? (
          <div className="h-full grid place-items-center text-sm text-slate-400">Ask for hints or debugging help</div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`max-w-[85%] px-3 py-2 rounded-lg border ${
                message.role === 'user'
                  ? 'ml-auto bg-indigo-600/20 border-indigo-500/50 text-indigo-100'
                  : 'mr-auto bg-slate-700/60 border-border text-slate-100'
              }`}
            >
              {renderContent(message.content)}
            </div>
          ))
        )}
        {isTyping && (
          <div className="mr-auto max-w-[85%] px-3 py-2 rounded-lg border bg-slate-700/60 border-border text-slate-100">
            <span className="inline-flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce" />
              <span className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce [animation-delay:120ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce [animation-delay:240ms]" />
            </span>
          </div>
        )}
      </div>

      <div className="border-t border-border p-3">
        <input
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              onSend(chatInput)
            }
          }}
          placeholder="Ask the AI assistant..."
          className="w-full rounded-lg bg-slate-700/60 border border-border px-3 py-2 text-sm outline-none focus:border-indigo-500"
        />
      </div>
    </section>
  )
}