'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, RefreshCw } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatPanelProps {
  propertyId?: string | null;
}

export function ChatPanel({ propertyId }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080';

  // Initialize session
  useEffect(() => {
    const storedSessionId = localStorage.getItem('aboka_session_id');
    if (storedSessionId) {
      setSessionId(storedSessionId);
    } else {
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('aboka_session_id', newSessionId);
      setSessionId(newSessionId);
    }
  }, []);

  // Welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: '¡Hola! 👋 Soy tu asistente de ABOKA AI. Puedo ayudarte con:\n\n• **Gestionar propiedades** - crear, buscar, actualizar\n• **Armario Digital** - buscar y enviar documentos\n• **Estudio Económico** - actualizar costes y valores\n• **Fotos** - buscar y enviar fotos de la reforma\n\n¿En qué te puedo ayudar?',
        timestamp: new Date()
      }]);
    }
  }, [messages.length]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${BACKEND_URL}/ui_chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: sessionId,
          property_id: propertyId || localStorage.getItem('maninos_property_id')
        })
      });

      const data = await response.json();

      const assistantMessage: Message = {
        id: `msg_${Date.now()}_assistant`,
        role: 'assistant',
        content: data.response || data.message || 'Lo siento, no pude procesar tu solicitud.',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        id: `msg_${Date.now()}_error`,
        role: 'assistant',
        content: '❌ Error de conexión. Por favor, verifica tu conexión e intenta de nuevo.',
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('aboka_session_id', newSessionId);
    setSessionId(newSessionId);
    setMessages([]);
  };

  const formatMessage = (content: string) => {
    // Simple markdown-like formatting
    return content
      .split('\n')
      .map((line, i) => {
        // Bold
        line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        // Lists
        if (line.startsWith('• ') || line.startsWith('- ')) {
          return `<div class="ml-2">${line}</div>`;
        }
        return line;
      })
      .join('<br/>');
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Bot size={18} className="text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-slate-800 text-sm">Asistente ABOKA</h2>
            <p className="text-xs text-slate-500">IA para gestión de reformas</p>
          </div>
        </div>
        <button
          onClick={handleNewChat}
          className="p-2 hover:bg-slate-200 rounded-lg transition-colors"
          title="Nueva conversación"
        >
          <RefreshCw size={16} className="text-slate-500" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
              message.role === 'user' 
                ? 'bg-blue-600' 
                : 'bg-slate-200'
            }`}>
              {message.role === 'user' 
                ? <User size={16} className="text-white" />
                : <Bot size={16} className="text-slate-600" />
              }
            </div>
            <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${
              message.role === 'user'
                ? 'bg-blue-600 text-white rounded-br-md'
                : 'bg-slate-100 text-slate-800 rounded-bl-md'
            }`}>
              <div 
                className="text-sm leading-relaxed"
                dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }}
              />
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-lg bg-slate-200 flex items-center justify-center">
              <Bot size={16} className="text-slate-600" />
            </div>
            <div className="bg-slate-100 rounded-2xl rounded-bl-md px-4 py-3">
              <Loader2 size={18} className="animate-spin text-slate-500" />
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-200 bg-white">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe tu mensaje..."
            className="flex-1 resize-none rounded-xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-h-[44px] max-h-[120px]"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="p-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-2 text-center">
          Presiona Enter para enviar, Shift+Enter para nueva línea
        </p>
      </div>
    </div>
  );
}

export default ChatPanel;
