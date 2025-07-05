"use client";

import { useRef, useState, useEffect } from "react";
import { marked } from "marked";
import Sidebar from "@/components/Sidebar";
import UpArrow from "@/icons/UpArrow";

interface Message {
  role: string;
  content: string;
  timestamp: string;
}

interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface User {
  id: string;
  username: string;
}

export default function ChatPage() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<
    string | null
  >(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [user, setUser] = useState<User>();
  const convRef = useRef<HTMLDivElement>(null);

  // Initialize the app with a new conversation
  useEffect(() => {
    initializeApp();
  }, []);

  async function initializeApp() {
    try {
      await createNewConversation();
      await loadConversations();
      await getUser();
    } catch (error) {
      console.error("Error initializing app:", error);
    }
  }

  async function createNewConversation() {
    try {
      const response = await fetch(
        "http://localhost:8000/chat/new-conversation",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setCurrentConversationId(data.conversation_id);
      setMessages([]);
      await loadConversations(); // Refresh conversations list
      console.log("New conversation created:", data.conversation_id);
    } catch (error) {
      console.error("Error creating new conversation:", error);
    }
  }

  async function loadConversations() {
    try {
      const response = await fetch("http://localhost:8000/chat/conversations");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setConversations(data.conversations);
    } catch (error) {
      console.error("Error loading conversations:", error);
    }
  }

  async function loadConversation(conversationId: string) {
    try {
      const response = await fetch(
        `http://localhost:8000/chat/${conversationId}`
      );
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const text = await response.text();
      setMessages([]);

      const lines = text.split("\n").filter((line) => line.trim());
      const loadedMessages: Message[] = [];

      for (const line of lines) {
        if (line.trim()) {
          try {
            const message = JSON.parse(line);
            loadedMessages.push(message);
          } catch (parseError) {
            console.warn("Failed to parse message line:", line, parseError);
          }
        }
      }

      setMessages(loadedMessages);
      setCurrentConversationId(conversationId);
    } catch (error) {
      console.error("Error loading conversation:", error);
    }
  }

  async function getUser() {
    try {
      const response = await fetch(`http://localhost:8000/me`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const user_profile = await response.json();
      setUser(user_profile);
    } catch (error) {
      console.error("Error getting user:", error);
    }
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    // Validate input
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt) {
      console.log("Empty prompt, not submitting");
      return;
    }

    if (!currentConversationId) {
      console.error("No active conversation");
      return;
    }

    console.log("Submitting prompt:", trimmedPrompt);
    setLoading(true);

    // Clear prompt immediately
    setPrompt("");

    try {
      const formData = new FormData();
      formData.append("prompt", trimmedPrompt);

      const response = await fetch(
        `http://localhost:8000/chat/${currentConversationId}`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await onFetchResponse(response);

      // Refresh conversations list to update timestamps
      await loadConversations();
    } catch (err) {
      console.error("Submit error:", err);
      setLoading(false);
    }
  }

  async function onFetchResponse(response: Response) {
    let text = "";
    const decoder = new TextDecoder();

    if (response.ok && response.body) {
      const reader = response.body.getReader();

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          text += chunk;
          updateMessages(text);
        }

        // Final decode
        const finalChunk = decoder.decode();
        if (finalChunk) {
          text += finalChunk;
          updateMessages(text);
        }

        setLoading(false);
      } catch (readError) {
        console.error("Error reading response stream:", readError);
        setLoading(false);
        throw readError;
      }
    } else {
      const text = await response.text();
      console.error(`Unexpected response: ${response.status}`, {
        response,
        text,
      });
      setLoading(false);
      throw new Error(`Unexpected response: ${response.status}`);
    }
  }

  function updateMessages(responseText: string) {
    const lines = responseText.split("\n");
    const newMessages: Message[] = [];

    for (const line of lines) {
      if (line.trim().length > 0) {
        try {
          const parsed = JSON.parse(line) as Message;
          newMessages.push(parsed);
        } catch (parseError) {
          console.warn("Failed to parse message line:", line, parseError);
        }
      }
    }

    if (newMessages.length > 0) {
      setMessages((prev) => {
        // Create a copy of existing messages
        const existingMessages = [...prev];

        // Process each new message
        for (const newMsg of newMessages) {
          // Find if this message already exists (by timestamp)
          const existingIndex = existingMessages.findIndex(
            (m) => m.timestamp === newMsg.timestamp
          );

          if (existingIndex >= 0) {
            // Update existing message (for streaming AI responses)
            existingMessages[existingIndex] = newMsg;
          } else {
            // For new messages, simply append to the end to maintain order
            // The backend sends messages in the correct order: user first, then AI response
            existingMessages.push(newMsg);
          }
        }

        return existingMessages;
      });

      // Smart scrolling behavior
      setTimeout(() => {
        if (convRef.current) {
          const container = convRef.current;
          const isUserAtBottom =
            container.scrollHeight - container.scrollTop <=
            container.clientHeight + 100;

          // Always scroll to bottom when new messages arrive, or when user is already near bottom
          if (
            isUserAtBottom ||
            newMessages.some((msg) => msg.role === "user")
          ) {
            container.scrollTop = container.scrollHeight;
          }
        }
      }, 50);
    }
  }

  // Handle Enter key press
  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const form = e.currentTarget.form;
      if (form) {
        form.requestSubmit();
      }
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-row">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onNewConversation={createNewConversation}
        onSelectConversation={loadConversation}
      />
      <div className="flex-1 flex flex-col h-screen">
        {/* Header - Fixed */}
        <div className="px-10 py-6 flex-shrink-0 bg-white border-b border-gray-200">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-2xl font-bold font-serif text-gray-700">
              {user ? `Hey there, ${user.username}.` : "Hey there."}
            </h1>
          </div>
        </div>

        {/* Messages Container - Scrollable */}
        <div className="flex-1 overflow-hidden">
          <div
            id="conversation"
            className="h-full overflow-y-auto px-4 py-6 space-y-4"
            ref={convRef}
          >
            <div className="max-w-4xl mx-auto space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.timestamp}
                  id={`msg-${msg.timestamp}`}
                  title={`${msg.role} at ${msg.timestamp}`}
                  className={`flex ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-3xl px-4 py-3 rounded-2xl ${
                      msg.role === "user"
                        ? "bg-gray-200 text-gray-600 shadow-sm border border-gray-300 shadow-sm"
                        : "bg-white text-gray-900 border border-gray-200 shadow-sm"
                    }`}
                  >
                    <div
                      className="prose prose-sm max-w-none prose-gray"
                      dangerouslySetInnerHTML={{
                        __html: marked.parse(msg.content),
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Loading Spinner - Fixed */}
        {loading && (
          <div className="flex justify-center py-4 flex-shrink-0 bg-white border-t border-gray-200">
            <div className="flex items-center gap-2 text-gray-600">
              <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
              <span className="text-sm">AI is thinking...</span>
            </div>
          </div>
        )}

        {/* Input Form - Fixed */}
        <div className="border-t border-gray-200 p-6 flex-shrink-0 bg-white">
          <div className="max-w-4xl mx-auto">
            <form onSubmit={onSubmit}>
              <div className="flex gap-3">
                <input
                  id="prompt-input"
                  name="prompt"
                  type="text"
                  className="flex-1 px-4 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:border-transparent transition-all duration-200"
                  placeholder="How can I help you today?"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={onKeyDown}
                  autoFocus
                />
                <button
                  className={`px-4 py-2 rounded-xl font-medium transition-all duration-200 bg-gray-400 text-white hover:bg-gray-700 transform hover:scale-105 active:scale-95`}
                  type="submit"
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    </div>
                  ) : (
                    <div className="hover:cursor-pointer transition-transform duration-100 hover:scale-150">
                      <UpArrow />
                    </div>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
