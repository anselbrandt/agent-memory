import { RefObject } from "react";
import { marked } from "marked";

marked.setOptions({
  breaks: true,
});

marked.use({
  renderer: {
    link({ href, text }) {
      return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline font-medium transition-colors duration-150">${text}</a>`;
    },
  },
});

interface Message {
  role: string;
  content: string;
  timestamp: string;
}

interface Props {
  messages: Message[];
  convRef: RefObject<HTMLDivElement | null>;
}

export default function Message({ messages, convRef }: Props) {
  return (
    <>
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
    </>
  );
}
