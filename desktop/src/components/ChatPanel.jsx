function renderContent(text) {
  const blocks = text.split(/```([\s\S]*?)```/g)
  return blocks.map((block, idx) => {
    if (idx % 2 === 1) {
      return (
        <pre key={idx} className="code-block">
          <code>{block}</code>
        </pre>
      )
    }
    return (
      <p key={idx} className="chat-text">
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
    <section className="panel shell">
      <div className="panel-header">
        <div className="panel-header-left">
          {quickActions.map((label) => (
            <button key={label} type="button" onClick={() => onQuickAction(label)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div ref={chatScrollRef} className="panel-body chat-body">
        {messages.length === 0 ? (
          <div className="panel-empty">Ask for hints or debugging help</div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={`chat-bubble ${message.role}`}>
              {renderContent(message.content)}
            </div>
          ))
        )}
        {isTyping && (
          <div className="chat-bubble assistant">
            <span className="typing">...</span>
          </div>
        )}
      </div>

      <div className="panel-footer">
        <input
          value={chatInput}
          onChange={(event) => setChatInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              onSend(chatInput)
            }
          }}
          placeholder="Ask the AI assistant..."
        />
      </div>
    </section>
  )
}
