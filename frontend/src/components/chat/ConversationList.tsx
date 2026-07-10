import type { Conversation } from '../../lib/chat'

type ConversationListProps = {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
}

export function ConversationList({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: ConversationListProps) {
  return (
    <div className="chat-conversations">
      <button type="button" className="chat-new" onClick={onNew}>
        + New chat
      </button>
      <div className="chat-conversation-items">
        {conversations.length === 0 ? (
          <p className="chat-empty-hint">No conversations yet.</p>
        ) : (
          conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={
                conversation.id === activeId
                  ? 'chat-conversation-item active'
                  : 'chat-conversation-item'
              }
            >
              <button
                type="button"
                className="chat-conversation-select"
                onClick={() => onSelect(conversation.id)}
                title={conversation.title ?? 'Untitled'}
              >
                {conversation.title || 'Untitled'}
              </button>
              <button
                type="button"
                className="chat-conversation-delete"
                aria-label="Delete conversation"
                onClick={() => onDelete(conversation.id)}
              >
                &times;
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
