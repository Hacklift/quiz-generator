import { useTranslation } from "react-i18next";
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
  const { t: uiText } = useTranslation("ui");

  const t = useTerms();

  return (
    <div className="flex h-full flex-col justify-between bg-paper p-4">
      <div className="flex flex-col gap-3">
        <ProfileButton />
        <GenerateQuizButton
          label={uiText("m37a7e45e1b49df1f", { value0: t("quiz") })}
        />
        <SavedQuizzesButton
          label={uiText("mce0983f3577f5ce9", { value0: t("quiz", "plural") })}
        />
        <BrowseByCategoryButton onBrowseClick={onBrowseClick} />
        <PopularQuizzesButton
          label={uiText("m8f69b479b1efca68", { value0: t("quiz", "plural") })}
        />
        <FoldersButton />
        <LiveQuizzesButton label={t("live_quiz", "plural")} />
        <QuizHistoryButton
          label={uiText("m0d6eb040a81b42bb", {
            value0: titleCaseTerm(t("quiz")),
          })}
        />
      </div>

      <div className="mt-10">
        <UpgradePlanButton />
      </div>
    </div>
  );
}
