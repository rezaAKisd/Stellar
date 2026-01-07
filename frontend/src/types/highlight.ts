export interface AddLinkRequest {
  url: string;
}

export interface HighlightProjectResponse {
  id: string;
  title: string;
  source: string;
  folder_path: string;
  item_count: number;
  download_status: string;
  export_status: string;
  download_progress: number;
  export_progress: number;
  error_message: string | null;
  has_downloads: boolean;
  has_exports: boolean;
}

export interface HighlightProjectsResponse {
  projects: HighlightProjectResponse[];
}

export interface TaskStartedResponse {
  message: string;
  task_id: string;
}

export type DownloadStatus = 'pending' | 'downloading' | 'downloaded' | 'failed';
export type ExportStatus = 'pending' | 'building' | 'exported' | 'failed';
