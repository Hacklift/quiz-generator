import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import {
  PersonaProvider,
  usePersona,
} from "@features/persona/context/personaContext";
import { updatePersona } from "@features/persona/api/personaApi";

const authState: {
  user: any;
  isAuthenticated: boolean;
  isLoading: boolean;
  refreshUser: jest.Mock;
} = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  refreshUser: jest.fn(),
};

jest.mock("next/router", () => ({
  useRouter: () => ({ query: {} }),
}));

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => authState,
}));

jest.mock("@features/persona/api/personaApi", () => ({
  updatePersona: jest.fn(),
}));

function Probe() {
  const { persona, source, isLoading, setPersona } = usePersona();
  return (
    <>
      <output data-testid="persona">
        {persona ? `${persona.category}:${persona.userType}:${source}` : "none"}
      </output>
      <output data-testid="loading">{String(isLoading)}</output>
      <button
        type="button"
        onClick={() => {
          void setPersona({ category: "school", userType: "teacher" }).catch(
            () => undefined,
          );
        }}
      >
        Set teacher
      </button>
    </>
  );
}

function renderProvider() {
  return render(
    <PersonaProvider>
      <Probe />
    </PersonaProvider>,
  );
}

describe("PersonaProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    authState.user = null;
    authState.isAuthenticated = false;
    authState.isLoading = false;
    authState.refreshUser.mockReset();
    jest.mocked(updatePersona).mockReset();
  });

  test("does not read browser storage during server rendering", () => {
    window.localStorage.setItem(
      "quizwerk.persona",
      JSON.stringify({ v: 1, category: "school", userType: "teacher" }),
    );

    const html = renderToString(
      <PersonaProvider>
        <Probe />
      </PersonaProvider>,
    );

    // Server markup must stay neutral even when a browser preference exists.
    // The client only reads storage from useEffect after hydration.
    expect(html).toContain("none");
  });

  test("hydrates a guest persona after mount", async () => {
    window.localStorage.setItem(
      "quizwerk.persona",
      JSON.stringify({ v: 1, category: "school", userType: "teacher" }),
    );

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId("persona")).toHaveTextContent(
        "school:teacher:storage",
      );
    });
  });

  test("does not use guest storage as an authenticated fallback", async () => {
    window.localStorage.setItem(
      "quizwerk.persona",
      JSON.stringify({ v: 1, category: "school", userType: "teacher" }),
    );
    authState.user = {
      id: "user-b",
      username: "b",
      email: "b@example.com",
      is_verified: false,
    };
    authState.isAuthenticated = true;

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId("persona")).toHaveTextContent("none");
    });
  });

  test("does not create local persona state when authenticated persistence fails", async () => {
    authState.user = {
      id: "user-a",
      username: "a",
      email: "a@example.com",
      is_verified: false,
    };
    authState.isAuthenticated = true;
    jest.mocked(updatePersona).mockRejectedValueOnce(new Error("network"));

    renderProvider();

    await act(async () => {
      screen.getByRole("button", { name: "Set teacher" }).click();
    });

    expect(updatePersona).toHaveBeenCalledWith({
      category: "school",
      userType: "teacher",
    });
    expect(window.localStorage.getItem("quizwerk.persona")).toBeNull();
    expect(screen.getByTestId("persona")).toHaveTextContent("none");
  });

  test("clears guest storage after an authenticated session ends", async () => {
    window.localStorage.setItem(
      "quizwerk.persona",
      JSON.stringify({ v: 1, category: "school", userType: "teacher" }),
    );
    authState.user = {
      id: "user-a",
      username: "a",
      email: "a@example.com",
      is_verified: true,
      persona_category: "corporate",
      persona_user_type: "employee",
    };
    authState.isAuthenticated = true;

    const view = renderProvider();
    await waitFor(() => {
      expect(screen.getByTestId("persona")).toHaveTextContent(
        "corporate:employee:profile",
      );
    });

    authState.user = null;
    authState.isAuthenticated = false;
    view.rerender(
      <PersonaProvider>
        <Probe />
      </PersonaProvider>,
    );

    await waitFor(() => {
      expect(window.localStorage.getItem("quizwerk.persona")).toBeNull();
      expect(screen.getByTestId("persona")).toHaveTextContent("none");
    });
  });
});
