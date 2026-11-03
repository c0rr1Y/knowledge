// ------- Knowledge Base -------
export interface KnowledgeBase {
  id: string
  name: string
  description: string
  document_count: number
  created_at: string
  access_level: string | null
}

// ------- Document -------
export interface DocumentInfo {
  id: string
  filename: string
  original_filename: string
  file_size: number
  status: 'uploaded' | 'processing' | 'done' | 'error'
  chunk_count: number
  error_message: string
  created_at: string
}

// ------- Auth -------
export interface UserInfo {
  user_id: string
  tenant_id: string
  tenant_name: string
  username: string
  email: string
  role: string
}

export interface LoginResponse {
  access_token: string
  user_id: string
  tenant_id: string
  tenant_name: string
  username: string
  email: string
  role: string
}

// ------- Chat -------
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  sources?: SourceInfo[]
  isStreaming?: boolean
}

export interface SourceInfo {
  kb_name?: string
  document_name: string
  page: number
  chunk_index?: number
  text_snippet: string
}

export interface KBMember {
  user_id: string
  username: string
  email: string
  access_level: string
}

export interface ChatStreamEvent {
  type: 'chunk' | 'sources' | 'done' | 'error'
  content: any
}
