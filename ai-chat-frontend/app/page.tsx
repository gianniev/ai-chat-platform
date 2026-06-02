"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { HugeiconsIcon } from "@hugeicons/react";
import {
  AiBrain01Icon,
  Delete02Icon,
  Moon02Icon,
  ThumbsDownIcon,
  ThumbsUpIcon,
  MoreHorizontalIcon,
  PencilEdit02Icon,
} from "@hugeicons/core-free-icons";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  feedback?: "up" | "down";
  isStreaming?: boolean;
};

type ChatThread = {
  localId: string;
  title: string;
  messages: ChatMessage[];
};

type ThemeMode = "light" | "dark";

type ThreadMenuState = {
  threadId: string;
  top: number;
  left: number;
};

const STORAGE_KEY = "ai-chat-demo-threads";
const TYPING_SPEED_MS = 18;

const welcomeMessage: ChatMessage = {
  id: "welcome-message",
  role: "assistant",
  content: "Hola, soy tu asistente con Hugging Face. ¿En qué te ayudo?",
};

const newConversationMessage: ChatMessage = {
  id: "new-conversation-message",
  role: "assistant",
  content: "Nueva conversación iniciada. ¿Qué te gustaría hacer?",
};

function createMessageId() {
  return createLocalId();
}

function createLocalId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `thread-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createFallbackThread(title = "Chat 1"): ChatThread {
  return {
    localId: createLocalId(),
    title,
    messages: [welcomeMessage],
  };
}

function isChatMessage(value: unknown): value is ChatMessage {
  if (!value || typeof value !== "object") {
    return false;
  }

  const message = value as Partial<ChatMessage>;
  return (
    (message.role === "user" || message.role === "assistant") &&
    typeof message.content === "string"
  );
}

function parseStoredThreads(value: string | null): ChatThread[] | null {
  if (!value) {
    return null;
  }

  try {
    const parsed = JSON.parse(value) as unknown;
    if (!Array.isArray(parsed)) {
      return null;
    }

    const threads = parsed
      .map((item) => {
        if (!item || typeof item !== "object") {
          return null;
        }

        const candidate = item as Partial<ChatThread>;
        if (
          typeof candidate.localId !== "string" ||
          typeof candidate.title !== "string" ||
          !Array.isArray(candidate.messages)
        ) {
          return null;
        }

        const messages = candidate.messages.filter(isChatMessage).map((message) => ({
          id: typeof message.id === "string" ? message.id : createMessageId(),
          role: message.role,
          content: message.content,
          feedback: message.feedback === "up" || message.feedback === "down" ? message.feedback : undefined,
          isStreaming: false,
        }));
        return {
          localId: candidate.localId,
          title: candidate.title,
          messages: messages.length > 0 ? messages : [newConversationMessage],
        };
      })
      .filter((thread): thread is ChatThread => Boolean(thread));

    return threads.length > 0 ? threads : null;
  } catch {
    return null;
  }
}

export default function HomePage() {
  const firstThreadIdRef = useRef(createLocalId());
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const tokenBuffer = useRef<string[]>([]);
  const typingInterval = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamFinished = useRef(false);

  const [threads, setThreads] = useState<ChatThread[]>([
    {
      localId: firstThreadIdRef.current,
      title: "Chat 1",
      messages: [welcomeMessage],
    },
  ]);
  const [activeThreadId, setActiveThreadId] = useState(firstThreadIdRef.current);
  const [searchTerm, setSearchTerm] = useState("");
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isAwaitingFirstToken, setIsAwaitingFirstToken] = useState(false);
  const [threadMenu, setThreadMenu] = useState<ThreadMenuState | null>(null);
  const [theme, setTheme] = useState<ThemeMode>("dark");
  const [hasLoadedStoredThreads, setHasLoadedStoredThreads] = useState(false);

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("theme-mode");
    if (savedTheme === "light" || savedTheme === "dark") {
      setTheme(savedTheme);
      return;
    }

    setTheme("dark");
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("theme-mode", theme);
  }, [theme]);

  useEffect(() => {
    const storedThreads = parseStoredThreads(window.localStorage.getItem(STORAGE_KEY));
    if (storedThreads) {
      setThreads(storedThreads);
      setActiveThreadId(storedThreads[0].localId);
    }
    setHasLoadedStoredThreads(true);
  }, []);

  useEffect(() => {
    if (!hasLoadedStoredThreads) {
      return;
    }

    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(threads));
  }, [hasLoadedStoredThreads, threads]);

  useEffect(() => {
    return () => {
      if (typingInterval.current) {
        clearInterval(typingInterval.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!threadMenu) {
      return;
    }

    function closeMenu() {
      setThreadMenu(null);
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setThreadMenu(null);
      }
    }

    window.addEventListener("resize", closeMenu);
    window.addEventListener("scroll", closeMenu, true);
    document.addEventListener("click", closeMenu);
    document.addEventListener("keydown", closeOnEscape);

    return () => {
      window.removeEventListener("resize", closeMenu);
      window.removeEventListener("scroll", closeMenu, true);
      document.removeEventListener("click", closeMenu);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [threadMenu]);

  const activeThread = useMemo(
    () => threads.find((thread) => thread.localId === activeThreadId) ?? threads[0],
    [threads, activeThreadId],
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [threads, activeThreadId, isLoading, isAwaitingFirstToken]);

  const filteredThreads = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    if (!q) {
      return threads;
    }
    return threads.filter((thread) => thread.title.toLowerCase().includes(q));
  }, [threads, searchTerm]);

  function selectThread(threadId: string) {
    setActiveThreadId(threadId);
    setThreadMenu(null);
  }

  function applyThreadRemoval(threadId: string) {
    const nextThreads = threads.filter((thread) => thread.localId !== threadId);

    if (nextThreads.length === 0) {
      const fallbackThread = createFallbackThread();
      setThreads([fallbackThread]);
      setActiveThreadId(fallbackThread.localId);
      setInput("");
      return;
    }

    setThreads(nextThreads);
    if (activeThreadId === threadId) {
      setActiveThreadId(nextThreads[0].localId);
      setInput("");
    }
  }

  function resetTypingBuffer() {
    tokenBuffer.current = [];
    streamFinished.current = false;
    if (typingInterval.current) {
      clearInterval(typingInterval.current);
      typingInterval.current = null;
    }
  }

  function startTypingInterval(threadId: string, messageId: string) {
    if (typingInterval.current) {
      return;
    }

    typingInterval.current = setInterval(() => {
      if (tokenBuffer.current.length > 0) {
        const token = tokenBuffer.current.shift() ?? "";
        if (!token) {
          return;
        }

        setThreads((prev) =>
          prev.map((thread) =>
            thread.localId === threadId
              ? {
                  ...thread,
                  messages: thread.messages.map((message) =>
                    message.id === messageId
                      ? { ...message, content: message.content + token }
                      : message,
                  ),
                }
              : thread,
          ),
        );
        return;
      }

      if (streamFinished.current) {
        if (typingInterval.current) {
          clearInterval(typingInterval.current);
          typingInterval.current = null;
        }

        setThreads((prev) =>
          prev.map((thread) =>
            thread.localId === threadId
              ? {
                  ...thread,
                  messages: thread.messages.map((message) =>
                    message.id === messageId ? { ...message, isStreaming: false } : message,
                  ),
                }
              : thread,
          ),
        );
        setIsLoading(false);
      }
    }, TYPING_SPEED_MS);
  }

  async function sendMessage() {
    if (!activeThread) {
      return;
    }

    const text = input.trim();
    if (!text || isLoading) {
      return;
    }

    resetTypingBuffer();

    const threadId = activeThread.localId;
    const currentTitle = activeThread.title;
    const shouldAutoTitle = activeThread.messages.length <= 1 && currentTitle.startsWith("Chat ");
    const nextTitle = shouldAutoTitle ? text.slice(0, 40) || "Nueva conversación" : currentTitle;
    const assistantMessageId = createMessageId();
    const nextHistory: ChatMessage[] = [
      ...activeThread.messages,
      { id: createMessageId(), role: "user", content: text },
    ];

    setInput("");
    setIsLoading(true);
    setIsAwaitingFirstToken(true);

    setThreads((prev) =>
      prev.map((thread) =>
        thread.localId === threadId
          ? {
              ...thread,
              title: nextTitle,
              messages: nextHistory,
            }
          : thread,
      ),
    );

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: text,
          history: nextHistory,
          persist: false,
        }),
      });

      if (!response.ok || !response.body) {
        const data = await response.json().catch(() => null);
        const errorText =
          typeof data?.error === "string" ? data.error : "Error al procesar el mensaje.";
        throw new Error(errorText);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let hasAssistantMessage = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) {
            continue;
          }

          const data = line.slice(6).trim();
          if (!data) {
            continue;
          }

          if (data === "[DONE]") {
            streamFinished.current = true;
            continue;
          }

          const parsed = JSON.parse(data) as { token?: string };
          const token = parsed.token ?? "";
          if (!token) {
            continue;
          }

          tokenBuffer.current.push(token);

          if (!hasAssistantMessage) {
            hasAssistantMessage = true;
            setIsAwaitingFirstToken(false);
            setThreads((prev) =>
              prev.map((thread) =>
                thread.localId === threadId
                  ? {
                      ...thread,
                      messages: [
                        ...thread.messages,
                        {
                          id: assistantMessageId,
                          role: "assistant",
                          content: "",
                          isStreaming: true,
                        },
                      ],
                    }
                  : thread,
              ),
            );
          }

          startTypingInterval(threadId, assistantMessageId);
        }
      }

      if (!hasAssistantMessage) {
        setThreads((prev) =>
          prev.map((thread) =>
            thread.localId === threadId
              ? {
                  ...thread,
                  messages: [
                    ...thread.messages,
                    {
                      id: assistantMessageId,
                      role: "assistant",
                      content: "Sin respuesta",
                      isStreaming: false,
                    },
                  ],
                }
              : thread,
          ),
        );
        setIsLoading(false);
      } else {
        streamFinished.current = true;
        startTypingInterval(threadId, assistantMessageId);
      }
    } catch (error) {
      resetTypingBuffer();
      const message = error instanceof Error ? error.message : "Error de conexión.";

      setThreads((prev) =>
        prev.map((thread) => {
          if (thread.localId !== threadId) {
            return thread;
          }
          return {
            ...thread,
            messages: [
              ...thread.messages,
              { id: createMessageId(), role: "assistant", content: message, isStreaming: false },
            ],
          };
        }),
      );
      setIsLoading(false);
    } finally {
      setIsAwaitingFirstToken(false);
    }
  }

  function createNewConversation() {
    const newThread: ChatThread = {
      localId: createLocalId(),
      title: `Chat ${threads.length + 1}`,
      messages: [newConversationMessage],
    };

    setThreads((prev) => [newThread, ...prev]);
    setActiveThreadId(newThread.localId);
    setThreadMenu(null);
    setInput("");
  }

  function renameThread(thread: ChatThread) {
    const nextTitle = window.prompt("Nuevo nombre del chat", thread.title)?.trim();

    if (!nextTitle) {
      setThreadMenu(null);
      return;
    }

    setThreads((prev) =>
      prev.map((item) =>
        item.localId === thread.localId ? { ...item, title: nextTitle } : item,
      ),
    );
    setThreadMenu(null);
  }

  function deleteThread(thread: ChatThread) {
    setThreadMenu(null);
    applyThreadRemoval(thread.localId);
  }

  async function sendFeedback(threadId: string, messageId: string, rating: "up" | "down") {
    setThreads((prev) =>
      prev.map((thread) =>
        thread.localId === threadId
          ? {
              ...thread,
              messages: thread.messages.map((message) =>
                message.id === messageId ? { ...message, feedback: rating } : message,
              ),
            }
          : thread,
      ),
    );

    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          rating,
          client_message_id: messageId,
          client_thread_id: threadId,
          model: "meta-llama/Llama-3.1-8B-Instruct",
        }),
      });
    } catch {
      // Feedback is best-effort; local UI state stays useful even if analytics is down.
    }
  }

  function toggleTheme() {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }

  return (
    <main className="appShell">
      <div className="layout">
        <aside className="sidebar">
          <div className="sidebarTop">
            <div className="brandBlock">
              <div className="brandMark" aria-hidden="true">
                <HugeiconsIcon icon={AiBrain01Icon} size={22} strokeWidth={1.8} />
              </div>
              <div className="brandCopy">
                <h1 className="brandTitle">AI Chat</h1>
                <span className="brandSignature">by Gianni Etcheverry</span>
              </div>
            </div>
            <h2 className="sidebarTitle">Chats</h2>
            <button type="button" className="secondaryButton fullWidth" onClick={createNewConversation}>
              Crear chat
            </button>
            <input
              className="searchInput"
              placeholder="Buscar chat..."
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </div>

          <div className="threadList">
            {filteredThreads.map((thread) => {
              const isActive = thread.localId === activeThread?.localId;
              const isMenuOpen = threadMenu?.threadId === thread.localId;

              return (
                <div
                  key={thread.localId}
                  className={`threadItem ${isActive ? "threadItemActive" : ""}`}
                >
                  <button
                    type="button"
                    className="threadMainButton"
                    onClick={() => selectThread(thread.localId)}
                  >
                    <span className="threadTitle">{thread.title}</span>
                    <span className="threadMeta">Local</span>
                  </button>
                  <div className="threadMenuWrap">
                    <button
                      type="button"
                      className="threadMenuButton"
                      aria-label={`Opciones de ${thread.title}`}
                      aria-expanded={isMenuOpen}
                      onClick={(event) => {
                        event.stopPropagation();
                        const rect = event.currentTarget.getBoundingClientRect();
                        const sidebarRect = event.currentTarget
                          .closest(".sidebar")
                          ?.getBoundingClientRect();
                        const menuWidth = 214;
                        const menuHeight = 100;
                        const outsideSidebarLeft = (sidebarRect?.right ?? rect.right) + 10;
                        const hasRoomOutside = outsideSidebarLeft + menuWidth <= window.innerWidth - 12;
                        const left = hasRoomOutside
                          ? outsideSidebarLeft
                          : Math.max(12, rect.left - menuWidth - 10);
                        const top = Math.min(rect.top - 8, window.innerHeight - menuHeight - 12);

                        setThreadMenu((current) =>
                          current?.threadId === thread.localId
                            ? null
                            : {
                                threadId: thread.localId,
                                top: Math.max(12, top),
                                left,
                              },
                        );
                      }}
                    >
                      <HugeiconsIcon icon={MoreHorizontalIcon} size={18} strokeWidth={1.9} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </aside>

        {threadMenu ? (() => {
          const menuThread = threads.find((thread) => thread.localId === threadMenu.threadId);

          if (!menuThread) {
            return null;
          }

          return (
            <div
              className="threadMenuPopover"
              role="menu"
              style={{ top: threadMenu.top, left: threadMenu.left }}
              onClick={(event) => event.stopPropagation()}
            >
              <button type="button" role="menuitem" onClick={() => renameThread(menuThread)}>
                <HugeiconsIcon icon={PencilEdit02Icon} size={17} strokeWidth={1.8} />
                <span>Cambiar nombre</span>
              </button>
              <button
                type="button"
                role="menuitem"
                className="dangerMenuItem"
                onClick={() => deleteThread(menuThread)}
              >
                <HugeiconsIcon icon={Delete02Icon} size={17} strokeWidth={1.8} />
                <span>Eliminar chat</span>
              </button>
            </div>
          );
        })() : null}

        <section className="chatPanel">
          <header className="header">
            <div className="headerBrand">
              <span>AI Chat Platform · Hugging Face + FastAPI</span>
              <span className="headerSignature">by Gianni Etcheverry</span>
            </div>
            <div className="headerActions">
              <button
                type="button"
                className="themeButton"
                onClick={toggleTheme}
                aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
                title={theme === "dark" ? "Modo claro" : "Modo oscuro"}
              >
                <HugeiconsIcon icon={Moon02Icon} size={18} strokeWidth={1.8} />
              </button>
            </div>
          </header>

          <section className="messages">
            {activeThread?.messages.map((msg, index) => (
              <div
                key={msg.id || `${msg.role}-${index}`}
                className={`messageGroup ${msg.role === "user" ? "userGroup" : "assistantGroup"}`}
              >
                <div className={`bubble ${msg.role === "user" ? "user" : "assistant"}`}>
                  {msg.content}
                </div>
                {msg.role === "assistant" && activeThread && !msg.isStreaming ? (
                  <div className="feedbackActions" aria-label="Feedback de la respuesta">
                    <button
                      type="button"
                      className={msg.feedback === "up" ? "feedbackButton feedbackButtonActive" : "feedbackButton"}
                      aria-label="Respuesta util"
                      title="Respuesta util"
                      onClick={() => void sendFeedback(activeThread.localId, msg.id, "up")}
                    >
                      <HugeiconsIcon icon={ThumbsUpIcon} size={15} strokeWidth={1.8} />
                    </button>
                    <button
                      type="button"
                      className={msg.feedback === "down" ? "feedbackButton feedbackButtonActive" : "feedbackButton"}
                      aria-label="Respuesta no util"
                      title="Respuesta no util"
                      onClick={() => void sendFeedback(activeThread.localId, msg.id, "down")}
                    >
                      <HugeiconsIcon icon={ThumbsDownIcon} size={15} strokeWidth={1.8} />
                    </button>
                  </div>
                ) : null}
              </div>
            ))}
            {isAwaitingFirstToken ? (
              <div className="messageGroup assistantGroup" aria-live="polite">
                <div className="processingBadge">
                  <span className="processingSpinner" aria-hidden="true" />
                  Procesando
                </div>
              </div>
            ) : null}
            <div ref={messagesEndRef} />
          </section>

          <section className="inputArea">
            <textarea
              className="input"
              placeholder="Escribe tu mensaje..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
              disabled={isLoading}
            />

            <button
              className="button"
              onClick={() => void sendMessage()}
              disabled={isLoading || !input.trim()}
            >
              {isLoading ? "Enviando..." : "Enviar"}
            </button>
          </section>
        </section>
      </div>
    </main>
  );
}
