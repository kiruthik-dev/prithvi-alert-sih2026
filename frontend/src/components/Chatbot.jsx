import React, { useState, useRef, useEffect } from 'react';

export default function Chatbot({ userLocation }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'I am PrithviAssist, an AI-assisted disaster information bot. How can I help you?', note: 'AI-Assisted Disaster Information (Retrieval Mode)' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (text) => {
    const query = text || input;
    if (!query.trim()) return;

    setMessages((prev) => [...prev, { role: 'user', content: query }]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          lat: userLocation?.lat || null,
          lon: userLocation?.lon || null,
        }),
      });
      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.message, note: data.note, action: data.action }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Network error connecting to PrithviAssist.' }]);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    "Is my area safe?",
    "What should I do?",
    "Road status",
    "Emergency contacts"
  ];

  return (
    <div className="fixed bottom-6 right-6 z-[2000]">
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="bg-blue-600 hover:bg-blue-500 text-white p-4 rounded-full shadow-2xl flex items-center justify-center transition-transform hover:scale-110"
        >
          <span className="text-xl">💬</span>
        </button>
      )}

      {isOpen && (
        <div className="w-80 h-96 bg-pa-card border border-pa-border rounded-xl shadow-2xl flex flex-col overflow-hidden">
          <div className="bg-blue-900/40 p-3 border-b border-pa-border flex justify-between items-center">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">💬 PrithviAssist</h3>
              <p className="text-[10px] text-gray-400">AI Disaster Assistance</p>
            </div>
            <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-white">✕</button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-[#0a0f1a]">
            {messages.map((msg, i) => (
              <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`p-2.5 rounded-lg max-w-[85%] text-sm whitespace-pre-wrap ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-200 border border-gray-700'}`}>
                  {msg.content}
                </div>
                {msg.note && (
                  <span className="text-[9px] text-gray-500 mt-1 italic">{msg.note}</span>
                )}
                {msg.action === 'REPORT_HAZARD' && (
                  <button onClick={() => document.getElementById('report-hazard-btn')?.click()} className="mt-2 text-xs bg-orange-600 text-white px-3 py-1 rounded hover:bg-orange-500">
                    REPORT HAZARD
                  </button>
                )}
              </div>
            ))}
            {loading && (
              <div className="text-gray-500 text-xs flex items-center gap-2">
                <span className="animate-pulse">●</span>
                <span className="animate-pulse delay-100">●</span>
                <span className="animate-pulse delay-200">●</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="p-2 bg-gray-900 border-t border-pa-border">
            <div className="flex flex-wrap gap-1 mb-2">
              {quickActions.map((action) => (
                <button
                  key={action}
                  onClick={() => handleSend(action)}
                  className="text-[10px] bg-blue-900/30 text-blue-300 border border-blue-800 rounded px-2 py-1 hover:bg-blue-800 hover:text-white transition-colors"
                >
                  {action}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask a question..."
                className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              />
              <button
                onClick={() => handleSend()}
                disabled={loading || !input.trim()}
                className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-2 rounded flex items-center justify-center transition-colors"
              >
                ➤
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
