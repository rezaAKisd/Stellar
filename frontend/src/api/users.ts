import apiClient from './client';
import {
  AddUserRequest,
  UserProfileResponse,
  UsersResponse,
  UserHighlightsResponse,
} from '../types/user';
import { TaskStartedResponse } from '../types/highlight';
import { MessageResponse } from '../types/auth';

export const usersApi = {
  /**
   * Add a new user to track
   */
  addUser: async (data: AddUserRequest): Promise<UserProfileResponse> => {
    const response = await apiClient.post<UserProfileResponse>('/users/add', data);
    return response.data;
  },

  /**
   * Get all tracked users
   */
  getUsers: async (): Promise<UsersResponse> => {
    const response = await apiClient.get<UsersResponse>('/users');
    return response.data;
  },

  /**
   * Get user highlights
   */
  getUserHighlights: async (username: string): Promise<UserHighlightsResponse> => {
    const response = await apiClient.get<UserHighlightsResponse>(
      `/users/${username}/highlights`
    );
    return response.data;
  },

  /**
   * Download user highlight
   */
  downloadUserHighlight: async (
    username: string,
    highlightId: string
  ): Promise<TaskStartedResponse> => {
    const response = await apiClient.post<TaskStartedResponse>(
      `/users/${username}/highlights/${highlightId}/download`
    );
    return response.data;
  },

  /**
   * Delete a tracked user
   */
  deleteUser: async (userId: string): Promise<MessageResponse> => {
    const response = await apiClient.delete<MessageResponse>(`/users/${userId}`);
    return response.data;
  },
};
