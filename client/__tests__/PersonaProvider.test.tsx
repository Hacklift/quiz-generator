import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import {
  PersonaProvider,
  usePersona,
} from "@features/persona/context/personaContext";

const mockRefreshUser = jest.fn();

let mockRouter = {
  asPath:
    "/generate?persona=lecturer&category=school&topic=Introduction+to+microeconomics",
  pathname: "/generate",
  query: {
    persona: "lecturer",
    category: "school",
    topic: "Introduction to microeconomics",
  },
};

jest.mock("next/router", () => ({
  useRouter: () => mockRouter,
}));

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    refreshUser: mockRefreshUser,
  }),
}));

function PersonaProbe() {
  const { persona, source } = usePersona();
  return (
    <p data-testid="persona-state">
      {persona ? `${persona.category}:${persona.userType}:${source}` : "none"}
    </p>
  );
}

describe("PersonaProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    mockRefreshUser.mockReset();
    mockRouter = {
      asPath:
        "/generate?persona=lecturer&category=school&topic=Introduction+to+microeconomics",
      pathname: "/generate",
      query: {
        persona: "lecturer",
        category: "school",
        topic: "Introduction to microeconomics",
      },
    };
  });

  test("persists guest query persona idempotently", async () => {
    const setItemSpy = jest.spyOn(Storage.prototype, "setItem");

    render(
      <PersonaProvider>
        <PersonaProbe />
      </PersonaProvider>,
    );

    expect(screen.getByTestId("persona-state")).toHaveTextContent(
      "school:lecturer:query",
    );

    await waitFor(() => expect(setItemSpy).toHaveBeenCalledTimes(1));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(setItemSpy).toHaveBeenCalledTimes(1);
    expect(JSON.parse(localStorage.getItem("quizwerk.persona") || "{}")).toEqual(
      {
        category: "school",
        userType: "lecturer",
        topic: "Introduction to microeconomics",
        v: 1,
      },
    );

    setItemSpy.mockRestore();
  });
});
