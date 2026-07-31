import GenerateQuizButton from "./sidebar/GenerateQuizButton";
import SavedQuizzesButton from "./sidebar/SavedQuizzesButton";
import BrowseByCategoryButton from "./sidebar/BrowseByCategoryButton";
import PopularQuizzesButton from "./sidebar/PopularQuizzesButton";
import FoldersButton from "./sidebar/FoldersButton";
import UpgradePlanButton from "./sidebar/UpgradePlanButton";
import QuizHistoryButton from "./sidebar/QuizHistoryButton";
import ProfileButton from "./sidebar/ProfileButton";
import LiveQuizzesButton from "./sidebar/LiveQuizzesButton";

interface SidebarProps {
  onBrowseClick: () => void;
}

export default function Sidebar({ onBrowseClick }: SidebarProps) {
  return (
    <div className="flex h-full flex-col justify-between bg-paper p-4">
      <div className="flex flex-col gap-3">
        <ProfileButton />
        <GenerateQuizButton />
        <SavedQuizzesButton />
        <BrowseByCategoryButton onBrowseClick={onBrowseClick} />
        <PopularQuizzesButton />
        <FoldersButton />
        <LiveQuizzesButton />
        <QuizHistoryButton />
      </div>

      <div className="mt-10">
        <UpgradePlanButton />
      </div>
    </div>
  );
}
