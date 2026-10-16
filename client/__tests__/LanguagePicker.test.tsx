import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { hydrateRoot, type Root } from "react-dom/client";
import LanguagePicker from "@features/locale/components/LanguagePicker";
import { LANGUAGES, languageDirection } from "@shared/config/locale";

test("independent users can search all registered languages by name and code", () => {
  const choose = jest.fn();
  render(<LanguagePicker value="en" onChange={choose} />);
  const list = screen.getByRole("listbox", { name: "Language" });
  expect(LANGUAGES.length).toBeGreaterThan(7000);
  expect(list.querySelectorAll("option").length).toBeLessThanOrEqual(101);
  expect(
    screen.queryByText("Use organization default"),
  ).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "Yoruba" },
  });
  expect(list.querySelector('option[value="yo"]')).toBeInTheDocument();
  expect(list.querySelector('option[value="fr"]')).not.toBeInTheDocument();
  fireEvent.change(list, { target: { value: "yo" } });
  expect(choose).toHaveBeenCalledWith("yo");
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "français" },
  });
  expect(list.querySelector('option[value="fr"]')).toBeInTheDocument();
});

test("organization inheritance is an explicit opt-in option only for eligible users", () => {
  const choose = jest.fn();
  render(
    <LanguagePicker value={null} onChange={choose} allowOrganizationDefault />,
  );
  const list = screen.getByRole("listbox");
  expect(list).toHaveValue("inherit");
  fireEvent.change(list, { target: { value: "es" } });
  fireEvent.change(list, { target: { value: "inherit" } });
  expect(choose).toHaveBeenLastCalledWith(null);
});

test("right-to-left languages set the appropriate direction", () => {
  expect(languageDirection("ar")).toBe("rtl");
  expect(languageDirection("fr")).toBe("ltr");
});

test.each(["different names", "missing language data"])(
  "hydrates safely when browser Intl has %s compared with the server",
  async (scenario) => {
    const displayNames = jest.spyOn(Intl, "DisplayNames");
    const errors = jest.spyOn(console, "error").mockImplementation(() => {});
    const recoverableError = jest.fn();
    const container = document.createElement("div");
    document.body.appendChild(container);
    let root: Root | undefined;
    const namesResult = (name: string): Intl.DisplayNames => ({
      of: () => name,
      resolvedOptions: () => ({
        locale: "en",
        style: "long",
        type: "language",
        fallback: "none",
        languageDisplay: "dialect",
      }),
    });
    try {
      displayNames.mockImplementation(() => namesResult("Server name"));
      const picker = <LanguagePicker value="ab" onChange={jest.fn()} />;
      container.innerHTML = renderToString(picker);
      expect(container.querySelector('option[value="ab"]')).toHaveTextContent(
        "Abkhazian (ab)",
      );
      expect(displayNames).not.toHaveBeenCalled();

      displayNames.mockImplementation(() => {
        if (scenario === "missing language data")
          throw new RangeError("Unsupported locale");
        return namesResult("Browser name");
      });
      await act(async () => {
        root = hydrateRoot(container, picker, {
          onRecoverableError: recoverableError,
        });
      });
      expect(displayNames).toHaveBeenCalled();
      expect(container.querySelector('option[value="ab"]')).toHaveTextContent(
        scenario === "different names"
          ? "Browser name · Abkhazian (ab)"
          : "Abkhazian (ab)",
      );
      expect(container.querySelector("select")).toHaveValue("ab");
      expect(recoverableError).not.toHaveBeenCalled();
      expect(errors).not.toHaveBeenCalled();
    } finally {
      if (root) act(() => root!.unmount());
      container.remove();
      displayNames.mockRestore();
      errors.mockRestore();
    }
  },
);
