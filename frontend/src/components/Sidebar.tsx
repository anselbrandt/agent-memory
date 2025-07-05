"use client";

import { useState } from "react";

import ChatIcon from "@/icons/ChatIcon";
import PlusIcon from "@/icons/PlusIcon";
import LeftArrow from "@/icons/LeftArrow";
import RightArrow from "@/icons/RightArrow";
import SidebarIcon from "@/icons/SidebarIcon";

interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface SidebarProps {
  conversations: Conversation[];
  currentConversationId: string | null;
  onNewConversation: () => void;
  onSelectConversation: (conversationId: string) => void;
}

export default function Sidebar({
  conversations,
  currentConversationId,
  onNewConversation,
  onSelectConversation,
}: SidebarProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleSidebar = () => {
    setIsExpanded((prev) => !prev);
  };

  return (
    <aside
      className={`
        h-screen bg-white border-r border-gray-200 
        flex flex-col items-start 
        transition-all duration-300 ease-in-out
        ${isExpanded ? "w-80" : "w-16"}
      `}
    >
      {/* Header Section */}
      <div className="w-full p-4 border-b border-gray-100">
        <button
          onClick={toggleSidebar}
          className="
            group relative 
            flex items-center justify-center 
            w-8 h-8 
            rounded-lg 
            hover:bg-gray-100 
            transition-all duration-200 
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            active:scale-95
          "
          aria-label={isExpanded ? "Collapse sidebar" : "Expand sidebar"}
        >
          {/* Default icon */}
          <div
            className="
            absolute inset-0 
            flex items-center justify-center
            opacity-100 group-hover:opacity-0 
            transition-opacity duration-200
          "
          >
            <SidebarIcon />
          </div>

          {/* Hover icon */}
          <div
            className="
            absolute inset-0 
            flex items-center justify-center
            opacity-0 group-hover:opacity-100 
            transition-opacity duration-200
          "
          >
            {isExpanded ? <LeftArrow /> : <RightArrow />}
          </div>
        </button>
      </div>

      {/* Action Buttons Section */}
      <div className="w-full p-4 space-y-3">
        <button
          onClick={onNewConversation}
          className="
            group 
            flex items-center justify-center 
            w-8 h-8 
            rounded-lg 
            hover:bg-gray-100 
            transition-all duration-200 
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            active:scale-95
          "
          aria-label="New chat"
        >
          <div
            className="
            transition-transform duration-200 
            group-hover:scale-110 
            group-active:scale-95
          "
          >
            <PlusIcon />
          </div>
        </button>

        <button
          className="
            group 
            flex items-center justify-center 
            w-8 h-8 
            rounded-lg 
            hover:bg-gray-100 
            transition-all duration-200 
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            active:scale-95
          "
          aria-label="Chat history"
        >
          <div
            className="
            transition-transform duration-200 
            group-hover:scale-110 
            group-active:scale-95
          "
          >
            <ChatIcon />
          </div>
        </button>
      </div>

      {/* Conversations List */}
      {isExpanded && (
        <div className="flex-1 w-full p-4 overflow-y-auto">
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-gray-500 mb-3">
              Conversations
            </h3>
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                onClick={() => onSelectConversation(conversation.id)}
                className={`
                  p-3 rounded-lg cursor-pointer transition-all duration-200
                  hover:bg-gray-50 border
                  ${
                    currentConversationId === conversation.id
                      ? "bg-blue-50 border-blue-200"
                      : "bg-white border-gray-200"
                  }
                `}
              >
                <div className="text-sm font-medium text-gray-900 truncate">
                  {conversation.title || "Untitled Chat"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}
