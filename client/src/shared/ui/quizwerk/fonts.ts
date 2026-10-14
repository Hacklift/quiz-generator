import { Archivo } from "next/font/google";

/**
 * The one Archivo instance in the app. A second next/font call would
 * double-load the font, so always import this rather than re-declaring it.
 */
export const archivo = Archivo({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});
