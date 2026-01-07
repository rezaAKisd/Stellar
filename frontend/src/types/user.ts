export interface AddUserRequest {
  username: string;
}

export interface UserHighlightResponse {
  id: string;
  name: string;
  cover_url: string;
  item_count: number;
  highlight_id: string;
  project_id: string | null;
}

export interface UserProfileResponse {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string;
  highlights: UserHighlightResponse[];
}

export interface UsersResponse {
  users: UserProfileResponse[];
}

export interface UserHighlightsResponse {
  highlights: UserHighlightResponse[];
}
