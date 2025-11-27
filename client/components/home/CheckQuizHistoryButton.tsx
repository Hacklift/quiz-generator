import { useRouter } from "next/navigation";

export default function CheckQuizHistoryButton() {
  const router = useRouter();
  const handleCheckQuizHistory = () => {
    const userId = "userId";
    const queryParams = new URLSearchParams({
      userId,
    }).toString();

    router.push(`/quiz_history?${queryParams}`);
  };

  return (
    <button
      onClick={handleCheckQuizHistory}
      type="button"
      className="bg-blue-500 text-white font-bold px-4 py-2 rounded hover:bg-blue-600 focus:outline-none focus:ring focus:ring-blue-300"
    >
      Check quiz history
    </button>
  );
}
