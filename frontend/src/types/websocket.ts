export type ProgressMessageType =
  | 'connected'
  | 'download_progress'
  | 'export_progress'
  | 'zip_progress'
  | 'task_complete'
  | 'error'
  | 'pong';

export interface ProgressMessage {
  type: ProgressMessageType;
  project_id?: string;
  progress?: number;
  status?: string;
  message?: string;
  task_id?: string;
  task_type?: 'download' | 'build' | 'create_zip';
}

export interface WebSocketContextType {
  isConnected: boolean;
  subscribe: (projectId: string, callback: (message: ProgressMessage) => void) => () => void;
  send: (data: string) => void;
}
