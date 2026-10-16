import "@testing-library/jest-dom";
import "@features/locale/i18n";
import { TextDecoder, TextEncoder } from "util";

Object.assign(global, { TextDecoder, TextEncoder });
