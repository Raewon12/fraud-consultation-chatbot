"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const QUICK_QUESTIONS = [
  "입금했는데 물건이 안 와요",
  "사기꾼을 처벌하고 싶어요",
  "소장 작성 도와주세요",
  "증거로 뭘 모아야 하나요",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "안녕하세요, 겟백입니다.\n중고거래 사기 피해 상황을 편하게 말씀해주세요.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isTyping) return;

      const userMsg: Message = { role: "user", content: text.trim() };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsTyping(true);

      // 빈 어시스턴트 메시지 추가 (스트리밍으로 채워나감)
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      try {
        const res = await fetch(`${API_URL}/api/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text.trim(), session_id: sessionId }),
        });

        if (!res.ok) throw new Error(`서버 오류: ${res.status}`);

        const reader = res.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) throw new Error("스트림을 읽을 수 없습니다");

        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // SSE 형식 파싱: "data: {...}\n\n"
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data:")) continue;
            const jsonStr = line.slice(5).trim();
            if (!jsonStr) continue;

            try {
              const data = JSON.parse(jsonStr);
              if (data.done) break;
              if (data.token) {
                // 마지막 메시지(어시스턴트)에 토큰 추가
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  updated[updated.length - 1] = {
                    ...last,
                    content: last.content + data.token,
                  };
                  return updated;
                });
              }
            } catch {
              // JSON 파싱 실패 시 무시
            }
          }
        }
      } catch (err) {
        console.error("채팅 오류:", err);
        // 오류 시 마지막 빈 메시지를 에러 메시지로 교체
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content:
              "죄송합니다, 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
          };
          return updated;
        });
      } finally {
        setIsTyping(false);
      }
    },
    [isTyping, sessionId]
  );

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-slate-200 bg-white">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="text-lg font-bold text-blue-600">
            겟백
          </Link>
          <span className="text-sm text-slate-400">AI 사기 피해 상담</span>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-800"
                }`}
              >
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {msg.content.split(/(\*\*[^*]+\*\*)/).map((part, j) =>
                    part.startsWith("**") && part.endsWith("**") ? (
                      <strong key={j}>{part.slice(2, -2)}</strong>
                    ) : (
                      <span key={j}>{part}</span>
                    )
                  )}
                </div>
              </div>
            </div>
          ))}

          {isTyping && messages[messages.length - 1]?.content === "" && (
            <div className="flex justify-start">
              <div className="bg-slate-100 rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:0.1s]" />
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Quick Questions */}
      {messages.length <= 1 && (
        <div className="flex-shrink-0 border-t border-slate-100 bg-slate-50">
          <div className="max-w-3xl mx-auto px-4 py-3">
            <div className="flex flex-wrap gap-2">
              {QUICK_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(q)}
                  className="text-sm bg-white border border-slate-200 text-slate-700 px-3 py-2 rounded-full hover:border-blue-300 hover:text-blue-600 transition"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="flex-shrink-0 border-t border-slate-200 bg-white">
        <div className="max-w-3xl mx-auto px-4 py-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage(input);
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="사기 피해 상황을 알려주세요..."
              className="flex-1 border border-slate-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="bg-blue-600 text-white px-5 py-3 rounded-xl text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              전송
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
