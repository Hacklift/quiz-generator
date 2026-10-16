import { createLocaleI18n } from "@features/locale/i18n";
import { loadLanguageCatalogs } from "@features/locale/catalogClient";
import en from "@features/locale/messages/ui.en.json";
import { api } from "@shared/api/http";

jest.mock("@shared/api/http", () => ({
  API_BASE_URL: "https://api.example.test",
  api: { post: jest.fn() },
}));
beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();
});

test.each(["es", "fr"])(
  "%s provides every registered UI message without a server or LLM",
  async (locale) => {
    global.fetch = jest.fn().mockRejectedValue(new Error("offline"));
    const instance = createLocaleI18n();
    await instance.changeLanguage(locale);
    const status = jest.fn();
    await loadLanguageCatalogs(
      instance,
      locale,
      true,
      new AbortController().signal,
      status,
    );
    const messageKeys = (
      messages: Record<string, unknown>,
      prefix = "",
    ): string[] =>
      Object.entries(messages).flatMap(([key, value]) => {
        const id = prefix ? `${prefix}.${key}` : key;
        return typeof value === "string"
          ? [id]
          : messageKeys(value as Record<string, unknown>, id);
      });
    for (const key of messageKeys(en)) {
      expect(instance.getResource(locale, "ui", key)).toEqual(
        expect.any(String),
      );
    }
    expect(instance.t("nav.home")).toBe(locale === "es" ? "Inicio" : "Accueil");
    expect(status).toHaveBeenLastCalledWith("ready");
    expect(api.post).not.toHaveBeenCalled();
  },
);

test("new languages load missing registered keys from the authenticated gateway and cache results", async () => {
  global.fetch = jest.fn(async (url: string | URL | Request) => {
    const namespace = String(url).split("/").pop()!;
    return {
      ok: true,
      json: async () => ({
        locale: "de",
        namespace,
        version: "v1",
        messages: {},
        missing: namespace === "translation" ? ["language.settings"] : [],
      }),
    } as Response;
  });
  (api.post as jest.Mock).mockResolvedValue({
    data: {
      locale: "de",
      namespace: "translation",
      version: "v1",
      messages: { "language.settings": "Sprache" },
      missing: [],
    },
  });
  const instance = createLocaleI18n();
  const status = jest.fn();
  await loadLanguageCatalogs(
    instance,
    "de",
    true,
    new AbortController().signal,
    status,
  );
  await instance.changeLanguage("de");
  expect(instance.t("language.settings")).toBe("Sprache");
  expect(api.post).toHaveBeenCalledWith(
    "/api/i18n/catalogs/de/translation",
    { keys: ["language.settings"] },
    expect.any(Object),
  );
  expect(localStorage.getItem("quizwerk.catalog.de.translation")).toContain(
    "Sprache",
  );
  global.fetch = jest.fn().mockRejectedValue(new Error("offline"));
  const offline = createLocaleI18n();
  await loadLanguageCatalogs(
    offline,
    "de",
    true,
    new AbortController().signal,
    status,
  );
  await offline.changeLanguage("de");
  expect(offline.t("language.settings")).toBe("Sprache");
  expect(status).toHaveBeenLastCalledWith("ready");
});

test("an aborted language switch never installs late responses", async () => {
  const controller = new AbortController();
  global.fetch = jest.fn(async () => {
    controller.abort();
    return {
      ok: true,
      json: async () => ({
        locale: "de",
        namespace: "translation",
        version: "v1",
        messages: { "language.settings": "Sprache" },
        missing: [],
      }),
    } as Response;
  });
  const instance = createLocaleI18n();
  await loadLanguageCatalogs(
    instance,
    "de",
    true,
    controller.signal,
    jest.fn(),
  );
  expect(
    instance.getResource("de", "translation", "language.settings"),
  ).toBeUndefined();
});
