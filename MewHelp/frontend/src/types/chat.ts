export type ChatRole = 'user' | 'assistant'

export type ChatMessageStatus = 'complete' | 'streaming' | 'error'

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  status: ChatMessageStatus
}

export interface ChatSession {
  id: string
  title: string
  preview: string
  messages: ChatMessage[]
}
