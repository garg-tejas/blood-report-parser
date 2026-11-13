"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  MessageCircle, Send, Maximize2, Minimize2, X, HeartPulse,
  Bot, User, AlertCircle, RefreshCw, ChevronUp, Loader2
} from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface ChatDrawerProps {
  testData: any
  selectedTest: any
  isOpen?: boolean
  onOpenChange?: (open: boolean) => void
  initialContext?: string
}

const suggestedQuestions = [
  {
    text: "Explain all my abnormal results",
    icon: AlertCircle,
    color: "text-danger bg-danger/10 border-danger/20"
  },
  {
    text: "What lifestyle changes do you recommend?",
    icon: HeartPulse,
    color: "text-warning bg-warning/10 border-warning/20"
  },
  {
    text: "Should I be concerned about anything?",
    icon: AlertCircle,
    color: "text-primary bg-primary/10 border-primary/20"
  },
  {
    text: "Give me a summary of my overall health",
    icon: Bot,
    color: "text-success bg-success/10 border-success/20"
  },
]

export default function ChatDrawer({
  testData,
  selectedTest,
  isOpen: externalIsOpen,
  onOpenChange,
  initialContext
}: ChatDrawerProps) {
  const [internalIsOpen, setInternalIsOpen] = useState(false)
  const [isMaximized, setIsMaximized] = useState(false)
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Use external control if provided, otherwise use internal state
  const isOpen = externalIsOpen !== undefined ? externalIsOpen : internalIsOpen
  const setIsOpen = onOpenChange || setInternalIsOpen

  // Handle initial context from external trigger
  useEffect(() => {
    if (initialContext && isOpen) {
      setInput(initialContext)
      // Focus the input
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [initialContext, isOpen])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Focus input when drawer opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 300)
    }
  }, [isOpen])

  const handleSubmit = async (question?: string) => {
    const messageContent = question || input
    if (!messageContent.trim() || isLoading) return

    const userMessage = { role: "user", content: messageContent }
    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      const context = selectedTest
        ? `Currently viewing: ${selectedTest.name} (${selectedTest.value} ${selectedTest.unit}, Status: ${selectedTest.status})`
        : ""

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: messageContent,
          context: `${context}\n\nAll test data: ${JSON.stringify(testData)}`,
        }),
      })

      if (!response.ok) throw new Error("Failed to get response")

      const data = await response.json()
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }])
    } catch (error) {
      console.error("Chat error:", error)
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I apologize, but I encountered an error. Please try again.",
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearChat = () => {
    setMessages([])
  }

  const drawerHeight = isMaximized ? "100vh" : "75vh"

  return (
    <>
      {/* Floating Button - Only show when closed */}
      <AnimatePresence>
        {!isOpen && (
          <motion.div
            initial={{ y: 100, opacity: 0, scale: 0.8 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 100, opacity: 0, scale: 0.8 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed bottom-6 right-6 z-40"
          >
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setIsOpen(true)}
              className="relative group flex items-center gap-3 px-5 py-3.5 rounded-2xl bg-gradient-to-r from-primary to-accent text-primary-foreground font-medium shadow-2xl glow-primary"
            >
              {/* Glow effect */}
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-primary to-accent opacity-0 group-hover:opacity-50 blur-xl transition-opacity" />

              <div className="relative flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center">
                  <MessageCircle className="w-4 h-4" />
                </div>
                <span className="text-sm">Ask Health Assistant</span>
                <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
              </div>
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Pull-up Tab when closed */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-0 left-1/2 -translate-x-1/2 z-30 px-6 py-2 rounded-t-xl bg-card/80 border border-b-0 border-border backdrop-blur-sm hover:bg-card transition-all group"
          >
            <div className="flex items-center gap-2 text-sm text-muted-foreground group-hover:text-foreground transition-colors">
              <ChevronUp className="w-4 h-4" />
              <span>Health Assistant</span>
            </div>
          </motion.button>
        )}
      </AnimatePresence>

      {/* Expanded Drawer */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop for maximized mode */}
            {isMaximized && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setIsMaximized(false)}
                className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40"
              />
            )}

            <motion.div
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              style={{ height: drawerHeight }}
              className="fixed bottom-0 left-0 right-0 z-50 flex flex-col"
            >
              {/* Glass background */}
              <div className="absolute inset-0 bg-card/95 backdrop-blur-2xl rounded-t-3xl border-t border-border" />

              {/* Content */}
              <div className="relative flex flex-col h-full rounded-t-3xl overflow-hidden">
                {/* Drag handle */}
                <div className="flex justify-center pt-3 pb-1">
                  <div className="w-12 h-1 rounded-full bg-border" />
                </div>

                {/* Header */}
                <div className="flex items-center justify-between px-5 py-3 border-b border-border">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg pulse-life">
                      <MessageCircle className="w-5 h-5 text-primary-foreground" />
                    </div>
                    <div>
                      <h3 className="font-serif font-medium text-foreground">Health Assistant</h3>
                      <p className="text-[10px] text-muted-foreground">Ask about your results</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {messages.length > 0 && (
                      <button
                        onClick={handleClearChat}
                        className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                        title="Clear chat"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => setIsMaximized(!isMaximized)}
                      className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                    >
                      {isMaximized ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => setIsOpen(false)}
                      className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Context Chip */}
                {selectedTest && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mx-5 mt-3"
                  >
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/20">
                      <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                      <span className="text-xs text-muted-foreground">Context:</span>
                      <span className="text-xs text-primary font-medium">{selectedTest.name}</span>
                      <span className="text-xs text-muted-foreground">
                        ({selectedTest.value} {selectedTest.unit})
                      </span>
                    </div>
                  </motion.div>
                )}

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 scrollbar-thin">
                  {messages.length === 0 ? (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="h-full flex flex-col items-center justify-center py-8"
                    >
                      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center mb-4 border border-border pulse-life">
                        <Bot className="w-8 h-8 text-primary" />
                      </div>
                      <h4 className="text-lg font-serif font-medium text-foreground mb-2">How can I help you?</h4>
                      <p className="text-sm text-muted-foreground text-center max-w-sm mb-6">
                        Ask me anything about your blood test results. I&apos;ll provide personalized insights and explanations.
                      </p>

                      {/* Suggested questions */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                        {suggestedQuestions.map((question, idx) => (
                          <motion.button
                            key={idx}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 + idx * 0.05 }}
                            onClick={() => handleSubmit(question.text)}
                            className={`flex items-center gap-2 p-3 rounded-xl border text-left transition-all hover:scale-[1.02] card-interactive ${question.color}`}
                          >
                            <question.icon className="w-4 h-4 flex-shrink-0" />
                            <span className="text-xs font-medium">{question.text}</span>
                          </motion.button>
                        ))}
                      </div>
                    </motion.div>
                  ) : (
                    <>
                      {messages.map((message, idx) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}
                        >
                          {/* Avatar */}
                          <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${message.role === "user"
                            ? "bg-primary/20"
                            : "bg-gradient-to-br from-primary to-accent"
                            }`}>
                            {message.role === "user" ? (
                              <User className="w-4 h-4 text-primary" />
                            ) : (
                              <Bot className="w-4 h-4 text-primary-foreground" />
                            )}
                          </div>

                          {/* Message bubble */}
                          <div
                            className={`max-w-[80%] p-4 rounded-2xl ${message.role === "user"
                              ? "bg-primary/20 border border-primary/30"
                              : "bg-muted/50 border border-border"
                              }`}
                          >
                            {message.role === "assistant" ? (
                              <div className="prose prose-sm max-w-none prose-p:text-foreground/80 prose-headings:text-foreground prose-strong:text-foreground prose-li:text-foreground/80 prose-a:text-primary">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                              </div>
                            ) : (
                              <p className="text-sm text-foreground">{message.content}</p>
                            )}
                          </div>
                        </motion.div>
                      ))}

                      {/* Loading indicator */}
                      {isLoading && (
                        <motion.div
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          className="flex gap-3"
                        >
                          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center flex-shrink-0">
                            <Bot className="w-4 h-4 text-primary-foreground" />
                          </div>
                          <div className="bg-muted/50 border border-border px-5 py-4 rounded-2xl">
                            <div className="flex items-center gap-2">
                              <Loader2 className="w-4 h-4 text-primary animate-spin" />
                              <span className="text-sm text-muted-foreground">Analyzing...</span>
                            </div>
                          </div>
                        </motion.div>
                      )}

                      <div ref={messagesEndRef} />
                    </>
                  )}
                </div>

                {/* Input Area */}
                <div className="p-4 border-t border-border bg-card">
                  <form
                    onSubmit={(e) => {
                      e.preventDefault()
                      handleSubmit()
                    }}
                    className="flex gap-2"
                  >
                    <div className="flex-1 relative">
                      <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about your results..."
                        className="w-full px-4 py-3 pr-12 rounded-xl bg-muted/50 border border-border focus:border-primary/50 focus:ring-2 focus:ring-primary/20 outline-none transition-all text-sm placeholder:text-muted-foreground"
                        disabled={isLoading}
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={!input.trim() || isLoading}
                      className="px-5 py-3 rounded-xl bg-gradient-to-r from-primary to-accent text-primary-foreground font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-all flex items-center gap-2 shadow-lg"
                    >
                      {isLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                      <span className="hidden sm:inline">Send</span>
                    </button>
                  </form>

                  {/* Quick actions when chat has messages */}
                  {messages.length > 0 && (
                    <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border">
                      <span className="text-[10px] text-muted-foreground">Quick:</span>
                      {["Explain more", "What should I do?", "Are there risks?"].map((q, i) => (
                        <button
                          key={i}
                          onClick={() => handleSubmit(q)}
                          disabled={isLoading}
                          className="px-2 py-1 rounded-md bg-muted/50 hover:bg-muted text-[10px] text-muted-foreground hover:text-foreground transition-all disabled:opacity-50 border border-border"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
