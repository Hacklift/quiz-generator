import { GetServerSideProps } from "next";
import TrainingRunDetailPage from "@features/training/pages/TrainingRunDetailPage";

export const getServerSideProps: GetServerSideProps<{ runId: string }> = async ({ params }) => ({
  props: { runId: String(params?.runId || "") },
});

export default TrainingRunDetailPage;
