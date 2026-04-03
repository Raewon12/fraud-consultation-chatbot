import Link from "next/link";

function Navbar() {
  return (
    <nav className="fixed top-0 w-full bg-white/80 backdrop-blur-sm border-b border-slate-100 z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <span className="text-xl font-bold text-blue-600">겟백</span>
        <div className="flex items-center gap-6">
          <Link href="/guide" className="text-sm text-slate-600 hover:text-slate-900">가이드</Link>
          <Link href="/chat" className="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700 transition">
            무료 상담
          </Link>
        </div>
      </div>
    </nav>
  );
}

function Hero() {
  return (
    <section className="pt-32 pb-20 px-6">
      <div className="max-w-3xl mx-auto text-center">
        <h1 className="text-4xl md:text-5xl font-bold leading-tight tracking-tight text-slate-900">
          돈 보냈는데 물건이 안 오고,<br />
          <span className="text-blue-600">연락도 안 되나요?</span>
        </h1>
        <p className="mt-6 text-lg text-slate-600 leading-relaxed">
          중고거래 입금 후 잠적 사기,<br />
          증거 수집부터 소장 작성까지 AI가 도와드립니다.
        </p>
        <div className="mt-10">
          <Link
            href="/chat"
            className="inline-block bg-blue-600 text-white text-lg font-medium px-8 py-4 rounded-xl hover:bg-blue-700 transition shadow-lg shadow-blue-600/25"
          >
            지금 무료 상담 시작하기
          </Link>
        </div>
      </div>
    </section>
  );
}

function Problem() {
  const problems = [
    {
      emoji: "😰",
      text: '"내일 보내드릴게요" 하더니 연락이 끊겼어요',
    },
    {
      emoji: "🚫",
      text: '경찰서에서 "민사로 하세요" 하고 돌려보냈어요',
    },
    {
      emoji: "😵",
      text: "소장이 뭔지, 고소장이 뭔지 모르겠어요",
    },
    {
      emoji: "💸",
      text: "변호사 상담료가 피해금액보다 비싸요",
    },
  ];

  return (
    <section className="py-20 px-6 bg-slate-50">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-3xl font-bold text-center text-slate-900">
          입금하고 며칠 기다렸는데, 읽씹당하고 있나요?
        </h2>
        <div className="mt-12 grid gap-4">
          {problems.map((p, i) => (
            <div
              key={i}
              className="flex items-center gap-4 bg-white p-5 rounded-xl border border-slate-200"
            >
              <span className="text-2xl">{p.emoji}</span>
              <span className="text-slate-700">{p.text}</span>
            </div>
          ))}
        </div>
        <p className="mt-8 text-center text-slate-500">
          결국 대부분 포기합니다.
        </p>
      </div>
    </section>
  );
}

function Solution() {
  const steps = [
    {
      icon: "📋",
      title: "증거 수집",
      desc: "뭘 캡처하고 뭘 저장해야 하는지 체크리스트로 알려드립니다",
    },
    {
      icon: "🧭",
      title: "방향 판단",
      desc: "돈을 돌려받을지, 처벌할지, 둘 다 할지 상황에 맞는 루트를 안내합니다",
    },
    {
      icon: "📝",
      title: "서식 작성",
      desc: "소장, 고소장, 내용증명을 대화만으로 자동 작성합니다",
    },
    {
      icon: "📮",
      title: "제출 안내",
      desc: "어디에, 어떻게 제출하는지 비용까지 알려드립니다",
    },
  ];

  return (
    <section className="py-20 px-6">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-center text-slate-900">
          겟백이 도와드리는 것
        </h2>
        <p className="mt-3 text-center text-slate-500">
          사기 피해자가 직접 대응할 수 있게
        </p>
        <div className="mt-12 grid md:grid-cols-2 gap-6">
          {steps.map((s, i) => (
            <div
              key={i}
              className="p-6 rounded-2xl border border-slate-200 hover:border-blue-200 hover:shadow-sm transition"
            >
              <span className="text-3xl">{s.icon}</span>
              <h3 className="mt-4 text-lg font-semibold text-slate-900">{s.title}</h3>
              <p className="mt-2 text-slate-600 leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    { num: "1", text: "사기 상황을 채팅으로 알려주세요" },
    { num: "2", text: "AI가 증거 수집 → 루트 판단 → 다음 행동을 안내합니다" },
    { num: "3", text: "필요한 서류는 대화 내용으로 자동 작성됩니다" },
  ];

  return (
    <section className="py-20 px-6 bg-slate-50">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-3xl font-bold text-center text-slate-900">
          이렇게 진행됩니다
        </h2>
        <div className="mt-12 flex flex-col gap-8">
          {steps.map((s, i) => (
            <div key={i} className="flex items-start gap-5">
              <div className="flex-shrink-0 w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
                {s.num}
              </div>
              <p className="text-lg text-slate-700 pt-1.5">{s.text}</p>
            </div>
          ))}
        </div>
        <div className="mt-12 text-center">
          <Link
            href="/chat"
            className="inline-block bg-blue-600 text-white font-medium px-8 py-4 rounded-xl hover:bg-blue-700 transition"
          >
            무료 상담 시작하기
          </Link>
        </div>
      </div>
    </section>
  );
}

function Stats() {
  const stats = [
    { value: "100+", label: "법률 데이터 분석" },
    { value: "5종", label: "서식 자동 작성" },
    { value: "2분", label: "평균 첫 답변" },
  ];

  return (
    <section className="py-16 px-6">
      <div className="max-w-4xl mx-auto grid grid-cols-3 gap-8">
        {stats.map((s, i) => (
          <div key={i} className="text-center">
            <div className="text-3xl font-bold text-blue-600">{s.value}</div>
            <div className="mt-1 text-sm text-slate-500">{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Reviews() {
  const reviews = [
    {
      stars: 5,
      text: "경찰서에서 돌려보내서 막막했는데, 소장 작성까지 도와줘서 실제로 제출했어요",
      meta: "50만원 피해 / 서식작성 도움",
    },
    {
      stars: 4,
      text: "어떤 증거를 모아야 하는지 바로 알 수 있어서 좋았어요",
      meta: "30만원 피해 / 증거수집 도움",
    },
    {
      stars: 5,
      text: "변호사 가기 전에 여기서 먼저 상담받길 잘했어요. 혼자서도 할 수 있겠더라고요",
      meta: "80만원 피해 / 방향판단 도움",
    },
  ];

  return (
    <section className="py-20 px-6 bg-slate-50">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-center text-slate-900">
          이용 후기
        </h2>
        <div className="mt-12 grid md:grid-cols-3 gap-6">
          {reviews.map((r, i) => (
            <div key={i} className="bg-white p-6 rounded-2xl border border-slate-200">
              <div className="text-amber-400">
                {"★".repeat(r.stars)}{"☆".repeat(5 - r.stars)}
              </div>
              <p className="mt-3 text-slate-700 leading-relaxed">&ldquo;{r.text}&rdquo;</p>
              <p className="mt-4 text-sm text-slate-400">{r.meta}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FAQ() {
  const faqs = [
    {
      q: "상담은 무료인가요?",
      a: "상담과 가이드는 무료입니다. 서식 자동 작성은 유료입니다.",
    },
    {
      q: "법적 효력이 있나요?",
      a: "AI가 작성한 초안입니다. 중요한 사안은 변호사 검토를 권장합니다.",
    },
    {
      q: "내 개인정보는 안전한가요?",
      a: "대화 내용은 저장하지 않습니다.",
    },
    {
      q: "소액(10만원 이하)도 되나요?",
      a: "됩니다. 금액별 현실적인 방법을 안내합니다.",
    },
  ];

  return (
    <section className="py-20 px-6">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-3xl font-bold text-center text-slate-900">
          자주 묻는 질문
        </h2>
        <div className="mt-12 flex flex-col gap-4">
          {faqs.map((f, i) => (
            <div key={i} className="border border-slate-200 rounded-xl p-5">
              <h3 className="font-semibold text-slate-900">{f.q}</h3>
              <p className="mt-2 text-slate-600">{f.a}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCTA() {
  return (
    <section className="py-20 px-6 bg-blue-600">
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-3xl font-bold text-white">
          사기당한 돈, 아직 돌려받을 수 있습니다.
        </h2>
        <div className="mt-8">
          <Link
            href="/chat"
            className="inline-block bg-white text-blue-600 text-lg font-medium px-8 py-4 rounded-xl hover:bg-blue-50 transition"
          >
            무료 상담 시작하기
          </Link>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="py-10 px-6 border-t border-slate-100">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <span className="text-sm text-slate-400">
          겟백은 법률 조언이 아닌 법률 정보를 제공합니다.
        </span>
        <span className="text-sm text-slate-400">
          &copy; 2026 겟백 (GetBack)
        </span>
      </div>
    </footer>
  );
}

export default function Home() {
  return (
    <>
      <Navbar />
      <Hero />
      <Problem />
      <Solution />
      <HowItWorks />
      <Stats />
      <Reviews />
      <FAQ />
      <FinalCTA />
      <Footer />
    </>
  );
}
