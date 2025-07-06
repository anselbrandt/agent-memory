"use client";

import { useRef, useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import Messages from "@/components/Messages";
import LoadingSpinner from "@/components/LoadingSpinner";
import InputForm from "@/components/InputForm";

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

export default function ChatPage() {
  const { refreshAuth } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<
    string | null
  >(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const convRef = useRef<HTMLDivElement>(null);

  // Handle session_id from OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get("session_id");

    if (sessionId) {
      // Set the session cookie on the frontend domain
      document.cookie = `session_id=${sessionId}; path=/; max-age=${
        7 * 24 * 60 * 60
      }; samesite=lax`;

      // Clean up the URL by removing the session_id parameter
      const newUrl = window.location.pathname;
      window.history.replaceState({}, document.title, newUrl);

      console.log("Session ID set from OAuth callback:", sessionId);

      // Refresh auth status to update the UI
      refreshAuth();
    }
  }, [refreshAuth]);

  // Initialize the app with a new conversation
  useEffect(() => {
    initializeApp();
  }, []);

  async function initializeApp() {
    try {
      await createNewConversation();
      await loadConversations();
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
        <Header />
        <Messages messages={messages} convRef={convRef} />
        <LoadingSpinner loading={loading} />
        <InputForm
          onSubmit={onSubmit}
          prompt={prompt}
          setPrompt={setPrompt}
          onKeyDown={onKeyDown}
          loading={loading}
        />
      </div>
    </div>
  );
}
