import GenerateQuizButton from "./sidebar/GenerateQuizButton";
import SavedQuizzesButton from "./sidebar/SavedQuizzesButton";
import BrowseByCategoryButton from "./sidebar/BrowseByCategoryButton";
import PopularQuizzesButton from "./sidebar/PopularQuizzesButton";
import FoldersButton from "./sidebar/FoldersButton";
import UpgradePlanButton from "./sidebar/UpgradePlanButton";
import QuizHistoryButton from "./sidebar/QuizHistoryButton";
import ProfileButton from "./sidebar/ProfileButton";
import LiveQuizzesButton from "./sidebar/LiveQuizzesButton";
import { useTerms } from "@features/persona/hooks/useTerms";
import { titleCaseTerm } from "@shared/config/terminology";

interface SidebarProps {
  onBrowseClick: () => void;
}

export default function Sidebar({ onBrowseClick }: SidebarProps) {
  const t = useTerms();

  return (
    <div className="flex h-full flex-col justify-between bg-paper p-4">
      <div className="flex flex-col gap-3">
        <ProfileButton />
        <GenerateQuizButton label={`Create ${t("quiz")}`} />
        <SavedQuizzesButton label={`Saved ${t("quiz", "plural")}`} />
        <BrowseByCategoryButton onBrowseClick={onBrowseClick} />
        <PopularQuizzesButton label={`Popular ${t("quiz", "plural")}`} />
        <FoldersButton />
        <LiveQuizzesButton label={t("live_quiz", "plural")} />
        <QuizHistoryButton label={`${titleCaseTerm(t("quiz"))} history`} />
      </div>

      <div className="mt-10">
        <UpgradePlanButton />
      </div>
    </div>
  );
}
