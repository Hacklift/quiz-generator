import type { GetServerSideProps } from "next";
import LiveQuizAttemptDetailPage from "@features/live-quiz/pages/LiveQuizAttemptDetailPage";

export default LiveQuizAttemptDetailPage;

export const getServerSideProps: GetServerSideProps = async ({ params }) => ({
  props: {
    quizId: String(params?.quizId || ""),
    sessionId: String(params?.sessionId || ""),
  },
});
