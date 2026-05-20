'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Bot, 
  User, 
  Activity, 
  Info, 
  ThumbsUp, 
  ThumbsDown, 
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Loader2,
  ShieldCheck,
  Zap,
  Cpu
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  trace_id?: string;
  context?: string;
  genai_duration?: number;
  ml_duration?: number;
  feedback_done?: boolean;
}

export default function BankAiChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(crypto.randomUUID().slice(0, 8));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const toggleSources = (id: string) => {
    setExpandedSources(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const chatHistory = messages.map(m => ({
        inputs: { question: m.role === 'user' ? m.content : '' },
        outputs: { answer: m.role === 'assistant' ? m.content : '' }
      })).filter(h => h.inputs.question || h.outputs.answer);

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input, chat_history: chatHistory }),
      });

      const data = await response.json();

      if (data.error) throw new Error(data.error);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.answer,
        intent: data.intent,
        trace_id: data.trace_id,
        context: data.context,
        genai_duration: data.genai_duration,
        ml_duration: data.ml_duration,
        feedback_done: false,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error(error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Error: ${error.message}. Please check your connection or environment variables.`,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFeedback = async (messageId: string, useful: 'Yes' | 'No') => {
    const msg = messages.find(m => m.id === messageId);
    if (!msg || !msg.trace_id) return;

    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trace_id: msg.trace_id,
          useful,
          question: messages[messages.indexOf(msg) - 1]?.content || '',
          answer: msg.content
        }),
      });

      setMessages(prev => prev.map(m => 
        m.id === messageId ? { ...m, feedback_done: true } : m
      ));
    } catch (error) {
      console.error('Feedback failed:', error);
    }
  };

  const startNewSession = () => {
    setMessages([]);
    setSessionId(crypto.randomUUID().slice(0, 8));
    setExpandedSources({});
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col hidden md:flex">
        <div className="p-8 flex flex-col h-full">
          <button 
            onClick={startNewSession}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-xl transition-all font-medium shadow-lg shadow-blue-500/20 active:scale-95"
          >
            <RotateCcw className="w-4 h-4" />
            New Session
          </button>

          <div className="mt-12 flex-1">
            {/* Sidebar content removed for minimalist look */}
          </div>

          <div className="pt-6 border-t border-slate-100 text-[10px] text-slate-300 text-center uppercase tracking-tighter font-bold">
            Secure AI Interface
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative">
        {/* Header */}
        <header className="h-16 bg-white/80 backdrop-blur-md border-b border-slate-200 flex items-center px-6 sticky top-0 z-10 justify-between">
          <div className="flex items-center gap-2">
            <Bot className="text-blue-600 w-5 h-5" />
            <h2 className="font-semibold text-slate-700">Customer Support Assistant</h2>
          </div>
          <Activity className="w-4 h-4 text-slate-300" />
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 scroll-smooth">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-6 opacity-80">
              <div className="bg-blue-50 p-6 rounded-3xl">
                <Bot className="w-16 h-16 text-blue-500" />
              </div>
              <div className="space-y-2">
                <h3 className="text-2xl font-bold text-slate-800">Hello! I'm your Credit Card Support System</h3>
                <p className="text-slate-500 max-w-sm mx-auto">
                  I specialize in providing precise information about credit card terms, fees, interest rates, and security procedures based on official policy documentation.
                </p>
              </div>
              <div className="grid grid-cols-1 gap-2 w-full">
                {['How do I report a lost card?', 'What are the interest rates?', 'Explain late payment fees'].map(q => (
                  <button 
                    key={q}
                    onClick={() => { setInput(q); }}
                    className="text-sm p-3 bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:bg-blue-50 transition-all text-slate-600 text-left"
                  >
                    "{q}"
                  </button>
                ))}
              </div>
            </div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((m) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[85%] md:max-w-[75%] flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center shadow-sm ${
                    m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-blue-600'
                  }`}>
                    {m.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                  </div>
                  
                  <div className="space-y-3">
                    <div className={`p-4 rounded-2xl shadow-sm ${
                      m.role === 'user' 
                        ? 'bg-blue-600 text-white rounded-tr-none' 
                        : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
                    }`}>
                      <div className={`prose prose-sm max-w-none ${m.role === 'user' ? 'prose-invert' : ''}`}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {m.content}
                        </ReactMarkdown>
                      </div>
                      
                      {m.role === 'assistant' && m.trace_id && (
                        <div className="mt-4 pt-3 border-t border-slate-100 flex flex-col gap-3">
                          {!m.feedback_done ? (
                            <div className="flex flex-col sm:flex-row gap-2">
                              <button 
                                onClick={() => handleFeedback(m.id, 'Yes')}
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-600 hover:bg-emerald-100 rounded-xl transition-all text-xs font-bold border border-emerald-100 active:scale-[0.98]"
                              >
                                <ThumbsUp size={14} />
                                Helpful
                              </button>
                              <button 
                                onClick={() => handleFeedback(m.id, 'No')}
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-rose-50 text-rose-600 hover:bg-rose-100 rounded-xl transition-all text-xs font-bold border border-rose-100 active:scale-[0.98]"
                              >
                                <ThumbsDown size={14} />
                                Not helpful
                              </button>
                            </div>
                          ) : (
                            <div className="flex">
                              <span className="flex items-center gap-2 text-xs font-bold text-emerald-600 bg-emerald-50 px-4 py-2 rounded-xl border border-emerald-100">
                                <ShieldCheck size={14} />
                                Feedback Received
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {m.role === 'assistant' && (
                      <div className="flex flex-col gap-2">
                        {m.intent && (
                          <div className="flex items-center gap-2">
                            <div className="bg-blue-50 border border-blue-100 p-2 px-3 rounded-xl flex flex-col min-w-[100px]">
                              <span className="text-[10px] font-bold text-blue-400 uppercase tracking-tighter">Intent</span>
                              <span className="text-xs font-bold text-blue-700">{m.intent}</span>
                            </div>
                          </div>
                        )}
                        
                        {(m.genai_duration !== undefined || m.ml_duration !== undefined) && (
                          <div className="flex flex-wrap gap-2 pt-1">
                            <div className="flex items-center gap-1.5 bg-slate-100/50 border border-slate-200 p-1.5 px-3 rounded-lg">
                              <Zap size={12} className="text-amber-500" />
                              <span className="text-[10px] font-bold text-slate-400 uppercase">GenAI:</span>
                              <span className="text-[10px] font-bold text-slate-600">{m.genai_duration?.toFixed(3)}s</span>
                            </div>
                            <div className="flex items-center gap-1.5 bg-slate-100/50 border border-slate-200 p-1.5 px-3 rounded-lg">
                              <Cpu size={12} className="text-blue-500" />
                              <span className="text-[10px] font-bold text-slate-400 uppercase">MLOps:</span>
                              <span className="text-[10px] font-bold text-slate-600">{m.ml_duration?.toFixed(3)}s</span>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {m.role === 'assistant' && m.context && (
                      <div className="mt-1">
                        <button 
                          onClick={() => toggleSources(m.id)}
                          className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-blue-600 transition-colors px-1"
                        >
                          {expandedSources[m.id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          {expandedSources[m.id] 
                            ? `Hide RAG sources (${m.context.split('\n\n---\n\n').length})` 
                            : `View RAG sources (${m.context.split('\n\n---\n\n').length})`}
                        </button>
                        
                        <AnimatePresence>
                          {expandedSources[m.id] && (
                            <motion.div 
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="overflow-hidden"
                            >
                              <div className="mt-2 space-y-2 max-w-lg">
                                {m.context.split('\n\n---\n\n').map((chunk, idx) => (
                                  <div key={idx} className="bg-slate-50 border border-slate-200 p-3 rounded-xl text-xs text-slate-600 leading-relaxed relative">
                                    <div className="absolute top-2 right-2 opacity-30">
                                      <Info size={12} />
                                    </div>
                                    <p className="font-bold text-slate-400 mb-1">Source #{idx + 1}</p>
                                    {chunk.replace('[Source] ', '').trim()}
                                  </div>
                                ))}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          
          {isLoading && (
            <motion.div 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              className="flex justify-start items-center gap-3"
            >
              <div className="w-9 h-9 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-blue-600 shadow-sm">
                <Loader2 className="animate-spin" size={18} />
              </div>
              <div className="bg-white border border-slate-200 p-4 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </motion.div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 md:p-6 bg-white border-t border-slate-200">
          <form 
            onSubmit={handleSend}
            className="max-w-4xl mx-auto relative group"
          >
            <input 
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your question here..."
              disabled={isLoading}
              className="w-full bg-slate-50 border border-slate-200 rounded-2xl p-4 pr-14 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-700 disabled:opacity-50"
            />
            <button 
              type="submit"
              disabled={!input.trim() || isLoading}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 text-white p-2.5 rounded-xl hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-500/20 active:scale-95"
            >
              <Send size={20} />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
