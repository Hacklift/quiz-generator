import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ProfilePage from "@features/profile/pages/ProfilePage";

const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockLogout = jest.fn();
const mockRefreshUser = jest.fn();
const mockUpdateProfile = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    isReady: true,
    query: {},
  }),
}));

const mockUser = {
  id: "u123",
  username: "testteacher",
  email: "teacher@school.edu",
  full_name: "Alex Teacher",
  bio: "Teaching biology and natural sciences.",
  location: "London, UK",
  website: "https://school.edu/alex",
  avatar_color: "#143E6F",
  is_verified: true,
  subscription_plan: "free",
  subscription_status: "active",
};

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({
    user: mockUser,
    isLoading: false,
    logout: mockLogout,
    refreshUser: mockRefreshUser,
  }),
}));

jest.mock("@features/persona/context/personaContext", () => ({
  usePersona: () => ({
    persona: { category: "school", userType: "teacher" },
    definition: {
      slug: "teacher",
      category: "school",
      label: "Teacher",
      description: "Class quizzes, homework checks, exam revision",
      defaultTopic: "Photosynthesis — Grade 8 biology",
      generationDefaults: {
        audienceType: "students",
        difficultyLevel: "medium",
        numQuestions: 10,
        questionType: "multichoice",
      },
    },
    categoryDefinition: {
      slug: "school",
      label: "School",
      description: "Teachers, lecturers, students and parents.",
    },
  }),
}));

jest.mock("@features/auth/api/authApi", () => ({
  updateProfile: (...args: any[]) => mockUpdateProfile(...args),
  requestEmailChange: jest.fn(),
  verifyEmailChange: jest.fn(),
  deleteAccount: jest.fn(),
}));

jest.mock("@features/profile/api/billingApi", () => ({
  createPortalSession: jest.fn().mockResolvedValue({ portal_url: "https://stripe.com/portal" }),
  getBillingErrorMessage: (_err: any, fallback: string) => fallback,
  getSubscriptionSummary: jest.fn(),
}));

jest.mock("@features/quiz/components/NavBar", () => () => <header data-testid="mock-navbar" />);
jest.mock("@features/quiz/components/Footer", () => () => <footer data-testid="mock-footer" />);
jest.mock("@features/auth/components/RequireAuth", () => ({ children }: { children: React.ReactNode }) => (
  <div>{children}</div>
));
jest.mock("@features/persona/components/PersonaPicker", () => () => (
  <div data-testid="mock-persona-picker">Mock Persona Picker</div>
));

describe("ProfilePage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders profile hero header with user details and verified badge", () => {
    render(<ProfilePage />);

    expect(screen.getByRole("heading", { name: "Profile Settings" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Alex Teacher" })).toBeInTheDocument();
    expect(screen.getAllByText(/@testteacher/).length).toBeGreaterThan(0);
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText(/School · Teacher/)).toBeInTheDocument();
  });

  test("renders all 4 navigation tabs", () => {
    render(<ProfilePage />);

    expect(screen.getByRole("button", { name: /overview & details/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /role & persona/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /subscription & billing/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /security & account/i })).toBeInTheDocument();
  });

  test("switches between tabs cleanly", () => {
    render(<ProfilePage />);

    // Switch to Role & Persona tab
    const personaTab = screen.getByRole("button", { name: /role & persona/i });
    fireEvent.click(personaTab);

    expect(
      screen.getByRole("heading", { name: "Role & Persona Configuration" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("mock-persona-picker")).toBeInTheDocument();

    // Switch to Subscription & Billing tab
    const billingTab = screen.getByRole("button", { name: /subscription & billing/i });
    fireEvent.click(billingTab);

    expect(
      screen.getByRole("heading", { name: "Subscription & Billing" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Free Plan/i).length).toBeGreaterThan(0);

    // Switch to Security & Account tab
    const securityTab = screen.getByRole("button", { name: /security & account/i });
    fireEvent.click(securityTab);

    expect(
      screen.getByRole("heading", { name: "Security & Credentials" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Danger Zone: Delete Account")).toBeInTheDocument();
  });

  test("allows toggling edit mode and saving updated profile details", async () => {
    mockUpdateProfile.mockResolvedValueOnce({ success: true });

    render(<ProfilePage />);

    // Click Edit Profile button
    const editBtn = screen.getByRole("button", { name: /edit profile/i });
    fireEvent.click(editBtn);

    // Edit full name
    const fullNameInput = screen.getByPlaceholderText("e.g. Dr. Alex Morgan");
    expect(fullNameInput).toHaveValue("Alex Teacher");

    fireEvent.change(fullNameInput, { target: { value: "Dr. Alex Teacher" } });

    // Submit save
    const saveBtn = screen.getByRole("button", { name: /save changes/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(mockUpdateProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          full_name: "Dr. Alex Teacher",
        }),
      );
    });
  });
});
