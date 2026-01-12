'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { 
  Send, 
  Mic, 
  MicOff, 
  Paperclip, 
  X, 
  Bot, 
  User, 
  Loader2,
  CheckCircle,
  AlertCircle,
  FileText,
  Image as ImageIcon,
  Sparkles,
  Plus,
  Home,
  MapPin
} from 'lucide-react';
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder';
import { ChatMessage } from '@/types/maninos';

interface ChatPanelProps {
  propertyId: string | null;
  propertyName?: string | null;
  isCreatingProperty?: boolean;
  onCancelCreation?: () => void;
  onPropertyCreated?: (propertyId: string, propertyName: string) => void;
  onFinancialDataUpdated?: () => void;
}

interface PendingFile {
  file: File;
  id: string;
  preview?: string;
}

export function ChatPanel({ 
  propertyId, 
  propertyName,
  isCreatingProperty = false,
  onCancelCreation,
  onPropertyCreated,
  onFinancialDataUpdated 
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  // Creation form state
  const [newPropertyName, setNewPropertyName] = useState('');
  const [newPropertyAddress, setNewPropertyAddress] = useState('');
  const [creationStep, setCreationStep] = useState<'name' | 'address' | 'confirm'>('name');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const {
    isRecording,
    recordingTime,
    audioBlob,
    error: voiceError,
    startRecording,
    stopRecording,
    cancelRecording,
    clearAudio
  } = useVoiceRecorder();

  // Reset creation form when creation mode changes
  useEffect(() => {
    if (isCreatingProperty) {
      setNewPropertyName('');
      setNewPropertyAddress('');
      setCreationStep('name');
    }
  }, [isCreatingProperty]);

  // Welcome message
  useEffect(() => {
    if (messages.length === 0 || isCreatingProperty) {
      const welcomeMessage: ChatMessage = {
        id: 'welcome',
        role: 'assistant',
        content: isCreatingProperty
          ? '🏠 **Nueva Evaluación**\n\nVamos a añadir una nueva propiedad. Por favor, completa el formulario a continuación con el nombre y dirección de la propiedad.'
          : propertyId 
            ? '¡Hola! Estoy listo para ayudarte con esta propiedad. ¿Qué necesitas?'
            : '¡Hola! Soy tu asistente de ABOKA AI. Para evaluar una nueva propiedad, haz clic en el botón "New Evaluation" del menú de propiedades.',
        timestamp: new Date().toISOString()
      };
      if (isCreatingProperty || messages.length === 0) {
        setMessages([welcomeMessage]);
      }
    }
  }, [propertyId, isCreatingProperty]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [inputText]);

  // Send audio when recording stops
  useEffect(() => {
    if (audioBlob && !isRecording) {
      handleSendMessage(undefined, audioBlob);
      clearAudio();
    }
  }, [audioBlob, isRecording]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    const newFiles: PendingFile[] = Array.from(files).map(file => ({
      file,
      id: crypto.randomUUID(),
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
    }));

    setPendingFiles(prev => [...prev, ...newFiles]);
    e.target.value = ''; // Reset input
  };

  const removeFile = (id: string) => {
    setPendingFiles(prev => {
      const file = prev.find(f => f.id === id);
      if (file?.preview) URL.revokeObjectURL(file.preview);
      return prev.filter(f => f.id !== id);
    });
  };

  const handleSendMessage = useCallback(async (
    textOverride?: string, 
    audioOverride?: Blob
  ) => {
    const text = textOverride ?? inputText.trim();
    const hasContent = text || pendingFiles.length > 0 || audioOverride;
    
    if (!hasContent || isLoading) return;

    setError(null);
    setIsLoading(true);

    // Add user message to UI
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: audioOverride 
        ? '🎤 Mensaje de voz...' 
        : text || `📎 ${pendingFiles.length} archivo(s)`,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);
    setInputText('');

    try {
      const formData = new FormData();
      formData.append('text', text);
      formData.append('session_id', `web-${propertyId || 'new'}`);
      
      if (propertyId) {
        formData.append('property_id', propertyId);
      }

      // Add audio file
      if (audioOverride) {
        formData.append('audio', audioOverride, 'voice-recording.webm');
      }

      // Add regular files
      for (const pf of pendingFiles) {
        formData.append('files', pf.file, pf.file.name);
      }

      const response = await fetch('/api/chat', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Error en la comunicación');
      }

      // Update user message if transcript exists
      if (data.transcript) {
        setMessages(prev => prev.map(m => 
          m.id === userMessage.id 
            ? { ...m, content: `🎤 "${data.transcript}"` }
            : m
        ));
      }

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.answer || 'No recibí respuesta del servidor.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMessage]);

      // Handle new property creation
      if (data.property_id && (!propertyId || data.property_id !== propertyId)) {
        onPropertyCreated?.(data.property_id, data.property_name || 'Nueva Propiedad');
      }

      // Detect if financial/estudio data was updated
      // Look for keywords in the response that indicate a financial update
      const responseText = (data.answer || '').toLowerCase();
      const financialKeywords = ['actualizado', 'precio', 'compra', 'venta', 'estimado', 'estudio', '€', 'euros'];
      const hasFinancialUpdate = financialKeywords.some(kw => responseText.includes(kw));
      if (hasFinancialUpdate && onFinancialDataUpdated) {
        onFinancialDataUpdated();
      }

      // Clear files after successful send
      pendingFiles.forEach(pf => {
        if (pf.preview) URL.revokeObjectURL(pf.preview);
      });
      setPendingFiles([]);

    } catch (err: any) {
      setError(err.message || 'Error al enviar el mensaje');
      // Remove the pending user message on error
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  }, [inputText, pendingFiles, propertyId, isLoading, onPropertyCreated]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Handle property creation via form
  const handleCreateProperty = useCallback(async () => {
    if (!newPropertyName.trim() || !newPropertyAddress.trim()) return;
    
    setIsLoading(true);
    setError(null);

    // Add confirmation message to UI
    const confirmMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: `Crear propiedad:\n📍 **${newPropertyName}**\n📫 ${newPropertyAddress}`,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, confirmMessage]);

    try {
      const formData = new FormData();
      formData.append('text', `Crear propiedad: ${newPropertyName} - ${newPropertyAddress}`);
      formData.append('session_id', 'web-new');
      formData.append('allow_create', 'true'); // Flag to allow creation

      const response = await fetch('/api/chat', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Error al crear la propiedad');
      }

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.answer || 'Propiedad creada correctamente.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMessage]);

      // Handle new property creation
      if (data.property_id) {
        onPropertyCreated?.(data.property_id, data.property_name || newPropertyName);
      }

    } catch (err: any) {
      setError(err.message || 'Error al crear la propiedad');
      // Remove the pending user message on error
      setMessages(prev => prev.filter(m => m.id !== confirmMessage.id));
    } finally {
      setIsLoading(false);
    }
  }, [newPropertyName, newPropertyAddress, onPropertyCreated]);

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getFileIcon = (file: File) => {
    if (file.type.startsWith('image/')) return <ImageIcon size={14} />;
    return <FileText size={14} />;
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 bg-white/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/25">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="font-bold text-slate-800 text-sm">Asistente ABOKA</h2>
            {propertyName ? (
              <div className="flex items-center gap-1.5">
                <Home size={11} className="text-blue-500 flex-shrink-0" />
                <p className="text-xs text-blue-600 font-medium truncate" title={propertyName}>
                  {propertyName}
                </p>
              </div>
            ) : (
              <p className="text-xs text-slate-500">
                {isLoading ? 'Pensando...' : 'Listo para ayudarte'}
              </p>
            )}
          </div>
          {propertyId && (
            <div className="px-2 py-1 bg-emerald-100 text-emerald-700 text-[10px] font-bold rounded-full uppercase">
              Conectado
            </div>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-thin">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 animate-fade-in ${
              message.role === 'user' ? 'flex-row-reverse' : ''
            }`}
          >
            {/* Avatar */}
            <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
              message.role === 'user' 
                ? 'bg-slate-800' 
                : 'bg-gradient-to-br from-blue-500 to-indigo-600'
            }`}>
              {message.role === 'user' 
                ? <User size={14} className="text-white" />
                : <Bot size={14} className="text-white" />
              }
            </div>

            {/* Message Bubble */}
            <div className={`max-w-[80%] ${message.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                message.role === 'user'
                  ? 'bg-slate-800 text-white rounded-br-md'
                  : 'bg-white border border-slate-200 text-slate-700 rounded-bl-md shadow-sm'
              }`}>
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
              {message.timestamp && (
                <p className={`text-[10px] text-slate-400 mt-1 ${
                  message.role === 'user' ? 'text-right' : 'text-left'
                }`}>
                  {new Date(message.timestamp).toLocaleTimeString('es-ES', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </p>
              )}
            </div>
          </div>
        ))}

        {/* Property Creation Form */}
        {isCreatingProperty && !isLoading && (
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl p-5 mx-2 shadow-sm animate-fade-in">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/25">
                <Plus size={20} className="text-white" />
              </div>
              <div>
                <h3 className="font-bold text-slate-800">Nueva Propiedad</h3>
                <p className="text-xs text-slate-500">Completa los campos para comenzar</p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Property Name */}
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                  <Home size={12} className="inline mr-1" />
                  Nombre de la propiedad
                </label>
                <input
                  type="text"
                  value={newPropertyName}
                  onChange={(e) => setNewPropertyName(e.target.value)}
                  placeholder="Ej: Casa Demo, Apartamento Centro..."
                  className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-300 transition-all"
                  autoFocus
                />
              </div>

              {/* Property Address */}
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                  <MapPin size={12} className="inline mr-1" />
                  Dirección completa
                </label>
                <input
                  type="text"
                  value={newPropertyAddress}
                  onChange={(e) => setNewPropertyAddress(e.target.value)}
                  placeholder="Ej: Calle Mayor 123, Madrid 28001"
                  className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-300 transition-all"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={onCancelCreation}
                  className="flex-1 px-4 py-2.5 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleCreateProperty}
                  disabled={!newPropertyName.trim() || !newPropertyAddress.trim()}
                  className="flex-1 px-4 py-2.5 text-sm font-bold text-white bg-blue-600 rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:bg-slate-300 transition-all shadow-lg shadow-blue-500/25 disabled:shadow-none flex items-center justify-center gap-2"
                >
                  <Plus size={16} />
                  Crear Propiedad
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex gap-3 animate-fade-in">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
              <Bot size={14} className="text-white" />
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
              <div className="flex gap-1.5">
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error Banner */}
      {(error || voiceError) && (
        <div className="mx-4 mb-2 px-4 py-2 bg-red-50 border border-red-100 rounded-xl flex items-center gap-2 text-sm text-red-600">
          <AlertCircle size={16} />
          <span>{error || voiceError}</span>
          <button 
            onClick={() => setError(null)} 
            className="ml-auto p-1 hover:bg-red-100 rounded-full"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Recording Banner */}
      {isRecording && (
        <div className="mx-4 mb-2 px-4 py-3 bg-red-500 text-white rounded-xl flex items-center gap-3 animate-fade-in">
          <div className="w-3 h-3 bg-white rounded-full animate-pulse" />
          <span className="font-medium">Grabando...</span>
          <span className="font-mono text-sm opacity-80">{formatTime(recordingTime)}</span>
          <button 
            onClick={cancelRecording}
            className="ml-auto text-sm underline hover:no-underline opacity-80 hover:opacity-100"
          >
            Cancelar
          </button>
        </div>
      )}

      {/* Pending Files */}
      {pendingFiles.length > 0 && (
        <div className="mx-4 mb-2 flex flex-wrap gap-2">
          {pendingFiles.map((pf) => (
            <div 
              key={pf.id}
              className="flex items-center gap-2 px-3 py-2 bg-slate-100 rounded-lg text-sm"
            >
              {pf.preview ? (
                <img src={pf.preview} alt="" className="w-8 h-8 rounded object-cover" />
              ) : (
                getFileIcon(pf.file)
              )}
              <span className="max-w-[100px] truncate text-slate-600">{pf.file.name}</span>
              <button 
                onClick={() => removeFile(pf.id)}
                className="p-1 hover:bg-slate-200 rounded-full text-slate-400 hover:text-slate-600"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input Area */}
      <div className="p-4 border-t border-slate-100 bg-white/80 backdrop-blur-sm">
        <div className="flex items-end gap-2">
          {/* File Button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || isRecording}
            className="p-2.5 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors disabled:opacity-50"
            title="Adjuntar archivo"
          >
            <Paperclip size={20} />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.webp"
            onChange={handleFileSelect}
            className="hidden"
          />

          {/* Text Input */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading || isRecording}
              placeholder={isRecording ? 'Grabando audio...' : 'Escribe tu mensaje...'}
              rows={1}
              className="w-full px-4 py-3 pr-12 bg-slate-100 border-0 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-sm placeholder:text-slate-400 disabled:opacity-50 transition-all"
              style={{ maxHeight: '120px' }}
            />
          </div>

          {/* Voice Button */}
          <button
            onClick={toggleRecording}
            disabled={isLoading}
            className={`p-2.5 rounded-xl transition-all ${
              isRecording
                ? 'bg-red-500 text-white shadow-lg shadow-red-500/25 animate-pulse'
                : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
            } disabled:opacity-50`}
            title={isRecording ? 'Detener grabación' : 'Grabar audio'}
          >
            {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
          </button>

          {/* Send Button */}
          <button
            onClick={() => handleSendMessage()}
            disabled={isLoading || isRecording || (!inputText.trim() && pendingFiles.length === 0)}
            className="p-2.5 rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:bg-slate-300 transition-all shadow-lg shadow-blue-500/25 disabled:shadow-none"
            title="Enviar mensaje"
          >
            {isLoading ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <Send size={20} />
            )}
          </button>
        </div>

        <p className="text-[10px] text-slate-400 text-center mt-2">
          Presiona Enter para enviar • Shift+Enter para nueva línea
        </p>
      </div>
    </div>
  );
}

