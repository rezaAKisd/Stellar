export interface DestinationUsername {
  id: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
  last_fetched_at: string | null;
  created_at: string;
}

export interface DestinationHighlight {
  id: string;
  highlight_id: string;
  name: string;
  cover_url: string | null;
  item_count: number;
  project_id: string | null;
}

export interface AddDestinationUsernameRequest {
  username: string;
}

export interface DestinationUsernamesResponse {
  destinations: DestinationUsername[];
}

export interface DestinationHighlightsResponse {
  highlights: DestinationHighlight[];
}
