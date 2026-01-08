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
  // v2 fields
  video_urls?: string;  // JSON string array
  photo_urls?: string;  // JSON string array
  merged_video_url?: string | null;
  zip_bundle_url?: string | null;
  expires_at?: string | null;
  is_expired?: number;  // 0 or 1
  submission_date?: string | null;
}

export interface HighlightProjectsResponse {
  projects: HighlightProjectResponse[];
}

export interface TaskStartedResponse {
  message: string;
  task_id?: string | null;
}

export type DownloadStatus = 'pending' | 'downloading' | 'downloaded' | 'failed';
export type ExportStatus = 'pending' | 'building' | 'exported' | 'failed';
