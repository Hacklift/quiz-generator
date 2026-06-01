import React from "react";
import NavBar from "../components/home/NavBar";
import Footer from "../components/home/Footer";

export default function Company() {
  const [openFaq, setOpenFaq] = React.useState<number | null>(null);

  const toggleFaq = (index: number) => {
    setOpenFaq(openFaq === index ? null : index);
  };

  return (
    <div className="flex flex-col min-h-screen">
      <NavBar />
      <main className="flex-grow">
        {/* Hero Section */}
        <section className="text-center py-16 px-4 max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            Empowering everyone to <span className="text-[#0F2654]">teach online</span>
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Launched in 2024, QuizGen is an AI-powered quiz generation platform 
            with a mission to empower everyone to create engaging quizzes instantly.
          </p>
        </section>

        {/* Stats Grid */}
        <section className="py-12 px-4 max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-3xl md:text-4xl font-bold text-[#0F2654]">2024</div>
              <div className="text-gray-500 mt-1">Launched</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-[#0F2654]">5k+</div>
              <div className="text-gray-500 mt-1">Users</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-[#0F2654]">100+</div>
              <div className="text-gray-500 mt-1">Schools</div>
            </div>
            <div>
              <div className="text-3xl md:text-4xl font-bold text-[#0F2654]">10</div>
              <div className="text-gray-500 mt-1">Countries</div>
            </div>
          </div>
        </section>

        {/* Vision Section */}
        <section className="py-16 px-4 bg-gray-50">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold text-center text-gray-900 mb-8">
              We look forward to a future where learning is even more
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
              {["Fun", "Collaborative", "Borderless", "Community-driven"].map((item) => (
                <div key={item} className="flex items-center justify-center p-4">
                  <span className="text-lg text-gray-700">✓ {item}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ Section with Accordion */}
        <section className="py-16 px-4 max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Frequently asked questions
          </h2>
          <div className="space-y-4">
            {[
              {
                q: "Who can use QuizGen?",
                a: "QuizGen is designed for educators, students, content creators, and anyone who wants to create quizzes quickly using AI."
              },
              {
                q: "How do I generate a quiz?",
                a: "Simply enter a topic, select difficulty level, number of questions, and click Generate. Your AI-powered quiz will be ready in seconds."
              },
              {
                q: "Can I share quizzes with students?",
                a: "Yes! You can share quizzes via a unique link, email, or access code for live quiz sessions."
              },
              {
                q: "Is there a free plan?",
                a: "Yes, we offer a free plan with basic features. Pro plans unlock advanced AI models, unlimited quizzes, and analytics."
              },
              {
                q: "How accurate are the AI-generated questions?",
                a: "Our AI uses OpenAI and other models trained on educational content. Accuracy is high, but we recommend reviewing generated quizzes."
              }
            ].map((faq, index) => (
              <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleFaq(index)}
                  className="w-full text-left px-6 py-4 font-medium text-gray-900 hover:bg-gray-50 flex justify-between items-center"
                >
                  <span>{faq.q}</span>
                  <span className="text-[#0F2654] text-xl">
                    {openFaq === index ? "−" : "+"}
                  </span>
                </button>
                {openFaq === index && (
                  <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
                    <p className="text-gray-600">{faq.a}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}