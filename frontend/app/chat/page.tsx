"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const QUICK_QUESTIONS = [
  "입금했는데 물건이 안 와요",
  "사기꾼을 처벌하고 싶어요",
  "소장 작성 도와주세요",
  "증거로 뭘 모아야 하나요",
];

const DUMMY_RESPONSES: Record<string, string> = {
  "입금했는데 물건이 안 와요":
    "당황스러우시죠. 우선 지금 바로 해야 할 것들을 안내드릴게요.\n\n1. **채팅 내역 전체 캡처** — 상대방이 삭제하기 전에\n2. **입금 내역 캡처** — 은행 앱에서 거래일시, 금액, 수취인\n3. **판매글 캡처** — 삭제되기 전에 URL 포함\n4. **상대방에게 마지막 경고** — \"○일까지 배송 없으면 법적 조치합니다\"\n\n증거를 확보하셨다면, 돈을 돌려받을지(민사소송) 처벌할지(형사고소) 방향을 정할 수 있습니다. 어떤 쪽이 궁금하세요?",
  "사기꾼을 처벌하고 싶어요":
    "사기꾼을 처벌하려면 **형사고소**를 진행해야 합니다.\n\n1. **고소장 작성** — 사기 경위를 시간순으로 정리\n2. **경찰서에 제출** — 등기우편으로 관할 경찰서에 발송 (비용 약 3,000원)\n3. **경찰 수사** — 접수 후 경찰이 수사 진행\n\n50만원 이하 소액이면 경찰이 미뤄둘 수 있는데, 등기우편 고소장은 거부할 수 없으니 이 방법을 추천드려요.\n\n고소장 작성을 도와드릴까요?",
  "소장 작성 도와주세요":
    "민사소장(법원에 내는 피해 신고서) 작성을 도와드릴게요.\n\n📌 서류 자동 작성은 **유료 서비스**입니다. (5,000~10,000원, 변호사 상담료의 1/10)\n\n다음 정보가 필요합니다:\n- **거래 플랫폼** (당근마켓, 중고나라 등)\n- **거래 물품과 금액**\n- **입금 날짜**\n- **상대방 계좌번호**\n- **사기 경위** (언제 연락이 끊겼는지 등)\n\n위 정보를 알려주시면 소장 초안을 작성해드리겠습니다.",
  "증거로 뭘 모아야 하나요":
    "사기 피해 증거는 크게 4가지입니다:\n\n1. **대화 기록** — 거래 채팅 전체 캡처 (가격 합의, 입금 요청 부분 필수)\n2. **송금 내역** — 은행 앱 거래내역 캡처 (날짜, 금액, 수취인 이름)\n3. **판매글** — 상품 게시글 캡처 (삭제되기 전에!)\n4. **연락 시도 기록** — 독촉 메시지, 통화 시도 내역\n\n추가로 더치트(thecheat.co.kr)에서 상대방 닉네임이나 계좌번호를 검색해보세요. 다른 피해자가 이미 신고했을 수 있습니다.\n\n증거 수집이 끝나면 다음 단계를 안내드릴게요.",
};

function getResponse(message: string): string {
  for (const [key, value] of Object.entries(DUMMY_RESPONSES)) {
    if (message.includes(key)) return value;
  }
  return "말씀하신 상황을 확인했습니다. 좀 더 구체적으로 알려주시면 정확한 안내를 드릴 수 있어요.\n\n예를 들어:\n- 피해 금액이 얼마인가요?\n- 어느 플랫폼에서 거래하셨나요?\n- 언제부터 연락이 안 되나요?\n\n이 내용은 일반적인 법률 정보이며, 구체적인 사안에 대해서는 변호사와 상담하시는 것을 권장합니다.";
}

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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = (text: string) => {
    if (!text.trim()) return;

    const userMsg: Message = { role: "user", content: text.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    setTimeout(() => {
      const response = getResponse(text.trim());
      setMessages((prev) => [...prev, { role: "assistant", content: response }]);
      setIsTyping(false);
    }, 800);
  };

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

          {isTyping && (
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
