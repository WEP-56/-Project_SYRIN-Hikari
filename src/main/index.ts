import { app, BrowserWindow, ipcMain, dialog, shell, screen } from 'electron';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';
import * as fs from 'fs';
import Store from 'electron-store';

// ============================================================================
// Types
// ============================================================================

interface StoreSchema {
  windowBounds: {
    width: number;
    height: number;
    x?: number;
    y?: number;
  };
  apiUrl: string;
  firstRun: boolean;
}

// ============================================================================
// Configuration
// ============================================================================

const store = new Store<StoreSchema>({
  defaults: {
    windowBounds: { width: 1200, height: 800 },
    apiUrl: 'http://127.0.0.1:8888',
    firstRun: true,
  },
});

const API_PORT = 8888;
const API_HOST = '127.0.0.1';

// ============================================================================
// Global State
// ============================================================================

let mainWindow: BrowserWindow | null = null;
let pythonProcess: ChildProcess | null = null;
let isQuitting = false;

// ============================================================================
// Python Server Management
// ============================================================================

function getPythonPath(): string {
  // In production, use bundled Python
  if (app.isPackaged) {
    const pythonExe = path.join(process.resourcesPath, 'python-server', 'python-embed', 'python.exe');
    if (fs.existsSync(pythonExe)) {
      return pythonExe;
    }
  }
  
  // Development: use system Python
  return 'python';
}

function getServerScriptPath(): string {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'python-server', 'api_server.py');
  }
  return path.join(__dirname, '..', '..', 'python-server', 'api_server.py');
}

function startPythonServer(): Promise<void> {
  return new Promise((resolve, reject) => {
    const pythonPath = getPythonPath();
    const scriptPath = getServerScriptPath();
    
    console.log('Starting Python server...');
    console.log(`Python: ${pythonPath}`);
    console.log(`Script: ${scriptPath}`);
    
    if (!fs.existsSync(scriptPath)) {
      // 如果没有找到脚本，可能是因为 Python 环境问题，尝试直接 reject
      // 但在开发环境，我们可能不应该这么快失败
      reject(new Error(`Server script not found: ${scriptPath}`));
      return;
    }
    
    // Environment variables
    const env = {
      ...process.env,
      YANDERE_PORT: API_PORT.toString(),
      YANDERE_HOST: API_HOST,
      PYTHONPATH: app.isPackaged 
        ? path.join(process.resourcesPath, 'python-server')
        : path.join(__dirname, '..', '..', 'python-server'),
    };
    
    // Start Python process
    try {
        pythonProcess = spawn(pythonPath, [scriptPath], {
          env,
          detached: false,
          stdio: ['ignore', 'pipe', 'pipe'],
        });
    } catch (e: any) {
        if (e.code === 'ENOENT') {
            reject(new Error(`无法启动后端服务: spawn ${pythonPath} ENOENT\n\n请确保已安装 Python 和必要的依赖。`));
            return;
        }
        reject(e);
        return;
    }
    
    let serverReady = false;
    let output = '';
    
    // Handle stdout
    pythonProcess.stdout?.on('data', (data) => {
      const text = data.toString();
      output += text;
      console.log(`[Python] ${text.trim()}`);
      
      checkServerReady(text);
    });
    
    // Handle stderr (loguru outputs to stderr)
    pythonProcess.stderr?.on('data', (data) => {
      const text = data.toString();
      output += text;
      console.error(`[Python Error] ${text.trim()}`);
      
      // loguru outputs logs to stderr, so check here too
      checkServerReady(text);
    });
    
    // Check if server is ready
    function checkServerReady(text: string) {
      if (!serverReady && (text.includes('Uvicorn running') || text.includes('Application startup complete'))) {
        serverReady = true;
        console.log('Python server is ready!');
        setTimeout(resolve, 1000); // Give it a moment to fully start
      }
    }
    
    // Handle process exit
    pythonProcess.on('exit', (code) => {
      console.log(`Python server exited with code ${code}`);
      pythonProcess = null;
      
      if (!serverReady && !isQuitting) {
        reject(new Error(`Python server exited unexpectedly: ${output}`));
      }
    });
    
    pythonProcess.on('error', (err: any) => {
      console.error('Failed to start Python server:', err);
      if (err.code === 'ENOENT') {
         reject(new Error(`无法启动后端服务: spawn ${pythonPath} ENOENT\n\n请确保已安装 Python 和必要的依赖。`));
      } else {
         reject(err);
      }
    });
    
    // HTTP health check as backup detection method
    const checkHttpHealth = () => {
      if (serverReady) return;
      
      const http = require('http');
      const req = http.get(`http://${API_HOST}:${API_PORT}/`, (res: any) => {
        if (res.statusCode === 200 && !serverReady) {
          serverReady = true;
          console.log('Python server detected via HTTP health check!');
          setTimeout(resolve, 500);
        }
      }).on('error', () => {
        // Ignore errors, just retry
      });
      
      req.setTimeout(2000, () => {
        req.destroy();
      });
    };
    
    // Try HTTP health check every 500ms
    const healthCheckInterval = setInterval(() => {
      if (serverReady) {
        clearInterval(healthCheckInterval);
      } else {
        checkHttpHealth();
      }
    }, 500);
    
    // Timeout
    setTimeout(() => {
      clearInterval(healthCheckInterval);
      if (!serverReady) {
        reject(new Error('Timeout waiting for Python server to start'));
      }
    }, 30000);
  });
}

function stopPythonServer(): Promise<void> {
  return new Promise((resolve) => {
    if (!pythonProcess) {
      resolve();
      return;
    }
    
    console.log('Stopping Python server...');
    
    // Kill the process
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', pythonProcess.pid!.toString(), '/f', '/t']);
    } else {
      pythonProcess.kill('SIGTERM');
    }
    
    // Force kill after timeout
    setTimeout(() => {
      if (pythonProcess && !pythonProcess.killed) {
        pythonProcess.kill('SIGKILL');
      }
      resolve();
    }, 5000);
  });
}

// ============================================================================
// Window Management
// ============================================================================

function createWindow(): void {
  const bounds = store.get('windowBounds');
  
  mainWindow = new BrowserWindow({
    x: bounds.x,
    y: bounds.y,
    width: bounds.width,
    height: bounds.height,
    minWidth: 900,
    minHeight: 600,
    show: false,
    title: 'Hikari',
    autoHideMenuBar: true,
    frame: false, // Frameless for custom titlebar
    transparent: true, // Transparent for rounded corners
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,
    },
  });

  mainWindow.webContents.openDevTools(); // Force open DevTools for debugging

  // Load content
  if (app.isPackaged) {
    mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
  } else {
    mainWindow.loadURL('http://localhost:5173');
  }
  
  // Window events
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
    
    if (store.get('firstRun')) {
      store.set('firstRun', false);
      // Show welcome dialog or tutorial
    }
  });

  // Fix for transparency issue on Windows where background becomes opaque on blur
  mainWindow.on('blur', () => {
    mainWindow?.setBackgroundColor('#00000000');
  });

  mainWindow.on('focus', () => {
    mainWindow?.setBackgroundColor('#00000000');
  });
  
  mainWindow.on('close', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      const bounds = mainWindow.getBounds();
      store.set('windowBounds', bounds);
    }
  });
  
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
  
  // Open external links in browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// ============================================================================
// IPC Handlers
// ============================================================================

ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

ipcMain.handle('get-api-url', () => {
  return `http://${API_HOST}:${API_PORT}`;
});

ipcMain.handle('get-store-value', (_, key: keyof StoreSchema) => {
  return store.get(key);
});

ipcMain.handle('set-store-value', (_, key: keyof StoreSchema, value: any) => {
  store.set(key, value);
});

ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openDirectory'],
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('show-save-dialog', async (_, options) => {
  const result = await dialog.showSaveDialog(mainWindow!, options);
  return result.canceled ? null : result.filePath;
});

ipcMain.handle('restart-server', async () => {
  try {
    await stopPythonServer();
    await startPythonServer();
    return { success: true };
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }
});

// Window Management Handlers

ipcMain.handle('set-ignore-mouse-events', (_, ignore: boolean, options?: { forward: boolean }) => {
  if (mainWindow) {
    mainWindow.setIgnoreMouseEvents(ignore, options);
  }
});

ipcMain.handle('minimize-window', () => {
  mainWindow?.minimize();
});

ipcMain.handle('close-window', () => {
  mainWindow?.close();
});

// ============================================================================
// App Lifecycle
// ============================================================================

app.whenReady().then(async () => {
  console.log('App is ready');
  
  try {
    // Start Python server first
    await startPythonServer();
    console.log('Python server started successfully');
    
    // Then create window
    createWindow();
    
  } catch (error) {
    console.error('Failed to start:', error);
    dialog.showErrorBox(
      '启动失败',
      `无法启动后端服务：${(error as Error).message}\n\n请确保已安装 Python 和必要的依赖。`
    );
    app.quit();
  }
});

app.on('window-all-closed', async () => {
  if (process.platform !== 'darwin') {
    isQuitting = true;
    await stopPythonServer();
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', async (event) => {
  if (!isQuitting) {
    isQuitting = true;
    event.preventDefault();
    await stopPythonServer();
    app.quit();
  }
});

// Security: prevent new window creation
app.on('web-contents-created', (_, contents) => {
  contents.setWindowOpenHandler(({ url }) => {
    // Prevent any new window from opening
    return { action: 'deny' };
  });
});
