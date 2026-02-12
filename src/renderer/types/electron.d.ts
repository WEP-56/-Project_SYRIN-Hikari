export interface ElectronAPI {
  minimizeWindow: () => Promise<void>;
  closeWindow: () => Promise<void>;
  getAppVersion: () => Promise<string>;
  getApiUrl: () => Promise<string>;
  getStoreValue: (key: string) => Promise<any>;
  setStoreValue: (key: string, value: any) => Promise<void>;
  selectDirectory: () => Promise<string | null>;
  showSaveDialog: (options: any) => Promise<string | null>;
  restartServer: () => Promise<{ success: boolean; error?: string }>;
  setIgnoreMouseEvents: (ignore: boolean, options?: { forward: boolean }) => Promise<void>;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}
