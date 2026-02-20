import WebApp from "@twa-dev/sdk";

export function useTelegram() {
  return {
    tg: WebApp,
    user: WebApp.initDataUnsafe?.user,
    initData: WebApp.initData,
    colorScheme: WebApp.colorScheme,
    themeParams: WebApp.themeParams,
    close: () => WebApp.close(),
    ready: () => WebApp.ready(),
    expand: () => WebApp.expand(),
    haptic: WebApp.HapticFeedback,
  };
}
