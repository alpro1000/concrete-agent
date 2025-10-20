import React, { useState } from 'react';
import { Send, Upload } from 'lucide-react';

export default function InputArea({ onSend, onUpload, isLoading }) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSend(input);
    setInput('');
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-white border-t border-gray-200 p-4">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Napiš otázku nebo popis úkolu..."
          disabled={isLoading}
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 disabled:bg-gray-100"
        />

        <button
          onClick={handleSend}
          disabled={isLoading}
          className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition"
        >
          <Send size={20} />
        </button>

        <button
          onClick={onUpload}
          type="button"
          className="border border-gray-300 text-gray-600 p-2 rounded-lg hover:bg-gray-50 transition"
        >
          <Upload size={20} />
        </button>
      </div>
    </div>
  );
}
