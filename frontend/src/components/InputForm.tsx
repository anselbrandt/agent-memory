import {
  Dispatch,
  FormEventHandler,
  KeyboardEventHandler,
  SetStateAction,
} from "react";

import UpArrow from "@/icons/UpArrow";

interface Props {
  onSubmit: FormEventHandler<HTMLFormElement>;
  prompt: string;
  setPrompt: Dispatch<SetStateAction<string>>;
  onKeyDown: KeyboardEventHandler<HTMLInputElement>;
  loading: boolean;
}

export default function InputForm({
  onSubmit,
  prompt,
  setPrompt,
  onKeyDown,
  loading,
}: Props) {
  return (
    <>
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
    </>
  );
}
