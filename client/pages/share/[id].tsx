import { GetServerSideProps } from "next";
import Head from "next/head";
import axios from "axios";
import { DisplaySharedQuiz, Footer, NavBar } from "../../components/home";
import { SharePageProps } from "../../interfaces/props";

export const getServerSideProps: GetServerSideProps = async (context) => {
  const id = context.params?.id as string;

  const API_BASE_URL = process.env.NEXT_PUBLIC_SSR_API_BASE_URL;

  try {
    console.log(API_BASE_URL);
    const res = await axios.get(`${API_BASE_URL}/share/shared-quiz/${id}`);
    const quiz = res.data;

    return {
      props: {
        quiz,
      },
    };
  } catch (err) {
    console.error("Error fetching quiz:", err);
    return {
      notFound: true,
    };
  }
};

export default function SharePage({ quiz }: SharePageProps) {
  const ShareUrl = process.env.SHARE_URL;

  return (
    <>
      <Head>
        <title>{quiz.title}</title>
        <meta property="og:title" content={quiz.title} />
        <meta
          property="og:description"
          content={quiz.description || "Take this quiz to test your knowledge!"}
        />
        <meta property="og:url" content={`${ShareUrl}/share/${quiz.id}`} />
        <meta property="og:type" content="website" />
        <meta property="og:image" content={`${ShareUrl}/quiz-preview.png`} />
        <meta property="og:site_name" content="HQuiz" />
      </Head>
      <div className="flex flex-col min-h-screen bg-gray-100">
        <NavBar />
        <main className="flex-1 flex justify-center px-4 py-8">
          <DisplaySharedQuiz quiz={quiz} />
        </main>
        <Footer />
      </div>
    </>
  );
}
