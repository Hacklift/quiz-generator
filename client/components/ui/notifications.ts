import { toast, ToastOptions } from "react-hot-toast";

const defaultOptions: ToastOptions = {
  duration: 5000,
  position: "top-right",
};

export const notify = {
  success: (msg: string, options?: ToastOptions) =>
    toast.success(msg, { ...defaultOptions, ...options }),

  error: (msg: string, options?: ToastOptions) =>
    toast.error(msg, { ...defaultOptions, ...options }),

  info: (msg: string, options?: ToastOptions) =>
    toast(msg, { ...defaultOptions, ...options }),

  custom: (msg: string, options?: ToastOptions) =>
    toast(msg, { ...defaultOptions, ...options }),
};
