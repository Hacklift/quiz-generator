import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { createLocaleI18n } from "@features/locale/i18n";
import PersonaBadge from "@features/persona/components/PersonaBadge";
import PersonaPicker from "@features/persona/components/PersonaPicker";
import {
  PersonaProvider,
  usePersona,
} from "@features/persona/context/personaContext";
import { useTerms } from "@features/persona/hooks/useTerms";

jest.mock("next/router", () => ({
  useRouter: () => ({ query: {}, pathname: "/dashboard" }),
}));
jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({ user: null, isAuthenticated: false, isLoading: false }),
}));

function PersonaProbe() {
  const { definition, persona } = usePersona();
  const term = useTerms();
  return (
    <p data-testid="selection">
      {persona?.userType}|{definition?.label}|{term("assignment")}
    </p>
  );
}

beforeEach(() => localStorage.clear());

test.each([
  ["es", "Madre o padre", "serie de ejercicios"],
  ["fr", "Parent", "série d’exercices"],
] as const)(
  "choosing a %s role keeps its machine ID and uses its localized terms",
  async (locale, label, assignment) => {
    const instance = createLocaleI18n();
    await instance.changeLanguage(locale);
    const onPicked = jest.fn();
    render(
      <I18nextProvider i18n={instance}>
        <PersonaProvider>
          <PersonaPicker initialCategory="school" onPicked={onPicked} />
          <PersonaProbe />
        </PersonaProvider>
      </I18nextProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: new RegExp(label) }));
    });
    expect(onPicked).toHaveBeenCalledWith({
      category: "school",
      userType: "parent",
    });
    expect(screen.getByTestId("selection")).toHaveTextContent(
      `parent|${label}|${assignment}`,
    );
  },
);

test("switching languages updates the badge and plural without affecting other instances", async () => {
  const first = createLocaleI18n();
  const second = createLocaleI18n();
  render(
    <>
      <I18nextProvider i18n={first}>
        <PersonaBadge
          userType="teacher"
          appliedDefaults={{
            audienceType: "students",
            questionType: "multichoice",
            numQuestions: 1,
            difficultyLevel: "easy",
          }}
        />
      </I18nextProvider>
      <I18nextProvider i18n={second}>
        <PersonaBadge userType="parent" />
      </I18nextProvider>
    </>,
  );
  await act(async () => {
    await first.changeLanguage("es");
  });
  expect(screen.getByText("Configurado para: Docente")).toBeInTheDocument();
  expect(screen.getByText("pregunta")).toBeInTheDocument();
  expect(screen.getByText("Set up for: Parent")).toBeInTheDocument();
  await act(async () => {
    await first.changeLanguage("fr");
  });
  expect(screen.getByText("Configuré pour : Enseignant")).toBeInTheDocument();
  expect(screen.getByText("Facile")).toBeInTheDocument();
  expect(screen.getByText("Set up for: Parent")).toBeInTheDocument();
});
