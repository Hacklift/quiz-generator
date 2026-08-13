import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import {
  PersonaProvider,
  usePersona,
} from "@features/persona/context/personaContext";

const mockRefreshUser = jest.fn();
const mockUpdatePersona = jest.fn(
  async (_persona: unknown, _source?: unknown) => ({}),
);
const guestAuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  refreshUser: mockRefreshUser,
};

let mockAuthState: {
  user: {
    persona_category?: string | null;
    persona_user_type?: string | null;
  } | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  refreshUser: typeof mockRefreshUser;
} = guestAuthState;

let mockRouter: {
  asPath: string;
  pathname: string;
  query: Record<string, string>;
} = {
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
  useAuth: () => mockAuthState,
}));

jest.mock("@features/persona/api/personaApi", () => ({
  updatePersona: (persona: unknown, source: unknown) =>
    mockUpdatePersona(persona, source),
}));

function PersonaProbe() {
  const { persona, source, setPersona, clearPersona } = usePersona();
  return (
    <>
      <p data-testid="persona-state">
        {persona ? `${persona.category}:${persona.userType}:${source}` : "none"}
      </p>
      <button
        type="button"
        onClick={() =>
          void setPersona(
            { category: "school", userType: "lecturer" },
            { source: "inferred" },
          )
        }
      >
        Infer persona
      </button>
      <button type="button" onClick={clearPersona}>
        Clear persona
      </button>
    </>
  );
}

describe("PersonaProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    mockRefreshUser.mockReset();
    mockUpdatePersona.mockClear();
    mockAuthState = guestAuthState;
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

  test("does not leak authenticated profile persona after logout", async () => {
    mockRouter = {
      asPath: "/generate",
      pathname: "/generate",
      query: {},
    };
    mockAuthState = {
      ...guestAuthState,
      user: {
        persona_category: "school",
        persona_user_type: "teacher",
      },
      isAuthenticated: true,
    };

    const { rerender } = render(
      <PersonaProvider>
        <PersonaProbe />
      </PersonaProvider>,
    );

    expect(screen.getByTestId("persona-state")).toHaveTextContent(
      "school:teacher:profile",
    );

    mockAuthState = guestAuthState;
    rerender(
      <PersonaProvider>
        <PersonaProbe />
      </PersonaProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("persona-state")).toHaveTextContent("none"),
    );
    expect(localStorage.getItem("quizwerk.persona")).toBeNull();
  });

  test("clears inferred authenticated override on logout before another user logs in", async () => {
    localStorage.setItem(
      "quizwerk.persona",
      JSON.stringify({
        category: "school",
        userType: "lecturer",
        topic: "Introduction to microeconomics",
        v: 1,
      }),
    );
    mockRouter = {
      asPath: "/generate",
      pathname: "/generate",
      query: {},
    };
    mockAuthState = {
      ...guestAuthState,
      user: {
        persona_category: null,
        persona_user_type: null,
      },
      isAuthenticated: true,
    };

    const { rerender } = render(
      <PersonaProvider>
        <PersonaProbe />
      </PersonaProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("persona-state")).toHaveTextContent(
        "school:lecturer:storage",
      ),
    );

    fireEvent.click(screen.getByRole("button", { name: "Infer persona" }));

    await waitFor(() => expect(mockUpdatePersona).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId("persona-state")).toHaveTextContent(
      "school:lecturer:profile",
    );
    expect(localStorage.getItem("quizwerk.persona")).not.toBeNull();

    mockAuthState = guestAuthState;
    rerender(
      <PersonaProvider>
        <PersonaProbe />
      </PersonaProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("persona-state")).toHaveTextContent(
        "school:lecturer:storage",
      ),
    );

    mockAuthState = {
      ...guestAuthState,
      user: {
        persona_category: "corporate",
        persona_user_type: "hr",
      },
      isAuthenticated: true,
    };
    rerender(
      <PersonaProvider>
        <PersonaProbe />
      </PersonaProvider>,
    );

    expect(screen.getByTestId("persona-state")).toHaveTextContent(
      "corporate:hr:profile",
    );
  });

  test("clearPersona clears local storage and cached stored persona state", async () => {
    localStorage.setItem(
      "quizwerk.persona",
      JSON.stringify({
        category: "corporate",
        userType: "hr",
        topic: "Onboarding checklist",
        v: 1,
      }),
    );
    mockRouter = {
      asPath: "/generate",
      pathname: "/generate",
      query: {},
    };

    render(
      <PersonaProvider>
        <PersonaProbe />
      </PersonaProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("persona-state")).toHaveTextContent(
        "corporate:hr:storage",
      ),
    );

    fireEvent.click(screen.getByRole("button", { name: "Clear persona" }));

    expect(localStorage.getItem("quizwerk.persona")).toBeNull();
    expect(screen.getByTestId("persona-state")).toHaveTextContent("none");
  });

  test("does not rewrite matching stored persona when query has no topic", async () => {
    localStorage.setItem(
      "quizwerk.persona",
      JSON.stringify({
        category: "school",
        userType: "lecturer",
        topic: "Introduction to microeconomics",
        v: 1,
      }),
    );
    mockRouter = {
      asPath: "/generate?persona=lecturer&category=school",
      pathname: "/generate",
      query: {
        persona: "lecturer",
        category: "school",
      },
    };
    const setItemSpy = jest.spyOn(Storage.prototype, "setItem");

    render(
      <PersonaProvider>
        <PersonaProbe />
      </PersonaProvider>,
    );

    expect(screen.getByTestId("persona-state")).toHaveTextContent(
      "school:lecturer:query",
    );

    await waitFor(() =>
      expect(screen.getByTestId("persona-state")).toHaveTextContent(
        "school:lecturer:query",
      ),
    );
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(setItemSpy).not.toHaveBeenCalled();
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
