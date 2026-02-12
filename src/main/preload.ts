import { contextBridge, ipcRenderer } from 'electron';

// ============================================================================
// Exposed API for Renderer Process
// ============================================================================

export interface ElectronAPI {
  // App info
  getAppVersion: () => Promise<string>;
  getApiUrl: () => Promise<string>;
  
  // Store
  getStoreValue: (key: string) => Promise<any>;
  setStoreValue: (key: string, value: any) => Promise<void>;
  
  // Dialogs
  selectDirectory: () => Promise<string | null>;
  showSaveDialog: (options: any) => Promise<string | null>;
  
  // Server management
  restartServer: () => Promise<{ success: boolean; error?: string }>;

  // Window Management
  setWindowMode: (mode: 'normal' | 'mini') => Promise<void>;
  setIgnoreMouseEvents: (ignore: boolean, options?: { forward: boolean }) => Promise<void>;
  minimizeWindow: () => Promise<void>;
  closeWindow: () => Promise<void>;
}

const api: ElectronAPI = {
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  getApiUrl: () => ipcRenderer.invoke('get-api-url'),
  getStoreValue: (key: string) => ipcRenderer.invoke('get-store-value', key),
  setStoreValue: (key: string, value: any) => ipcRenderer.invoke('set-store-value', key, value),
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  showSaveDialog: (options: any) => ipcRenderer.invoke('show-save-dialog', options),
  restartServer: () => ipcRenderer.invoke('restart-server'),
  
  // Window Management
  setWindowMode: (mode) => ipcRenderer.invoke('set-window-mode', mode),
  setIgnoreMouseEvents: (ignore, options) => ipcRenderer.invoke('set-ignore-mouse-events', ignore, options),
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),
};

contextBridge.exposeInMainWorld('electronAPI', api);

// Type declaration for TypeScript
declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}
