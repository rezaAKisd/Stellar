import apiClient from './client';
import {
  AddLinkRequest,
  HighlightProjectResponse,
  HighlightProjectsResponse,
  TaskStartedResponse,
} from '../types/highlight';
import { MessageResponse } from '../types/auth';

export const highlightsApi = {
  /**
   * Add a new highlight by URL
   */
  addLink: async (data: AddLinkRequest): Promise<HighlightProjectResponse> => {
    const response = await apiClient.post<HighlightProjectResponse>('/highlights/add-link', data);
    return response.data;
  },

  /**
   * Get all highlight projects
   */
  getProjects: async (): Promise<HighlightProjectsResponse> => {
    const response = await apiClient.get<HighlightProjectsResponse>('/highlights/projects');
    return response.data;
  },

  /**
   * Get project status
   */
  getProjectStatus: async (projectId: string): Promise<HighlightProjectResponse> => {
    const response = await apiClient.get<HighlightProjectResponse>(
      `/highlights/${projectId}/status`
    );
    return response.data;
  },

  /**
   * Start downloading highlight
   */
  downloadHighlight: async (projectId: string): Promise<TaskStartedResponse> => {
    const response = await apiClient.post<TaskStartedResponse>(
      `/highlights/${projectId}/download`
    );
    return response.data;
  },

  /**
   * Start building video from highlight
   */
  buildVideo: async (projectId: string): Promise<TaskStartedResponse> => {
    const response = await apiClient.post<TaskStartedResponse>(
      `/highlights/${projectId}/build-video`
    );
    return response.data;
  },

  /**
   * Delete a project
   */
  deleteProject: async (projectId: string): Promise<MessageResponse> => {
    const response = await apiClient.delete<MessageResponse>(`/highlights/${projectId}`);
    return response.data;
  },
};
