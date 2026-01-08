import apiClient from './client';
import type {
  DestinationUsername,
  DestinationHighlight,
  AddDestinationUsernameRequest,
  DestinationUsernamesResponse,
  DestinationHighlightsResponse,
} from '../types/destination';

export const destinationsApi = {
  /**
   * Add a new destination username to track
   */
  addDestination: async (username: string): Promise<DestinationUsername> => {
    const response = await apiClient.post<DestinationUsername>('/destinations/add', {
      username,
    });
    return response.data;
  },

  /**
   * Get all destination usernames for the current user
   */
  listDestinations: async (): Promise<DestinationUsername[]> => {
    const response = await apiClient.get<DestinationUsernamesResponse>('/destinations');
    return response.data.destinations;
  },

  /**
   * Fetch highlights for a destination username from Instagram
   */
  fetchHighlights: async (usernameId: string): Promise<DestinationHighlight[]> => {
    const response = await apiClient.post<DestinationHighlightsResponse>(
      `/destinations/${usernameId}/fetch-highlights`
    );
    return response.data.highlights;
  },

  /**
   * Get cached highlights for a destination username
   */
  getHighlights: async (usernameId: string): Promise<DestinationHighlight[]> => {
    const response = await apiClient.get<DestinationHighlightsResponse>(
      `/destinations/${usernameId}/highlights`
    );
    return response.data.highlights;
  },

  /**
   * Download a destination highlight (creates project + enqueues task)
   */
  downloadHighlight: async (
    usernameId: string,
    highlightId: string
  ): Promise<{ message: string; project_id: string; task_id?: string }> => {
    const response = await apiClient.post(
      `/destinations/${usernameId}/highlights/${highlightId}/download`
    );
    return response.data;
  },

  /**
   * Delete a destination username (cascades to highlights)
   */
  deleteDestination: async (usernameId: string): Promise<void> => {
    await apiClient.delete(`/destinations/${usernameId}`);
  },
};
