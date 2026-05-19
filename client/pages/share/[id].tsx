import { GetServerSideProps } from "next";
import Head from "next/head";
import axios from "axios";
import { useEffect } from "react";
import { useRouter } from "next/router";
import { DisplaySharedQuiz, Footer, NavBar } from "../../components/home";
import { SharePageProps } from "../../interfaces/props";

export const getServerSideProps: GetServerSideProps = async (context) => {
  const id = context.params?.id as string;

  const API_BASE_URL = process.env.NEXT_PUBLIC_SSR_API_BASE_URL;

  try {
    const res = await axios.get(`${API_BASE_URL}/share/shared-quiz/${id}`);
    const quiz = res.data;

    return {
      props: {
        quiz,
        notFoundQuiz: false,
      },
    };
  } catch (err) {
    console.error("Error fetching quiz:", err);
    context.res.statusCode = 404;
    return {
      props: {
        quiz: null,
        notFoundQuiz: true,
      },
    };
  }
};

function SharedQuizMissingState() {
  const router = useRouter();

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      router.replace("/");
    }, 2500);

    return () => window.clearTimeout(timeout);
  }, [router]);

  return (
    <div className="mx-auto flex min-h-[50vh] max-w-xl flex-col items-center justify-center rounded-2xl bg-white px-6 py-10 text-center shadow-sm">
      <h1 className="mb-3 text-2xl font-semibold text-[#0F2654]">
        Quiz not found
      </h1>
      <p className="text-gray-600">
        This shared quiz link is invalid or no longer available. Redirecting to
        the home page.
      </p>
    </div>
  );
}

export default function SharePage({ quiz, notFoundQuiz }: SharePageProps) {
  const ShareUrl = process.env.SHARE_URL;

  return (
    <>
      <Head>
        <title>{quiz?.title || "Quiz not found"}</title>
        <meta property="og:title" content={quiz?.title || "Quiz not found"} />
        <meta
          property="og:description"
          content={
            quiz?.description || "This shared quiz is invalid or unavailable."
          }
        />
        <meta
          property="og:url"
          content={`${ShareUrl}/share/${quiz?.id || ""}`}
        />
        <meta property="og:type" content="website" />
        <meta property="og:image" content={`${ShareUrl}/quiz-preview.png`} />
        <meta property="og:site_name" content="HQuiz" />
      </Head>
      <div className="flex flex-col min-h-screen bg-gray-100">
        <NavBar />
        <main className="flex-1 flex justify-center px-4 py-8">
          {notFoundQuiz ? (
            <SharedQuizMissingState />
          ) : (
            <DisplaySharedQuiz quiz={quiz} />
          )}
        </main>
        <Footer />
      </div>
    </>
  );
}
