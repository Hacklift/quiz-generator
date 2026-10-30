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
import { Users } from "lucide-react";
import { ROUTES } from "@shared/config/patterns/routes";
import SidebarButton from "./sidebar/SidebarButton";

interface SidebarProps {
  onBrowseClick: () => void;
}

export default function Sidebar({ onBrowseClick }: SidebarProps) {
  const t = useTerms();

  return (
    <div className="flex min-h-full flex-col gap-8 bg-paper p-4">
      <div className="flex shrink-0 flex-col gap-3">
        <ProfileButton />
        <GenerateQuizButton label={`Create ${t("quiz")}`} />
        <SavedQuizzesButton label={`Saved ${t("quiz", "plural")}`} />
        <BrowseByCategoryButton onBrowseClick={onBrowseClick} />
        <PopularQuizzesButton label={`Popular ${t("quiz", "plural")}`} />
        <FoldersButton />
        <SidebarButton
          href={ROUTES.COHORTS}
          icon={<Users aria-hidden="true" size={20} />}
          label={`${titleCaseTerm(t("group", "plural"))} & assignments`}
        />
        <LiveQuizzesButton label={t("live_quiz", "plural")} />
        <QuizHistoryButton label={`${titleCaseTerm(t("quiz"))} history`} />
      </div>

      <div className="mt-auto shrink-0">
        <UpgradePlanButton />
      </div>
    </div>
  );
}
