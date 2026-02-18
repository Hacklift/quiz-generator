import GenerateQuizButton from "./sidebar/GenerateQuizButton";
import SavedQuizzesButton from "./sidebar/SavedQuizzesButton";
import BrowseByCategoryButton from "./sidebar/BrowseByCategoryButton";
import PopularQuizzesButton from "./sidebar/PopularQuizzesButton";
import FoldersButton from "./sidebar/FoldersButton";
import UpgradePlanButton from "./sidebar/UpgradePlanButton";
import QuizHistoryButton from "./sidebar/QuizHistoryButton";
import ProfileButton from "./sidebar/ProfileButton";

interface SidebarProps {
  onBrowseClick: () => void;
}

export default function Sidebar({ onBrowseClick }: SidebarProps) {
  return (
    <div className="flex flex-col justify-between h-full p-4 bg-[#f2f2f2]">
      <div className="flex flex-col gap-3">
        <ProfileButton />
        <GenerateQuizButton />
        <SavedQuizzesButton />
        <BrowseByCategoryButton onBrowseClick={onBrowseClick} />
        <PopularQuizzesButton />
        <FoldersButton />
        <QuizHistoryButton />
      </div>

      <div className="mt-10">
        <UpgradePlanButton />
      </div>
    </div>
  );
}
