# Multi-Chat Development Plan

## Overview
This plan outlines the implementation of multi-chat functionality with a collapsible sidebar, chat management, and persistent storage in PostgreSQL.

## Database Schema Changes

### 1. Create Chat Sessions Table
```sql
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Modify Messages Table
```sql
-- Drop existing table and recreate with proper structure
DROP TABLE IF EXISTS messages;

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    chat_session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'model')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add index for better performance
CREATE INDEX IF NOT EXISTS idx_messages_chat_session_id ON messages(chat_session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
```

## Backend API Changes

### 1. New API Endpoints

#### Chat Sessions Management
- `GET /chats/` - List all chat sessions
- `POST /chats/` - Create new chat session
- `DELETE /chats/{chat_id}` - Delete chat session
- `PUT /chats/{chat_id}` - Update chat session title

#### Modified Chat Endpoints
- `GET /chat/{chat_id}` - Get messages for specific chat
- `POST /chat/{chat_id}` - Send message to specific chat

### 2. Backend Implementation Details

#### New Models/Types
```python
class ChatSession(TypedDict):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int

class CreateChatRequest(TypedDict):
    title: str

class UpdateChatRequest(TypedDict):
    title: str
```

#### Database Class Updates
- Add `create_chat_session()` method
- Add `get_chat_sessions()` method
- Add `delete_chat_session()` method
- Add `update_chat_session()` method
- Modify `get_messages()` to accept chat_session_id
- Modify `add_messages()` to accept chat_session_id
- Add `get_or_create_default_chat()` method

#### API Route Updates
- Modify existing `/chat/` routes to work with chat IDs
- Add new chat session management routes
- Update message storage to include chat_session_id
- Add auto-title generation for new chats

## Frontend Changes

### 1. New Components

#### Sidebar Component
```typescript
interface SidebarProps {
  chats: ChatSession[];
  currentChatId: string | null;
  onChatSelect: (chatId: string) => void;
  onNewChat: () => void;
  onDeleteChat: (chatId: string) => void;
  onRenameChat: (chatId: string, newTitle: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}
```

#### Chat Item Component
```typescript
interface ChatItemProps {
  chat: ChatSession;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (newTitle: string) => void;
}
```

### 2. Main Component Updates

#### New State Management
```typescript
const [chats, setChats] = useState<ChatSession[]>([]);
const [currentChatId, setCurrentChatId] = useState<string | null>(null);
const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
const [chatMessages, setChatMessages] = useState<Record<string, Message[]>>({});
```

#### New Functions
- `loadChats()` - Load all chat sessions
- `createNewChat()` - Create new chat session
- `deleteChat()` - Delete chat session
- `renameChat()` - Rename chat session
- `switchChat()` - Switch to different chat
- `generateChatTitle()` - Auto-generate title from first message

### 3. UI Layout Changes

#### New Layout Structure
```
┌─────────────────────────────────────────────────────────────┐
│ [☰] AI Chat Assistant                                       │
├─────────────────────────────────────────────────────────────┤
│ [Sidebar] │ [Chat Area]                                     │
│ ├─ New   │ ├─ Chat Header (Current Chat Title)            │
│ ├─ Chat1 │ ├─ Messages Container                          │
│ ├─ Chat2 │ ├─ Loading Spinner                             │
│ └─ Chat3 │ └─ Input Form                                  │
└─────────────────────────────────────────────────────────────┘
```

#### Responsive Design
- Sidebar auto-collapses on mobile
- Chat area adapts to sidebar state
- Touch-friendly interactions

## Implementation Steps

### Phase 1: Database Setup
1. Create migration scripts for new schema
2. Update database connection and initialization
3. Test database operations

### Phase 2: Backend API
1. Implement new database methods
2. Create chat session API endpoints
3. Update existing chat endpoints to work with chat IDs
4. Add proper error handling and validation
5. Test all API endpoints

### Phase 3: Frontend Core
1. Create sidebar component with basic functionality
2. Update main component state management
3. Implement chat switching logic
4. Add new chat creation
5. Test basic multi-chat functionality

### Phase 4: Frontend Enhancement
1. Add chat deletion functionality
2. Implement chat renaming
3. Add auto-title generation
4. Implement sidebar collapse/expand
5. Add proper loading states and error handling

### Phase 5: Polish & Testing
1. Add responsive design
2. Implement proper keyboard navigation
3. Add confirmation dialogs for destructive actions
4. Performance optimization
5. End-to-end testing

## Key Features

### Auto-Title Generation
- Use first 3-5 words of the first user message
- Fallback to "New Chat" with timestamp
- Allow manual renaming

### Chat Management
- Drag-and-drop reordering (future enhancement)
- Search/filter chats (future enhancement)
- Archive/unarchive chats (future enhancement)

### Memory Management
- Load chat history on demand
- Cache recent chats for quick switching
- Implement pagination for very long chats

### UX Considerations
- Smooth transitions between chats
- Preserve scroll position when switching
- Clear visual indication of active chat
- Confirmation before deleting chats
- Keyboard shortcuts for common actions

## Technical Considerations

### Performance
- Lazy load chat messages
- Implement virtual scrolling for long chats
- Debounce search and filtering
- Cache frequently accessed chats

### Error Handling
- Graceful degradation when API fails
- Retry mechanisms for network errors
- User-friendly error messages
- Offline capability (future enhancement)

### Security
- Validate chat ownership
- Sanitize user inputs
- Implement rate limiting
- Add CSRF protection

## Testing Strategy

### Unit Tests
- Database operations
- API endpoints
- Component logic
- Utility functions

### Integration Tests
- API workflows
- Database transactions
- Component interactions

### E2E Tests
- Complete user workflows
- Chat creation and deletion
- Message sending across chats
- Sidebar interactions

## Migration Strategy

### Backward Compatibility
- Migrate existing messages to default chat
- Preserve message timestamps
- Maintain existing API contracts during transition

### Data Migration
```sql
-- Create default chat for existing messages
INSERT INTO chat_sessions (id, title, created_at) 
VALUES ('default-chat-id', 'Default Chat', CURRENT_TIMESTAMP);

-- Migrate existing messages (if any exist in old format)
-- This depends on current message storage format
```

## Future Enhancements

### Phase 2 Features
- Chat folders/categories
- Shared chats
- Export chat history
- Advanced search
- Chat templates

### Phase 3 Features
- Real-time collaboration
- Voice messages
- File attachments
- Advanced AI memory
- Custom AI personalities per chat

## Estimated Timeline

- **Phase 1**: 1-2 days
- **Phase 2**: 2-3 days  
- **Phase 3**: 3-4 days
- **Phase 4**: 2-3 days
- **Phase 5**: 1-2 days

**Total**: 9-14 days

## Success Metrics

- Users can create and manage multiple chats
- Chat history persists across sessions
- Sidebar provides intuitive navigation
- Performance remains smooth with multiple chats
- No data loss during chat operations
- Responsive design works on all devices